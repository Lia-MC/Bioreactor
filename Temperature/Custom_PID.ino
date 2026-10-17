#include <PID_v1.h>
#include <DS18B20.h>
#include <stdlib.h>

void TemperatureSetup();
void TemperatureUpdate();
unsigned long start;

#define TMP 6
#define HEATER 8

DS18B20 ds(TMP);
double currentTemp, heaterCommand;
double prevTemp;
double targetTemp = 50;
bool tempIncreasing = false;
bool tempDecreasing = false;
bool targetReached = false;
double prevTarget = 3;
float Kp = 800;
float minOutput = 3500;
float Ki = 50;
float integral = 0;
unsigned long prevPIDCalc = 0;
int windowSize = 5000;
unsigned long windowStartTime;

bool KiMultiplied = false;

bool recovered = false;

void setup() {
  TemperatureSetup();
  Serial.begin(115200);
  delay(500);
  Serial.println("Ready");
  start = millis();
  prevPIDCalc = millis();
  prevTemp = (double)ds.getTempC();
}

void loop() {
  TemperatureUpdate();
}

void TemperatureSetup() {
  pinMode(HEATER, OUTPUT);
  windowStartTime = millis();
}

float readTemperature() {
  return ds.getTempC();
}

float ComputePID() {
  float output = 0;
  double error = targetTemp - currentTemp;
  if (error <= 0) {
    targetReached = true;
    recovered = false;
    integral = 0;
  }
  output += Kp * error;
  if (error > 0 && targetReached) {
    if (tempIncreasing) {
      recovered = true;
    }
    if (tempDecreasing) {
      recovered = false;
    }
    if (!recovered) {
      output += minOutput;
    }
  }
  if (error > 0) {
    if (prevTemp >= currentTemp) {
      if (prevTemp > currentTemp && !KiMultiplied) {
        Ki *= 10;
        KiMultiplied = true;
      }
      integral += (millis() - prevPIDCalc) * Ki / 1000;
    } else {
      if (KiMultiplied) {
        Ki /= 10;
        KiMultiplied = false;
      }
      integral = 0;
    }
    if (integral > 5000) integral = 5000;
  } else if (KiMultiplied) {
    Ki /= 10;
    KiMultiplied = false; 
  }
  output += integral;
  if (KiMultiplied && !targetReached) {
    output += minOutput;
  }
  if (output <= 0) output = 0;
  if (output > windowSize) output = windowSize;
  if (windowSize - output < 200 && output != windowSize) output = windowSize - 200;
  if (output < 200) output = 0;
  prevPIDCalc = millis();
  return output;
}

void TemperatureUpdate() {
  if (prevTarget != targetTemp) {
    targetReached = false;
    prevTarget = targetTemp;
    Kp = 0.00131173 * exp(targetTemp * 0.332841) + 800;
  }
  currentTemp = (double)ds.getTempC();
  tempIncreasing = currentTemp > prevTemp;
  tempDecreasing = currentTemp < prevTemp;
  heaterCommand = ComputePID();
  prevTemp = currentTemp;
  if (heaterCommand < 200) heaterCommand = 0;
  Serial.print(round((millis() - start) / 1000));
  Serial.print(": T ");
  Serial.print(currentTemp);
  Serial.print(" C ");
  Serial.print(heaterCommand);
  Serial.print(" I ");
  Serial.print(integral);
  Serial.println("");
  unsigned long now = millis();
  if (now - windowStartTime > windowSize) {
    windowStartTime = millis();
  }
  if (heaterCommand > now - windowStartTime) digitalWrite(HEATER, HIGH);
  else digitalWrite(HEATER, LOW);
}
