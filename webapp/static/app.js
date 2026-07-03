const $ = (id) => document.getElementById(id);

let lastShareText = "";
let lastResult = null;

const QUICK = ["TITAN", "RELIANCE", "TCS", "HDFCBANK", "INFY", "BAJFINANCE"];

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2500);
}

function signalClass(signal) {
  const s = (signal || "").toUpperCase();
  if (s.includes("STRONG")) return "strong-buy";
  if (s === "BUY") return "buy";
  if (s === "WATCH") return "watch";
  return "avoid";
}

function fmtRs(n) {
  if (n == null || isNaN(n)) return "—";
  return "Rs." + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function renderMarket(benchmark) {
  const pill = $("market-pill");
  const mood = (benchmark.mood || "NEUTRAL").toLowerCase();
  pill.className = "market-pill " + mood;
  pill.textContent = `Nifty ${benchmark.mood} · 20d ${benchmark.change_20d >= 0 ? "+" : ""}${benchmark.change_20d}%`;
}

function renderPosition(pos) {
  const body = $("position-body");
  const actions = $("position-actions");

  if (!pos) {
    body.innerHTML = '<p class="muted">No open position. Use your broker app to buy, then record here after cloud signal.</p>';
    actions.classList.add("hidden");
    return;
  }

  const pnlClass = pos.pnl_pct >= 0 ? "up" : "down";
  const sig = (pos.signal || "HOLD").toLowerCase();

  body.innerHTML = `
    <div class="position-hero">
      <span class="position-symbol">${pos.symbol}</span>
      <span class="pnl ${pnlClass}">${pos.pnl_pct >= 0 ? "+" : ""}${pos.pnl_pct}%</span>
    </div>
    <span class="signal-pill ${sig}">${pos.signal}</span>
    <div class="stats-grid">
      <div class="stat"><span class="stat-label">LTP</span><span class="stat-val">${fmtRs(pos.ltp)}</span></div>
      <div class="stat"><span class="stat-label">Avg</span><span class="stat-val">${fmtRs(pos.avg_price)}</span></div>
      <div class="stat"><span class="stat-label">Sell @ +3%</span><span class="stat-val green">${fmtRs(pos.sell_target)}</span></div>
      <div class="stat"><span class="stat-label">Avg trigger</span><span class="stat-val">${fmtRs(pos.avg_trigger)}</span></div>
      <div class="stat"><span class="stat-label">Qty</span><span class="stat-val">${pos.qty}</span></div>
      <div class="stat"><span class="stat-label">Invested</span><span class="stat-val">${fmtRs(pos.invested)}</span></div>
    </div>
    <p class="muted small">${pos.signal_reason || ""}</p>
  `;
  actions.classList.remove("hidden");
}

function renderPicks(picks, date) {
  const list = $("picks-list");
  $("picks-date").textContent = date ? `From scan: ${date}` : "No morning scan yet";

  if (!picks || !picks.length) {
    list.innerHTML = '<p class="muted">Run morning scan or search a stock above.</p>';
    return;
  }

  list.innerHTML = picks.map((p) => `
    <div class="pick-item" data-symbol="${p.symbol}">
      <div class="pick-left">
        <strong>${p.symbol}</strong>
        <span>${p.index_group} · ${p.signal}</span>
      </div>
      <div class="pick-right">
        <div class="pick-score">${p.score}/100</div>
        <div>${fmtRs(p.price)}</div>
      </div>
    </div>
  `).join("");

  list.querySelectorAll(".pick-item").forEach((el) => {
    el.addEventListener("click", () => {
      $("symbol-input").value = el.dataset.symbol;
      runAnalyze(el.dataset.symbol);
    });
  });
}

function renderResult(data) {
  lastResult = data;
  lastShareText = data.share_text || "";

  const card = $("result-card");
  card.classList.remove("hidden");

  $("res-symbol").textContent = data.symbol;
  $("res-index").textContent = data.index_group || "";
  const sigEl = $("res-signal");
  sigEl.textContent = data.signal;
  sigEl.className = "signal-badge " + signalClass(data.signal);

  const score = data.swing_score || 0;
  $("res-score").textContent = score;
  $("res-score-bar").style.width = score + "%";

  $("res-price").textContent = fmtRs(data.price);
  $("res-target").textContent = fmtRs(data.target);
  $("res-rsi").textContent = data.rsi ?? "—";
  $("res-trend").textContent = data.trend ?? "—";
  const vn = data.vs_nifty_20d;
  $("res-vs-nifty").textContent = vn != null ? `${vn >= 0 ? "+" : ""}${vn}%` : "—";
  $("res-qty").textContent = data.buy_qty ? `${data.buy_qty} @ ${fmtRs(data.buy_amount)}` : "—";

  const reasons = data.reasons || [];
  $("res-reasons").innerHTML = reasons.length
    ? "<ul>" + reasons.map((r) => `<li>${r}</li>`).join("") + "</ul>"
    : "";

  const newsEl = $("res-news");
  if (data.news_headlines && data.news_headlines.length) {
    newsEl.classList.remove("hidden");
    newsEl.innerHTML = "<strong>News</strong><ul>" +
      data.news_headlines.map((n) => `<li>${n.title}</li>`).join("") + "</ul>";
  } else if (data.news_summary) {
    newsEl.classList.remove("hidden");
    newsEl.innerHTML = `<strong>News</strong><p>${data.news_summary}</p>`;
  } else {
    newsEl.classList.add("hidden");
  }

  const aiEl = $("res-ai");
  if (data.ai_note) {
    aiEl.classList.remove("hidden");
    aiEl.innerHTML = `<strong>AI Analyst</strong><p>${data.ai_note}</p>`;
  } else {
    aiEl.classList.add("hidden");
  }

  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    renderMarket(data.benchmark);
    renderPosition(data.position);
    renderPicks(data.top_picks, data.report_date);
    $("report-preview").textContent = data.report_preview || "No morning report saved yet.";
  } catch (e) {
    toast("Could not load dashboard");
  }
}

