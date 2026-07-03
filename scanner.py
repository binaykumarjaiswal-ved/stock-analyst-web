"""Scan Nifty 50 + Next 50 for best 3% swing entry (1 stock per day)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from news_fetcher import symbol_news_score
from nse_data import nse_quote
from pa_config import STOCK_SCAN_LIMIT
from stock_universe import get_universe
from strategy import enrich_pick_with_order
from technical import analyze_technicals, fetch_ohlcv

BASE_DIR = Path(__file__).parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))
TRADES_LOG = BASE_DIR / "data" / "trades_log.json"


def _load_today_buy() -> str | None:
    """Return symbol if we already signalled/picked a buy today."""
    if not TRADES_LOG.exists():
        return None
    try:
        log = json.loads(TRADES_LOG.read_text(encoding="utf-8"))
        today = datetime.now().strftime("%Y-%m-%d")
        for entry in reversed(log.get("entries", [])):
            if entry.get("date") == today and entry.get("action") == "BUY_SIGNAL":
                return entry.get("symbol")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def log_buy_signal(symbol: str, score: float, price: float) -> None:
    TRADES_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        log = json.loads(TRADES_LOG.read_text(encoding="utf-8")) if TRADES_LOG.exists() else {"entries": []}
    except json.JSONDecodeError:
        log = {"entries": []}
    log["entries"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "action": "BUY_SIGNAL",
        "symbol": symbol,
        "score": score,
        "price": price,
        "time": datetime.now().strftime("%H:%M"),
    })
    TRADES_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _apply_news_score(tech_score: float, news_items: list) -> tuple[float, dict]:
    """Blend technical score with news sentiment (from Swing Trading Agent)."""
    sent, summary = symbol_news_score(news_items)
    meta = {
        "news_sentiment": round(sent, 2),
        "news_summary": summary,
        "news_count": len(news_items),
        "tech_score": round(tech_score, 1),
    }
    if not news_items:
        return tech_score, meta

    weight = CONFIG.get("news_weight", 0.15)
    news_score = 50 + sent * 30
    blended = tech_score * (1 - weight) + news_score * weight
    if sent > 0.2:
        blended += 3
    elif sent < -0.2:
        blended -= 8
    return max(0, min(100, round(blended, 1))), meta


def scan_universe(
    symbols: list[str] | None = None,
    nifty50_set: set[str] | None = None,
    min_score: float | None = None,
    news_by_symbol: dict[str, list] | None = None,
) -> list[dict[str, Any]]:
    min_score = min_score or CONFIG.get("min_buy_score", 62)
    universe = get_universe()
    symbols = symbols or universe["all"]
    if STOCK_SCAN_LIMIT > 0:
        symbols = symbols[:STOCK_SCAN_LIMIT]
    nifty50_set = nifty50_set or set(universe["nifty50"])

    nifty_df = fetch_ohlcv("NIFTYBEES", days=60)
    if nifty_df is None:
        nifty_df = fetch_ohlcv("^NSEI", days=60)

    results = []
    for i, sym in enumerate(symbols):
        print(f"  [{i + 1}/{len(symbols)}] {sym}...", flush=True)
        tech = analyze_technicals(sym, nifty_df)
        if tech.get("status") != "ok":
            continue

        live = nse_quote(sym)
        if live and live.get("ltp", 0) > 0:
            enrich_pick_with_order(tech, live)
        else:
            tech["live_source"] = "history"
            tech["change_pct"] = 0
            enrich_pick_with_order(tech)

        score = tech["swing_score"]
        if tech["macd_bullish"] and 40 <= tech["rsi"] <= 62:
            score = min(100, score + 5)
        if tech["trend"] == "down":
            score = max(0, score - 8)

        news_items = (news_by_symbol or {}).get(sym, [])
        score, news_meta = _apply_news_score(score, news_items)

        signal = "SKIP"
        if score >= 75:
            signal = "STRONG BUY"
        elif score >= min_score:
            signal = "BUY"

        results.append({
            **tech,
            **news_meta,
            "swing_score": round(score, 1),
            "signal": signal,
            "index_group": "Nifty 50" if sym in nifty50_set else "Nifty Next 50",
        })

    results.sort(key=lambda x: x["swing_score"], reverse=True)
    return results


def pick_best_buy(results: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    if CONFIG.get("one_buy_per_day") and _load_today_buy():
        sym = _load_today_buy()
        if results:
            for r in results:
                if r["symbol"] == sym:
                    return {**r, "signal": "BUY", "already_picked_today": True}
        return {"symbol": sym, "signal": "BUY", "already_picked_today": True, "reason": "Already picked today"}

    if results is None:
        results = scan_universe()

    min_score = CONFIG.get("min_buy_score", 62)
    for r in results:
        if r["signal"] in ("BUY", "STRONG BUY") and r["swing_score"] >= min_score:
            return r
    return results[0] if results else None