const byte TACH_PIN = 2;      

const byte PWM_PIN  = 9;      


volatile unsigned long pulseCount = 0;

unsigned long lastCalcTime = 0;

unsigned int currentRPM = 0;

int currentSpeedPercent = 100; 


void tachISR() {

  pulseCount++;

}


void setup() {

  Serial.begin(9600);

  pinMode(TACH_PIN, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(TACH_PIN), tachISR, FALLING);


  pinMode(PWM_PIN, OUTPUT);

  setFanSpeed(currentSpeedPercent);


  Serial.print(F("Sunon fan controller ready - hardcoded to "));

  Serial.print(currentSpeedPercent);

  Serial.println(F("% speed."));

  lastCalcTime = millis();

}


void loop() {


  if (millis() - lastCalcTime >= 1000) {

    noInterrupts();

    unsigned long pulses = pulseCount;

    pulseCount = 0;

    interrupts();


 

    currentRPM = (pulses / 2) * 60;


    Serial.print(F("RPM: "));

    Serial.print(currentRPM);

    Serial.print(F("   Commanded speed: "));

    Serial.print(currentSpeedPercent);

    Serial.println(F("%"));


    lastCalcTime = millis();

  }

}


void setFanSpeed(int percent) {

  percent = constrain(percent, 0, 100);

  currentSpeedPercent = percent;

  int pwmValue = map(percent, 0, 100, 0, 255);

  analogWrite(PWM_PIN, pwmValue);

}

