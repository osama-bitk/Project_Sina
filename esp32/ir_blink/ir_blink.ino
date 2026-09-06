// Sina IR emitter blink test.
//
// Not a protocol test — this just drives the IR LED hard on and off so a
// phone camera can see it. A ~60ms protocol burst is nearly invisible on
// camera; 500ms solid is obvious.
//
// Expect on a phone camera (front camera if the rear one filters IR):
// a faint purple/white glow, 0.5s on, 1.5s off, in step with the serial log.
//
// Duty cycle is kept low deliberately: IR LEDs are rated for pulsed use and
// continuous DC can cook them.
//
// Wiring under test: emitter DAT -> GPIO4, VCC -> 5V, GND -> GND

#include <Arduino.h>

const uint16_t kIrLedPin = 14;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  pinMode(kIrLedPin, OUTPUT);
  digitalWrite(kIrLedPin, LOW);

  Serial.println();
  Serial.printf("IR emitter blink test on GPIO%d\n", kIrLedPin);
  Serial.println("Point a phone camera at the IR LED. 0.5s on, 1.5s off.");
  Serial.println("If the LED never glows, the module is miswired, unpowered,");
  Serial.println("or the signal pin is not GPIO4.");
  Serial.println("------------------------------------------------------------");
}

void loop() {
  Serial.println("LED ON");
  digitalWrite(kIrLedPin, HIGH);
  delay(500);

  Serial.println("LED off");
  digitalWrite(kIrLedPin, LOW);
  delay(1500);
}
