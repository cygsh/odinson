"""Data models and wire-format parsing for sensor readings."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Reading:
    """One calibrated 3-axis acceleration sample."""

    ax: float
    ay: float
    az: float
    timestamp: str = ""        # local HH:MM:SS.mmm — kept for the web UI / history pages
    iso_timestamp: str = ""    # UTC ISO-8601 — used as the DynamoDB sort key
    device_id: str = "odinson-01"
    source: str = "serial"     # "serial" | "mock"

    @classmethod
    def from_accel(
        cls,
        ax: float,
        ay: float,
        az: float,
        *,
        device_id: str = "odinson-01",
        source: str = "serial",
        now: datetime | None = None,
    ) -> Reading:
        now = now or datetime.now()
        utc = datetime.now(timezone.utc)
        return cls(
            ax=ax,
            ay=ay,
            az=az,
            timestamp=now.strftime("%H:%M:%S.%f")[:-3],
            iso_timestamp=utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            device_id=device_id,
            source=source,
        )


def parse_serial_line(line: str) -> tuple[float, float, float] | None:
    """Parse one line from the Arduino into ``(ax, ay, az)``.

    Supports the firmware-v2 JSON wire format ``{"t": 123, "ax": 1, "ay": 2, "az": 3}``
    and the legacy CSV format ``millis,ax,ay,az``. Returns ``None`` for non-data
    lines (boot banners, calibration messages, garbage) so callers can skip them.
    """
    line = line.strip()
    if not line:
        return None
    if line.startswith("{"):
        try:
            payload = json.loads(line)
            return (float(payload["ax"]), float(payload["ay"]), float(payload["az"]))
        except (ValueError, KeyError, TypeError):
            return None
    parts = line.split(",")
    if len(parts) >= 4:
        try:
            return (float(parts[1]), float(parts[2]), float(parts[3]))
        except ValueError:
            return None
    return None
