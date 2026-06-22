from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st


st.set_page_config(page_title="Finance Assistant", page_icon="📈", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    backend_host = os.getenv("BACKEND_HOST")
    backend_port = os.getenv("BACKEND_PORT")
    BACKEND_URL = (
        f"http://{backend_host}:{backend_port}"
        if backend_host and backend_port
        else "http://127.0.0.1:8000"
    )

PERIOD_MAP = {"10D": "10d", "1M": "1mo", "3M": "3mo", "6M": "6mo"}


def _inject_css() -> None:
    st.markdown(
        """
<style>
:root {
  --bg: #0b1220;
  --panel: rgba(255,255,255,0.06);
  --panel-2: rgba(255,255,255,0.08);
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.60);
  --border: rgba(255,255,255,0.10);
  --accent: #7c3aed;
  --green: #22c55e;
  --red: #ef4444;
}

html, body, [data-testid="stAppViewContainer"] {
  background: radial-gradient(1200px 800px at 20% 10%, rgba(124,58,237,0.18), transparent 60%),
              radial-gradient(1000px 700px at 90% 20%, rgba(34,197,94,0.10), transparent 60%),
              var(--bg) !important;
  color: var(--text) !important;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stStatusWidget"] {
  background: transparent !important;
}
.block-container { padding-top: 1.2rem !important; }

.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 18px 14px 18px;
  margin-bottom: 14px;
}
.kpi {
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
}
.kpi .label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: .06em; }
.kpi .value { font-size: 1.18rem; font-weight: 700; margin-top: 3px; }
.kpi .sub   { font-size: 0.82rem; margin-top: 2px; color: var(--muted); }

.price-hero { padding: 12px 0 4px 0; }
.price-hero .name  { font-size: 0.9rem; color: var(--muted); }
.price-hero .price { font-size: 2.4rem; font-weight: 800; line-height: 1.1; }
.price-hero .chg   { font-size: 1rem; font-weight: 600; }

.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.stat-row  { display: flex; justify-content: space-between; align-items: baseline;
             border-bottom: 1px solid var(--border); padding: 5px 0; font-size: 0.86rem; }
.stat-row .sk { color: var(--muted); }
.stat-row .sv { font-weight: 600; }

.range-bar-wrap { background: var(--panel-2); border-radius: 6px; height: 6px; overflow: hidden; }
.range-bar-fill { background: linear-gradient(90deg, #7c3aed, #22c55e); height: 6px; border-radius: 6px; }

.pill-pos { background: rgba(34,197,94,0.15); color: #22c55e; border-radius: 6px;
            padding: 1px 8px; font-size: 0.78rem; font-weight: 700; }
.pill-neg { background: rgba(239,68,68,0.15); color: #ef4444; border-radius: 6px;
            padding: 1px 8px; font-size: 0.78rem; font-weight: 700; }
.pill-neu { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6); border-radius: 6px;
            padding: 1px 8px; font-size: 0.78rem; font-weight: 700; }

.chat-wrap { display: flex; flex-direction: column; gap: 12px; padding: 8px 0; }
.chat-user {
  align-self: flex-end; background: linear-gradient(135deg,#7c3aed,#6d28d9);
  color: #fff; border-radius: 18px 18px 4px 18px; padding: 10px 16px;
  max-width: 75%; font-size: 0.92rem; line-height: 1.5;
}
.chat-ai {
  align-self: flex-start; background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.10); color: rgba(255,255,255,0.92);
  border-radius: 18px 18px 18px 4px; padding: 12px 16px;
  max-width: 85%; font-size: 0.92rem; line-height: 1.6;
}
.chat-ai .ai-label { font-size: 0.72rem; color: #a78bfa; font-weight: 700;
                     letter-spacing: .05em; margin-bottom: 6px; }

.graph-note {
  margin-top: 8px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.045);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  color: rgba(255,255,255,0.78);
  font-size: 0.88rem;
  line-height: 1.5;
}
.graph-note strong { color: rgba(255,255,255,0.94); }

div[data-testid="stExpander"] > details {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 8px 10px;
}
a { color: #a78bfa !important; }

[data-testid="stSidebar"] { background: rgba(11,18,32,0.92) !important; border-right: 1px solid var(--border); }
</style>""",
        unsafe_allow_html=True,
    )


def fetch_analysis(ticker: str, question: str, period: str, interval: str) -> Dict[str, Any]:
    payload = {"ticker": ticker, "question": question, "period": period, "interval": interval}
    r = requests.post(f"{BACKEND_URL}/query", json=payload, timeout=90)
    r.raise_for_status()
    return r.json()


def _fmt_large(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v >= 1e12:
        return f"${v/1e12:.2f}T"
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.2f}M"
    return f"${v:,.0f}"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v*100:.2f}%" if v is not None else "—"