async function runAnalyze(symbol) {
  symbol = (symbol || "").trim().toUpperCase();
  if (!symbol) {
    toast("Enter a stock symbol");
    return;
  }

  $("loading").classList.remove("hidden");
  $("result-card").classList.add("hidden");
  $("btn-analyze").disabled = true;

  try {
    const res = await fetch(`/api/analyze/${encodeURIComponent(symbol)}`);
    const data = await res.json();
    if (!data.ok) {
      toast(data.error || "Analysis failed");
      return;
    }
    renderResult(data);
  } catch (e) {
    toast("Network error — retry in a moment (cloud may be waking up)");
  } finally {
    $("loading").classList.add("hidden");
    $("btn-analyze").disabled = false;
  }
}

async function shareResult() {
  if (!lastShareText) {
    toast("Run analysis first");
    return;
  }
  if (navigator.share) {
    try {
      await navigator.share({
        title: `Stock Analyst — ${lastResult?.symbol || ""}`,
        text: lastShareText,
      });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  await copyText(lastShareText);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard");
  } catch (e) {
    toast("Copy failed");
  }
}

async function positionAction(action) {
  if (action === "sell" && !confirm("Record that you sold in broker?")) return;
  if (action === "average" && !confirm("Record average down in broker?")) return;

  try {
    const res = await fetch(`/api/position/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const data = await res.json();
    if (data.ok) {
      toast(action === "sell" ? "Position closed" : "Recorded");
      loadDashboard();
    } else {
      toast(data.error || "Failed");
    }
  } catch (e) {
    toast("Action failed");
  }
}

function initChips() {
  const row = $("quick-chips");
  row.innerHTML = QUICK.map((s) => `<button type="button" class="chip" data-sym="${s}">${s}</button>`).join("");
  row.querySelectorAll(".chip").forEach((c) => {
    c.addEventListener("click", () => {
      $("symbol-input").value = c.dataset.sym;
      runAnalyze(c.dataset.sym);
    });
  });
}

$("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  runAnalyze($("symbol-input").value);
});

$("btn-share").addEventListener("click", shareResult);
$("btn-copy").addEventListener("click", () => copyText(lastShareText));
$("btn-refresh").addEventListener("click", loadDashboard);

$("position-actions").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (btn) positionAction(btn.dataset.action);
});

initChips();
loadDashboard();