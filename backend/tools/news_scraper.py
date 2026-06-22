from __future__ import annotations

from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _safe_get(url: str, timeout: int = 10) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_market_headlines(ticker: str) -> List[Dict[str, Any]]:
    ticker = ticker.upper().strip()
    out: List[Dict[str, Any]] = []

    # Source 1: Finviz quote page
    try:
        html = _safe_get(f"https://finviz.com/quote.ashx?t={ticker}")
        soup = BeautifulSoup(html, "html.parser")
        news_table = soup.find("table", {"class": "fullview-news-outer"})
        if news_table is not None:
            for a in news_table.find_all("a")[:20]:
                title = a.get_text(strip=True)
                href = a.get("href")
                if title:
                    out.append({"source": "finviz", "title": title, "url": href})
    except Exception:
        pass

    # Source 2: Yahoo Finance quote page (headlines can be dynamic; attempt best-effort)
    if len(out) < 5:
        try:
            html = _safe_get(f"https://finance.yahoo.com/quote/{ticker}")
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[data-test-locator='mega']")[:10]:
                title = a.get_text(strip=True)
                href = a.get("href")
                if title:
                    url = href
                    if url and url.startswith("/"):
                        url = "https://finance.yahoo.com" + url
                    out.append({"source": "yahoo", "title": title, "url": url})
        except Exception:
            pass

    # De-dup
    seen = set()
    dedup: List[Dict[str, Any]] = []
    for item in out:
        key = (item.get("source"), item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)

    return dedup[:25]
