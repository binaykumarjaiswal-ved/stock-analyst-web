#!/usr/bin/env python3
"""Stock Analyst — cloud web dashboard."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, render_template, request

from webapp.services import (
    analyze_symbol,
    cron_morning_scan,
    format_share_text,
    get_dashboard,
    get_report,
    get_scan_status_api,
    list_reports,
    position_action,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "service": "stock-analyst-web"})


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard())


@app.route("/api/scan-status")
def api_scan_status():
    return jsonify(get_scan_status_api())


@app.route("/api/cron/morning")
def api_cron_morning():
    key = request.args.get("key", "")
    return jsonify(cron_morning_scan(key))


@app.route("/api/analyze/<symbol>")
def api_analyze(symbol: str):
    with_ai = request.args.get("ai", "1") != "0"
    data = analyze_symbol(symbol, with_ai=with_ai)
    if data.get("ok"):
        data["share_text"] = format_share_text(data)
    return jsonify(data)


@app.route("/api/share/<symbol>")
def api_share(symbol: str):
    data = analyze_symbol(symbol, with_ai=True)
    return jsonify({"text": format_share_text(data)})


@app.route("/api/reports")
def api_reports():
    return jsonify({"reports": list_reports()})


@app.route("/api/reports/<date>")
def api_report(date: str):
    return jsonify(get_report(date))


@app.route("/api/position/<action>", methods=["POST"])
def api_position(action: str):
    body = request.get_json(silent=True) or {}
    result = position_action(
        action,
        symbol=body.get("symbol"),
        price=body.get("price"),
    )
    return jsonify(result)


def main():
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()