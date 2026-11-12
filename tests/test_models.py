from odinson.models import Reading, parse_serial_line


def test_parse_json_wire_format():
    assert parse_serial_line('{"t": 123, "ax": 10, "ay": -4, "az": 16384}') == (10.0, -4.0, 16384.0)


def test_parse_legacy_csv_format():
    assert parse_serial_line("1234,10,-4,16384") == (10.0, -4.0, 16384.0)


def test_parse_ignores_banners_and_garbage():
    assert parse_serial_line("Calibrating MPU6050...") is None
    assert parse_serial_line("INFO calibration done") is None
    assert parse_serial_line("") is None
    assert parse_serial_line("not,a,number,here") is None
    assert parse_serial_line('{"t": 1}') is None  # missing axes


def test_reading_carries_both_timestamp_formats():
    r = Reading.from_accel(1, 2, 3, device_id="dev-1", source="mock")
    assert r.device_id == "dev-1"
    assert r.source == "mock"
    assert len(r.timestamp) == 12  # HH:MM:SS.mmm
    assert "T" in r.iso_timestamp and r.iso_timestamp.endswith("Z")
