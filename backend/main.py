from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.dashboard import DASHBOARD_HTML
from backend.orchestrator import Orchestrator
from backend.tools.gemini_qa import answer_question


load_dotenv()

app = FastAPI(title="Multi-Agent Finance Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return DASHBOARD_HTML


class QueryRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker, e.g. AAPL")
    question: str = Field("", description="User question about the ticker")
    period: str = Field("6mo", description="yfinance period, e.g. 1mo, 6mo, 1y")
    interval: str = Field("1d", description="yfinance interval, e.g. 1d, 1h")


class AskRequest(BaseModel):
    ticker: str = Field(..., description="Current stock ticker")
    question: str = Field(..., description="User question")
    company: Dict[str, Any] = Field(default_factory=dict)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    prediction: Dict[str, Any] = Field(default_factory=dict)
    prices: List[Dict[str, Any]] = Field(default_factory=list)
    chat_history: List[Dict[str, str]] = Field(default_factory=list)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest) -> Dict[str, Any]:
    result = orchestrator.run(
        ticker=req.ticker,
        question=req.question,
        period=req.period,
        interval=req.interval,
    )
    return result


@app.post("/ask")
def ask(req: AskRequest) -> Dict[str, str]:
    try:
        answer = answer_question(
            question=req.question,
            ticker=req.ticker,
            company=req.company,
            analysis=req.analysis,
            prediction=req.prediction,
            prices=req.prices,
            chat_history=req.chat_history,
        )
    except Exception as e:
        answer = f"Sorry, I couldn't generate an answer right now: {e}"
    return {"answer": answer}
