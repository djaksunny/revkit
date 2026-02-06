const int encoderPin1 = D6;  // Channel A
const int encoderPin2 = D7;  // Channel B
const int motorPin1 = D2;
const int motorPin2 = D3;

volatile unsigned long lastPulseMicros = 0;
volatile unsigned long pulseIntervalMicros = 0;
volatile bool newPulse = false;
volatile int direction = 1;

volatile float rpm = 0;

const int pulsesPerRev = 224;

void IRAM_ATTR onPulse() {
  unsigned long now = micros();
  pulseIntervalMicros = now - lastPulseMicros;
  lastPulseMicros = now;
  direction = digitalRead(encoderPin2) ? 1 : -1;  // if B is high when A rises, direction is reverse
  rpm = direction * (60.0 * 1e6) / (pulsesPerRev * pulseIntervalMicros);
  // newPulse = true;
}

void setup() {
  Serial.begin(115200);
  pinMode(encoderPin1, INPUT_PULLUP);
  pinMode(encoderPin2, INPUT_PULLUP);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(encoderPin1), onPulse, RISING);
}

void loop() {
  // Handle incoming PWM command
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    int pwm = input.toInt();

    if (pwm > 0) {
      analogWrite(motorPin1, pwm);
      analogWrite(motorPin2, 0);  // Forward
    } else {
      analogWrite(motorPin2, -pwm);
      analogWrite(motorPin1, 0);  // Backward
    }

    Serial.print("I:");
    Serial.println(rpm, 1);
  }

  // // Compute and send RPM
  // static unsigned long lastPrintMicros = 0;
  // unsigned long now = micros();

  // if (newPulse) {
  //   newPulse = false;
  //   if (pulseIntervalMicros > 0) {
  //     float rpm = (60.0 * 1e6) / (pulsesPerRev * pulseIntervalMicros);
  //     Serial.print("I:");
  //     Serial.println(direction * rpm, 1);
  //   }
  //   lastPrintMicros = now;
  // } else if (now - lastPrintMicros > 30000) {
  //   Serial.println("I:0.0");
  //   lastPrintMicros = now;
  // }

  // // delay(5);
}
