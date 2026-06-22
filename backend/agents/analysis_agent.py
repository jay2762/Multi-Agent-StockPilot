from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.tools.glossary_rag import lookup_terms
from backend.tools.indicators import add_indicators
from backend.tools.sentiment import score_headlines


class AnalysisAgent:
    def run(self, ticker: str, question: str, scraped: Dict[str, Any], news: List[Dict[str, Any]]) -> Dict[str, Any]:
        t = ticker.strip().upper()
        trace: List[Dict[str, str]] = []

        trace.append(
            {
                "stage": "decide_tools",
                "thought": "Need technical indicators and sentiment; pick indicators based on available history.",
                "action": "Compute RSI/MACD/Bollinger/SMA/EMA if prices present; compute sentiment from headlines.",
                "observation": "Tool selection done.",
                "reflection": "Proceed to compute and then summarize explainably.",
            }
        )

        prices = scraped.get("prices", [])
        if isinstance(prices, list) and prices:
            df = pd.DataFrame(prices)
        elif isinstance(prices, list):
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(prices)

        analysis: Dict[str, Any] = {
            "indicators": {},
            "trend": {},
            "sentiment": {},
            "terminology": {},
        }

        if df.empty or "close" not in df.columns:
            trace.append(
                {
                    "stage": "indicators_skip",
                    "thought": "No usable price series; skip indicator calculations.",
                    "action": "return_empty_indicators",
                    "observation": f"df_empty={df.empty}",
                    "reflection": "Still compute sentiment and return partial result.",
                }
            )
            enriched = df
        else:
            enriched = add_indicators(df)
            trace.append(
                {
                    "stage": "compute_indicators",
                    "thought": "Compute standard technical indicators.",
                    "action": "add_indicators(df) => RSI, MACD, Bollinger, SMA/EMA",
                    "observation": f"Computed columns: {', '.join([c for c in enriched.columns if c not in df.columns])}",
                    "reflection": "Use latest row to produce a simple explainable readout.",
                }
            )

            last = enriched.dropna().tail(1)
            if not last.empty:
                row = last.iloc[0].to_dict()
                analysis["indicators"] = {
                    "rsi_14": float(row.get("rsi_14")) if row.get("rsi_14") is not None else None,
                    "macd": float(row.get("macd")) if row.get("macd") is not None else None,
                    "macd_signal": float(row.get("macd_signal")) if row.get("macd_signal") is not None else None,
                    "bb_upper": float(row.get("bb_upper")) if row.get("bb_upper") is not None else None,
                    "bb_middle": float(row.get("bb_middle")) if row.get("bb_middle") is not None else None,
                    "bb_lower": float(row.get("bb_lower")) if row.get("bb_lower") is not None else None,
                    "sma_20": float(row.get("sma_20")) if row.get("sma_20") is not None else None,
                    "ema_20": float(row.get("ema_20")) if row.get("ema_20") is not None else None,
                }

            close = enriched["close"].astype(float)
            analysis["trend"] = {
                "last_close": float(close.iloc[-1]),
                "change_5": float((close.iloc[-1] / close.iloc[-6] - 1.0) * 100.0) if len(close) >= 6 else None,
                "change_20": float((close.iloc[-1] / close.iloc[-21] - 1.0) * 100.0) if len(close) >= 21 else None,
            }

        sentiment = score_headlines(news)
        analysis["sentiment"] = sentiment
        trace.append(
            {
                "stage": "sentiment",
                "thought": "Score headlines sentiment and aggregate.",
                "action": "vaderSentiment headline scoring",
                "observation": f"n={sentiment.get('count', 0)}, compound={sentiment.get('compound')}",
                "reflection": "Combine with indicators for a balanced summary.",
            }
        )

        terms = lookup_terms(question or "")
        analysis["terminology"] = terms
        if terms:
            trace.append(
                {
                    "stage": "rag_terms",
                    "thought": "User asked about finance concepts; retrieve definitions.",
                    "action": "lookup_terms(question)",
                    "observation": f"matched={len(terms)}",
                    "reflection": "Attach concise definitions in response.",
                }
            )

        summary = self._summarize(t, analysis)
        trace.append(
            {
                "stage": "reflect",
                "thought": "Ensure summary is consistent and caveated.",
                "action": "generate_summary_rules",
                "observation": "Summary created.",
                "reflection": "Remind that this is informational only.",
            }
        )

        return {"analysis": analysis, "summary": summary, "trace": trace, "enriched": enriched.to_dict(orient="records") if not enriched.empty else []}

    def _summarize(self, ticker: str, analysis: Dict[str, Any]) -> str:
        ind = analysis.get("indicators", {})
        trend = analysis.get("trend", {})
        sent = analysis.get("sentiment", {})

        parts: List[str] = []
        last_close = trend.get("last_close")
        if last_close is not None:
            parts.append(f"{ticker} last close: {last_close:.2f}.")

        rsi = ind.get("rsi_14")
        if rsi is not None:
            if rsi >= 70:
                parts.append(f"RSI(14) is {rsi:.1f}, which is often interpreted as overbought.")
            elif rsi <= 30:
                parts.append(f"RSI(14) is {rsi:.1f}, which is often interpreted as oversold.")
            else:
                parts.append(f"RSI(14) is {rsi:.1f}, in a neutral range.")

        ch5 = trend.get("change_5")
        if ch5 is not None:
            parts.append(f"5-day change: {ch5:+.2f}%. ")

        compound = sent.get("compound")
        if compound is not None:
            label = "neutral"
            if compound >= 0.15:
                label = "positive"
            elif compound <= -0.15:
                label = "negative"
            parts.append(f"News sentiment is {label} (compound {compound:+.2f}).")

        if not parts:
            parts.append("Insufficient data to compute indicators; try a different ticker or refresh.")

        parts.append("This is informational only, not financial advice.")
        return " ".join(parts)
