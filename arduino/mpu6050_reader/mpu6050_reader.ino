/*
 * Odinson MPU6050 reader — firmware v2
 *
 * Streams calibrated 3-axis acceleration as JSON lines at 20 Hz:
 *   {"t": <millis>, "ax": <x>, "ay": <y>, "az": <z>}
 *
 * The Python gateway (odinson/models.py :: parse_serial_line) accepts this
 * JSON format and still accepts the legacy CSV format "millis,ax,ay,az".
 *
 * Wiring (I2C): VCC->3.3V, GND->GND, SDA->SDA, SCL->SCL
 */
#include <Wire.h>
#include <MPU6050.h>

MPU6050 mpu;

const unsigned long BAUD_RATE = 115200;
const unsigned long SAMPLE_DELAY_MS = 50;  // 20 Hz
const int CALIBRATION_SAMPLES = 1000;

long calX = 0, calY = 0, calZ = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  Wire.begin();

  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println(F("{\"error\":\"MPU6050 not connected\"}"));
    while (true) {
      delay(1000);
    }
  }

  Serial.println(F("INFO calibrating..."));
  for (int i = 0; i < CALIBRATION_SAMPLES; i++) {
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    calX += ax;
    calY += ay;
    calZ += az;
    delay(2);
  }
  calX /= CALIBRATION_SAMPLES;
  calY /= CALIBRATION_SAMPLES;
  calZ /= CALIBRATION_SAMPLES;
  Serial.println(F("INFO calibration done"));
}

void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  Serial.print(F("{\"t\":"));
  Serial.print(millis());
  Serial.print(F(",\"ax\":"));
  Serial.print(ax - calX);
  Serial.print(F(",\"ay\":"));
  Serial.print(ay - calY);
  Serial.print(F(",\"az\":"));
  Serial.print(az - calZ);
  Serial.println(F("}"));

  delay(SAMPLE_DELAY_MS);
}
