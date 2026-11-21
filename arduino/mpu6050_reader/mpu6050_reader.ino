/*
 * Odinson MPU6050 reader — firmware v2 (Direct Wire / megaAVR compatible)
 *
 * Streams calibrated 3-axis acceleration as JSON lines at 20 Hz:
 *   {"t": <millis>, "ax": <x>, "ay": <y>, "az": <z>}
 *
 * Wiring (I2C):
 *   VCC -> 5V (or 3.3V)
 *   GND -> GND
 *   SDA -> A4
 *   SCL -> A5
 *   AD0 -> GND (sets I2C address to 0x68)
 */
#include <Wire.h>

const int MPU_ADDR = 0x68;
const unsigned long BAUD_RATE = 115200;
const unsigned long SAMPLE_DELAY_MS = 50;  // 20 Hz
const int CALIBRATION_SAMPLES = 500;

long calX = 0, calY = 0, calZ = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  Wire.begin();
  delay(100);

  // Wake up MPU-6050 (clear sleep bit in PWR_MGMT_1 register 0x6B)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);
  delay(100);

  Serial.println(F("INFO calibrating..."));
  for (int i = 0; i < CALIBRATION_SAMPLES; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);  // Register for ACCEL_XOUT_H
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

    if (Wire.available() >= 6) {
      int16_t ax = (Wire.read() << 8) | Wire.read();
      int16_t ay = (Wire.read() << 8) | Wire.read();
      int16_t az = (Wire.read() << 8) | Wire.read();
      calX += ax;
      calY += ay;
      calZ += az;
    }
    delay(4);
  }
  calX /= CALIBRATION_SAMPLES;
  calY /= CALIBRATION_SAMPLES;
  calZ /= CALIBRATION_SAMPLES;
  Serial.println(F("INFO calibration done"));
}

void loop() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  if (Wire.available() >= 6) {
    int16_t ax = (Wire.read() << 8) | Wire.read();
    int16_t ay = (Wire.read() << 8) | Wire.read();
    int16_t az = (Wire.read() << 8) | Wire.read();

    Serial.print(F("{\"t\":"));
    Serial.print(millis());
    Serial.print(F(",\"ax\":"));
    Serial.print(ax - calX);
    Serial.print(F(",\"ay\":"));
    Serial.print(ay - calY);
    Serial.print(F(",\"az\":"));
    Serial.print(az - calZ);
    Serial.println(F("}"));
  }

  delay(SAMPLE_DELAY_MS);
}
