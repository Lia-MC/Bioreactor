#include <PID_v1.h>
#include <DS18B20.h>
#include <Adafruit_AS7343.h>
#include <SoftWire.h>
#include <Wire.h>
#include "AS7343Soft.h"
//self written ^

#include <ArduinoJson.h>

//Pin assignments
const int FAN_TACH = 2;
const int FAN_PWM = 4;
const int PUMP = 3;
const int TEMP_SENSOR = 6;
const int HEATER = 8;
const int OD_SDA = 17;
const int OD_SCL = 15;

uint8_t rxBuffer[32];
uint8_t txBuffer[32];
unsigned long printCycleStart;
unsigned long runStart;
  SoftWire REF(16, 17);
  AS7343Soft sensor2(REF); //sensor2 is reference sensor

class Fan {
  private:
    static Fan *instance;
    int tach_pin;
    int pwm_pin;
    unsigned long lastCalcTime;
    int prevSpeedPercent = 0;
    static void tachISR() {
      if (instance) instance->pulseCount++;
    }
  public:
    unsigned long currentRPM = 0;
    volatile unsigned long pulseCount = 0;
    int speedPercent = 0;
    Fan(int tach, int pwm) : tach_pin(tach), pwm_pin(pwm) {
      pinMode(tach_pin, INPUT_PULLUP);
      pinMode(pwm_pin, OUTPUT);
      instance = this;
      attachInterrupt(digitalPinToInterrupt(tach_pin), tachISR, FALLING);
      lastCalcTime = millis();
    }
    void setSpeed(int percent) {
      percent = constrain(percent, 0, 100);
      speedPercent = percent;
      int pwmValue = map(percent, 0, 100, 0, 255);
      analogWrite(pwm_pin, pwmValue);
    }
    void update() {
      //Serial.println(this->pulseCount);
      unsigned long currentTime = millis();
      if (currentTime - lastCalcTime >= 1000) {
        noInterrupts();
        unsigned long pulses = pulseCount;
        pulseCount = 0;
        interrupts();
        currentRPM = 60000 * pulses / 2 / (currentTime - lastCalcTime);
        lastCalcTime = currentTime;
      }
      if (speedPercent != prevSpeedPercent) {
        setSpeed(speedPercent);
        prevSpeedPercent = speedPercent;
      }
    }
};
Fan* Fan::instance = nullptr;

// Pump stuff
class Pump {
  private:
    int pin;
    unsigned long moveStart;
  public:
    bool active = false;
    bool continuousMode = false; // for continuous operation of pumps since active mode depends on moveDuration
    unsigned long moveDuration = 0;
    int speedPercent = 0;
    Pump(int p) : pin(p) { pinMode(pin, OUTPUT); }
    void setSpeed(int pwmValue) { analogWrite(pin, constrain(pwmValue, 0, 255)); }
    void setSpeedPercent(int percent) { setSpeed(map(constrain(percent, 0, 100), 0, 100, 0, 255)); }
    void stop() { analogWrite(pin, 0); }
    void update() {
      if (!active && moveDuration) {
        active = true;
        moveStart = millis();
        setSpeedPercent(speedPercent);
      }
      if (active && millis() - moveStart > moveDuration) {
        setSpeedPercent(0);
        moveDuration = 0;
        active = false;
        stop();
      }
    }
};

class Temperature {
  private:
    int probe_pin, heater_pin;
    double prevTemp;
    double prevTarget = 3;
    bool tempIncreasing = false;
    bool tempDecreasing = false;
    bool targetReached = false;
    float Kp = 800;
    float Ki = 50;
    float integral = 0;
    float minOutput = 3500;
    unsigned long prevPIDCalc, windowStartTime;
    int windowSize = 5000;
    bool KiMultiplied = false;
    bool recovered = false;
    DS18B20 ds;
  public:
    double currentTemp;
    double targetTemp = 20;
    bool on = false;
    double heaterCommand = 0;
    Temperature(int probe, int heater) : heater_pin(heater), ds(probe) {
      pinMode(heater_pin, OUTPUT);
    }
    void init() {
      currentTemp = (double)ds.getTempC();
      prevTemp = currentTemp;
      windowStartTime = millis();
      prevPIDCalc = millis();
    }
    void update() {
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
      unsigned long now = millis();
      if (now - windowStartTime > windowSize) {
        windowStartTime = millis();
      }
      if (heaterCommand > now - windowStartTime) digitalWrite(heater_pin, HIGH);
      else digitalWrite(heater_pin, LOW);
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
};

class OD {
  private: 
    Adafruit_AS7343 sensor1; //sensor1 is collecting
    uint8_t rxBuffer[32];
    uint8_t txBuffer[32];

