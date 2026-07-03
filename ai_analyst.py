"""AI brief for daily stock signal."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text(encoding="utf-8"))


def load_ai_keys() -> bool:
    if os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return True
    ai_tools = Path(CONFIG.get("ai_tools_path", r"D:\BINAY-Projects\01-GLM-AI-Tools"))
    ps1 = ai_tools / "load-ai-keys.ps1"
    if not ps1.exists():
        return False
    script = (
        f"& '{ps1}' | Out-Null; "
        "@{GEMINI_API_KEY=$env:GEMINI_API_KEY; GROQ_API_KEY=$env:GROQ_API_KEY; "
        "OPENROUTER_API_KEY=$env:OPENROUTER_API_KEY; GLM_API_KEY=$env:GLM_API_KEY} "
        "| ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            cwd=str(ai_tools),
            check=True,
            capture_output=True,
            text=True,
        )
        keys = json.loads(result.stdout.strip())
        loaded = 0
        for name, value in keys.items():
            if value:
                os.environ[name] = value
                loaded += 1
        return loaded > 0
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return False


def _ask_groq_cloud(prompt: str) -> str:
    import requests

    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.4,
            },
            timeout=45,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _ask(prompt: str) -> str:
    if os.environ.get("GROQ_API_KEY"):
        text = _ask_groq_cloud(prompt)
        if text:
            return text
    ai_tools = Path(CONFIG.get("ai_tools_path", r"D:\BINAY-Projects\01-GLM-AI-Tools"))
    if not ai_tools.exists():
        return ""
    sys.path.insert(0, str(ai_tools))
    try:
        from ai_client import ask  # noqa: WPS433
        text, _provider = ask(prompt)
        return text.strip()
    except Exception:
        return ""


def generate_morning_briefing(
    picks: list[dict],
    market_headlines: list[dict],
    benchmark: dict,
) -> str:
    if not CONFIG.get("ai_enabled", True):
        return ""
    if not load_ai_keys():
        return ""

    pick_lines = []
    for p in picks[:5]:
        pick_lines.append(
            f"- {p['symbol']}: score {p.get('swing_score')}, signal {p.get('signal')}, "
            f"RSI {p.get('rsi')}, news: {p.get('news_summary', '')[:80]}"
        )
    headlines = "\n".join(f"- {h['title'][:80]}" for h in market_headlines[:8])

    prompt = f"""Indian stock swing analyst. Morning briefing max 250 words.

Strategy: 3% profit delivery swing, Rs.30,000 per trade, Nifty 50 + Next 50 only.
Market: {benchmark.get('mood')} mood, Nifty 20d {benchmark.get('change_20d', 0):+.1f}%

Top research picks:
{chr(10).join(pick_lines)}

Market headlines:
{headlines}

Include: market mood, top 2-3 pick highlights, key risks, end with not SEBI advice."""

    text = _ask(prompt)
    return f"[AI Morning Brief]\n{text}" if text else ""


def analyze_buy(pick: dict, benchmark: dict) -> str:
    if not CONFIG.get("ai_enabled", True):
        return ""
    if not load_ai_keys():
        return ""

    reasons = "; ".join(pick.get("reasons", [])[:3])
    prompt = f"""You are an Indian swing trading analyst. Write 3-4 short sentences (max 80 words).

Strategy: delivery swing, sell at +3% profit within 1 week. On -3% loss, average 30% more (max 5 times).

Market: Nifty mood {benchmark.get('mood', 'NEUTRAL')}, 20d {benchmark.get('change_20d', 0):+.1f}%

Today's BUY pick: {pick['symbol']} ({pick.get('index_group', '')})
Score {pick.get('swing_score', 0)}, RSI {pick.get('rsi')}, trend {pick.get('trend')}
Entry Rs.{pick.get('entry', 0):.2f}, target Rs.{pick.get('target', 0):.2f}
Reasons: {reasons}
News: {pick.get('news_summary', 'No recent news')}

Explain why this stock fits a 3% swing in ~5-7 days. One risk line. No fluff."""

    return _ask(prompt)


def analyze_position(signal: dict, symbol: str) -> str:
    if not CONFIG.get("ai_enabled", True):
        return ""
    if not load_ai_keys():
        return ""

    prompt = f"""Indian swing trader. 3 sentences max.

Open position: {symbol}
Signal: {signal['signal']}
LTP Rs.{signal.get('ltp', 0):.2f}, avg Rs.{signal.get('avg_price', 0):.2f}, P&L {signal.get('pnl_pct', 0):+.2f}%
Reason: {signal.get('reason', '')}

Brief action advice for today. Not SEBI advice."""

    return _ask(prompt)