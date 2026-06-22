from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import backend.tools.alpha_vantage_tools as _av
import backend.tools.yahoo_direct_tools as _yd
import backend.tools.yfinance_tools as _yf
from backend.tools.news_scraper import fetch_market_headlines

# Fields that indicate rich company data (beyond just OHLCV seeds)
_RICH_KEYS = {"marketCap", "trailingPE", "beta", "sector", "longName"}


def _fetch_prices(ticker: str, period: str, interval: str):
    # 1. Alpha Vantage (disk cache hits first; fresh call if quota available)
    try:
        rows = _av.fetch_price_history(ticker, period=period, interval=interval)
        if rows:
            return rows, "alphavantage"
    except Exception:
        pass
    # 2. Yahoo Finance direct session (cookie-warmed v8 chart endpoint)
    try:
        rows = _yd.fetch_price_history(ticker, period=period, interval=interval)
        if rows:
            return rows, "yahoo_direct"
    except Exception:
        pass
    # 3. yfinance library (last resort)
    rows = _yf.fetch_price_history(ticker, period=period, interval=interval)
    return rows, "yfinance"


def _fetch_info(ticker: str, price_history=None):
    # 1. Alpha Vantage (quota-aware, falls back gracefully)
    try:
        info = _av.fetch_company_info(ticker, price_history=price_history)
        if info and _RICH_KEYS & set(info.keys()):
            return info, "alphavantage"
    except Exception:
        pass
    # 2. Yahoo Finance direct session
    try:
        info = _yd.fetch_company_info(ticker, price_history=price_history)
        if info and len(info) > 1:
            return info, "yahoo_direct"
    except Exception:
        pass
    # 3. yfinance library
    info = _yf.fetch_company_info(ticker)
    return info, "yfinance"


@dataclass
class TraceStep:
    stage: str
    thought: str
    action: str
    observation: str
    reflection: str


class ScrapingAgent:
    def run(self, ticker: str, question: str, period: str, interval: str) -> Dict[str, Any]:
        t = ticker.strip().upper()
        trace: List[Dict[str, str]] = []

        trace.append(
            {
                "stage": "identify_source",
                "thought": "Need price history, company info, and recent headlines.",
                "action": "Use Alpha Vantage API for market data; scrape headline sources for news.",
                "observation": "Selecting Alpha Vantage (TIME_SERIES_DAILY_ADJUSTED + OVERVIEW + GLOBAL_QUOTE) + public news pages.",
                "reflection": "Proceed; if API call fails, degrade gracefully with empty structures.",
            }
        )

        data: Dict[str, Any] = {"prices": [], "company": {}, "meta": {"period": period, "interval": interval}}

        try:
            prices_df, prices_src = _fetch_prices(t, period=period, interval=interval)
            data["prices"] = prices_df
            trace.append(
                {
                    "stage": "fetch_prices",
                    "thought": "Fetch historical candles.",
                    "action": f"{prices_src} price history(ticker={t}, period={period})",
                    "observation": f"Received {len(prices_df)} rows.",
                    "reflection": "If rows are too few, try a longer period.",
                }
            )
            if len(prices_df) < 20 and period != "1y":
                prices_df2, _ = _fetch_prices(t, period="1y", interval=interval)
                if len(prices_df2) > len(prices_df):
                    data["prices"] = prices_df2
                    data["meta"]["period"] = "1y"
                    trace.append(
                        {
                            "stage": "fallback_prices",
                            "thought": "Not enough rows for indicators; fallback to 1y.",
                            "action": f"price history(ticker={t}, period=1y)",
                            "observation": f"Received {len(prices_df2)} rows.",
                            "reflection": "Now should be sufficient for common indicators.",
                        }
                    )
        except Exception as e:  # noqa: BLE001
            trace.append(
                {
                    "stage": "fetch_prices_error",
                    "thought": "Price fetch failed; continue with empty prices.",
                    "action": "catch_exception",
                    "observation": repr(e),
                    "reflection": "Frontend will show error state; analysis agent should handle empty series.",
                }
            )

        try:
            info, info_src = _fetch_info(t, price_history=data["prices"] or None)
            data["company"] = info
            trace.append(
                {
                    "stage": "fetch_company",
                    "thought": "Get company metadata.",
                    "action": f"{info_src} company info(ticker={t})",
                    "observation": "Company info populated." if info else "No company info.",
                    "reflection": "Ok; proceed to headlines.",
                }
            )
        except Exception as e:  # noqa: BLE001
            trace.append(
                {
                    "stage": "fetch_company_error",
                    "thought": "Company info failed; continue.",
                    "action": "catch_exception",
                    "observation": repr(e),
                    "reflection": "Not critical for indicator computation.",
                }
            )

        headlines: List[Dict[str, Any]] = []
        try:
            headlines = fetch_market_headlines(t)
            trace.append(
                {
                    "stage": "fetch_news",
                    "thought": "Collect relevant headlines for sentiment.",
                    "action": "requests+BeautifulSoup scrape (multiple sources)",
                    "observation": f"Collected {len(headlines)} headlines.",
                    "reflection": "If none returned, sentiment will be neutral.",
                }
            )
        except Exception as e:  # noqa: BLE001
            trace.append(
                {
                    "stage": "fetch_news_error",
                    "thought": "Headline fetch failed; continue.",
                    "action": "catch_exception",
                    "observation": repr(e),
                    "reflection": "Degrade gracefully with empty news list.",
                }
            )

        return {"data": data, "news": headlines, "trace": trace}
