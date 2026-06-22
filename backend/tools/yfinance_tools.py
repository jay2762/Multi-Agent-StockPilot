from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf


def _flatten(hist: pd.DataFrame) -> pd.DataFrame:
    if isinstance(hist.columns, pd.MultiIndex):
        hist = hist.copy()
        hist.columns = hist.columns.get_level_values(0)
    return hist


def fetch_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> List[Dict[str, Any]]:
    # yf.download() uses a more reliable v7 endpoint vs tk.history() which hits v8 (rate-limited)
    hist = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
        actions=False,
    )
    if hist is None or hist.empty:
        return []

    hist = _flatten(hist).reset_index()
    hist.columns = [str(c).lower() for c in hist.columns]

    ts_col = next((c for c in hist.columns if c in ("date", "datetime", "timestamp")), hist.columns[0])
    ts = pd.to_datetime(hist[ts_col])
    if hasattr(ts.dt, "tz") and ts.dt.tz is not None:
        ts = ts.dt.tz_localize(None)

    out = pd.DataFrame(
        {
            "timestamp": ts.dt.strftime("%Y-%m-%d"),
            "open":   pd.to_numeric(hist.get("open",   0), errors="coerce").fillna(0),
            "high":   pd.to_numeric(hist.get("high",   0), errors="coerce").fillna(0),
            "low":    pd.to_numeric(hist.get("low",    0), errors="coerce").fillna(0),
            "close":  pd.to_numeric(hist.get("close",  0), errors="coerce").fillna(0),
            "volume": pd.to_numeric(hist.get("volume", 0), errors="coerce").fillna(0),
        }
    )
    return out[out["close"] > 0].to_dict(orient="records")


def fetch_company_info(ticker: str) -> Dict[str, Any]:
    tk = yf.Ticker(ticker)
    out: Dict[str, Any] = {"symbol": ticker.upper()}

    # ── fast_info: lightweight, rarely rate-limited ──────────────────────────
    try:
        fi = tk.fast_info
        fast_map: Dict[str, str] = {
            "currentPrice":       "last_price",
            "previousClose":      "previous_close",
            "dayHigh":            "day_high",
            "dayLow":             "day_low",
            "marketCap":          "market_cap",
            "fiftyTwoWeekHigh":   "fifty_two_week_high",
            "fiftyTwoWeekLow":    "fifty_two_week_low",
            "fiftyDayAverage":    "fifty_day_average",
            "twoHundredDayAverage": "two_hundred_day_average",
            "exchange":           "exchange",
            "currency":           "currency",
            "regularMarketVolume": "three_month_average_volume",
            "shares":             "shares",
        }
        for out_key, attr in fast_map.items():
            try:
                val = getattr(fi, attr, None)
                if val is not None:
                    out[out_key] = float(val) if isinstance(val, (int, float)) else val
            except Exception:
                pass
    except Exception:
        pass

    # ── tk.info: full details — may 429, treat as best-effort ───────────────
    try:
        info = tk.info or {}
        extra_keys = [
            "shortName", "longName", "sector", "industry", "website", "country", "quoteType",
            "open", "regularMarketPreviousClose", "averageVolume", "averageVolume10days",
            "enterpriseValue", "trailingPE", "forwardPE", "priceToBook",
            "trailingEps", "forwardEps", "dividendYield", "dividendRate",
            "beta", "totalRevenue", "grossMargins", "operatingMargins", "profitMargins",
            "returnOnEquity", "returnOnAssets", "debtToEquity",
            "longBusinessSummary", "fullTimeEmployees",
        ]
        for k in extra_keys:
            if info.get(k) is not None and k not in out:
                out[k] = info[k]
        # Prefer info's currentPrice if fast_info missed it
        for price_key in ("currentPrice", "regularMarketPrice"):
            if info.get(price_key) and "currentPrice" not in out:
                out["currentPrice"] = info[price_key]
    except Exception:
        pass

    # ── Derived fields ────────────────────────────────────────────────────────
    price: Optional[float] = out.get("currentPrice")
    prev:  Optional[float] = out.get("previousClose") or out.get("regularMarketPreviousClose")
    if price and prev:
        out["priceChange"]    = round(float(price) - float(prev), 4)
        out["priceChangePct"] = round((float(price) / float(prev) - 1) * 100, 4)

    return out
