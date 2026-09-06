// Sina IR diagnostic — isolates a TX problem from an RX problem.
//
// Every 2s it transmits one known frame. Between transmissions it prints
// anything the receiver decodes, from the emitter or from the LG remote.
//
// That gives two independent checks:
//   RX works  -> press the LG remote at the VS1838B, a line appears.
//   TX works  -> point a phone camera at the IR LED; the emitter flashes
//                visibly (phone sensors see IR, the human eye does not).
//
// Wiring: emitter DAT -> GPIO4, VCC -> 5V, GND -> GND
//         VS1838B OUT -> GPIO15, VCC -> 3.3V, GND -> GND

#include <Arduino.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <IRrecv.h>
#include <IRutils.h>

const uint16_t kIrLedPin          = 14;
const uint16_t kRecvPin           = 15;
const uint16_t kCaptureBufferSize = 1024;
const uint8_t  kTimeout           = 50;
const uint16_t kMinUnknownSize    = 12;
const uint16_t kLgAcBits          = 28;
const uint32_t kTestFrame         = 0x8808754;  // cool 22C fan=auto

IRsend irsend(kIrLedPin);
IRrecv irrecv(kRecvPin, kCaptureBufferSize, kTimeout, /*save_buffer=*/true);
decode_results results;

uint32_t lastSend = 0;
uint32_t sendCount = 0;
uint32_t recvCount = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  pinMode(kIrLedPin, OUTPUT);
  digitalWrite(kIrLedPin, LOW);

  irsend.begin();
  irrecv.setUnknownThreshold(kMinUnknownSize);
  irrecv.enableIRIn();

  Serial.println();
  Serial.println("Sina IR diagnostic");
  Serial.printf("TX on GPIO%d, RX on GPIO%d\n", kIrLedPin, kRecvPin);
  Serial.println("Sending 0x8808754 every 2s. Press the LG remote to test RX.");
  Serial.println("Point a phone camera at the IR LED to test TX visually.");
  Serial.println("------------------------------------------------------------");
}

void loop() {
  if (millis() - lastSend > 2000) {
    lastSend = millis();
    sendCount++;
    Serial.printf("[tx #%u] sending 0x%07X\n", (unsigned)sendCount, kTestFrame);
    irsend.sendLG2(kTestFrame, kLgAcBits);
    irrecv.resume();
  }

  if (irrecv.decode(&results)) {
    recvCount++;
    Serial.printf("[rx #%u] 0x%llX  [%s, %d bits]\n", (unsigned)recvCount,
                  (unsigned long long)results.value,
                  typeToString(results.decode_type, results.repeat).c_str(),
                  results.bits);
    irrecv.resume();
  }
}