def _fmt_num(v: Optional[float], decimals: int = 2) -> str:
    return f"{v:,.{decimals}f}" if v is not None else "—"


def _chg_color(v: Optional[float]) -> str:
    if v is None:
        return "rgba(255,255,255,0.6)"
    return "#22c55e" if v >= 0 else "#ef4444"


def _graph_note(text: str) -> None:
    st.markdown(f"<div class='graph-note'><strong>Summary:</strong> {text}</div>", unsafe_allow_html=True)


def _clean_chat_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _price_chart_summary(df: pd.DataFrame, df_enriched: pd.DataFrame) -> str:
    if df.empty or "close" not in df.columns:
        return "No price history is available, so the trend cannot be summarized yet."

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        return "No usable closing prices are available for this ticker."

    first = float(close.iloc[0])
    last = float(close.iloc[-1])
    change_pct = (last / first - 1.0) * 100.0 if first else 0.0
    direction = "uptrend" if change_pct > 2 else "downtrend" if change_pct < -2 else "sideways trend"

    ma_text = ""
    if not df_enriched.empty and "sma_20" in df_enriched.columns:
        sma = pd.to_numeric(df_enriched["sma_20"], errors="coerce").dropna()
        if not sma.empty:
            ma_text = " Price is above the 20-day average, which supports short-term strength." if last >= float(sma.iloc[-1]) else " Price is below the 20-day average, which suggests short-term weakness."

    band_text = ""
    if not df_enriched.empty and {"bb_upper", "bb_lower"}.issubset(df_enriched.columns):
        upper = pd.to_numeric(df_enriched["bb_upper"], errors="coerce").dropna()
        lower = pd.to_numeric(df_enriched["bb_lower"], errors="coerce").dropna()
        if not upper.empty and not lower.empty:
            if last > float(upper.iloc[-1]):
                band_text = " It is trading near or above the upper Bollinger Band, so momentum may be stretched."
            elif last < float(lower.iloc[-1]):
                band_text = " It is trading near or below the lower Bollinger Band, so the stock may be oversold."
            else:
                band_text = " It is inside the Bollinger Bands, which points to a normal volatility range."

    volume_text = ""
    if "volume" in df.columns:
        volume = pd.to_numeric(df["volume"], errors="coerce").dropna()
        if len(volume) >= 5:
            recent_vol = float(volume.tail(5).mean())
            avg_vol = float(volume.mean())
            volume_text = " Recent volume is above average, so the move has stronger participation." if recent_vol > avg_vol * 1.15 else " Recent volume is not unusually high, so the move looks less forceful."

    return f"The stock moved {change_pct:+.2f}% over this range, showing a {direction}.{ma_text}{band_text}{volume_text}"


def _rsi_summary(df_enriched: pd.DataFrame) -> str:
    if df_enriched.empty or "rsi_14" not in df_enriched.columns:
        return "RSI is unavailable because there is not enough price history."

    rsi = pd.to_numeric(df_enriched["rsi_14"], errors="coerce").dropna()
    if rsi.empty:
        return "RSI is unavailable because there is not enough complete indicator data."

    latest = float(rsi.iloc[-1])
    if latest >= 70:
        zone = "overbought, meaning recent buying may be stretched"
    elif latest <= 30:
        zone = "oversold, meaning selling pressure may be stretched"
    else:
        zone = "neutral, meaning momentum is not at an extreme"

    slope = ""
    if len(rsi) >= 6:
        delta = latest - float(rsi.iloc[-6])
        slope = " RSI has been rising recently, showing improving momentum." if delta > 3 else " RSI has been falling recently, showing weakening momentum." if delta < -3 else " RSI has been mostly stable recently."

    return f"RSI is {latest:.1f}, which is {zone}.{slope}"


