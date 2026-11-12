# Architecture

## Data flow

```
MPU6050 --I2C--> Arduino --USB/serial JSON @20Hz--> gateway collector
    -> magnitude = sqrt(ax^2+ay^2+az^2)
    -> delta = |magnitude - EWMA baseline|          (odinson/detector.py)
    -> classify: alert if delta > ALERT_THRESHOLD, log if delta > LOG_THRESHOLD
    -> push to shared state (web UI buffers)
    -> CSV log + SQLite row          (local persistence, odinson/storage.py)
    -> AWS bridge (optional)         (DynamoDB + SNS + CloudWatch + S3)
```

## Wire format (serial)

Firmware v2 emits one JSON object per sample:

```
{"t": 12034, "ax": 12, "ay": -8, "az": 16390}
```

`odinson/models.py::parse_serial_line` accepts this and the legacy CSV format
`millis,ax,ay,az`; anything else (boot banners, `INFO ...` lines) is skipped.

## Threading model (run.py)

- **collector thread** — reads the sensor source (serial with auto-reconnect, falling back to
  mock after 3 failed connects; or `--mock`), runs detection, persists, publishes to AWS.
- **web thread** — Flask/werkzeug serving the UI + JSON API on `ODINSON_PORT` (default 5000).
- **main thread** — matplotlib live plot (skipped with `--no-plot`, e.g. in Docker/headless).

All shared state goes through `MonitorState`'s lock; SQLite access is serialized with a lock
and one connection per operation.

## Local storage schema

`vibration_data` (SQLite) — v2-compatible, migrated in place on open:

| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | |
| timestamp | TEXT | `HH:MM:SS.mmm` local — used by the history UI range queries |
| iso_timestamp | TEXT | UTC ISO-8601 |
| delta | REAL | deviation from baseline |
| alert | INTEGER | 0/1 |
| device_id | TEXT | |
| source | TEXT | `serial` / `mock` |

CSV logs: `logs/vibration_log_<run-timestamp>.csv`, line-buffered.

## AWS data model

DynamoDB table `odinson-readings`:

| attribute | role |
|-----------|------|
| `device_id` (S) | partition key |
| `ts` (S) | sort key — ISO-8601 UTC |
| `delta`, `alert`, `timestamp`, `source` | payload |
| `expires_at` (N) | TTL attribute — rows auto-delete after 90 days |

CloudWatch custom metrics in namespace `Odinson`: `Delta` (unit None) and `Alert` (Count),
dimensioned by `device_id`. Alarms: alert-sum → SNS; `AWS/Billing EstimatedCharges > $1` → SNS
guardrail. See `cloud/infrastructure/odinson-stack.yaml` and `cloud/monitoring/dashboard.json`.

## Alerting

`AlertLatch` fires once per rising edge, so a 20 Hz alert stream produces exactly one
Telegram/SNS/sound notification per event. Notifiers never crash the collector (all wrapped).
