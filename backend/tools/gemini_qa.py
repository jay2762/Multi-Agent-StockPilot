from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import requests


_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Tried in order; skip on 429 (quota) or 503 (unavailable)
_MODELS = [
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-pro-latest",
]


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err: str = "No models tried."
    for model in _MODELS:
        url = _GEMINI_BASE.format(model=model)
        try:
            r = requests.post(url, params={"key": api_key}, json=payload, timeout=45)
            if r.status_code in (429, 503):
                last_err = f"HTTP {r.status_code} on {model}"
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            last_err = f"{model}: {exc}"
            continue
    raise RuntimeError(f"All Gemini models failed — {last_err}")


def _clean_answer(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _fmt(v: Any, decimals: int = 2, suffix: str = "") -> str:
    if v is None:
        return "unavailable"
    try:
        return f"{float(v):,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def _local_answer(
    question: str,
    ticker: str,
    company: Dict[str, Any],
    analysis: Dict[str, Any],
    prediction: Dict[str, Any],
) -> str:
    c = company or {}
    ind = analysis.get("indicators") or {}
    trend = analysis.get("trend") or {}
    sent = analysis.get("sentiment") or {}
    forecast = prediction.get("forecast") or {}
    short = forecast.get("short_term") or {}
    long = forecast.get("long_term") or {}
    risk = prediction.get("risk") or {}
    model = prediction.get("model") or {}

    name = c.get("longName") or c.get("shortName") or ticker.upper()
    price = c.get("currentPrice") or c.get("regularMarketPrice") or trend.get("last_close")
    rsi = ind.get("rsi_14")
    macd = ind.get("macd")
    macd_signal = ind.get("macd_signal")
    sentiment_score = sent.get("compound")

    rsi_text = "RSI is unavailable"
    if rsi is not None:
        if rsi >= 70:
            rsi_text = f"RSI is {_fmt(rsi)}, which suggests the stock may be getting overbought"
        elif rsi <= 30:
            rsi_text = f"RSI is {_fmt(rsi)}, which suggests the stock may be oversold"
        else:
            rsi_text = f"RSI is {_fmt(rsi)}, which is in a neutral range"

    macd_text = "MACD data is unavailable"
    if macd is not None and macd_signal is not None:
        macd_text = (
            f"MACD is {_fmt(macd)} versus a signal line of {_fmt(macd_signal)}, "
            f"which is {'bullish' if macd > macd_signal else 'bearish' if macd < macd_signal else 'neutral'}"
        )

    sentiment_text = "News sentiment is unavailable"
    if sentiment_score is not None:
        label = "positive" if sentiment_score >= 0.15 else "negative" if sentiment_score <= -0.15 else "neutral"
        sentiment_text = f"News sentiment is {label} with a compound score of {_fmt(sentiment_score)}"

    short_text = ""
    if short:
        short_text = (
            f"The 5-day rough forecast is {_fmt(short.get('predicted_price'))}, "
            f"or {_fmt(short.get('expected_change_pct'), suffix='%')}."
        )
    long_text = ""
    if long:
        long_text = (
            f"The 20-day rough forecast is {_fmt(long.get('predicted_price'))}, "
            f"or {_fmt(long.get('expected_change_pct'), suffix='%')}."
        )

    risk_text = ""
    if risk:
        flags = risk.get("flags") or []
        flag_text = f" Main risk note: {flags[0]}" if flags else ""
        confidence = model.get("confidence")
        confidence_text = _fmt(confidence * 100, 0, "%") if isinstance(confidence, (int, float)) else "unavailable"
        risk_text = f"Estimated risk is {risk.get('level', 'unavailable')} with model confidence of {confidence_text}.{flag_text}"

    question_lower = (question or "").lower()
    buy_language = "good time" in question_lower or "buy" in question_lower
    if buy_language:
        stance = "The data looks constructive, but not a clear aggressive buy signal."
        if rsi is not None and rsi >= 70:
            stance = "I would be cautious about buying immediately because momentum looks stretched."
        elif risk.get("level") == "High":
            stance = "I would be cautious because the current risk estimate is high."
        elif long.get("expected_change_pct") is not None and long.get("expected_change_pct") > 1 and sentiment_score is not None and sentiment_score >= -0.15:
            stance = "It may be reasonable for a long-term investor, but short-term entries should still be cautious."
    else:
        stance = "Here is a concise read of the current stock setup."

    parts = [
        f"{stance} {name} is currently around {_fmt(price)}.",
        f"Technically, {rsi_text}. {macd_text}. {sentiment_text}.",
    ]
    if short_text or long_text:
        parts.append(f"{short_text} {long_text}".strip())
    if risk_text:
        parts.append(risk_text)
    parts.append("This is informational only and should not be treated as financial advice.")
    return "\n\n".join(parts)


