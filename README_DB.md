# Odinson v2 notes (legacy)

The database + history-view version of the app has been folded into the v3
architecture. Everything v2 did still works — it now lives in the `odinson`
package:

- SQLite storage + history page → `odinson/storage.py`, `odinson/webapp.py`, `templates/history.html`
- Live monitor → `templates/index.html`
- Old entrypoint → `python/maincode_with_db.py` (shim that forwards to `run.py`)

**Run the current version from the repo root:**

```bash
python run.py            # live hardware
python run.py --mock     # no hardware
```

See the main [README.md](README.md) and [docs/](docs/) for the full guide,
including the AWS deployment.
