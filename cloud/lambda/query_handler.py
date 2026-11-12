"""Odinson query Lambda: ``GET /readings?device_id=&start=&end=&limit=``.

Queries the DynamoDB table for readings of one device within an ISO-8601
timestamp range, newest first. Powers the cloud history view and any
dashboard that talks to the API directly.
"""
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ.get("TABLE_NAME", "odinson-readings")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    device_id = params.get("device_id", "odinson-01")
    start = params.get("start", "0000-01-01T00:00:00.000Z")
    end = params.get("end", "9999-12-31T23:59:59.999Z")
    try:
        limit = min(int(params.get("limit", "1000")), 5000)
    except ValueError:
        limit = 1000

    resp = table.query(
        KeyConditionExpression=Key("device_id").eq(device_id) & Key("ts").between(start, end),
        Limit=limit,
        ScanIndexForward=False,  # newest first
    )
    items = resp.get("Items", [])
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"device_id": device_id, "count": len(items), "items": items}, default=str),
    }