    double blankOD;
    double referenceOD;
    uint16_t darkValue1; // LED off
    uint16_t darkValue2; // LED off

    uint16_t run_sensor1() {
    //Manually command fresh reading cycle
      sensor1.startMeasurement();
      while (!sensor1.dataReady()) {
        delay(1);
      }
      //for violet light, 405nm
      int FXL_value = sensor1.readChannel(AS7343_CHANNEL_FXL);
      return FXL_value;
    }


    uint16_t run_sensor2() {
      //!!!!!!THIS IS A SAFETY MEASURE
      if (!sensor2.startMeasurement()) {
        Serial.println("startMeasurement failed");
        delay(100000);
      }
      while (!sensor2.dataReady()) {
        delay(1);
      }

    uint16_t fxlValue;
    //!!!!!!!if else is safety measure
      if (sensor2.readLightFXL(fxlValue))  return fxlValue;
      else  Serial.println("Could not read FXL");
    }
  
  public: 
    double nOD;
  OD()  {//!!!!!!!I assume we configure when calling the object
    //give memory to softwire, sensor2 configure
    
  }

  void init() {
    REF.setRxBuffer(rxBuffer, 32);
    REF.setTxBuffer(txBuffer, 32);
    REF.setClock(50000);        //slower = more stable, I2C standard is 100kHz
    REF.setTimeout_ms(100);     //if SoftWire is slower than I2C for more than 100mili, give up instead of freezing forever
    REF.begin();

    //!!!!!!!!!!THIS IS A SAFETY CAUTION
    if (!sensor2.begin()) {
      Serial.println("Could not find AS7343 sensor2!");
      Serial.flush();
      while(1);
      exit(0);
    }

    if (!sensor1.begin()) {
      Serial.println("Could not find AS7343 sensor1!");
      Serial.flush();
      while(1);
      exit(0);
    } 
    //sensor1 configure
    sensor1.setGain(AS7343_GAIN_64X);
    sensor1.setATIME(29);  // Integration cycles
    sensor1.setASTEP(599); // Step size

    //!!!!!!!!!!THIS IS A SAFETY CAUTION
    uint16_t readings[18];
    //need to read all channels to first trigger the global reading, pulls data from memory bank after read starts
    if(!sensor1.readAllChannels(readings)) {
      Serial.println("Read failed!");
      delay(500);
      exit(0);
    } 
  }

  void dark() {
    Serial.println("Now running value for dark");
    darkValue1 = run_sensor1();
    darkValue2 = run_sensor2();
  }

  void blank() {
    Serial.println("Now running for blank vial values");
    blankOD = ((double)run_sensor1() - darkValue1) / ((double)run_sensor2() - darkValue2);
  }

  void reference() {
    Serial.println("Now running for initial values");
    uint16_t total_sensor1 = 0;
    uint16_t total_sensor2 = 0;

    //take the mean of 10 values at the start
    for(uint8_t i = 0; i < 10; i++) {
      total_sensor1 += run_sensor1();
      total_sensor2 += run_sensor2();
    }

    referenceOD = ((total_sensor1/10.0) - darkValue1) / ((total_sensor2/10.0) - darkValue2);
  }

  void read() {
    nOD = (((double)run_sensor1() - darkValue1) / (run_sensor2() - darkValue2) - blankOD) / (referenceOD - blankOD);
  }
};

// declare objects to call
Fan myFan(FAN_TACH, FAN_PWM);
Pump myPump(PUMP);
Temperature myTemp(TEMP_SENSOR, HEATER);
OD myOD;

void ReadJson() {
    if (!Serial.available()) {
        return;
    }

    // json is terminated by '\n'
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() == 0) {
        return;
    }

    StaticJsonDocument<256> doc;

    DeserializationError error = deserializeJson(doc, cmd);

    if (error) {
        Serial.print("JSON parse error: ");
        Serial.println(error.c_str());
        return;
    }

    // make sure the message is a JSON object
    if (!doc.is<JsonObject>()) {
        Serial.println("Invalid command: expected JSON object");
        return;
    }

