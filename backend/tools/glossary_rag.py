from __future__ import annotations

from typing import Dict


_GLOSSARY: Dict[str, str] = {
    "rsi": "Relative Strength Index (RSI) is a momentum oscillator (0-100) often used to gauge overbought/oversold conditions.",
    "macd": "MACD (Moving Average Convergence Divergence) compares two EMAs (commonly 12 and 26) to measure trend/momentum; a signal line (commonly 9 EMA of MACD) is used for crossovers.",
    "bollinger": "Bollinger Bands use a moving average with upper/lower bands at a multiple of standard deviation to reflect volatility.",
    "sma": "Simple Moving Average (SMA) is the mean of prices over a window.",
    "ema": "Exponential Moving Average (EMA) weights recent prices more heavily than older prices.",
    "support": "Support is a price level where buying interest has historically been strong enough to prevent further declines.",
    "resistance": "Resistance is a price level where selling interest has historically been strong enough to prevent further rises.",
    "volatility": "Volatility refers to the degree of variation in price over time; higher volatility implies larger swings.",
}


def lookup_terms(text: str) -> Dict[str, str]:
    q = (text or "").lower()
    matched: Dict[str, str] = {}
    for k, v in _GLOSSARY.items():
        if k in q:
            matched[k] = v
    return matched
