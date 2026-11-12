"""AWS cloud bridge for the local gateway.

Publishes every reading to DynamoDB, alert events to SNS, metrics to
CloudWatch, and periodically archives the CSV log to S3.

Disabled by default (``ODINSON_AWS_ENABLED=false``). Every call is fail-safe:
a cloud outage never interrupts local monitoring. Point
``ODINSON_AWS_ENDPOINT_URL`` at LocalStack (``http://localhost:4566``) to
exercise the full pipeline locally without an AWS account.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from ..config import Settings

logger = logging.getLogger(__name__)


class AWSBridge:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self.enabled = settings.aws_enabled
        self.last_ok: bool | None = None
        self._counter = 0
        self._last_archive = time.monotonic()
        self._ddb = None
        self._sns = None
        self._cw = None
        self._s3 = None
        if not self.enabled:
            logger.info("AWS bridge disabled (set ODINSON_AWS_ENABLED=true to enable)")
            return
        try:
            import boto3
        except ImportError:
            logger.warning("boto3 is not installed; AWS bridge disabled (pip install boto3)")
            self.enabled = False
            return
        session = boto3.session.Session(region_name=settings.aws_region)
        kwargs = {"endpoint_url": settings.aws_endpoint_url or None}
        self._ddb = session.resource("dynamodb", **kwargs).Table(settings.dynamodb_table)
        self._sns = session.client("sns", **kwargs)
        self._cw = session.client("cloudwatch", **kwargs)
        self._s3 = session.client("s3", **kwargs)
        logger.info(
            "AWS bridge enabled: region=%s table=%s topic=%s bucket=%s",
            settings.aws_region,
            settings.dynamodb_table,
            settings.sns_topic_arn or "-",
            settings.s3_bucket or "-",
        )

    def publish_reading(
        self,
        *,
        iso_timestamp: str,
        timestamp: str,
        delta: float,
        alert: int,
        device_id: str,
        source: str,
    ) -> bool:
        """Write one reading to DynamoDB; on alert also fire SNS. Always emit metrics."""
        if not self.enabled:
            return False
        self._counter += 1
        ok = True
        if self._counter % max(1, self._s.cloud_publish_every) == 0:
            try:
                self._ddb.put_item(
                    Item={
                        "device_id": device_id,
                        "ts": iso_timestamp,  # sort key (ISO-8601 UTC)
                        "timestamp": timestamp,
                        "delta": round(delta, 4),
                        "alert": alert,
                        "source": source,
                        "expires_at": int(time.time()) + 90 * 24 * 3600,  # DynamoDB TTL
                    }
                )
            except Exception as exc:
                ok = False
                logger.warning("DynamoDB put_item failed: %s", exc)
            try:
                self._cw.put_metric_data(
                    Namespace=self._s.cloudwatch_namespace,
                    MetricData=[
                        {
                            "MetricName": "Delta",
                            "Value": round(delta, 4),
                            "Unit": "None",
                            "Dimensions": [{"Name": "device_id", "Value": device_id}],
                        },
                        {
                            "MetricName": "Alert",
                            "Value": alert,
                            "Unit": "Count",
                            "Dimensions": [{"Name": "device_id", "Value": device_id}],
                        },
                    ],
                )
            except Exception as exc:
                ok = False
                logger.warning("CloudWatch put_metric_data failed: %s", exc)
        if alert and self._s.sns_topic_arn:
            try:
                self._sns.publish(
                    TopicArn=self._s.sns_topic_arn,
                    Subject=f"Odinson alert on {device_id}",
                    Message=(
                        f"Abnormal vibration detected on {device_id} at {iso_timestamp} "
                        f"(delta={delta:.2f}, source={source})"
                    ),
                )
            except Exception as exc:
                ok = False
                logger.warning("SNS publish failed: %s", exc)
        self.last_ok = ok
        return ok

    def maybe_archive_log(self, csv_path: Path) -> bool:
        """Upload the current CSV log to S3 at most once per archive interval."""
        if not self.enabled or not self._s.s3_bucket:
            return False
        now = time.monotonic()
        if now - self._last_archive < self._s.s3_archive_interval_s:
            return False
        self._last_archive = now
        try:
            key = f"logs/{self._s.device_id}/{csv_path.name}"
            self._s3.upload_file(str(csv_path), self._s.s3_bucket, key)
            logger.info("Archived %s to s3://%s/%s", csv_path, self._s.s3_bucket, key)
            return True
        except Exception as exc:
            logger.warning("S3 archive failed: %s", exc)
            self.last_ok = False
            return False

    def close(self) -> None:
        """Nothing persistent to flush; kept for a symmetric lifecycle."""
