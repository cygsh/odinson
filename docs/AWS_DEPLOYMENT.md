# AWS Deployment Guide

Everything in this stack is sized to stay inside the **AWS Free Tier** for a single-sensor
student project:

| Service | Free tier | Odinson usage |
|---|---|---|
| DynamoDB (on-demand) | 25 WCU + 25 GB, **permanent** | ~4 writes/s (see `ODINSON_CLOUD_PUBLISH_EVERY`), TTL deletes after 90 d |
| Lambda | 1M req + 400k GB-s/mo, **permanent** | ~4 invocations/s |
| CloudWatch | 10 custom metrics + 10 alarms, **permanent** | 2 metrics + 2 alarms |
| SNS | 1M publishes/mo | alerts only |
| S3 | 5 GB (12 mo) | KB-sized CSVs, lifecycle caps growth |
| API Gateway (HTTP API) | 1M req/mo (first 12 mo) | ingest/query |
| IoT Core | 500k msgs/mo (first 12 mo) | optional device publishing |

Guardrails baked in: DynamoDB TTL, S3 lifecycle (IA @ 30 d, delete @ 365 d), publish throttling,
and a **billing alarm** that emails you if `EstimatedCharges > $1`.

## 1. Prerequisites

```bash
aws --version                 # AWS CLI v2, configured: aws configure
# use the ap-south-1 (Mumbai) region unless you prefer another — set AWS_REGION accordingly
```

## 2. Deploy the stack

```bash
aws cloudformation deploy \
  --template-file cloud/infrastructure/odinson-stack.yaml \
  --stack-name odinson \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides AlertEmail=you@example.com
```

`deploy` packages `cloud/lambda/` into S3 automatically. When it finishes, note the outputs:
`IngestEndpoint`, `AlertsTopicArn`, `LogBucketName`, `TableName`.

**Confirm the SNS email subscription** (check your inbox, click the confirm link) — otherwise
alerts go nowhere.

## 3. Give the gateway least-privilege access

Create an IAM user for the local gateway and attach `cloud/iam/odinson-gateway-policy.json`
as an inline policy (the ARNs use wildcards for account/region, so it works as-is):

```bash
aws iam create-user --user-name odinson-gateway
aws iam put-user-policy --user-name odinson-gateway --policy-name odinson-gateway \
  --policy-document file://cloud/iam/odinson-gateway-policy.json
aws iam create-access-key --user-name odinson-gateway   # store the keys in .env / env vars
```

(On your own dev machine, `aws configure` with your user keys is enough. On shared machines,
prefer an IAM role / SSO instead of long-lived keys.)

## 4. Wire up the gateway

In `.env`:

```dotenv
ODINSON_AWS_ENABLED=true
ODINSON_AWS_REGION=ap-south-1
ODINSON_DYNAMODB_TABLE=odinson-readings
ODINSON_SNS_TOPIC_ARN=<AlertsTopicArn output>
ODINSON_S3_BUCKET=<LogBucketName output>
ODINSON_CLOUD_PUBLISH_EVERY=20     # 1 cloud write/s at 20 Hz sampling — well inside free tier
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from step 3 (or AWS_PROFILE)
```

Run `python run.py --mock` and watch the **AWS Cloud** indicator on the dashboard flip to
**Synced**. Verify data in the DynamoDB console (`odinson-readings`) and metrics under
CloudWatch → Metrics → `Odinson`.

## 5. Import the dashboard

```bash
aws cloudwatch put-dashboard --dashboard-name Odinson \
  --dashboard-body file://cloud/monitoring/dashboard.json
```

## 6. Ingest from anywhere (API / IoT)

- `POST {IngestEndpoint}` with `{"device_id": "odinson-01", "ts": "...", "delta": 12.3, "alert": 1}`
  (or `{"readings": [...]}` for batches).
- `GET {ApiUrl}/readings?device_id=odinson-01&start=2026-11-12T00:00:00.000Z&end=...&limit=1000`
- MQTT devices: publish to `odinson/<device_id>/readings` via AWS IoT Core — the topic rule in
  the stack forwards it to the ingest Lambda (attach a cert + policy per device).

## 7. Zero-cost local sandbox (LocalStack)

Iterate without touching the real account:

```bash
docker compose --profile aws up
# create the table in LocalStack, then:
#   ODINSON_AWS_ENABLED=true
#   ODINSON_AWS_ENDPOINT_URL=http://localhost:4566
#   AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
```

## 8. Teardown

```bash
aws cloudformation delete-stack --stack-name odinson
# empty + delete the S3 bucket first if it contains logs:
#   aws s3 rm s3://<LogBucketName> --recursive && aws s3 rb s3://<LogBucketName>
```
