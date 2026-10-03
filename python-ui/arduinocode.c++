#include <Arduino.h>

float temperature = 25.0;
float temperatureTarget = 37.0;

float od = 0.10;
float ph = 7.00;

int pumpSpeed = 0;
bool pumpActive = false;

int fanPWM = 0;
int fanRPM = 0;

unsigned long lastSend = 0;

void setup() {

  Serial.begin(115200);

}

float getFakeTemperature() {

  if (temperature < temperatureTarget) {
    temperature += 0.2;
  }
  else if (temperature > temperatureTarget) {
    temperature -= 0.2;
  }

  return temperature;

}

float getFakeOD() {

  od += 0.005;

  if (od > 2.0) {
    od = 0.10;
  }

  return od;

}

void sendJSON() {

  temperature = getFakeTemperature();
  od = getFakeOD();

  fanRPM = fanPWM * 20;

  Serial.print("{");

  Serial.print("\"time\":");
  Serial.print(millis() / 1000.0);

  Serial.print(",\"Fan PWM\":");
  Serial.print(fanPWM);

  Serial.print(",\"Fan RPM\":");
  Serial.print(fanRPM);

  Serial.print(",\"Pump Active\":");
  Serial.print(pumpActive ? "true" : "false");

  Serial.print(",\"Pump Speed\":");
  Serial.print(pumpSpeed);

  Serial.print(",\"Temperature\":");
  Serial.print(temperature, 2);

  Serial.print(",\"Temperature Target\":");
  Serial.print(temperatureTarget, 2);

  Serial.print(",\"OD\":");
  Serial.print(od, 3);

  Serial.print(",\"pH\":");
  Serial.print(ph, 2);

  Serial.println("}");

}

void processCommand(String command) {

  command.trim();

  if (command.indexOf("\"Temperature\"") >= 0) {

    int start = command.indexOf("\"Temperature\"");

    start = command.indexOf(":", start);

    int end = command.indexOf(",", start);

    if (end == -1) {
      end = command.indexOf("}", start);
    }

    if (start >= 0 && end >= 0) {

      String value = command.substring(start + 1, end);

      temperatureTarget = value.toFloat();

    }

  }

  if (command.indexOf("\"Input Pump 1\"") >= 0) {

    int start = command.indexOf("\"Input Pump 1\"");

    start = command.indexOf(":", start);

    int end = command.indexOf(",", start);

    if (end == -1) {
      end = command.indexOf("}", start);
    }

    if (start >= 0 && end >= 0) {

      String value = command.substring(start + 1, end);

      pumpSpeed = value.toInt();

      pumpActive = pumpSpeed > 0;

    }

  }

  if (command.indexOf("\"Stirring Fan\"") >= 0) {

    int start = command.indexOf("\"Stirring Fan\"");

    start = command.indexOf(":", start);

    int end = command.indexOf(",", start);

    if (end == -1) {
      end = command.indexOf("}", start);
    }

    if (start >= 0 && end >= 0) {

      String value = command.substring(start + 1, end);

      fanPWM = value.toInt();

    }

  }

}

void loop() {

  if (Serial.available() > 0) {

    String command = Serial.readStringUntil('\n');

    processCommand(command);

  }

  if (millis() - lastSend >= 1000) {

    lastSend = millis();

    sendJSON();

  }

}