"""Sensor sources: live serial from the Arduino, or a synthetic mock for demos/tests.

Both yield :class:`odinson.models.Reading` objects until the ``running`` event
is cleared, so the collector loop is identical for hardware and simulation.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Iterator

from .config import Settings
from .models import Reading, parse_serial_line

logger = logging.getLogger(__name__)

_SERIAL_FALLBACK_ATTEMPTS = 3  # after this many failed connects, drop to mock mode


def _wait_interruptibly(running: threading.Event, seconds: float) -> None:
    """Sleep up to ``seconds``, waking early if ``running`` is cleared.

    (Event.wait(timeout) returns immediately when the event is *set*, so it
    cannot be used for throttling — this helper sleeps in small slices.)
    """
    deadline = time.monotonic() + seconds
    while running.is_set() and time.monotonic() < deadline:
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


class SerialSource:
    """Reads JSON/CSV lines from the Arduino over USB serial, reconnecting on failure.

    If the port never opens (no hardware attached), falls back to mock data so
    the UI/cloud pipeline can still be exercised end-to-end.
    """

    def __init__(self, settings: Settings, running: threading.Event) -> None:
        self._s = settings
        self._running = running

    def readings(self) -> Iterator[Reading]:
        import serial  # pyserial — imported lazily so mock mode works without it

        failures = 0
        while self._running.is_set():
            try:
                ser = serial.Serial(self._s.serial_port, self._s.baud_rate, timeout=1)
            except Exception as exc:
                failures += 1
                if failures >= _SERIAL_FALLBACK_ATTEMPTS:
                    logger.warning(
                        "Serial port %s unavailable after %d attempts (%s); switching to MOCK data",
                        self._s.serial_port, failures, exc,
                    )
                    yield from MockSource(self._s, self._running).readings()
                    return
                logger.warning("Serial port %s unavailable (%s); retrying...", self._s.serial_port, exc)
                _wait_interruptibly(self._running, 2.0)
                continue
            logger.info("Serial connected on %s @ %d baud", self._s.serial_port, self._s.baud_rate)
            try:
                while self._running.is_set():
                    line = ser.readline().decode("utf-8", errors="replace")
                    accel = parse_serial_line(line)
                    if accel is None:
                        continue
                    ax, ay, az = accel
                    yield Reading.from_accel(ax, ay, az, device_id=self._s.device_id, source="serial")
            except Exception as exc:
                logger.warning("Serial read error: %s; will reconnect", exc)
            finally:
                try:
                    ser.close()
                except Exception:
                    pass


class MockSource:
    """Synthetic ~20 Hz vibration signal with occasional spikes. No hardware needed."""

    def __init__(self, settings: Settings, running: threading.Event, seed: int | None = None) -> None:
        self._s = settings
        self._running = running
        self._rng = random.Random(seed)

    def readings(self) -> Iterator[Reading]:
        baseline = 1.0  # ~1g at rest on the z-axis
        while self._running.is_set():
            if self._rng.random() < self._s.mock_spike_probability:
                magnitude = baseline + self._rng.uniform(10.0, 30.0)  # simulated event
            else:
                magnitude = baseline + (self._rng.random() - 0.5) * 0.5  # sensor noise
            baseline = 0.95 * baseline + 0.05 * magnitude
            yield Reading.from_accel(0.0, 0.0, magnitude, device_id=self._s.device_id, source="mock")
            _wait_interruptibly(self._running, self._s.sample_period_s)


def open_source(settings: Settings, running: threading.Event, force_mock: bool = False):
    """Factory: mock when requested, serial otherwise (serial itself falls back to mock)."""
    if force_mock or settings.mock_mode:
        return MockSource(settings, running)
    return SerialSource(settings, running)