def _macd_summary(df_enriched: pd.DataFrame) -> str:
    needed = {"macd", "macd_signal"}
    if df_enriched.empty or not needed.issubset(df_enriched.columns):
        return "MACD is unavailable because there is not enough price history."

    macd = pd.to_numeric(df_enriched["macd"], errors="coerce")
    signal = pd.to_numeric(df_enriched["macd_signal"], errors="coerce")
    hist = (macd - signal).dropna()
    macd = macd.dropna()
    signal = signal.dropna()
    if macd.empty or signal.empty or hist.empty:
        return "MACD is unavailable because there is not enough complete indicator data."

    latest_macd = float(macd.iloc[-1])
    latest_signal = float(signal.iloc[-1])
    latest_hist = float(hist.iloc[-1])
    bias = "bullish" if latest_macd > latest_signal else "bearish" if latest_macd < latest_signal else "neutral"

    hist_text = ""
    if len(hist) >= 6:
        hist_delta = latest_hist - float(hist.iloc[-6])
        hist_text = " The histogram is improving, so momentum is strengthening." if hist_delta > 0 else " The histogram is weakening, so momentum is fading." if hist_delta < 0 else " The histogram is flat, so momentum is steady."

    zero_text = " MACD is above zero, which usually supports an upward trend." if latest_macd > 0 else " MACD is below zero, which usually points to a weaker trend."
    return f"MACD is {bias} because the MACD line is {'above' if latest_macd > latest_signal else 'below' if latest_macd < latest_signal else 'equal to'} the signal line.{zero_text}{hist_text}"


def make_price_chart(df: pd.DataFrame, df_enriched: pd.DataFrame) -> go.Figure:
    use = df_enriched if not df_enriched.empty else df
    has_vol = "volume" in use.columns and use["volume"].sum() > 0

    fig = make_subplots(
        rows=2 if has_vol else 1,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25] if has_vol else [1.0],
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=use["timestamp"],
            open=use["open"],
            high=use["high"],
            low=use["low"],
            close=use["close"],
            name="Price",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        ),
        row=1, col=1,
    )

    # Overlays on enriched data
    if not df_enriched.empty:
        for col, label, color in [
            ("sma_20", "SMA 20", "#a78bfa"),
            ("ema_20", "EMA 20", "#38bdf8"),
        ]:
            if col in df_enriched.columns:
                fig.add_trace(
                    go.Scatter(x=df_enriched["timestamp"], y=df_enriched[col], name=label,
                               line=dict(color=color, width=1.5), opacity=0.85),
                    row=1, col=1,
                )
        if "bb_upper" in df_enriched.columns and "bb_lower" in df_enriched.columns:
            fig.add_trace(
                go.Scatter(x=df_enriched["timestamp"], y=df_enriched["bb_upper"],
                           name="BB Upper", line=dict(color="#64748b", width=1), opacity=0.6),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(x=df_enriched["timestamp"], y=df_enriched["bb_lower"],
                           name="BB Lower", line=dict(color="#64748b", width=1), opacity=0.6,
                           fill="tonexty", fillcolor="rgba(148,163,184,0.07)"),
                row=1, col=1,
            )

    # Volume bars
    if has_vol:
        colors = ["#22c55e" if c >= o else "#ef4444"
                  for c, o in zip(use["close"], use["open"])]
        fig.add_trace(
            go.Bar(x=use["timestamp"], y=use["volume"], name="Volume",
                   marker_color=colors, opacity=0.6, showlegend=False),
            row=2, col=1,
        )

    fig.update_layout(
        height=480,
        margin=dict(l=0, r=0, t=30, b=0),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)", zeroline=False)
    return fig


def make_rsi_chart(df_enriched: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "rsi_14" not in df_enriched.columns:
        return fig
    fig.add_trace(go.Scatter(x=df_enriched["timestamp"], y=df_enriched["rsi_14"],
                             name="RSI 14", line=dict(color="#f59e0b", width=2)))
    fig.add_hline(y=70, line=dict(color="#ef4444", dash="dash", width=1))
    fig.add_hline(y=30, line=dict(color="#22c55e", dash="dash", width=1))
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)", line_width=0)
    fig.update_layout(
        height=200, margin=dict(l=0, r=0, t=30, b=0),
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text="RSI (14)", font=dict(size=13)),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
        xaxis=dict(showgrid=False), hovermode="x unified",
    )
    return fig


