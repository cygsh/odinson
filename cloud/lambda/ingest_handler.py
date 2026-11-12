"""Odinson ingest Lambda.

Triggered by either:
  * API Gateway (HTTP API):  ``POST /readings`` with a JSON body — a single
    reading ``{"device_id", "ts", "delta", "alert", ...}`` or a batch
    ``{"readings": [...]}``.
  * AWS IoT Core topic rule: topic ``odinson/<device_id>/readings`` whose
    payload is the reading JSON (the rule SQL injects ``device_id`` from the
    topic via ``topic(2)``).

Each reading is written to DynamoDB; alert-level readings also publish to the
SNS alerts topic, and every reading emits CloudWatch metrics (Delta, Alert).

Environment variables: TABLE_NAME, SNS_TOPIC_ARN, METRIC_NAMESPACE, TTL_DAYS.
boto3 is pre-installed in the Lambda Python runtime, so no deployment package
is needed beyond this file.
"""
import json
import os
import time

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "odinson-readings")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "Odinson")
TTL_DAYS = int(os.environ.get("TTL_DAYS", "90"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
sns = boto3.client("sns")
cloudwatch = boto3.client("cloudwatch")


def _record(body: dict) -> dict:
    """Normalize an inbound payload into a DynamoDB item."""
    device_id = str(body.get("device_id", "unknown"))
    ts = str(
        body.get("ts")
        or body.get("iso_timestamp")
        or time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    )
    return {
        "device_id": device_id,          # partition key
        "ts": ts,                        # sort key (ISO-8601 UTC)
        "timestamp": str(body.get("timestamp", "")),
        "delta": float(body.get("delta", 0.0)),
        "alert": int(bool(body.get("alert", 0))),
        "source": str(body.get("source", "iot")),
        "expires_at": int(time.time()) + TTL_DAYS * 86400,  # DynamoDB TTL
    }


def _emit(records: list[dict]) -> None:
    metrics = []
    for rec in records:
        table.put_item(Item=rec)
        dims = [{"Name": "device_id", "Value": rec["device_id"]}]
        metrics.append({"MetricName": "Delta", "Value": rec["delta"], "Unit": "None", "Dimensions": dims})
        metrics.append({"MetricName": "Alert", "Value": rec["alert"], "Unit": "Count", "Dimensions": dims})
        if rec["alert"] and SNS_TOPIC_ARN:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Odinson alert on {rec['device_id']}",
                Message=(
                    f"Abnormal vibration on {rec['device_id']} at {rec['ts']} "
                    f"(delta={rec['delta']:.2f}, source={rec['source']})"
                ),
            )
    # CloudWatch accepts at most 20 metrics per PutMetricData call.
    for i in range(0, len(metrics), 20):
        cloudwatch.put_metric_data(Namespace=METRIC_NAMESPACE, MetricData=metrics[i : i + 20])


def lambda_handler(event, context):
    if "readings" in event:  # batch via IoT rule or API body
        records = [_record(r) for r in event["readings"]]
    elif "delta" in event or "ts" in event:  # single reading via IoT rule
        records = [_record(event)]
    else:  # API Gateway HTTP API (v2) proxy event
        try:
            body = json.loads(event.get("body") or "{}")
        except ValueError:
            return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON body"})}
        if "readings" in body:
            records = [_record(r) for r in body["readings"]]
        else:
            records = [_record(body)]
    _emit(records)
    return {"statusCode": 200, "body": json.dumps({"ingested": len(records)})}
