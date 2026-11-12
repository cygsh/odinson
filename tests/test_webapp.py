from odinson.webapp import create_app


def make_client(settings, store, state):
    app = create_app(settings, store, state)
    app.config["TESTING"] = True
    return app.test_client()


def test_health(settings, store, state):
    client = make_client(settings, store, state)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_latest_and_buffer_reflect_pushed_samples(settings, store, state):
    state.push("10:00:00.000", 3.5, False)
    client = make_client(settings, store, state)
    latest = client.get("/latest").get_json()
    assert latest == {"time": "10:00:00.000", "delta": 3.5, "alert": 0}
    buf = client.get("/buffer").get_json()
    assert buf == {"times": ["10:00:00.000"], "deltas": [3.5]}


def test_history_endpoints(settings, store, state):
    store.insert(timestamp="10:00:01.000", delta=5.0, alert=1)
    store.insert(timestamp="10:00:02.000", delta=6.0, alert=0)
    client = make_client(settings, store, state)
    hist = client.get("/history?limit=10").get_json()
    assert hist["times"] == ["10:00:01.000", "10:00:02.000"]
    assert hist["alerts"] == [1, 0]
    ranged = client.get("/history/10:00:00.000/10:00:01.500").get_json()
    assert ranged["times"] == ["10:00:01.000"]


def test_status_reports_mode_and_counts(settings, store, state):
    state.aws_enabled = True
    state.push("10:00:00.000", 20.0, True)
    client = make_client(settings, store, state)
    status = client.get("/status").get_json()
    assert status["mode"] == "mock"
    assert status["aws_enabled"] is True
    assert status["sample_count"] == 1
    assert status["alert_count"] == 1
    assert status["db_rows"] == 0


def test_pages_render(settings, store, state):
    client = make_client(settings, store, state)
    assert client.get("/").status_code == 200
    assert b"Odinson" in client.get("/").data
    assert client.get("/history_view").status_code == 200
