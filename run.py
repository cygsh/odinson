#!/usr/bin/env python3
"""Odinson gateway entrypoint.

Usage:
    python run.py                     # live serial mode (falls back to mock without hardware)
    python run.py --mock              # synthetic data, no hardware needed
    python run.py --mock --no-plot    # headless (servers, Docker)
    python run.py --port 8080         # different web UI port

All configuration comes from environment variables / .env (see .env.example).
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import threading
import time

from odinson.alerts import AlertManager, SoundNotifier, TelegramNotifier
from odinson.cloud.aws_bridge import AWSBridge
from odinson.config import Settings
from odinson.detector import BaselineTracker, classify, compute_magnitude
from odinson.sensor import open_source
from odinson.state import MonitorState
from odinson.storage import CSVLogger, SQLiteStore
from odinson.webapp import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("odinson")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Odinson vibration monitoring gateway")
    parser.add_argument("--mock", action="store_true", help="use synthetic data instead of serial")
    parser.add_argument("--host", default=None, help="web UI host (default: ODINSON_HOST or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="web UI port (default: ODINSON_PORT or 5000)")
    parser.add_argument("--no-plot", action="store_true", help="disable the matplotlib live plot (headless)")
    parser.add_argument("--no-cloud", action="store_true", help="disable the AWS cloud bridge")
    return parser.parse_args()


def run_collector(
    settings: Settings,
    store: SQLiteStore,
    csv_log: CSVLogger,
    state: MonitorState,
    bridge: AWSBridge,
    alert_manager: AlertManager,
    running: threading.Event,
    force_mock: bool,
) -> None:
    """Read samples -> detect -> persist locally -> publish to AWS."""
    tracker = BaselineTracker(alpha=settings.baseline_alpha)
    source = open_source(settings, running, force_mock=force_mock)
    for reading in source.readings():
        if not running.is_set():
            break
        magnitude = compute_magnitude(reading.ax, reading.ay, reading.az)
        delta = tracker.update(magnitude)
        is_alert, should_log = classify(
            delta,
            alert_threshold=settings.alert_threshold,
            log_threshold=settings.log_threshold,
        )
        state.push(reading.timestamp, delta, is_alert)
        if alert_manager.process(delta):
            logger.warning("ALERT: delta=%.2f at %s (device=%s)", delta, reading.timestamp, reading.device_id)
        if should_log:
            csv_log.log(
                timestamp=reading.timestamp,
                delta=delta,
                alert=int(is_alert),
                iso_timestamp=reading.iso_timestamp,
                device_id=reading.device_id,
                source=reading.source,
            )
            store.insert(
                timestamp=reading.timestamp,
                delta=delta,
                alert=int(is_alert),
                iso_timestamp=reading.iso_timestamp,
                device_id=reading.device_id,
                source=reading.source,
            )
        if bridge.publish_reading(
            iso_timestamp=reading.iso_timestamp,
            timestamp=reading.timestamp,
            delta=delta,
            alert=int(is_alert),
            device_id=reading.device_id,
            source=reading.source,
        ):
            state.aws_last_ok = True
        elif bridge.enabled:
            state.aws_last_ok = False
        bridge.maybe_archive_log(csv_log.path)


def _wait(running: threading.Event) -> None:
    try:
        while running.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def _run_plot(running: threading.Event, state: MonitorState, settings: Settings) -> None:
    """Live matplotlib waveform in the main thread (skipped with --no-plot / headless)."""
    try:
        import matplotlib

        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        logger.warning("matplotlib unavailable (%s); running headless", exc)
        _wait(running)
        return

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Real-time Vibration Delta")
    ax.set_xlabel("Sample")
    ax.set_ylabel("Delta Magnitude")
    ax.grid(True, alpha=0.3)
    (line,) = ax.plot([], [], "w-", linewidth=2)
    ax.axhline(y=settings.log_threshold, color="white", linestyle="--", linewidth=1, alpha=0.7)
    plt.tight_layout()
    plt.show(block=False)

    try:
        while running.is_set():
            snap = state.snapshot_buffers()
            deltas = snap["deltas"]
            if deltas:
                line.set_data(range(len(deltas)), deltas)
                ax.set_xlim(0, max(len(deltas), 1))
                ymax = max(deltas) * 1.5
                ymin = min(min(deltas) * 1.5, -settings.log_threshold * 0.5)
                ax.set_ylim(ymin, max(ymax, settings.log_threshold * 3.0))
                fig.canvas.draw_idle()
            plt.pause(0.05)
    except KeyboardInterrupt:
        pass


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    if args.mock:
        settings = dataclasses.replace(settings, mock_mode=True)
    if args.no_cloud:
        settings = dataclasses.replace(settings, aws_enabled=False)
    host = args.host or settings.host
    port = args.port or settings.port
    mock = args.mock or settings.mock_mode

    running = threading.Event()
    running.set()

    store = SQLiteStore(settings.db_path)
    csv_log = CSVLogger(settings.log_dir)
    state = MonitorState(buffer_size=settings.buffer_size, mode="mock" if mock else "serial")
    state.aws_enabled = settings.aws_enabled
    bridge = AWSBridge(settings)
    notifiers = [
        TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id),
        SoundNotifier(),
    ]
    alert_manager = AlertManager(notifiers, latch_threshold=settings.alert_threshold)

    collector = threading.Thread(
        target=run_collector,
        args=(settings, store, csv_log, state, bridge, alert_manager, running, args.mock),
        name="collector",
        daemon=True,
    )
    collector.start()
    logger.info("Collector started (mode=%s)", state.mode)

    app = create_app(settings, store, state)
    flask_thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        name="web",
        daemon=True,
    )
    flask_thread.start()
    logger.info("Web UI available at http://localhost:%d", port)

    try:
        if args.no_plot:
            _wait(running)
        else:
            _run_plot(running, state, settings)
    finally:
        logger.info("Shutting down...")
        running.clear()
        collector.join(timeout=5.0)
        try:
            import requests

            requests.post(f"http://localhost:{port}/shutdown", timeout=2)
        except Exception:
            pass
        flask_thread.join(timeout=5.0)
        csv_log.close()
        bridge.close()
        logger.info("Bye.")


if __name__ == "__main__":
    main()
