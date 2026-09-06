// Sina IR bridge — Phase 4.
//
// The node holds no codebook and makes no decisions (invariant 4). The brain
// builds a finished LG frame and hands it over; this transmits it verbatim.
// Serial now, HTTP later — the contract is the same either way, so swapping
// the transport does not change the node's job.
//
// Protocol (line-based, 115200 baud):
//   SEND <hex> [bits]   transmit an LG2 frame, e.g. "SEND 0x8808754"
//   PING                replies PONG
//   -> replies "OK <hex> <bits>" or "ERR <reason>"
//
// Also prints anything the receiver decodes as "RX <hex>", which keeps the
// VS1838B useful for confirming what the AC's own remote sends.
//
// Wiring: emitter SIG -> GPIO14, VCC -> 3V3 (5V for more range), GND -> GND
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
const uint16_t kDefaultBits       = 28;

IRsend irsend(kIrLedPin);
IRrecv irrecv(kRecvPin, kCaptureBufferSize, kTimeout, /*save_buffer=*/true);
decode_results results;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(300);

  irsend.begin();
  irrecv.setUnknownThreshold(kMinUnknownSize);
  irrecv.enableIRIn();

  Serial.println();
  Serial.println("READY Sina IR bridge");
  Serial.printf("TX GPIO%d, RX GPIO%d\n", kIrLedPin, kRecvPin);
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.equalsIgnoreCase("PING")) {
    Serial.println("PONG");
    return;
  }

  if (!line.startsWith("SEND ") && !line.startsWith("send ")) {
    Serial.println("ERR unknown command");
    return;
  }

  String rest = line.substring(5);
  rest.trim();

  int space = rest.indexOf(' ');
  String hexPart = (space < 0) ? rest : rest.substring(0, space);
  uint16_t bits = kDefaultBits;
  if (space >= 0) {
    bits = (uint16_t)rest.substring(space + 1).toInt();
    if (bits == 0) bits = kDefaultBits;
  }

  char *end = nullptr;
  uint64_t value = strtoull(hexPart.c_str(), &end, 16);
  if (end == hexPart.c_str() || value == 0) {
    Serial.println("ERR bad hex");
    return;
  }

  irsend.sendLG2(value, bits);
  Serial.printf("OK 0x%llX %u\n", (unsigned long long)value, bits);
}

void loop() {
  if (Serial.available()) {
    handleLine(Serial.readStringUntil('\n'));
  }

  if (irrecv.decode(&results)) {
    Serial.printf("RX 0x%llX [%s, %d bits]\n", (unsigned long long)results.value,
                  typeToString(results.decode_type, results.repeat).c_str(),
                  results.bits);
    irrecv.resume();
  }
}
