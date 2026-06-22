from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


_BASE = "https://www.alphavantage.co/query"
_PERIOD_TO_DAYS: Dict[str, int] = {
    "5d": 5, "10d": 10, "1mo": 22, "3mo": 65, "6mo": 130, "1y": 252, "2y": 504,
}

_TTL_OVERVIEW = 86400.0   # OVERVIEW: 24 h
_TTL_QUOTE    = 300.0     # GLOBAL_QUOTE: 5 min
_TTL_SERIES   = 3600.0    # TIME_SERIES_DAILY: 1 h

# Disk cache survives server restarts — lives next to this file
_CACHE_FILE = Path(__file__).parent / ".av_cache.json"

# In-memory layer loaded from disk at import time
_CACHE: Dict[str, Tuple[float, Any]] = {}


def _load_cache() -> None:
    if _CACHE_FILE.exists():
        try:
            raw = json.loads(_CACHE_FILE.read_text())
            now = time.time()
            for k, (ts, data) in raw.items():
                _CACHE[k] = (float(ts), data)
            # Evict obviously stale OVERVIEW entries (>48 h) to keep file small
            stale = [k for k, (ts, _) in _CACHE.items() if now - ts > 172800]
            for k in stale:
                del _CACHE[k]
        except Exception:
            pass


def _save_cache() -> None:
    try:
        _CACHE_FILE.write_text(json.dumps({k: list(v) for k, v in _CACHE.items()}))
    except Exception:
        pass


_load_cache()   # populate from disk on module import


def _api_key() -> str:
    return os.getenv("ALPHA_VANTAGE_API_KEY", "demo")


def _get(params: Dict[str, str], ttl: float = 0.0) -> Dict[str, Any]:
    cache_key = str(sorted(params.items()))
    now = time.time()
    if ttl > 0 and cache_key in _CACHE:
        ts, cached = _CACHE[cache_key]
        if now - ts < ttl:
            return cached

    p = dict(params)
    p["apikey"] = _api_key()
    r = requests.get(_BASE, params=p, timeout=20)
    r.raise_for_status()
    data = r.json()

    if "Note" in data:
        print(f"[AV] rate-limit note: {data['Note']}", file=sys.stderr)
        raise RuntimeError("Alpha Vantage rate limit")
    if "Information" in data:
        print(f"[AV] quota exceeded: {data['Information'][:120]}", file=sys.stderr)
        raise RuntimeError("Alpha Vantage quota exceeded")
    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage error: {data['Error Message']}")

    if ttl > 0:
        _CACHE[cache_key] = (now, data)
        _save_cache()   # persist immediately after every successful fetch
    return data


def _to_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return None if f == 0 else f
    except (TypeError, ValueError):
        return None


def fetch_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> List[Dict[str, Any]]:
    n_days = _PERIOD_TO_DAYS.get(period, 130)

    if interval == "1d":
        output_size = "full" if n_days > 100 else "compact"
        data = _get(
            {"function": "TIME_SERIES_DAILY", "symbol": ticker, "outputsize": output_size},
            ttl=_TTL_SERIES,
        )
        ts = data.get("Time Series (Daily)", {})
        records = []
        for date_str in sorted(ts.keys()):
            v = ts[date_str]
            records.append({
                "timestamp": date_str,
                "open":   float(v.get("1. open",  0)),
                "high":   float(v.get("2. high",  0)),
                "low":    float(v.get("3. low",   0)),
                "close":  float(v.get("4. close", 0)),
                "volume": float(v.get("5. volume", 0)),
            })
        return records[-n_days:] if records else []

    # Intraday
    av_interval = "60min" if interval in ("1h", "60m") else "30min"
    data = _get(
        {"function": "TIME_SERIES_INTRADAY", "symbol": ticker,
         "interval": av_interval, "outputsize": "compact"},
        ttl=_TTL_SERIES,
    )
    ts = data.get(f"Time Series ({av_interval})", {})
    records = []
    for dt_str in sorted(ts.keys()):
        v = ts[dt_str]
        records.append({
            "timestamp": dt_str,
            "open":   float(v.get("1. open",  0)),
            "high":   float(v.get("2. high",  0)),
            "low":    float(v.get("3. low",   0)),
            "close":  float(v.get("4. close", 0)),
            "volume": float(v.get("5. volume", 0)),
        })
    return records


