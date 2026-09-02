# Project Documentation

## Project Overview

This project reads vibration data from an **MPU6050 sensor** using Arduino and monitors it with a **Python script**. Alerts are sent via **Telegram** when vibrations exceed defined thresholds.  

The repository includes:
- Arduino code to read sensor data.
- Python scripts to monitor the data.
- Documentation and structure to organize the project.

---

## Hardware Setup (Arduino + MPU6050)

1. Connect the **MPU6050 sensor** to your Arduino board.
2. Open `arduino/mpu6050_reader.ino` in the **Arduino IDE**.
3. Upload the code to the Arduino board.
4. Make sure the Arduino is powered and connected via USB to your computer.

> Optional: Include a wiring diagram here for clarity.

---

## Software Setup (Python Monitoring)

1. Ensure **Python 3.x** is installed.
2. Install required packages:

```bash
pip install pyserial python-telegram-bot