def make_macd_chart(df_enriched: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "macd" not in df_enriched.columns:
        return fig
    hist_vals = df_enriched["macd"] - df_enriched.get("macd_signal", df_enriched["macd"])
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in hist_vals]
    fig.add_trace(go.Bar(x=df_enriched["timestamp"], y=hist_vals, name="Histogram",
                         marker_color=colors, opacity=0.65))
    fig.add_trace(go.Scatter(x=df_enriched["timestamp"], y=df_enriched["macd"],
                             name="MACD", line=dict(color="#38bdf8", width=2)))
    if "macd_signal" in df_enriched.columns:
        fig.add_trace(go.Scatter(x=df_enriched["timestamp"], y=df_enriched["macd_signal"],
                                 name="Signal", line=dict(color="#f59e0b", width=2)))
    fig.update_layout(
        height=220, margin=dict(l=0, r=0, t=56, b=0),
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text="MACD (12, 26, 9)", font=dict(size=13), x=0, y=0.98),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.16, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig


# ─── Bootstrap ───────────────────────────────────────────────────────────────

_inject_css()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📈 Finance Assistant")
    st.divider()
    ticker_input = st.text_input("Stock Ticker", value="AAPL", placeholder="e.g. TSLA, MSFT…")
    st.markdown("**Time Range**")
    range_choice = st.radio("Time Range", list(PERIOD_MAP.keys()), index=2, horizontal=True, label_visibility="collapsed")
    period = PERIOD_MAP[range_choice]
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    question = st.text_area("Ask the agents (optional)",
                             value="Give me a technical indicator summary and sentiment outlook.",
                             height=100)
    refresh = st.button("🔄  Refresh Data", use_container_width=True)
    show_reasoning = st.toggle("Show agent reasoning", value=False)
    st.divider()
    st.caption(f"Backend: {BACKEND_URL}")

# ─── Fetch data ───────────────────────────────────────────────────────────────

needs_refresh = (
    refresh
    or "last_result" not in st.session_state
    or st.session_state.get("last_ticker") != ticker_input
    or st.session_state.get("last_period") != period
)

if needs_refresh:
    with st.spinner(f"Fetching data for **{ticker_input.upper()}**…"):
        try:
            st.session_state.last_result = fetch_analysis(
                ticker=ticker_input, question=question, period=period, interval=interval
            )
            st.session_state.last_ticker = ticker_input
            st.session_state.last_period = period
        except Exception as e:
            st.error(f"Backend error: {e}")
            st.stop()

res = st.session_state.last_result
prices = res.get("data", {}).get("prices", [])
df = pd.DataFrame(prices)
enriched_series = res.get("enriched", [])
df_enriched = pd.DataFrame(enriched_series)
company = res.get("data", {}).get("company", {})
analysis = res.get("analysis", {})
prediction = res.get("prediction", {})
sent = analysis.get("sentiment") or {}
ind = analysis.get("indicators") or {}
trend = analysis.get("trend") or {}

# ─── Price Hero Header ───────────────────────────────────────────────────────

ticker_sym = res.get("ticker", ticker_input.upper())
price = company.get("currentPrice") or company.get("regularMarketPrice") or trend.get("last_close")
change = company.get("priceChange")
change_pct = company.get("priceChangePct")
name = company.get("longName") or company.get("shortName") or ticker_sym
currency = company.get("currency", "USD")

chg_color = _chg_color(change)
chg_sign = "+" if (change or 0) >= 0 else ""

