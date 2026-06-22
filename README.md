# Multi-Agent StockPilot

Multi-Agent StockPilot is a finance dashboard that combines live stock data, technical indicators, news sentiment, lightweight forecasting, and agent reasoning into one Streamlit interface.

**Live app:** https://finance-assistant-frontend-lbts.onrender.com/

## Overview

The project is split into two deployable Python services:

- **Frontend:** Streamlit dashboard in `frontend/app.py`
- **Backend:** FastAPI API in `backend/main.py`

The frontend sends stock-analysis requests to the backend. The backend coordinates multiple agents for scraping, analysis, prediction, sentiment, and question answering.

## Features

- Interactive Streamlit dashboard for stock lookup
- Ticker, time range, and interval controls
- Candlestick price chart with volume
- SMA, EMA, Bollinger Bands, RSI, MACD, and trend summaries
- News headline scraping and VADER sentiment scoring
- Lightweight short-term and long-term forecast estimates
- Optional agent reasoning trace display
- Gemini-powered question answering when `GEMINI_API_KEY` is configured
- Render-ready deployment blueprint for separate frontend/backend services

## Architecture

```text
frontend/app.py
  Streamlit dashboard
  Calls BACKEND_URL/query and BACKEND_URL/ask

backend/main.py
  FastAPI application
  Exposes /health, /query, and /ask

backend/orchestrator.py
  Coordinates scraping, analysis, and prediction agents

backend/agents/
  scraping_agent.py
  analysis_agent.py
  prediction_agent.py

backend/tools/
  Alpha Vantage, Yahoo Finance, yfinance, indicators,
  sentiment, news scraping, and Gemini Q&A helpers
```

## Tech Stack

- Python
- FastAPI
- Streamlit
- Pandas / NumPy
- Plotly
- yfinance
- Alpha Vantage API
- BeautifulSoup
- VADER Sentiment
- Gemini API
- Render

## Local Setup

Clone the repository:

```bash
git clone https://github.com/jay2762/Multi-Agent-StockPilot.git
cd Multi-Agent-StockPilot
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
CORS_ALLOW_ORIGINS=*
BACKEND_URL=http://127.0.0.1:8000
```

Start the backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```bash
BACKEND_URL=http://127.0.0.1:8000 streamlit run frontend/app.py
```

Open the Streamlit URL shown in the terminal, usually:

```text
http://localhost:8501
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns:

```json
{"status":"ok"}
```

### Stock Analysis

```http
POST /query
```

Example request:

```json
{
  "ticker": "AAPL",
  "question": "Give me a technical indicator summary and sentiment outlook.",
  "period": "3mo",
  "interval": "1d"
}
```

### Ask Follow-Up Question

```http
POST /ask
```

Uses the current stock context and chat history to answer follow-up questions.

## Deployment

This repo includes `render.yaml`, which defines two Render web services:

- `finance-assistant-backend`
- `finance-assistant-frontend`

Deploy from Render using **New Blueprint** and select this repository.

Required environment variables:

```text
GEMINI_API_KEY
ALPHA_VANTAGE_API_KEY
```

The frontend can connect to the backend through:

```text
BACKEND_URL=https://your-backend-service.onrender.com
```

Current deployed frontend:

```text
https://finance-assistant-frontend-lbts.onrender.com/
```

## Notes

- The app is for educational and informational use only.
- Forecasts are rough statistical estimates and should not be treated as financial advice.
- API keys should only be stored in local `.env` files or deployment environment variables.
