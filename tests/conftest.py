import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odinson.config import Settings  # noqa: E402
from odinson.state import MonitorState  # noqa: E402
from odinson.storage import SQLiteStore  # noqa: E402


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        db_path=tmp_path / "test.db",
        log_dir=tmp_path / "logs",
        aws_enabled=False,
        telegram_bot_token="",
        telegram_chat_id="",
    )


@pytest.fixture()
def store(tmp_path) -> SQLiteStore:
    return SQLiteStore(tmp_path / "test.db")


@pytest.fixture()
def state() -> MonitorState:
    return MonitorState(buffer_size=50, mode="mock")
