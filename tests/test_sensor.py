import threading
import time

from odinson.sensor import MockSource, _wait_interruptibly


def test_mock_source_samples_at_configured_rate(settings):
    """20 Hz target: 21 samples should take ~1s, not a busy loop."""
    running = threading.Event()
    running.set()
    source = MockSource(settings, running, seed=1)
    readings = source.readings()
    start = time.monotonic()
    samples = [next(readings) for _ in range(21)]
    elapsed = time.monotonic() - start
    running.clear()
    assert 0.7 < elapsed < 2.5
    assert all(s.source == "mock" and s.device_id == settings.device_id for s in samples)


def test_wait_interruptibly_wakes_early_when_cleared():
    ev = threading.Event()
    ev.set()
    start = time.monotonic()
    t = threading.Thread(target=_wait_interruptibly, args=(ev, 30.0))
    t.start()
    time.sleep(0.1)
    ev.clear()
    t.join(timeout=2.0)
    assert not t.is_alive()
    assert time.monotonic() - start < 2.0
