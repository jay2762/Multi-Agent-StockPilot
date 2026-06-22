from __future__ import annotations


DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Finance Assistant</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07111f;
      --sidebar: #080f1f;
      --panel: rgba(255, 255, 255, 0.06);
      --panel-2: rgba(255, 255, 255, 0.08);
      --text: rgba(255, 255, 255, 0.92);
      --muted: rgba(255, 255, 255, 0.58);
      --line: rgba(255, 255, 255, 0.12);
      --accent: #7c3aed;
      --green: #22c55e;
      --red: #ef4444;
      --blue: #38bdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(1100px 720px at 38% 8%, rgba(124, 58, 237, .22), transparent 58%),
                  radial-gradient(980px 680px at 86% 15%, rgba(34, 197, 94, .12), transparent 56%),
                  var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app { display: grid; grid-template-columns: 310px 1fr; min-height: 100vh; }
    .sidebar {
      background: rgba(8, 15, 31, .92);
      border-right: 1px solid var(--line);
      padding: 86px 28px 28px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 26px;
      font-weight: 800;
      margin-bottom: 72px;
    }
    .divider { height: 1px; background: var(--line); margin: 0 0 34px; }
    label {
      display: block;
      color: var(--text);
      font-size: 15px;
      font-weight: 750;
      margin: 22px 0 10px;
    }
    input, textarea, select, button {
      width: 100%;
      border: 1px solid transparent;
      border-radius: 8px;
      background: rgba(0, 0, 0, .28);
      color: var(--text);
      font: inherit;
    }
    input, select { min-height: 48px; padding: 0 14px; }
    textarea {
      min-height: 116px;
      resize: vertical;
      padding: 14px;
      line-height: 1.5;
    }
    .range-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-top: 12px;
    }
    .radio {
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(255, 255, 255, .82);
      font-weight: 700;
      cursor: pointer;
    }
    .dot {
      width: 18px;
      height: 18px;
      border-radius: 999px;
      border: 2px solid rgba(255,255,255,.25);
      background: rgba(255,255,255,.08);
    }
    .radio.active .dot {
      border: 6px solid #ff4b4b;
      background: white;
    }
    button {
      min-height: 48px;
      margin-top: 18px;
      border: 1px solid rgba(255,255,255,.22);
      background: rgba(255,255,255,.12);
      font-weight: 800;
      cursor: pointer;
    }
    button:disabled { cursor: wait; opacity: .65; }
    .toggle-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 28px;
      font-weight: 800;
    }
    .toggle {
      width: 38px;
      height: 20px;
      border-radius: 999px;
      background: rgba(255,255,255,.32);
      position: relative;
    }
    .toggle::after {
      content: "";
      position: absolute;
      width: 14px;
      height: 14px;
      left: 3px;
      top: 3px;
      border-radius: 999px;
      background: white;
    }
    .backend {
      border-top: 1px solid var(--line);
      margin-top: 70px;
      padding-top: 32px;
      color: var(--muted);
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    .backend a { color: #a78bfa; }
    main { padding: 58px 62px 46px; min-width: 0; }
    .topbar {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 18px;
      margin-bottom: 8px;
      color: rgba(255,255,255,.82);
      font-weight: 800;
    }
    .ticker-small {
      color: var(--muted);
      font-weight: 800;
      letter-spacing: .08em;
      margin-bottom: 8px;
    }
    .hero {
      display: flex;
      align-items: baseline;
      gap: 18px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }
    .price {
      font-size: clamp(40px, 5vw, 58px);
      line-height: 1;
      font-weight: 900;
      letter-spacing: 0;
    }
    .currency { color: var(--muted); font-weight: 850; }
    .change { color: var(--green); font-weight: 900; font-size: 22px; }
    .muted { color: var(--muted); }
    .kpis {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 18px;
      margin: 12px 0 28px;
    }
    .card {
      min-height: 92px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
    }
    .card .label, .section-label {
      color: var(--muted);
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: .08em;
      font-weight: 850;
    }
    .card .value {
      margin-top: 14px;
      font-size: 24px;
      font-weight: 900;
    }
    .content-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, .78fr);
      gap: 34px;
      align-items: start;
    }
    h2 {
      margin: 0 0 18px;
      font-size: 22px;
      letter-spacing: 0;
    }
    #chart {
      width: 100%;
      height: 560px;
      background: transparent;
    }
    .summary {
      margin-top: 16px;
      padding: 16px;
      background: rgba(255,255,255,.055);
      border: 1px solid var(--line);
      border-radius: 10px;
      color: rgba(255,255,255,.78);
      line-height: 1.55;
      font-weight: 650;
    }
    .stats h2 { margin-bottom: 28px; }
    .range-track {
      height: 8px;
      border-radius: 999px;
      background: rgba(255,255,255,.09);
      overflow: hidden;
      margin: 10px 0 22px;
    }
    .range-fill {
      width: 72%;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), var(--green));
    }
    .range-labels {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-weight: 760;
    }
    .stat-row {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      border-bottom: 1px solid rgba(255,255,255,.09);
      padding: 10px 0;
      color: var(--muted);
      font-weight: 750;
    }
    .stat-row strong { color: rgba(255,255,255,.88); }
    .below {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, .48fr);
      gap: 28px;
      margin-top: 26px;
    }
    .panel {
      background: rgba(255,255,255,.045);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 18px;
    }
    .headlines ul { margin: 12px 0 0; padding-left: 20px; }
    .headlines li { margin: 9px 0; color: rgba(255,255,255,.78); }
    .headlines a { color: #93c5fd; }
    .reasoning { display: none; }
    .reasoning.visible { display: block; }
    .reasoning pre {
      white-space: pre-wrap;
      color: rgba(255,255,255,.74);
      line-height: 1.45;
      margin: 12px 0 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
    }
    .loading {
      min-height: 560px;
      display: grid;
      place-items: center;
      color: var(--muted);
      font-weight: 800;
    }
    .error {
      display: none;
      color: #fecaca;
      background: rgba(127, 29, 29, .42);
      border: 1px solid rgba(248, 113, 113, .35);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 18px;
    }
    @media (max-width: 1100px) {
      .app { grid-template-columns: 1fr; }
      .sidebar { padding: 28px; }
      .brand { margin-bottom: 24px; }
      main { padding: 32px 24px; }
      .kpis, .content-grid, .below { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand"><span>📈</span><span>Finance Assistant</span></div>
      <div class="divider"></div>

      <label for="ticker">Stock Ticker</label>
      <input id="ticker" value="AAPL" autocomplete="off" />

      <label>Time Range</label>
      <div class="range-row" id="range-row">
        <div class="radio" data-period="10d"><span class="dot"></span><span>10D</span></div>
        <div class="radio" data-period="1mo"><span class="dot"></span><span>1M</span></div>
        <div class="radio active" data-period="3mo"><span class="dot"></span><span>3M</span></div>
        <div class="radio" data-period="6mo"><span class="dot"></span><span>6M</span></div>
      </div>

      <label for="interval">Interval</label>
      <select id="interval">
        <option value="1d" selected>1d</option>
        <option value="1h">1h</option>
      </select>

      <label for="question">Ask the agents (optional)</label>
      <textarea id="question">Give me a technical indicator summary and sentiment outlook.</textarea>

      <button id="refresh">🔄 Refresh Data</button>

      <div class="toggle-row">
        <span class="toggle" id="reason-toggle" role="switch" aria-checked="false"></span>
        <span>Show agent reasoning</span>
      </div>

      <div class="backend">Backend: <a href="/health">/health</a></div>
    </aside>

    <main>
      <div class="topbar"><span>Deploy</span><span>⋮</span></div>
      <div class="error" id="error"></div>
      <div id="dashboard" class="loading">Fetching market data and running analysis...</div>
    </main>
  </div>

  <script>
    const state = { period: "3mo", data: null, showReasoning: false };
    const dashboard = document.getElementById("dashboard");
    const errorBox = document.getElementById("error");
    const refresh = document.getElementById("refresh");
    const rangeRow = document.getElementById("range-row");
    const reasonToggle = document.getElementById("reason-toggle");

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
    const num = (value) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };
    const money = (value, digits = 2) => {
      const parsed = num(value);
      return parsed === null ? "—" : parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    };
    const compactMoney = (value) => {
      const parsed = num(value);
      if (parsed === null) return "—";
      if (parsed >= 1e12) return `$${(parsed / 1e12).toFixed(2)}T`;
      if (parsed >= 1e9) return `$${(parsed / 1e9).toFixed(2)}B`;
      if (parsed >= 1e6) return `$${(parsed / 1e6).toFixed(2)}M`;
      return `$${parsed.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
    };
    const pct = (value) => {
      const parsed = num(value);
      return parsed === null ? "—" : `${parsed >= 0 ? "+" : ""}${parsed.toFixed(2)}%`;
    };
    const latestEnriched = (rows) => [...(rows || [])].reverse().find((row) => Object.values(row).some((value) => value !== null));

    function renderShell(data) {
      const company = data.data?.company || {};
      const analysis = data.analysis || {};
      const prediction = data.prediction || {};
      const sentiment = analysis.sentiment || {};
      const indicators = analysis.indicators || {};
      const enrichedLatest = latestEnriched(data.enriched) || {};
      const price = company.currentPrice ?? company.regularMarketPrice ?? analysis.trend?.last_close;
      const change = company.priceChange;
      const changePct = company.priceChangePct;
      const rsi = indicators.rsi_14 ?? enrichedLatest.rsi_14;
      const beta = company.beta;

      dashboard.className = "";
      dashboard.innerHTML = `
        <div class="ticker-small">${esc(data.ticker)} ·</div>
        <section class="hero">
          <div class="price">${money(price)}</div>
          <div class="currency">USD</div>
          <div class="change">${change === undefined ? "" : `+${money(change)} (${pct(changePct).replace("+", "")})`}</div>
          <div class="muted">vs previous close</div>
        </section>

        <section class="kpis">
          <div class="card"><div class="label">Market Cap</div><div class="value">${compactMoney(company.marketCap)}</div></div>
          <div class="card"><div class="label">P/E (TTM)</div><div class="value">${money(company.trailingPE)}</div></div>
          <div class="card"><div class="label">RSI (14)</div><div class="value">${money(rsi, 1)}</div><div class="muted">${rsiLabel(rsi)}</div></div>
          <div class="card"><div class="label">Beta</div><div class="value">${money(beta)}</div></div>
          <div class="card"><div class="label">Sentiment</div><div class="value">${pct(sentiment.compound).replace("%", "")}</div><div class="muted">${sentimentLabel(sentiment.compound)}</div></div>
        </section>

        <section class="content-grid">
          <div>
            <h2>${esc(data.ticker)} · ${labelPeriod(state.period)} Price Chart</h2>
            <div id="chart"></div>
            <div class="summary"><strong>Summary:</strong> ${esc(data.summary || prediction.summary || "No summary available.")}</div>
          </div>
          <aside class="stats">
            <h2>Key Statistics</h2>
            ${rangeBlock(company)}
            ${statRows(company)}
          </aside>
        </section>

        <section class="below">
          <div class="panel headlines">
            <div class="section-label">Latest Headlines</div>
            <ul>${(data.news || []).slice(0, 8).map((item) => `<li><a href="${esc(item.url)}" target="_blank" rel="noreferrer">${esc(item.title)}</a></li>`).join("") || "<li>No headlines returned.</li>"}</ul>
          </div>
          <div class="panel reasoning ${state.showReasoning ? "visible" : ""}">
            <div class="section-label">Agent Reasoning</div>
            <pre>${esc(reasoningText(data.traces))}</pre>
          </div>
        </section>
      `;
      drawChart(data);
    }

    function rsiLabel(value) {
      const parsed = num(value);
      if (parsed === null) return "—";
      if (parsed >= 70) return "Overbought";
      if (parsed <= 30) return "Oversold";
      return "Neutral";
    }
    function sentimentLabel(value) {
      const parsed = num(value);
      if (parsed === null) return "Neutral";
      if (parsed >= .15) return "Positive";
      if (parsed <= -.15) return "Negative";
      return "Neutral";
    }
    function labelPeriod(period) {
      return ({ "10d": "10D", "1mo": "1M", "3mo": "3M", "6mo": "6M" })[period] || period;
    }
    function rangeBlock(company) {
      const low = num(company.fiftyTwoWeekLow);
      const high = num(company.fiftyTwoWeekHigh);
      const price = num(company.currentPrice);
      const width = low !== null && high !== null && price !== null && high > low
        ? Math.max(2, Math.min(100, ((price - low) / (high - low)) * 100))
        : 55;
      return `
        <div class="range-labels"><span>52-Week Low: ${money(low)}</span><span>52-Week High: ${money(high)}</span></div>
        <div class="range-track"><div class="range-fill" style="width:${width}%"></div></div>
      `;
    }
    function statRows(company) {
      const rows = [
        ["Open", money(company.open)],
        ["Day High", money(company.dayHigh)],
        ["Day Low", money(company.dayLow)],
        ["Prev. Close", money(company.previousClose)],
        ["Volume", num(company.regularMarketVolume)?.toLocaleString("en-US") || "—"],
        ["Avg Volume", num(company.averageVolume)?.toLocaleString("en-US") || "—"],
        ["Market Cap", compactMoney(company.marketCap)],
        ["P/E (TTM)", money(company.trailingPE)],
        ["P/E (Fwd)", money(company.forwardPE)],
        ["EPS (TTM)", money(company.trailingEps)],
        ["Price/Book", money(company.priceToBook)],
        ["Beta", money(company.beta)],
        ["Div Yield", company.dividendYield ? `${(Number(company.dividendYield) * 100).toFixed(2)}%` : "—"],
        ["50D Avg", money(company.fiftyDayAverage)],
        ["200D Avg", money(company.twoHundredDayAverage)],
        ["Gross Margin", company.grossMargins ? `${(Number(company.grossMargins) * 100).toFixed(2)}%` : "—"],
      ];
      return rows.map(([key, value]) => `<div class="stat-row"><span>${key}</span><strong>${value}</strong></div>`).join("");
    }
    function reasoningText(traces) {
      if (!traces) return "No trace data returned.";
      return Object.entries(traces).map(([name, items]) => {
        const lines = (items || []).map((item) => `- ${item.stage}: ${item.thought || ""} ${item.observation ? `(${item.observation})` : ""}`);
        return `${name.toUpperCase()}\\n${lines.join("\\n")}`;
      }).join("\\n\\n");
    }
    function drawChart(data) {
      const prices = data.data?.prices || [];
      const enriched = data.enriched || [];
      const x = prices.map((row) => row.timestamp);
      const closeByTime = new Map(enriched.map((row) => [row.timestamp, row]));
      const tracePrice = {
        type: "candlestick",
        name: "Price",
        x,
        open: prices.map((row) => row.open),
        high: prices.map((row) => row.high),
        low: prices.map((row) => row.low),
        close: prices.map((row) => row.close),
        increasing: { line: { color: "#22c55e" }, fillcolor: "#22c55e" },
        decreasing: { line: { color: "#ef4444" }, fillcolor: "#ef4444" },
        yaxis: "y"
      };
      const volume = {
        type: "bar",
        name: "Volume",
        x,
        y: prices.map((row) => row.volume),
        marker: { color: prices.map((row) => Number(row.close) >= Number(row.open) ? "rgba(34,197,94,.55)" : "rgba(239,68,68,.55)") },
        yaxis: "y2"
      };
      const lineTrace = (key, name, color) => ({
        type: "scatter",
        mode: "lines",
        name,
        x,
        y: prices.map((row) => closeByTime.get(row.timestamp)?.[key] ?? null),
        line: { color, width: 2 },
        yaxis: "y"
      });
      Plotly.newPlot("chart", [
        lineTrace("bb_lower", "BB Lower", "#64748b"),
        lineTrace("bb_upper", "BB Upper", "#94a3b8"),
        lineTrace("ema_20", "EMA 20", "#38bdf8"),
        lineTrace("sma_20", "SMA 20", "#a78bfa"),
        tracePrice,
        volume
      ], {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "rgba(255,255,255,.82)" },
        margin: { t: 26, r: 12, b: 34, l: 46 },
        legend: { orientation: "h", x: 0.08, y: 1.08 },
        xaxis: { gridcolor: "rgba(255,255,255,.08)", rangeslider: { visible: false } },
        yaxis: { domain: [.28, 1], gridcolor: "rgba(255,255,255,.08)" },
        yaxis2: { domain: [0, .2], gridcolor: "rgba(255,255,255,.06)" }
      }, { responsive: true, displaylogo: false });
    }
    async function loadData() {
      refresh.disabled = true;
      refresh.textContent = "Running...";
      errorBox.style.display = "none";
      dashboard.className = "loading";
      dashboard.textContent = "Fetching market data and running analysis...";
      try {
        const response = await fetch("/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker: document.getElementById("ticker").value.trim().toUpperCase() || "AAPL",
            question: document.getElementById("question").value.trim(),
            period: state.period,
            interval: document.getElementById("interval").value
          })
        });
        if (!response.ok) throw new Error(`Request failed with ${response.status}`);
        state.data = await response.json();
        renderShell(state.data);
      } catch (error) {
        dashboard.className = "loading";
        dashboard.textContent = "Could not load the dashboard.";
        errorBox.textContent = error.message;
        errorBox.style.display = "block";
      } finally {
        refresh.disabled = false;
        refresh.textContent = "🔄 Refresh Data";
      }
    }
    rangeRow.addEventListener("click", (event) => {
      const option = event.target.closest(".radio");
      if (!option) return;
      state.period = option.dataset.period;
      document.querySelectorAll(".radio").forEach((item) => item.classList.toggle("active", item === option));
    });
    refresh.addEventListener("click", loadData);
    reasonToggle.addEventListener("click", () => {
      state.showReasoning = !state.showReasoning;
      reasonToggle.setAttribute("aria-checked", String(state.showReasoning));
      if (state.data) renderShell(state.data);
    });
    loadData();
  </script>
</body>
</html>
"""
