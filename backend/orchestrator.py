from __future__ import annotations

from typing import Any, Dict

from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.prediction_agent import PredictionAgent
from backend.agents.scraping_agent import ScrapingAgent


class Orchestrator:
    def __init__(self) -> None:
        self.scraping_agent = ScrapingAgent()
        self.analysis_agent = AnalysisAgent()
        self.prediction_agent = PredictionAgent()

    def run(self, ticker: str, question: str, period: str, interval: str) -> Dict[str, Any]:
        scrape_out = self.scraping_agent.run(
            ticker=ticker,
            question=question,
            period=period,
            interval=interval,
        )
        analysis_out = self.analysis_agent.run(
            ticker=ticker,
            question=question,
            scraped=scrape_out["data"],
            news=scrape_out["news"],
        )
        prediction_out = self.prediction_agent.run(
            ticker=ticker,
            question=question,
            scraped=scrape_out["data"],
            analysis=analysis_out["analysis"],
            enriched=analysis_out.get("enriched", []),
        )

        return {
            "ticker": ticker.upper(),
            "question": question,
            "data": scrape_out["data"],
            "enriched": analysis_out.get("enriched", []),
            "news": scrape_out["news"],
            "analysis": analysis_out["analysis"],
            "prediction": prediction_out,
            "summary": analysis_out["summary"],
            "traces": {
                "scraping": scrape_out["trace"],
                "analysis": analysis_out["trace"],
                "prediction": prediction_out["trace"],
            },
        }
