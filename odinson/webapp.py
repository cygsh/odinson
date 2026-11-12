"""Flask web UI + JSON API for the Odinson gateway.

Routes:
    GET  /                          live monitor page
    GET  /history_view              historical data page
    GET  /latest                    latest reading (JSON)
    GET  /buffer                    rolling waveform buffers (JSON)
    GET  /history?limit=N           recent persisted rows (JSON)
    GET  /history/<start>/<end>     rows in a time range (JSON)
    GET  /status                    gateway status: mode, counts, AWS state (JSON)
    GET  /health                    liveness probe (JSON)
    POST /shutdown                  stop the werkzeug server
"""
from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template, request

from .config import BASE_DIR, Settings
from .state import MonitorState
from .storage import SQLiteStore

logger = logging.getLogger(__name__)

TEMPLATE_DIR = BASE_DIR / "templates"


def create_app(settings: Settings, store: SQLiteStore, state: MonitorState) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/latest")
    def latest():
        return jsonify(state.snapshot_latest())

    @app.route("/buffer")
    def buffer():
        return jsonify(state.snapshot_buffers())

    @app.route("/history")
    def history():
        limit = request.args.get("limit", default=500, type=int) or 500
        data = store.recent(limit=limit)
        return jsonify(
            {
                "times": [d["time"] for d in data],
                "deltas": [d["delta"] for d in data],
                "alerts": [d["alert"] for d in data],
            }
        )

    @app.route("/history/<start_time>/<end_time>")
    def history_range(start_time: str, end_time: str):
        data = store.by_range(start_time, end_time)
        return jsonify(
            {
                "times": [d["time"] for d in data],
                "deltas": [d["delta"] for d in data],
                "alerts": [d["alert"] for d in data],
            }
        )

    @app.route("/history_view")
    def history_view():
        return render_template("history.html")

    @app.route("/status")
    def status():
        return jsonify(state.snapshot_status(db_rows=store.count()))

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        func = request.environ.get("werkzeug.server.shutdown")
        if func is None:
            return jsonify({"status": "not running under the werkzeug server"}), 400
        func()
        return jsonify({"status": "shutting down"})

    return app
