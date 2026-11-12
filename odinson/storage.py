"""Local persistence: a thread-safe SQLite store (with legacy-schema migration)
and an append-only CSV logger (one file per run, line-buffered)."""
from __future__ import annotations

import csv
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

# Columns added since v2 of the app. Used to migrate old databases in place
# (SQLite can't ADD COLUMN with NOT NULL and no default, so keep these plain).
_EXTRA_COLUMNS = {
    "iso_timestamp": "TEXT",
    "device_id": "TEXT",
    "source": "TEXT",
}


class SQLiteStore:
    """Thread-safe SQLite storage for vibration records."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vibration_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        delta REAL NOT NULL,
                        alert INTEGER DEFAULT 0
                    )
                    """
                )
                existing = {row["name"] for row in conn.execute("PRAGMA table_info(vibration_data)")}
                for column, decl in _EXTRA_COLUMNS.items():
                    if column not in existing:
                        conn.execute(f"ALTER TABLE vibration_data ADD COLUMN {column} {decl}")
                conn.commit()
        finally:
            conn.close()

    def insert(
        self,
        *,
        timestamp: str,
        delta: float,
        alert: int,
        iso_timestamp: str = "",
        device_id: str = "",
        source: str = "",
    ) -> None:
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    "INSERT INTO vibration_data (timestamp, iso_timestamp, delta, alert, device_id, source)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (timestamp, iso_timestamp, delta, alert, device_id, source),
                )
                conn.commit()
        finally:
            conn.close()

    def recent(self, limit: int = 500) -> list[dict]:
        """Most recent ``limit`` rows, returned oldest-first."""
        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    "SELECT timestamp, delta, alert FROM vibration_data ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        finally:
            conn.close()
        return [
            {"time": r["timestamp"], "delta": r["delta"], "alert": r["alert"]}
            for r in reversed(rows)
        ]

    def by_range(self, start_time: str, end_time: str) -> list[dict]:
        """Rows whose ``HH:MM:SS.mmm`` timestamp falls within [start, end]."""
        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    "SELECT timestamp, delta, alert FROM vibration_data"
                    " WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
                    (start_time, end_time),
                ).fetchall()
        finally:
            conn.close()
        return [{"time": r["timestamp"], "delta": r["delta"], "alert": r["alert"]} for r in rows]

    def count(self) -> int:
        conn = self._connect()
        try:
            with self._lock:
                return int(conn.execute("SELECT COUNT(*) AS n FROM vibration_data").fetchone()["n"])
        finally:
            conn.close()


class CSVLogger:
    """Append-only CSV log; one file per process run, line-buffered for crash safety."""

    def __init__(self, log_dir: Path | str) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        run_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = self.log_dir / f"vibration_log_{run_stamp}.csv"
        self._file = open(self.path, "w", newline="", buffering=1)
        self._writer = csv.writer(self._file)
        self._writer.writerow(["time_24h", "delta", "alert", "iso_timestamp", "device_id", "source"])
        self._lock = threading.Lock()

    def log(
        self,
        *,
        timestamp: str,
        delta: float,
        alert: int,
        iso_timestamp: str = "",
        device_id: str = "",
        source: str = "",
    ) -> None:
        with self._lock:
            self._writer.writerow([timestamp, round(delta, 2), alert, iso_timestamp, device_id, source])

    def close(self) -> None:
        with self._lock:
            if not self._file.closed:
                self._file.close()
