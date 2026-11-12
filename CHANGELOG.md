# Changelog

All notable changes to Odinson are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [3.0.0] — AWS Cloud Edition — 2026-11-12

Odinson graduates from a local prototype to a full IoT pipeline:
**Arduino edge → Python gateway → AWS** (DynamoDB, Lambda, API Gateway, SNS, CloudWatch, S3, IoT Core),
all provisioned with a single CloudFormation command.

### Added
- **AWS cloud pipeline as code** — `cloud/infrastructure/odinson-stack.yaml` (SAM/CloudFormation):
  DynamoDB `odinson-readings` (on-demand, TTL 90d, PITR, SSE), ingest + query Lambdas behind an
  HTTP API (`POST/GET /readings`), an **AWS IoT Core topic rule** (`odinson/+/readings`), SNS
  `odinson-alerts` topic with email subscription, CloudWatch metrics + high-vibration alarm,
  a **$1 billing guardrail alarm**, and an encrypted S3 log bucket (public access blocked,
  lifecycle IA@30d / expire@365d).
- **Local gateway → AWS bridge** (`odinson/cloud/aws_bridge.py`): every reading → DynamoDB,
  alerts → SNS, metrics → CloudWatch, CSV logs → S3. Fail-safe — cloud outages never interrupt
  local monitoring. LocalStack support via `ODINSON_AWS_ENDPOINT_URL` for $0 local testing.
- **Cloud Lambda handlers** (`cloud/lambda/`): `ingest_handler.py` (API Gateway + IoT Core),
  `query_handler.py` (history API), plus least-privilege IAM policy (`cloud/iam/`) and an
  importable CloudWatch dashboard (`cloud/monitoring/dashboard.json`).
- **Python package refactor**: the 407-line `maincode_with_db.py` script became the `odinson/`
  package — `config` (env-driven `Settings`, `.env` support), `models` (wire-format parser),
  `detector` (magnitude / EWMA baseline / edge-triggered alert latch), `sensor` (serial with
  auto-reconnect + automatic mock fallback, mock source), `storage` (thread-safe SQLite with
  in-place v2 schema migration, CSV logger), `alerts` (Telegram + sound, never crash the
  collector), `state`, `webapp` (Flask app factory, new `/status` and `/health` endpoints).
- **Firmware v2** (`arduino/mpu6050_reader/`): JSON lines @ 20 Hz, 115200 baud, MPU6050
  connection check at boot. Legacy CSV format still parsed by the gateway.
- **Engineering hygiene**: 28 pytest tests (parser, detector, storage, web API, sensor rate,
  AWS bridge with stubbed boto3), ruff lint, GitHub Actions CI (Python 3.10 + 3.12),
  `Dockerfile`, `docker-compose.yml` with a `localstack` profile, `pyproject.toml`,
  `requirements*.txt`, `.env.example`, rewritten README with architecture diagram,
  `docs/ARCHITECTURE.md`, `docs/AWS_DEPLOYMENT.md`.
- **Web UI**: live **Source (LIVE/MOCK)** and **AWS Cloud (Synced/Off/Error)** status indicators
  on the dashboard.

### Changed
- Entrypoint is now `python run.py` from the repo root (`--mock`, `--no-plot`, `--port` flags).
  `python/maincode_with_db.py` still works — it forwards to `run.py`.
- All configuration via environment / `.env` (see `.env.example`); serial baud default
  **9600 → 115200**.
- Templates moved from `python/templates/` to `templates/`.
- Alerts fire once per event (edge-triggered latch) instead of once per sample above threshold.

### Security
- Removed the hardcoded Telegram bot token from the source. **It remains in git history —
  revoke/rotate it via @BotFather.** Secrets now live only in the gitignored `.env`.
- Gateway IAM policy is least-privilege (`cloud/iam/odinson-gateway-policy.json`).
- `vibration_data.db` and `logs/` are no longer tracked; `.gitignore` fixed (it previously
  matched `*.txt` and `config.py`, which would have ignored `requirements.txt` and
  `odinson/config.py`).

### Free-tier note
At single-sensor scale this stack stays inside the AWS Free Tier (DynamoDB 25 WCU/25 GB and
Lambda 1M req/mo are permanent free tier; API Gateway/S3/IoT Core have 12-month tiers),
with TTL, lifecycle rules, publish throttling and the billing guardrail as safety nets.

---

## [2.0.0] — 2026 (previous)

- SQLite persistence + historical data viewer (`/history_view`) with pagination, date-range
  filtering and CSV export.
- Flask web server alongside the matplotlib live plot; CSV logs in `logs/`.
- Telegram + sound alerts on threshold breach.

## [1.0.0] — initial

- MPU6050 digital seismometer: Arduino serial reader, real-time magnitude/delta computation,
  adaptive baseline, CSV logging, matplotlib live plot, Telegram alerts.
