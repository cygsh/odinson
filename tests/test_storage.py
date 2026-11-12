import sqlite3

from odinson.storage import CSVLogger, SQLiteStore


def test_insert_and_recent_are_chronological(store):
    store.insert(timestamp="10:00:01.000", delta=5.0, alert=0, iso_timestamp="t1")
    store.insert(timestamp="10:00:02.000", delta=20.0, alert=1, iso_timestamp="t2")
    rows = store.recent(limit=10)
    assert [r["time"] for r in rows] == ["10:00:01.000", "10:00:02.000"]
    assert rows[1]["alert"] == 1


def test_recent_respects_limit(store):
    for i in range(10):
        store.insert(timestamp=f"10:00:{i:02d}.000", delta=float(i), alert=0)
    assert len(store.recent(limit=3)) == 3


def test_range_query(store):
    store.insert(timestamp="10:00:01.000", delta=1, alert=0)
    store.insert(timestamp="10:00:05.000", delta=2, alert=0)
    store.insert(timestamp="10:00:09.000", delta=3, alert=1)
    rows = store.by_range("10:00:02.000", "10:00:06.000")
    assert [r["time"] for r in rows] == ["10:00:05.000"]


def test_count(store):
    assert store.count() == 0
    store.insert(timestamp="10:00:01.000", delta=1, alert=0)
    assert store.count() == 1


def test_legacy_v2_database_is_migrated_in_place(tmp_path):
    """A v2 database (only timestamp/delta/alert columns) must keep working."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE vibration_data ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " timestamp TEXT NOT NULL, delta REAL NOT NULL, alert INTEGER DEFAULT 0)"
    )
    conn.execute("INSERT INTO vibration_data (timestamp, delta, alert) VALUES ('09:00:00.000', 3.0, 0)")
    conn.commit()
    conn.close()

    store = SQLiteStore(db)
    store.insert(
        timestamp="09:00:01.000", delta=4.0, alert=1,
        iso_timestamp="iso", device_id="d", source="mock",
    )
    assert store.count() == 2
    assert store.recent(2)[1]["delta"] == 4.0


def test_csv_logger_writes_header_and_rows(tmp_path):
    log = CSVLogger(tmp_path / "logs")
    log.log(timestamp="10:00:00.000", delta=7.5, alert=1, iso_timestamp="iso", device_id="d", source="mock")
    log.close()
    lines = log.path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "time_24h,delta,alert,iso_timestamp,device_id,source"
    assert lines[1].split(",")[0] == "10:00:00.000"
    assert log.path.name.startswith("vibration_log_")
