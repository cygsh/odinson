"""Thread-safe shared state between the collector, the web UI and the cloud bridge."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class MonitorState:
    """Rolling buffers + counters, guarded by a single lock."""

    buffer_size: int = 200
    mode: str = "serial"  # "serial" | "mock"
    started_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.lock = threading.Lock()
        self.time_buffer: deque[str] = deque(maxlen=self.buffer_size)
        self.delta_buffer: deque[float] = deque(maxlen=self.buffer_size)
        self.latest: dict = {"time": "", "delta": 0.0, "alert": 0}
        self.sample_count: int = 0
        self.alert_count: int = 0
        self.aws_enabled: bool = False
        self.aws_last_ok: bool | None = None

    def push(self, time_str: str, delta: float, alert: bool) -> None:
        with self.lock:
            self.time_buffer.append(time_str)
            self.delta_buffer.append(delta)
            self.latest = {"time": time_str, "delta": round(delta, 2), "alert": int(alert)}
            self.sample_count += 1
            if alert:
                self.alert_count += 1

    def snapshot_buffers(self) -> dict:
        with self.lock:
            return {"times": list(self.time_buffer), "deltas": list(self.delta_buffer)}

    def snapshot_latest(self) -> dict:
        with self.lock:
            return dict(self.latest)

    def snapshot_status(self, *, db_rows: int) -> dict:
        with self.lock:
            return {
                "mode": self.mode,
                "sample_count": self.sample_count,
                "alert_count": self.alert_count,
                "aws_enabled": self.aws_enabled,
                "aws_last_ok": self.aws_last_ok,
                "db_rows": db_rows,
                "uptime_s": round(time.time() - self.started_at, 1),
            }