def fetch_company_info(ticker: str, price_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"symbol": ticker.upper()}

    # ── Seed basic OHLCV from price history so stats show even if API is down ─
    if price_history:
        last  = price_history[-1]
        prev  = price_history[-2] if len(price_history) >= 2 else {}
        out["open"]    = last.get("open")
        out["dayHigh"] = last.get("high")
        out["dayLow"]  = last.get("low")
        out["regularMarketVolume"] = last.get("volume")
        out["currentPrice"] = last.get("close")
        if prev.get("close"):
            out["previousClose"] = prev["close"]
            out["priceChange"]    = round(last["close"] - prev["close"], 4)
            out["priceChangePct"] = round((last["close"] / prev["close"] - 1) * 100, 4)
        # 52-week high/low from the full history passed in
        closes = [r["close"] for r in price_history if r.get("close")]
        highs  = [r["high"]  for r in price_history if r.get("high")]
        lows   = [r["low"]   for r in price_history if r.get("low")]
        if highs:
            out["fiftyTwoWeekHigh"] = max(highs)
        if lows:
            out["fiftyTwoWeekLow"]  = min(lows)

    # ── Real-time quote (best-effort, overrides history values if available) ──
    try:
        gq = _get(
            {"function": "GLOBAL_QUOTE", "symbol": ticker}, ttl=_TTL_QUOTE
        ).get("Global Quote", {})
        field_map = {
            "currentPrice":        ("05. price",           float),
            "open":                ("02. open",             float),
            "dayHigh":             ("03. high",             float),
            "dayLow":              ("04. low",              float),
            "regularMarketVolume": ("06. volume",           float),
            "previousClose":       ("08. previous close",  float),
            "priceChange":         ("09. change",           float),
        }
        for key, (av_k, cast) in field_map.items():
            val = gq.get(av_k)
            if val:
                try:
                    out[key] = cast(val)
                except (ValueError, TypeError):
                    pass
        pct_str = gq.get("10. change percent", "").replace("%", "")
        if pct_str:
            try:
                out["priceChangePct"] = float(pct_str)
            except ValueError:
                pass
    except Exception as e:
        print(f"[AV] GLOBAL_QUOTE failed for {ticker}: {e}", file=sys.stderr)

    # ── Company overview (cached 24 h — only burns 1 daily quota per ticker) ──
    try:
        time.sleep(0.25)   # brief pause to stay under 5 req/min
        ov = _get({"function": "OVERVIEW", "symbol": ticker}, ttl=_TTL_OVERVIEW)
        str_keys = {
            "Name":        "longName",
            "Exchange":    "exchange",
            "Currency":    "currency",
            "Sector":      "sector",
            "Industry":    "industry",
            "Description": "longBusinessSummary",
        }
        num_keys = {
            "MarketCapitalization":  "marketCap",
            "PERatio":               "trailingPE",
            "ForwardPE":             "forwardPE",
            "EPS":                   "trailingEps",
            "BookValue":             "priceToBook",
            "DividendYield":         "dividendYield",
            "Beta":                  "beta",
            "52WeekHigh":            "fiftyTwoWeekHigh",
            "52WeekLow":             "fiftyTwoWeekLow",
            "50DayMovingAverage":    "fiftyDayAverage",
            "200DayMovingAverage":   "twoHundredDayAverage",
            "ProfitMargin":          "profitMargins",
            "OperatingMarginTTM":    "operatingMargins",
            "ReturnOnEquityTTM":     "returnOnEquity",
            "ReturnOnAssetsTTM":     "returnOnAssets",
            "FullTimeEmployees":     "fullTimeEmployees",
            "AnalystTargetPrice":    "targetMeanPrice",
        }
        for av_k, out_k in str_keys.items():
            v = ov.get(av_k)
            if v and v not in ("None", "-", ""):
                out[out_k] = v
        for av_k, out_k in num_keys.items():
            v = _to_float(ov.get(av_k))
            if v is not None:
                out[out_k] = v
    except Exception as e:
        print(f"[AV] OVERVIEW failed for {ticker}: {e}", file=sys.stderr)

    return out
