"""Vibration detection: magnitude, adaptive baseline, alert classification.

These functions are pure and side-effect free so they can be unit-tested
without any hardware (see tests/test_detector.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def compute_magnitude(ax: float, ay: float, az: float) -> float:
    """Euclidean acceleration magnitude in raw MPU6050 units."""
    return math.sqrt(ax * ax + ay * ay + az * az)


@dataclass
class BaselineTracker:
    """Exponentially-weighted moving baseline of the acceleration magnitude.

    Slow drift (temperature, mounting creep) is absorbed into the baseline;
    sudden motion produces a large deviation (delta) from it.
    """

    alpha: float = 0.05
    baseline: float | None = None

    def update(self, magnitude: float) -> float:
        """Feed a new magnitude; returns the absolute deviation from the baseline."""
        if self.baseline is None:
            self.baseline = magnitude
            return 0.0
        delta = abs(magnitude - self.baseline)
        self.baseline = (1.0 - self.alpha) * self.baseline + self.alpha * magnitude
        return delta


class AlertLatch:
    """Fires exactly once on the rising edge of an alert; resets when it goes quiet.

    Prevents alert spam: one Telegram/SNS/sound notification per event, not per sample.
    """

    def __init__(self) -> None:
        self.active = False

    def update(self, delta: float, threshold: float) -> bool:
        if delta > threshold:
            if not self.active:
                self.active = True
                return True
        else:
            self.active = False
        return False


def classify(delta: float, *, alert_threshold: float, log_threshold: float) -> tuple[bool, bool]:
    """Return ``(is_alert, should_log)`` for a deviation value."""
    return delta > alert_threshold, delta > log_threshold
