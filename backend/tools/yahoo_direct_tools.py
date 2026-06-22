from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import requests


_SESSION: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://finance.yahoo.com",
        })
        try:
            _SESSION.get("https://finance.yahoo.com", timeout=8)
        except Exception:
            pass
    return _SESSION


_PERIOD_TO_RANGE: Dict[str, str] = {
    "5d": "5d", "10d": "1mo", "1mo": "1mo", "3mo": "3mo",
    "6mo": "6mo", "1y": "1y", "2y": "2y",
}


def fetch_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> List[Dict[str, Any]]:
    yf_range = _PERIOD_TO_RANGE.get(period, "6mo")
    yf_interval = "1d" if interval == "1d" else "60m"
    path = f"/v8/finance/chart/{ticker.upper()}?interval={yf_interval}&range={yf_range}"
    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    s = _get_session()
    r = None
    for host in hosts:
        try:
            r = s.get(f"https://{host}{path}", timeout=15)
            if r.status_code == 200:
                break
        except Exception:
            continue
    if r is None or r.status_code != 200:
        global _SESSION
        _SESSION = None
        s = _get_session()
        for host in hosts:
            try:
                r = s.get(f"https://{host}{path}", timeout=15)
                if r.status_code == 200:
                    break
            except Exception:
                continue
    if r is None:
        raise RuntimeError("Yahoo Finance unreachable")
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    q = result["indicators"]["quote"][0]
    opens   = q.get("open",   [])
    highs   = q.get("high",   [])
    lows    = q.get("low",    [])
    closes  = q.get("close",  [])
    volumes = q.get("volume", [])

    records = []
    for i, ts in enumerate(timestamps):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue
        dt = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        records.append({
            "timestamp": dt,
            "open":   float(opens[i])   if i < len(opens)   and opens[i]   else c,
            "high":   float(highs[i])   if i < len(highs)   and highs[i]   else c,
            "low":    float(lows[i])    if i < len(lows)    and lows[i]    else c,
            "close":  float(c),
            "volume": float(volumes[i]) if i < len(volumes) and volumes[i] else 0.0,
        })
    return records


def fetch_company_info(ticker: str, price_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"symbol": ticker.upper()}

    if price_history:
        last = price_history[-1]
        prev = price_history[-2] if len(price_history) >= 2 else {}
        out["currentPrice"] = last.get("close")
        out["open"]    = last.get("open")
        out["dayHigh"] = last.get("high")
        out["dayLow"]  = last.get("low")
        out["regularMarketVolume"] = last.get("volume")
        if prev.get("close"):
            out["previousClose"]  = prev["close"]
            out["priceChange"]    = round(last["close"] - prev["close"], 4)
            out["priceChangePct"] = round((last["close"] / prev["close"] - 1) * 100, 4)
        highs  = [r["high"]  for r in price_history if r.get("high")]
        lows   = [r["low"]   for r in price_history if r.get("low")]
        if highs:
            out["fiftyTwoWeekHigh"] = max(highs)
        if lows:
            out["fiftyTwoWeekLow"]  = min(lows)

    s = _get_session()
    try:
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker.upper()}"
            "?modules=assetProfile,summaryDetail,defaultKeyStatistics,financialData,price"
        )
        r = s.get(url, timeout=15)
        if r.status_code != 200:
            return out
        data = r.json().get("quoteSummary", {}).get("result", [{}])[0]

        price_mod = data.get("price", {})
        summary   = data.get("summaryDetail", {})
        stats     = data.get("defaultKeyStatistics", {})
        fin       = data.get("financialData", {})
        profile   = data.get("assetProfile", {})

        def _v(d: dict, k: str):
            v = d.get(k)
            if isinstance(v, dict):
                return v.get("raw")
            return v

        mappings = [
            (price_mod,  "regularMarketPrice",           "currentPrice"),
            (price_mod,  "regularMarketOpen",            "open"),
            (price_mod,  "regularMarketDayHigh",         "dayHigh"),
            (price_mod,  "regularMarketDayLow",          "dayLow"),
            (price_mod,  "regularMarketVolume",          "regularMarketVolume"),
            (price_mod,  "regularMarketPreviousClose",   "previousClose"),
            (price_mod,  "regularMarketChange",          "priceChange"),
            (price_mod,  "regularMarketChangePercent",   "priceChangePct"),
            (price_mod,  "marketCap",                    "marketCap"),
            (price_mod,  "shortName",                    "shortName"),
            (price_mod,  "longName",                     "longName"),
            (price_mod,  "exchangeName",                 "exchange"),
            (price_mod,  "currency",                     "currency"),
            (summary,    "trailingPE",                   "trailingPE"),
            (summary,    "forwardPE",                    "forwardPE"),
            (summary,    "dividendYield",                "dividendYield"),
            (summary,    "beta",                         "beta"),
            (summary,    "fiftyTwoWeekHigh",             "fiftyTwoWeekHigh"),
            (summary,    "fiftyTwoWeekLow",              "fiftyTwoWeekLow"),
            (summary,    "fiftyDayAverage",              "fiftyDayAverage"),
            (summary,    "twoHundredDayAverage",         "twoHundredDayAverage"),
            (summary,    "averageVolume",                "averageVolume"),
            (stats,      "trailingEps",                  "trailingEps"),
            (stats,      "forwardEps",                   "forwardEps"),
            (stats,      "priceToBook",                  "priceToBook"),
            (fin,        "profitMargins",                "profitMargins"),
            (fin,        "operatingMargins",             "operatingMargins"),
            (fin,        "returnOnEquity",               "returnOnEquity"),
            (fin,        "returnOnAssets",               "returnOnAssets"),
            (fin,        "revenuePerShare",              "revenuePerShare"),
            (profile,    "sector",                       "sector"),
            (profile,    "industry",                     "industry"),
            (profile,    "longBusinessSummary",          "longBusinessSummary"),
            (profile,    "fullTimeEmployees",            "fullTimeEmployees"),
        ]
        for src, src_key, out_key in mappings:
            val = _v(src, src_key)
            if val is not None:
                out[out_key] = val

        if out.get("priceChange") is None and out.get("currentPrice") and out.get("previousClose"):
            p, pc = float(out["currentPrice"]), float(out["previousClose"])
            out["priceChange"]    = round(p - pc, 4)
            out["priceChangePct"] = round((p / pc - 1) * 100, 4)

    except Exception:
        pass

    return out
