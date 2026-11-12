"""Environment-driven configuration for the Odinson gateway.

Every secret and environment-specific value comes from environment variables,
optionally loaded from a local ``.env`` file (which is never committed — see
``.gitignore``). Copy ``.env.example`` to ``.env`` and fill in your values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path = BASE_DIR / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines, '#' comments).

    Existing environment variables win — real env always overrides the file.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def _get_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for one gateway process."""

    # --- serial / sensor ---
    serial_port: str = "COM3"
    baud_rate: int = 115200
    mock_mode: bool = False
    device_id: str = "odinson-01"

    # --- detection ---
    alert_threshold: float = 15.0   # delta above this => alert (sound + Telegram + SNS)
    log_threshold: float = 2.0      # delta above this => persisted to CSV/SQLite/DynamoDB
    baseline_alpha: float = 0.05    # EWMA weight of new samples in the adaptive baseline
    buffer_size: int = 200          # rolling window for the live waveform

    # --- sampling (mock source) ---
    sample_period_s: float = 0.05   # 20 Hz
    mock_spike_probability: float = 0.05

    # --- local storage ---
    db_path: Path = BASE_DIR / "vibration_data.db"
    log_dir: Path = BASE_DIR / "logs"

    # --- web UI ---
    host: str = "0.0.0.0"
    port: int = 5000

    # --- Telegram alerts (get a token from @BotFather; never commit it) ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- AWS cloud bridge ---
    aws_enabled: bool = False
    aws_region: str = "ap-south-1"
    aws_endpoint_url: str = ""      # set to a LocalStack URL to emulate AWS locally
    dynamodb_table: str = "odinson-readings"
    sns_topic_arn: str = ""
    s3_bucket: str = ""
    cloudwatch_namespace: str = "Odinson"
    cloud_publish_every: int = 5    # persist every Nth reading to DynamoDB/CloudWatch
                                    # (20 Hz sampling -> 4 writes/s: far inside the
                                    #  permanent 25 WCU DynamoDB free tier)
    s3_archive_interval_s: float = 300.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            serial_port=_get_str("ODINSON_SERIAL_PORT", "COM3"),
            baud_rate=_get_int("ODINSON_BAUD_RATE", 115200),
            mock_mode=_get_bool("ODINSON_MOCK", False),
            device_id=_get_str("ODINSON_DEVICE_ID", "odinson-01"),
            alert_threshold=_get_float("ODINSON_ALERT_THRESHOLD", 15.0),
            log_threshold=_get_float("ODINSON_LOG_THRESHOLD", 2.0),
            baseline_alpha=_get_float("ODINSON_BASELINE_ALPHA", 0.05),
            buffer_size=_get_int("ODINSON_BUFFER_SIZE", 200),
            sample_period_s=_get_float("ODINSON_SAMPLE_PERIOD_S", 0.05),
            mock_spike_probability=_get_float("ODINSON_MOCK_SPIKE_PROBABILITY", 0.05),
            db_path=Path(_get_str("ODINSON_DB_PATH", str(BASE_DIR / "vibration_data.db"))),
            log_dir=Path(_get_str("ODINSON_LOG_DIR", str(BASE_DIR / "logs"))),
            host=_get_str("ODINSON_HOST", "0.0.0.0"),
            port=_get_int("ODINSON_PORT", 5000),
            telegram_bot_token=_get_str("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=_get_str("TELEGRAM_CHAT_ID", ""),
            aws_enabled=_get_bool("ODINSON_AWS_ENABLED", False),
            aws_region=_get_str("ODINSON_AWS_REGION", os.environ.get("AWS_REGION", "ap-south-1")),
            aws_endpoint_url=_get_str("ODINSON_AWS_ENDPOINT_URL", os.environ.get("AWS_ENDPOINT_URL", "")),
            dynamodb_table=_get_str("ODINSON_DYNAMODB_TABLE", "odinson-readings"),
            sns_topic_arn=_get_str("ODINSON_SNS_TOPIC_ARN", ""),
            s3_bucket=_get_str("ODINSON_S3_BUCKET", ""),
            cloudwatch_namespace=_get_str("ODINSON_CLOUDWATCH_NAMESPACE", "Odinson"),
            cloud_publish_every=_get_int("ODINSON_CLOUD_PUBLISH_EVERY", 5),
            s3_archive_interval_s=_get_float("ODINSON_S3_ARCHIVE_INTERVAL_S", 300.0),
        )