def _build_context(
    ticker: str,
    company: Dict[str, Any],
    analysis: Dict[str, Any],
    prediction: Dict[str, Any],
    prices: List[Dict[str, Any]],
) -> str:
    c = company
    ind = analysis.get("indicators") or {}
    trend = analysis.get("trend") or {}
    sent = analysis.get("sentiment") or {}
    forecast = prediction.get("forecast") or {}
    short = forecast.get("short_term") or {}
    long = forecast.get("long_term") or {}
    risk = prediction.get("risk") or {}
    model = prediction.get("model") or {}

    def f(v, fmt=".2f"):
        return f"{v:{fmt}}" if v is not None else "N/A"

    last_prices = prices[-5:] if prices else []
    price_snippet = ", ".join(
        f"{p['timestamp']}: ${p['close']:.2f}" for p in last_prices
    )

    ctx = f"""
=== STOCK CONTEXT FOR {ticker.upper()} ===

Company: {c.get('longName', ticker)}
Exchange: {c.get('exchange', 'N/A')} | Sector: {c.get('sector', 'N/A')} | Industry: {c.get('industry', 'N/A')}

--- Current Price Data ---
Current Price:  ${f(c.get('currentPrice'))}
Previous Close: ${f(c.get('previousClose'))}
Day Open:       ${f(c.get('open'))}
Day High:       ${f(c.get('dayHigh'))}
Day Low:        ${f(c.get('dayLow'))}
Price Change:   {f(c.get('priceChange'))} ({f(c.get('priceChangePct'))}%)
Volume:         {int(c.get('regularMarketVolume', 0) or 0):,}

--- Valuation ---
Market Cap:     {c.get('marketCap', 'N/A')}
P/E (TTM):      {f(c.get('trailingPE'))}
P/E (Fwd):      {f(c.get('forwardPE'))}
EPS (TTM):      ${f(c.get('trailingEps'))}
Price/Book:     {f(c.get('priceToBook'))}

--- Risk & Range ---
Beta:           {f(c.get('beta'))}
52-Week High:   ${f(c.get('fiftyTwoWeekHigh'))}
52-Week Low:    ${f(c.get('fiftyTwoWeekLow'))}
50-Day Avg:     ${f(c.get('fiftyDayAverage'))}
200-Day Avg:    ${f(c.get('twoHundredDayAverage'))}

--- Dividends ---
Dividend Yield: {f(c.get('dividendYield'))}

--- Profitability ---
Profit Margin:  {f(c.get('profitMargins'))}
Op. Margin:     {f(c.get('operatingMargins'))}
ROE:            {f(c.get('returnOnEquity'))}

--- Technical Indicators ---
RSI (14):       {f(ind.get('rsi_14'))}
MACD:           {f(ind.get('macd'))}
MACD Signal:    {f(ind.get('macd_signal'))}
BB Upper:       ${f(ind.get('bb_upper'))}
BB Lower:       ${f(ind.get('bb_lower'))}
SMA 20:         ${f(ind.get('sma_20'))}
EMA 20:         ${f(ind.get('ema_20'))}
5-Day Change:   {f(trend.get('change_5'))}%
20-Day Change:  {f(trend.get('change_20'))}%

--- News Sentiment ---
Sentiment Score (compound): {f(sent.get('compound'))}
Positive Headlines: {sent.get('positive', 0)}
Negative Headlines: {sent.get('negative', 0)}
Neutral Headlines:  {sent.get('neutral', 0)}

--- Prediction Agent ---
Model:          {model.get('selected', 'N/A')}
Confidence:     {f(model.get('confidence'))}
Risk Level:     {risk.get('level', 'N/A')} ({f(risk.get('score'))})
5-Day Forecast: ${f(short.get('predicted_price'))} ({f(short.get('expected_change_pct'))}%)
20-Day Forecast:${f(long.get('predicted_price'))} ({f(long.get('expected_change_pct'))}%)
Risk Flags:     {'; '.join(risk.get('flags', [])) if risk.get('flags') else 'N/A'}

--- Recent Closing Prices ---
{price_snippet}

--- Company Description ---
{c.get('longBusinessSummary', 'Not available.')[:800]}
""".strip()
    return ctx


def answer_question(
    question: str,
    ticker: str,
    company: Dict[str, Any],
    analysis: Dict[str, Any],
    prediction: Dict[str, Any],
    prices: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    ctx = _build_context(ticker, company, analysis, prediction, prices)

    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"\n{role}: {msg['content']}"

    prompt = f"""You are an expert financial analyst assistant. You have access to the following real-time stock data context.

{ctx}

{f"Previous conversation:{history_text}" if history_text else ""}

User question: {question}

Instructions:
- Answer clearly and concisely using the data context above.
- If the question asks to compare two stocks and the second stock's data is not in the context, use your general knowledge to provide a reasonable comparison.
- For technical analysis questions, reference the indicators provided.
- Always mention that this is for informational purposes only, not financial advice.
- Be specific with numbers from the context when available.
- Write in natural paragraphs, like a professional ChatGPT response.
- Do not use markdown formatting, headings, bullet points, numbered lists, bold text, asterisks, or hash symbols.
- Keep the answer concise. Prefer 3 to 5 short paragraphs.
"""

    try:
        return _clean_answer(_call_gemini(prompt))
    except Exception:
        return _clean_answer(_local_answer(question, ticker, company, analysis, prediction))
