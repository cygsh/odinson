#include <Wire.h>
#include <MPU6050.h>

MPU6050 mpu;

int16_t ax, ay, az;
int16_t gx, gy, gz;

long cal_x = 0, cal_y = 0, cal_z = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin();

  mpu.initialize();

  Serial.println("Calibrating MPU6050...");
  for (int i = 0; i < 1000; i++) {
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    cal_x += ax;
    cal_y += ay;
    cal_z += az;
    delay(2);
  }

  cal_x /= 1000;
  cal_y /= 1000;
  cal_z /= 1000;

  Serial.println("Calibration done");
}

void loop() {
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  Serial.print(millis());
  Serial.print(",");
  Serial.print(ax - cal_x);
  Serial.print(",");
  Serial.print(ay - cal_y);
  Serial.print(",");
  Serial.println(az - cal_z);

  delay(100);
}
