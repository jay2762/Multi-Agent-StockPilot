from __future__ import annotations

from typing import Any, Dict, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


_analyzer = SentimentIntensityAnalyzer()


def score_headlines(headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not headlines:
        return {"count": 0, "compound": 0.0, "positive": 0, "negative": 0, "neutral": 0, "items": []}

    items = []
    pos = neg = neu = 0
    compounds = []

    for h in headlines[:25]:
        title = (h.get("title") or "").strip()
        if not title:
            continue
        s = _analyzer.polarity_scores(title)
        compounds.append(s["compound"])
        label = "neutral"
        if s["compound"] >= 0.15:
            label = "positive"
            pos += 1
        elif s["compound"] <= -0.15:
            label = "negative"
            neg += 1
        else:
            neu += 1
        items.append({"title": title, "compound": s["compound"], "label": label, "source": h.get("source"), "url": h.get("url")})

    compound = sum(compounds) / len(compounds) if compounds else 0.0
    return {"count": len(items), "compound": compound, "positive": pos, "negative": neg, "neutral": neu, "items": items}
