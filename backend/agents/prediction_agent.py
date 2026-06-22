from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from backend.tools.glossary_rag import lookup_terms


class PredictionAgent:
    """Generate lightweight price forecasts and risk estimates.

    The project does not ship heavyweight ML dependencies, so this agent uses a
    conservative ensemble that can run anywhere: log-return momentum, linear
    trend, mean reversion, volatility, and sentiment adjustments.
    """

    def run(
        self,
        ticker: str,
        question: str,
        scraped: Dict[str, Any],
        analysis: Dict[str, Any],
        enriched: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        t = ticker.strip().upper()
        trace: List[Dict[str, str]] = []

        trace.append(
            {
                "stage": "collect_inputs",
                "thought": "Need historical closes, current indicators, and news sentiment.",
                "action": "Read structured time-series data from ScrapingAgent and indicators/sentiment from AnalysisAgent.",
                "observation": "Inputs collected for model selection.",
                "reflection": "Proceed only if enough recent price history is available.",
            }
        )

        prices = scraped.get("prices", [])
        df = pd.DataFrame(enriched or prices)
        if df.empty or "close" not in df.columns or len(df) < 15:
            trace.append(
                {
                    "stage": "insufficient_data",
                    "thought": "Forecast quality would be poor with fewer than 15 closes.",
                    "action": "Return high-risk partial prediction.",
                    "observation": f"rows={len(df)}",
                    "reflection": "Flag uncertainty instead of forcing a numeric forecast.",
                }
            )
            return {
                "forecast": {},
                "risk": {
                    "level": "High",
                    "score": 0.9,
                    "flags": ["Insufficient historical data for a reliable rough forecast."],
                },
                "model": {
                    "selected": "none",
                    "confidence": 0.1,
                    "reason": "Need at least 15 historical closes.",
                },
                "concepts": lookup_terms(question or "volatility risk support resistance"),
                "summary": f"Prediction unavailable for {t}: insufficient historical data. This is informational only, not financial advice.",
                "trace": trace,
            }

        df = df.copy()
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        close = df["close"].astype(float)
        current = float(close.iloc[-1])
        log_returns = np.log(close / close.shift(1)).dropna()

        trace.append(
            {
                "stage": "select_model",
                "thought": "Choose a model that matches available data volume and runtime constraints.",
                "action": "Use lightweight ARIMA-style ensemble: momentum + linear trend + mean reversion + sentiment adjustment.",
                "observation": f"rows={len(close)}, returns={len(log_returns)}",
                "reflection": "This gives rough directional estimates without requiring TensorFlow/statsmodels.",
            }
        )

        sentiment = analysis.get("sentiment") or {}
        indicators = analysis.get("indicators") or {}
        sentiment_score = float(sentiment.get("compound") or 0.0)
        volatility = float(log_returns.tail(min(30, len(log_returns))).std(ddof=0) or 0.0)

        forecasts = {
            "short_term": self._forecast_horizon(
                close=close,
                log_returns=log_returns,
                horizon=5,
                sentiment_score=sentiment_score,
                indicators=indicators,
            ),
            "long_term": self._forecast_horizon(
                close=close,
                log_returns=log_returns,
                horizon=20,
                sentiment_score=sentiment_score,
                indicators=indicators,
            ),
        }

        risk = self._estimate_risk(
            volatility=volatility,
            sentiment_score=sentiment_score,
            indicators=indicators,
            rows=len(close),
        )
        confidence = self._confidence(rows=len(close), volatility=volatility, risk_score=risk["score"])

        trace.append(
            {
                "stage": "evaluate_confidence",
                "thought": "Forecasts should be discounted when volatility or model uncertainty is high.",
                "action": "Combine data sufficiency, realized volatility, indicator extremes, and sentiment risk.",
                "observation": f"confidence={confidence:.2f}, risk={risk['level']}",
                "reflection": "Report rough ranges and caveats instead of over-precise price targets.",
            }
        )

        summary = self._summary(t, current, forecasts, risk, confidence)
        trace.append(
            {
                "stage": "reflect",
                "thought": "Check whether the response is appropriately caveated.",
                "action": "Attach risk flags and informational-only disclaimer.",
                "observation": "Prediction summary created.",
                "reflection": "Ready for frontend display.",
            }
        )

        return {
            "forecast": forecasts,
            "risk": risk,
            "model": {
                "selected": "lightweight_arima_style_ensemble",
                "confidence": confidence,
                "reason": "Uses historical log returns, linear trend, mean reversion, technical indicators, and news sentiment.",
            },
            "concepts": lookup_terms(question or "volatility risk support resistance"),
            "summary": summary,
            "trace": trace,
        }

    def _forecast_horizon(
        self,
        close: pd.Series,
        log_returns: pd.Series,
        horizon: int,
        sentiment_score: float,
        indicators: Dict[str, Any],
    ) -> Dict[str, Any]:
        current = float(close.iloc[-1])
        recent = log_returns.tail(min(10, len(log_returns)))
        momentum_daily = float(recent.mean() if not recent.empty else 0.0)

        x = np.arange(len(close.tail(min(60, len(close)))))
        y = np.log(close.tail(min(60, len(close))).to_numpy())
        trend_daily = float(np.polyfit(x, y, 1)[0]) if len(x) >= 2 else 0.0

        ma_window = min(20, len(close))
        mean_anchor = float(close.tail(ma_window).mean())
        mean_reversion_daily = float(np.log(mean_anchor / current) / max(horizon, 1))

        sentiment_daily = max(-0.002, min(0.002, sentiment_score * 0.0025))
        rsi = indicators.get("rsi_14")
        indicator_daily = 0.0
        if rsi is not None:
            if rsi >= 70:
                indicator_daily -= 0.0015
            elif rsi <= 30:
                indicator_daily += 0.0015

        daily_return = (
            0.40 * momentum_daily
            + 0.25 * trend_daily
            + 0.20 * mean_reversion_daily
            + 0.10 * sentiment_daily
            + 0.05 * indicator_daily
        )
        predicted = float(current * np.exp(daily_return * horizon))

        vol = float(log_returns.tail(min(30, len(log_returns))).std(ddof=0) or 0.0)
        band = max(current * vol * np.sqrt(horizon) * 1.25, current * 0.01)
        direction = "up" if predicted > current * 1.005 else "down" if predicted < current * 0.995 else "flat"

        return {
            "horizon_days": horizon,
            "current_price": current,
            "predicted_price": predicted,
            "expected_change_pct": float((predicted / current - 1.0) * 100.0),
            "low_estimate": max(0.0, predicted - band),
            "high_estimate": predicted + band,
            "direction": direction,
        }

    def _estimate_risk(
        self,
        volatility: float,
        sentiment_score: float,
        indicators: Dict[str, Any],
        rows: int,
    ) -> Dict[str, Any]:
        flags: List[str] = []
        score = min(1.0, volatility * 18.0)

        if rows < 40:
            score += 0.20
            flags.append("Limited history reduces prediction reliability.")
        if volatility >= 0.035:
            flags.append("Recent realized volatility is elevated.")
        if sentiment_score <= -0.15:
            score += 0.12
            flags.append("News sentiment is negative.")
        elif sentiment_score >= 0.15:
            score -= 0.04

        rsi = indicators.get("rsi_14")
        if rsi is not None and (rsi >= 70 or rsi <= 30):
            score += 0.08
            flags.append("RSI is in an extreme range, so short-term reversals are more likely.")

        score = max(0.05, min(1.0, score))
        level = "Low" if score < 0.33 else "Medium" if score < 0.66 else "High"
        if not flags:
            flags.append("No major short-term risk flags from the available data.")
        return {"level": level, "score": score, "flags": flags}

    def _confidence(self, rows: int, volatility: float, risk_score: float) -> float:
        data_score = min(1.0, rows / 120.0)
        vol_penalty = min(0.45, volatility * 8.0)
        confidence = 0.25 + 0.45 * data_score + 0.25 * (1.0 - risk_score) - vol_penalty
        return max(0.1, min(0.85, confidence))

    def _summary(
        self,
        ticker: str,
        current: float,
        forecasts: Dict[str, Dict[str, Any]],
        risk: Dict[str, Any],
        confidence: float,
    ) -> str:
        short = forecasts["short_term"]
        long = forecasts["long_term"]
        return (
            f"{ticker} rough forecast from {current:.2f}: "
            f"about {short['predicted_price']:.2f} over {short['horizon_days']} trading days "
            f"({short['expected_change_pct']:+.2f}%) and {long['predicted_price']:.2f} over "
            f"{long['horizon_days']} trading days ({long['expected_change_pct']:+.2f}%). "
            f"Model confidence is {confidence:.0%}; estimated risk is {risk['level']}. "
            "This is a rough statistical estimate for informational purposes only, not financial advice."
        )
