"""AWS bridge tests with a fake boto3 — no AWS account or network needed."""
import sys
import types

import pytest

from odinson.cloud.aws_bridge import AWSBridge
from odinson.config import Settings


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


class FakeClient:
    def __init__(self):
        self.calls = []

    def put_metric_data(self, **kw):
        self.calls.append(("cloudwatch", kw))

    def publish(self, **kw):
        self.calls.append(("sns", kw))

    def upload_file(self, Filename, Bucket, Key):
        self.calls.append(("s3", Bucket, Key))


class FakeSession:
    last = None

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.table = FakeTable()
        self.sns = FakeClient()
        self.cw = FakeClient()
        self.s3 = FakeClient()
        FakeSession.last = self

    def resource(self, name, **kw):
        assert name == "dynamodb"
        return types.SimpleNamespace(Table=lambda table_name: self.table)

    def client(self, name, **kw):
        return {"sns": self.sns, "cloudwatch": self.cw, "s3": self.s3}[name]


@pytest.fixture()
def fake_boto3(monkeypatch):
    module = types.ModuleType("boto3")
    module.session = types.SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", module)
    return module


def make_settings(tmp_path, **overrides) -> Settings:
    base = dict(
        aws_enabled=True,
        aws_region="ap-south-1",
        dynamodb_table="odinson-readings",
        sns_topic_arn="arn:aws:sns:ap-south-1:123456789012:odinson-alerts",
        s3_bucket="odinson-logs-test",
        db_path=tmp_path / "x.db",
        log_dir=tmp_path / "logs",
        s3_archive_interval_s=0,
        cloud_publish_every=1,  # disable throttling so every test reading is persisted
    )
    base.update(overrides)
    return Settings(**base)


def publish(bridge, alert=0, delta=1.0):
    return bridge.publish_reading(
        iso_timestamp="2026-11-12T10:00:00.000Z",
        timestamp="10:00:00.000",
        delta=delta,
        alert=alert,
        device_id="dev-1",
        source="mock",
    )


def test_publish_writes_dynamodb_item_with_ttl(fake_boto3, tmp_path):
    bridge = AWSBridge(make_settings(tmp_path))
    assert publish(bridge, alert=1, delta=25.0) is True
    item = FakeSession.last.table.items[0]
    assert item["device_id"] == "dev-1"
    assert item["ts"] == "2026-11-12T10:00:00.000Z"
    assert item["delta"] == 25.0
    assert item["alert"] == 1
    assert item["expires_at"] > 0  # DynamoDB TTL set


def test_alert_fires_sns_and_emits_metrics(fake_boto3, tmp_path):
    bridge = AWSBridge(make_settings(tmp_path))
    publish(bridge, alert=1, delta=30.0)
    sess = FakeSession.last
    assert any(c[0] == "sns" for c in sess.sns.calls)
    assert any(c[0] == "cloudwatch" for c in sess.cw.calls)
    metric_names = [m["MetricName"] for c in sess.cw.calls for m in c[1]["MetricData"]]
    assert "Delta" in metric_names and "Alert" in metric_names


def test_quiet_reading_skips_sns(fake_boto3, tmp_path):
    bridge = AWSBridge(make_settings(tmp_path))
    publish(bridge, alert=0, delta=1.0)
    assert FakeSession.last.sns.calls == []


def test_publish_throttle(fake_boto3, tmp_path):
    bridge = AWSBridge(make_settings(tmp_path, cloud_publish_every=2))
    publish(bridge)
    publish(bridge)
    assert len(FakeSession.last.table.items) == 1  # only every 2nd reading persisted


def test_disabled_bridge_is_a_noop(tmp_path):
    bridge = AWSBridge(make_settings(tmp_path, aws_enabled=False))
    assert publish(bridge) is False
    assert bridge.last_ok is None


def test_archive_uploads_csv_to_s3(fake_boto3, tmp_path):
    csv_file = tmp_path / "vibration_log_test.csv"
    csv_file.write_text("time_24h,delta\n10:00:00.000,3.0\n", encoding="utf-8")
    bridge = AWSBridge(make_settings(tmp_path, s3_archive_interval_s=0))
    assert bridge.maybe_archive_log(csv_file) is True
    kind, bucket, key = FakeSession.last.s3.calls[0]
    assert kind == "s3" and bucket == "odinson-logs-test"
    assert key == "logs/odinson-01/vibration_log_test.csv"  # key uses the configured device_id
