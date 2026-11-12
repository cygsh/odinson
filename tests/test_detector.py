from odinson.detector import AlertLatch, BaselineTracker, classify, compute_magnitude


def test_magnitude_is_euclidean():
    assert compute_magnitude(3, 4, 0) == 5
    assert compute_magnitude(0, 0, 0) == 0


def test_baseline_first_sample_has_zero_delta():
    tracker = BaselineTracker(alpha=0.05)
    assert tracker.update(100.0) == 0.0
    assert tracker.baseline == 100.0


def test_baseline_returns_deviation_then_absorbs_drift():
    tracker = BaselineTracker(alpha=0.5)
    tracker.update(10.0)
    assert tracker.update(12.0) == 2.0  # |12 - 10|
    for _ in range(50):
        tracker.update(10.0)  # slow return to rest: baseline follows, delta shrinks
    assert abs(tracker.baseline - 10.0) < 1e-6


def test_latch_fires_once_per_rising_edge():
    latch = AlertLatch()
    assert latch.update(20, threshold=15) is True
    assert latch.update(20, threshold=15) is False  # still alerting: no repeat
    assert latch.update(5, threshold=15) is False   # quiet: latch resets
    assert latch.update(20, threshold=15) is True   # new event fires again


def test_classify_thresholds():
    assert classify(20, alert_threshold=15, log_threshold=2) == (True, True)
    assert classify(5, alert_threshold=15, log_threshold=2) == (False, True)
    assert classify(1, alert_threshold=15, log_threshold=2) == (False, False)
