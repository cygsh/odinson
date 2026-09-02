# MPU6050 Digital Seismometer

A low-cost digital seismometer prototype built using an Arduino-compatible microcontroller and an MPU6050 accelerometer. The system performs real-time vibration analysis, detects abnormal motion using a dynamic baseline, logs significant events, visualizes data live, and triggers automated alerts.

---

## 📌 Overview
This project demonstrates how inertial sensors can be used to monitor vibration and seismic-like motion. Three-axis acceleration data is acquired from the MPU6050, calibrated at startup, and streamed to a Python application for processing. Sudden deviations in acceleration magnitude are interpreted as vibration events and handled accordingly.

---

## 🔧 Hardware Used
- Arduino Nano / Uno (or compatible)
- MPU6050 Accelerometer & Gyroscope
- USB connection (power + serial communication)

---

## 🔌 Wiring (I2C)
| MPU6050 | Arduino |
|--------|---------|
| VCC    | 3.3V    |
| GND    | GND     |
| SDA    | SDA     |
| SCL    | SCL     |

A wiring reference image can be placed in `docs/wiring.png`.

---

## 🧠 Working Principle
1. Raw acceleration values (ax, ay, az) are read from the MPU6050.
2. Initial calibration offsets are calculated at startup.
3. Acceleration magnitude is computed in real time.
4. A moving baseline is maintained to filter slow drift.
5. The absolute deviation (`delta`) from the baseline is monitored.
6. When thresholds are exceeded:
   - A sound alert is triggered
   - A Telegram alert is sent
   - Data is logged to a CSV file
7. Live vibration data is plotted using Matplotlib.

---

## 🖥 Software Stack

### Arduino
- `Wire.h`
- `MPU6050` library

### Python
- `pyserial`
- `matplotlib`
- `requests`
- `winsound`
- `csv`

---

## 📊 Outputs
- Real-time vibration delta plot
- CSV log files with timestamps
- Audible alert on abnormal motion
- Telegram notification for critical events

---

## ▶ How to Run

### Arduino
1. Install the **MPU6050** library
2. Upload `arduino/mpu6050_reader.ino` to the board

### Python
```bash
pip install pyserial matplotlib requests
python vibration_monitor.py