    if (doc.containsKey("Temperature")) {
        double target = doc["Temperature"].as<double>();

        // double check with James for temperature bounds
        myTemp.targetTemp = constrain(target, 20.0, 65.0);
    }

    if (doc.containsKey("Input Pump 1")) {
        int speed = doc["Input Pump 1"].as<int>();
        speed = constrain(speed, 0, 100);

        myPump.continuousMode = true;
        myPump.speedPercent = speed;
        myPump.active = (speed > 0);

        if (myPump.active) {
            myPump.setSpeedPercent(myPump.speedPercent);
        } else {
            myPump.stop();
        }
    }

    if (doc.containsKey("Stirring Fan")) {
        int speed = doc["Stirring Fan"].as<int>();
        speed = constrain(speed, 0, 100);

        myFan.speedPercent = speed;
    }
}


void setup() {
  Serial.begin(115200);
  delay(1000);
  printCycleStart = millis();
  Serial.println("Run starts");
  runStart = millis();
  myOD.init();
  myOD.dark();
  myOD.blank();
  myOD.reference(); //will need buttons to run this, or delays idk
  myTemp.init();
}

// use if front-end does not work :sob:
void HandleSerial() {
  if (!Serial.available()) {
    return;
  }
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.startsWith("F ") || cmd.startsWith("f ")) {
    myFan.speedPercent = cmd.substring(2).toInt();
  }
  if (cmd.startsWith("P ") || cmd.startsWith("p ")) {
    int spaceIndex = cmd.indexOf(' ', 2);
    if (spaceIndex != -1 && !myPump.active) {
      myPump.moveDuration = cmd.substring(2, spaceIndex).toInt() * 1000;
      myPump.speedPercent = cmd.substring(spaceIndex + 1).toInt();
    }
  }
  if (cmd.startsWith("T ") || cmd.startsWith("t ")) {
    myTemp.targetTemp = cmd.substring(2).toDouble();
  }
}

// used only for non-UI/manual version
void PrintStats() {
  Serial.print("{\"Fan PWM\":");
  Serial.print(myFan.speedPercent);
  Serial.print(",\"Fan RPM\":");
  Serial.print(myFan.currentRPM);
  Serial.print(",\"Pump Active\":");
  Serial.print(myPump.active ? "true" : "false");
  Serial.print(",\"Pump Speed\":");
  Serial.print(myPump.speedPercent);
  Serial.print(",\"Pump Duration\":");
  Serial.print(myPump.moveDuration / 1000);
  Serial.print(",\"Temperature\":");
  Serial.print(myTemp.currentTemp, 2);
  Serial.print(",\"Temperature Target\":");
  Serial.print(myTemp.targetTemp, 2);
  Serial.print(",\"OD\":");
  Serial.print(myOD.nOD, 4);
  Serial.println("}");
  
} 

// expected format: {"Fan PWM": 45, "Fan RPM": 900, "Pump Active": true, 
//"Pump Speed": 55, "Temperature": 37.0, "Temperature Target": 37.0, "OD": 0.960, "pH": 7.00}
void SendStats() {
    StaticJsonDocument<256> doc;

    doc["Fan PWM"] = myFan.speedPercent;
    doc["Fan RPM"] = myFan.currentRPM;

    doc["Pump Active"] = myPump.active;
    doc["Pump Speed"] = myPump.speedPercent;
    doc["Pump Duration"] = myPump.moveDuration / 1000;

    doc["Temperature"] = myTemp.currentTemp;
    doc["Temperature Target"] = myTemp.targetTemp;

    doc["OD"] = myOD.nOD;

    serializeJson(doc, Serial);
    Serial.println();
}

void loop() {
  delay(100);
  //HandleSerial(); // uncomment if not running UI
  ReadJson();
  myFan.update();
  myPump.update();
  myOD.read();
  myTemp.update();
  SendStats(); // comment out if doing manual commands
  /*unsigned long now = millis();
  if (millis() - printCycleStart > 1000) {
    int minutes = (now - runStart) / 60000;
    int seconds = ((now - runStart) % 60000) / 1000;
    Serial.print(minutes);
    Serial.print(':');
    Serial.println(seconds);
    PrintStats();
    printCycleStart = millis();
  }*/ // also uncomment if not running UI
}

