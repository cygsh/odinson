"""Alerting: Telegram push + local sound, dispatched once per alert event.

Never let a failing notifier crash the collector — every call is wrapped.
"""
from __future__ import annotations

import logging
import threading
from typing import Protocol

from .detector import AlertLatch

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def notify(self, message: str) -> None: ...


class TelegramNotifier:
    """Sends messages via the Telegram Bot API. Disabled when no token is configured."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.enabled = bool(bot_token and chat_id)
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage" if bot_token else ""
        self._chat_id = chat_id

    def notify(self, message: str) -> None:
        if not self.enabled:
            return
        import requests

        try:
            resp = requests.get(
                self._url,
                params={"chat_id": self._chat_id, "text": message},
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Telegram alert failed: %s", exc)


class SoundNotifier:
    """Local audible alert: winsound beep on Windows, terminal bell elsewhere."""

    def notify(self, message: str) -> None:
        try:
            import winsound  # type: ignore[import-not-found]  # stdlib on Windows only

            threading.Thread(target=winsound.Beep, args=(1000, 500), daemon=True).start()
        except ImportError:
            print("\a", end="", flush=True)  # ASCII bell on POSIX terminals


class AlertManager:
    """Edge-triggered dispatcher: fires all notifiers once per rising alert edge."""

    def __init__(self, notifiers: list[Notifier], latch_threshold: float) -> None:
        self._notifiers = notifiers
        self._latch = AlertLatch()
        self._threshold = latch_threshold

    def process(self, delta: float, message: str = "Vibration alert: abnormal motion detected") -> bool:
        """Return True if this sample is the start of a new alert event."""
        if not self._latch.update(delta, self._threshold):
            return False
        for notifier in self._notifiers:
            try:
                notifier.notify(message)
            except Exception as exc:
                logger.warning("Notifier %s failed: %s", type(notifier).__name__, exc)
        return True
