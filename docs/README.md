# Project Documentation

## Project Overview

Odinson reads vibration data from an **MPU6050** sensor via an **Arduino**, processes it in a
**Python gateway** (adaptive-baseline detection, alerts, local web UI + SQLite/CSV), and can
stream everything to **AWS** (DynamoDB, Lambda, API Gateway, SNS, CloudWatch, S3, IoT Core)
provisioned with CloudFormation.

- [Architecture & data flow](ARCHITECTURE.md)
- [AWS deployment guide](AWS_DEPLOYMENT.md)
- Main [README](../README.md) — quickstart, config, API, structure

## Hardware Setup (Arduino + MPU6050)

1. Wire the MPU6050 over I2C: VCC→3.3V, GND→GND, SDA→SDA, SCL→SCL.
2. Install the **MPU6050** library in the Arduino IDE.
3. Upload `arduino/mpu6050_reader/mpu6050_reader.ino` (outputs JSON lines at 20 Hz, 115200 baud).
4. Connect the Arduino via USB.

> Optional: drop a wiring photo into `docs/images/wiring.png` — it is whitelisted in `.gitignore`.

## Software Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then edit: serial port, thresholds, tokens, AWS ARNs
python run.py --mock        # demo without hardware
python run.py               # live hardware
```

Open http://localhost:5000 for the live monitor, `/history_view` for past data.
