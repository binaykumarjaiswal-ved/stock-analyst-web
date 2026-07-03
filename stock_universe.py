"""Nifty 50 + Nifty Next 50 universe."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
CACHE = BASE_DIR / "data" / "nifty_universe.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nseindia.com/",
}

FALLBACK_N50 = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "SBIN", "BHARTIARTL",
    "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "MARUTI", "TITAN", "SUNPHARMA",
    "WIPRO", "HCLTECH", "ULTRACEMCO", "POWERGRID", "NTPC", "ONGC", "COALINDIA",
    "TATASTEEL", "ADANIENT", "ADANIPORTS", "CIPLA", "DRREDDY", "EICHERMOT",
    "GRASIM", "HINDALCO", "HINDUNILVR", "INDUSINDBK", "JSWSTEEL", "M&M",
    "NESTLEIND", "BAJAJ-AUTO", "BAJAJFINSV", "BPCL", "BRITANNIA", "DIVISLAB",
    "HEROMOTOCO", "HDFCLIFE", "SBILIFE", "TATACONSUM", "TECHM", "APOLLOHOSP",
    "ASIANPAINT", "UPL",
]
FALLBACK_NN50 = [
    "GAIL", "VEDL", "IOC", "BANKBARODA", "PNB", "CANBK", "INDIGO", "DLF",
    "GODREJCP", "DABUR", "MARICO", "PIDILITIND", "HAVELLS", "SIEMENS", "ABB",
    "TRENT", "JINDALSTEL", "SAIL", "NMDC", "RECLTD", "LICI", "IRCTC", "NAUKRI",
    "MUTHOOTFIN", "CHOLAFIN", "BOSCHLTD", "SHREECEM", "SRF", "PIIND", "LUPIN",
    "AMBUJACEM", "BERGEPAINT", "COLPAL", "PETRONET", "ATGL", "ADANIGREEN",
    "AUROPHARMA", "BIOCON", "PERSISTENT", "OFSS", "PAGEIND", "SBICARD",
    "ICICIGI", "ICICIPRULI", "HDFCAMC", "MOTHERSON", "INDUSTOWER", "TATACOMM",
    "VBL",
]


def _fetch_index(name: str) -> list[str]:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get("https://www.nseindia.com", timeout=15)
    time.sleep(1)
    url = f"https://www.nseindia.com/api/equity-stockIndices?index={name.replace(' ', '%20')}"
    data = s.get(url, timeout=20).json()
    return [i["symbol"] for i in data.get("data", []) if i.get("symbol")]


def _pack_universe(n50: list[str], nn50: list[str], source: str) -> dict:
    all_s = list(dict.fromkeys(n50 + nn50))
    return {
        "nifty50": n50,
        "niftynext50": nn50,
        "all": all_s,
        "source": source,
    }


def get_universe() -> dict:
    if CACHE.exists():
        try:
            d = json.loads(CACHE.read_text(encoding="utf-8"))
            if datetime.now() - datetime.fromisoformat(d["updated"]) < timedelta(days=7):
                return _pack_universe(d["nifty50"], d["niftynext50"], "NSE (cached)")
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    try:
        n50 = _fetch_index("NIFTY 50")
        nn50 = _fetch_index("NIFTY NEXT 50")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(
            json.dumps({"updated": datetime.now().isoformat(), "nifty50": n50, "niftynext50": nn50}, indent=2),
            encoding="utf-8",
        )
        return _pack_universe(n50, nn50, "NSE live")
    except Exception:
        n50 = FALLBACK_N50
        nn50 = [s for s in FALLBACK_NN50 if s not in FALLBACK_N50]
        return _pack_universe(n50, nn50, "Fallback list")