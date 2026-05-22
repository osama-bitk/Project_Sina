// Sina IR decoder — Phase 3 reconnaissance sketch.
//
// Reads IR signals from a VS1838B module on GPIO15 and prints the decoded
// protocol/bits/value for each press. Point the LG AC remote, press a button,
// copy the line into ../../ir_codes/lg_ac.json.
//
// Library: IRremoteESP8266 (works on ESP32 despite the name).
// Wiring : VS1838B OUT -> GPIO15, VCC -> 3.3V (modules with regulator are 5V tolerant), GND -> GND.

#include <Arduino.h>
#include <IRremoteESP8266.h>
#include <IRrecv.h>
#include <IRutils.h>

const uint16_t kRecvPin           = 15;
const uint16_t kCaptureBufferSize = 1024;  // LG AC frames are long; leave room
const uint8_t  kTimeout           = 50;    // ms of silence = end of frame
const uint16_t kMinUnknownSize    = 12;    // ignore noise shorter than this

IRrecv irrecv(kRecvPin, kCaptureBufferSize, kTimeout, /*save_buffer=*/true);
decode_results results;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  Serial.println();
  Serial.println("Sina IR decoder ready.");
  Serial.println("Point the LG remote at the VS1838B and press a button.");
  Serial.println("Format: <protocol> | <bits> bits | <hex>");
  Serial.println("------------------------------------------------------------");
  irrecv.setUnknownThreshold(kMinUnknownSize);
  irrecv.enableIRIn();
}

void loop() {
  if (!irrecv.decode(&results)) {
    return;
  }

  // Concise copy-paste line for the codebook.
  Serial.printf(
    "%s | %d bits | 0x%llX\n",
    typeToString(results.decode_type, results.repeat).c_str(),
    results.bits,
    (unsigned long long)results.value
  );

  // Raw timing array — useful if the protocol is UNKNOWN and we need to
  // replay it as a timing sequence rather than a clean hex code.
  Serial.println(resultToTimingInfo(&results));
  Serial.println();

  yield();
}