st.markdown(
    f"""
<div class='price-hero'>
  <div class='name'>{name} &nbsp;·&nbsp; {company.get('exchange','')}</div>
  <div style='display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;'>
    <span class='price'>{f"{price:,.2f}" if price else "—"} <span style='font-size:1rem;color:rgba(255,255,255,0.5)'>{currency}</span></span>
    <span class='chg' style='color:{chg_color}'>
      {chg_sign}{f"{change:+.2f}" if change is not None else "—"}
      &nbsp;({chg_sign}{f"{change_pct:.2f}" if change_pct is not None else "—"}%)
    </span>
    <span style='font-size:0.8rem;color:rgba(255,255,255,0.45)'>vs previous close</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Top KPI row ─────────────────────────────────────────────────────────────

rsi = ind.get("rsi_14")
compound = sent.get("compound")
mktcap = company.get("marketCap")
pe = company.get("trailingPE")

k1, k2, k3, k4, k5 = st.columns(5)
kpi_data = [
    (k1, "Market Cap", _fmt_large(mktcap), ""),
    (k2, "P/E (TTM)", _fmt_num(pe, 2) if pe else "—", ""),
    (k3, "RSI (14)", f"{rsi:.1f}" if rsi else "—",
     "Overbought" if rsi and rsi >= 70 else ("Oversold" if rsi and rsi <= 30 else "Neutral")),
    (k4, "Beta", _fmt_num(company.get("beta"), 2), ""),
    (k5, "Sentiment", f"{compound:+.2f}" if compound is not None else "—",
     "Positive" if compound and compound >= 0.15 else ("Negative" if compound and compound <= -0.15 else "Neutral")),
]
for col, label, val, sub in kpi_data:
    with col:
        sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
        st.markdown(
            f"<div class='kpi'><div class='label'>{label}</div>"
            f"<div class='value'>{val}</div>{sub_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)

# ─── Main layout ─────────────────────────────────────────────────────────────

left, right = st.columns([1.6, 1.0], gap="medium")

with left:
    # Price chart
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"**{ticker_sym} · {range_choice} Price Chart**")
    if not df.empty:
        st.plotly_chart(make_price_chart(df, df_enriched), use_container_width=True)
        _graph_note(_price_chart_summary(df, df_enriched))
    else:
        st.warning("⚠️ No price data returned. Check the ticker symbol and try refreshing.")
    st.markdown("</div>", unsafe_allow_html=True)

    # RSI
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    if not df_enriched.empty and "rsi_14" in df_enriched.columns:
        st.plotly_chart(make_rsi_chart(df_enriched), use_container_width=True)
        _graph_note(_rsi_summary(df_enriched))
    else:
        st.caption("RSI unavailable — need more price history.")
    st.markdown("</div>", unsafe_allow_html=True)

    # MACD
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    if not df_enriched.empty and "macd" in df_enriched.columns:
        st.plotly_chart(make_macd_chart(df_enriched), use_container_width=True)
        _graph_note(_macd_summary(df_enriched))
    else:
        st.caption("MACD unavailable — need more price history.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Ask the Assistant
    st.markdown(
        "<div class='card'>"
        "<div style='font-size:1.15rem;font-weight:700;margin-bottom:4px'>💬 Ask the Assistant</div>"
        "<div style='font-size:0.83rem;color:rgba(255,255,255,0.5);margin-bottom:14px'>"
        "Ask anything about this stock — technicals, fundamentals, comparisons, or market context."
        "</div>",
        unsafe_allow_html=True,
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_ticker" not in st.session_state:
        st.session_state.chat_ticker = ""

    if st.session_state.chat_ticker != ticker_input.upper():
        st.session_state.chat_history = []
        st.session_state.chat_ticker = ticker_input.upper()

    if st.session_state.chat_history:
        bubbles_html = "<div class='chat-wrap'>"
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                bubbles_html += f"<div class='chat-user'>{msg['content']}</div>"
            else:
                content = _clean_chat_text(msg["content"]).replace("\n", "<br/>")
                bubbles_html += (
                    f"<div class='chat-ai'>"
                    f"<div class='ai-label'>🤖 ASSISTANT</div>"
                    f"{content}</div>"
                )
        bubbles_html += "</div>"
        st.markdown(bubbles_html, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

    col_q, col_btn = st.columns([5, 1])
    with col_q:
        user_question = st.text_input(
            "Ask a stock question", placeholder="e.g. Is TSLA a good buy right now? How does it compare to AAPL?",
            label_visibility="collapsed", key="chat_input"
        )
    with col_btn:
        ask_clicked = st.button("Ask ✦", use_container_width=True, type="primary")

    if ask_clicked and user_question.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_question.strip()})
        with st.spinner("Thinking…"):
            try:
                payload = {
                    "ticker": ticker_input.upper(),
                    "question": user_question.strip(),
                    "company": company,
                    "analysis": analysis,
                    "prediction": prediction,
                    "prices": prices[-30:],
                    "chat_history": st.session_state.chat_history[:-1],
                }
                r = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=60)
                r.raise_for_status()
                answer = r.json().get("answer", "No response.")
            except Exception as e:
                answer = f"Error contacting assistant: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # ── Key Statistics ──────────────────────────────────────────────────────
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Key Statistics**")

    w52h = company.get("fiftyTwoWeekHigh")
    w52l = company.get("fiftyTwoWeekLow")
    fill_pct = 0.0
    if w52h and w52l and price and (w52h - w52l) > 0:
        fill_pct = max(0.0, min(1.0, (price - w52l) / (w52h - w52l))) * 100

    if w52h and w52l:
        st.markdown(
            f"""<div style='margin:6px 0 10px 0'>
  <div style='display:flex;justify-content:space-between;font-size:0.78rem;color:rgba(255,255,255,0.55);margin-bottom:4px'>
    <span>52-Week Low: {w52l:,.2f}</span><span>52-Week High: {w52h:,.2f}</span>
  </div>
  <div class='range-bar-wrap'><div class='range-bar-fill' style='width:{fill_pct:.1f}%'></div></div>
</div>""",
            unsafe_allow_html=True,
        )

    stats = [
        ("Open", f"{company.get('open'):,.2f}" if company.get('open') else "—"),
        ("Day High", f"{company.get('dayHigh'):,.2f}" if company.get('dayHigh') else "—"),
        ("Day Low", f"{company.get('dayLow'):,.2f}" if company.get('dayLow') else "—"),
        ("Prev. Close", f"{company.get('previousClose'):,.2f}" if company.get('previousClose') else "—"),
        ("Volume", f"{int(company.get('regularMarketVolume',0)):,}" if company.get('regularMarketVolume') else "—"),
        ("Avg Volume", f"{int(company.get('averageVolume',0)):,}" if company.get('averageVolume') else "—"),
        ("Market Cap", _fmt_large(company.get("marketCap"))),
        ("P/E (TTM)", _fmt_num(company.get("trailingPE"), 2)),
        ("P/E (Fwd)", _fmt_num(company.get("forwardPE"), 2)),
        ("EPS (TTM)", _fmt_num(company.get("trailingEps"), 2)),
        ("Price/Book", _fmt_num(company.get("priceToBook"), 2)),
        ("Beta", _fmt_num(company.get("beta"), 2)),
        ("Div Yield", _fmt_pct(company.get("dividendYield"))),
        ("50D Avg", f"{company.get('fiftyDayAverage'):,.2f}" if company.get('fiftyDayAverage') else "—"),
        ("200D Avg", f"{company.get('twoHundredDayAverage'):,.2f}" if company.get('twoHundredDayAverage') else "—"),
        ("Gross Margin", _fmt_pct(company.get("grossMargins"))),
        ("Profit Margin", _fmt_pct(company.get("profitMargins"))),
        ("ROE", _fmt_pct(company.get("returnOnEquity"))),
        ("Debt/Equity", _fmt_num(company.get("debtToEquity"), 2)),
        ("Employees", f"{int(company.get('fullTimeEmployees',0)):,}" if company.get('fullTimeEmployees') else "—"),
    ]
    rows_html = "".join(
        f"<div class='stat-row'><span class='sk'>{k}</span><span class='sv'>{v}</span></div>"
        for k, v in stats
    )
    st.markdown(f"<div>{rows_html}</div>", unsafe_allow_html=True)

    # Sector / industry
    if company.get("sector"):
        st.markdown(
            f"<div style='margin-top:10px;font-size:0.82rem;color:rgba(255,255,255,0.55)'>"
            f"🏢 {company.get('sector')} &nbsp;·&nbsp; {company.get('industry','')}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Analysis Summary ────────────────────────────────────────────────────
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**🤖 Analysis Summary**")
    st.write(res.get("summary", ""))

    terms = (analysis.get("terminology") or {})
    if terms:
        st.divider()
        st.markdown("**Terminology**")
        for t, d in terms.items():
            st.caption(f"**{t.upper()}**: {d}")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Prediction Agent ───────────────────────────────────────────────────
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**🔮 Prediction Agent**")
    st.write(prediction.get("summary", "Prediction unavailable."))

    forecast = prediction.get("forecast") or {}
    short_fc = forecast.get("short_term") or {}
    long_fc = forecast.get("long_term") or {}
    risk = prediction.get("risk") or {}
    model = prediction.get("model") or {}

    if short_fc or long_fc:
        p1, p2 = st.columns(2)
        forecast_cards = [
            (p1, "5D Forecast", short_fc),
            (p2, "20D Forecast", long_fc),
        ]
        for col, label, fc in forecast_cards:
            with col:
                change = fc.get("expected_change_pct")
                pred = fc.get("predicted_price")
                low = fc.get("low_estimate")
                high = fc.get("high_estimate")
                direction = (fc.get("direction") or "flat").upper()
                color = _chg_color(change)
                st.markdown(
                    f"<div class='kpi'><div class='label'>{label} · {direction}</div>"
                    f"<div class='value'>{f'{pred:,.2f}' if pred is not None else '—'}</div>"
                    f"<div class='sub' style='color:{color}'>{f'{change:+.2f}%' if change is not None else '—'}</div>"
                    f"<div class='sub'>Range: {f'{low:,.2f}' if low is not None else '—'} - {f'{high:,.2f}' if high is not None else '—'}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    conf = model.get("confidence")
    risk_score = risk.get("score")
    st.caption(
        f"Model: {model.get('selected', 'N/A')} · "
        f"Confidence: {conf:.0%}" if conf is not None else f"Model: {model.get('selected', 'N/A')}"
    )
    if risk:
        level = risk.get("level", "N/A")
        st.markdown(
            f"<div style='font-size:0.86rem;margin-top:8px'>"
            f"<strong>Risk:</strong> {level}"
            f"{f' ({risk_score:.0%})' if risk_score is not None else ''}</div>",
            unsafe_allow_html=True,
        )
        for flag in risk.get("flags", []):
            st.caption(f"• {flag}")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── News Sentiment ──────────────────────────────────────────────────────
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"**📰 News Sentiment** &nbsp; <span style='font-size:0.8rem;color:rgba(255,255,255,0.5)'>{sent.get('count',0)} headlines</span>", unsafe_allow_html=True)

    sc = sent.get("compound", 0)
    bar_color = "#22c55e" if sc >= 0.15 else ("#ef4444" if sc <= -0.15 else "#94a3b8")
    st.markdown(
        f"<div style='display:flex;gap:16px;margin:8px 0 12px 0'>"
        f"<span style='color:#22c55e'>✅ {sent.get('positive',0)} pos</span>"
        f"<span style='color:#ef4444'>❌ {sent.get('negative',0)} neg</span>"
        f"<span style='color:#94a3b8'>⬜ {sent.get('neutral',0)} neu</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    items = sent.get("items", [])
    for it in items[:12]:
        title = it.get("title", "")
        url = it.get("url")
        label = it.get("label", "neutral")
        c = it.get("compound", 0)
        pill = f"<span class='pill-{'pos' if label=='positive' else 'neg' if label=='negative' else 'neu'}'>{c:+.2f}</span>"
        link = f"<a href='{url}' target='_blank'>{title}</a>" if url else title
        st.markdown(
            f"<div style='font-size:0.83rem;margin-bottom:8px;line-height:1.4'>{link}"
            f"<br/>{pill}</div>",
            unsafe_allow_html=True,
        )
    if not items:
        st.info("No headlines available.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Company Description ─────────────────────────────────────────────────
    bio = company.get("longBusinessSummary")
    if bio:
        with st.expander("📄 Company Description"):
            st.write(bio)

# ─── Agent Reasoning Trace ───────────────────────────────────────────────────

if show_reasoning:
    with st.expander("🤖 Agent Reasoning (ReAct Trace)", expanded=False):
        traces = res.get("traces", {})
        t1, t2, t3 = st.tabs(["Scraping Agent", "Analysis Agent", "Prediction Agent"])
        with t1:
            st.json(traces.get("scraping", []))
        with t2:
            st.json(traces.get("analysis", []))
        with t3:
            st.json(traces.get("prediction", []))
