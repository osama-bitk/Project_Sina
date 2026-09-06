// Sina IR closed-loop self-test — Phase 4, step 1.
//
// Transmits each known frame on the IR emitter and decodes it back through
// the VS1838B receiver on the same breadboard. Proves the frames built by
// mac/lg_ir.py are ones real IR hardware emits and reads back correctly,
// with no AC and no Wi-Fi in the loop.
//
// Wiring: emitter DAT -> GPIO4, VCC -> 5V, GND -> GND
//         VS1838B OUT -> GPIO15, VCC -> 3.3V, GND -> GND
//
// NOTE: this actually transmits. A real AC in range WILL respond to these
// frames (including power-off and jet). Aim away from the unit, or expect it
// to react.

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

IRsend irsend(kIrLedPin);
IRrecv irrecv(kRecvPin, kCaptureBufferSize, kTimeout, /*save_buffer=*/true);
decode_results results;

struct TestFrame {
  const char *name;
  uint32_t    value;
};

// Every frame below came from ../../ir_codes/lg_ac.json.
const TestFrame kFrames[] = {
  {"cool 16C fan=auto", 0x880815E},
  {"cool 22C fan=auto", 0x8808754},
  {"cool 30C fan=auto", 0x8808F5C},
  {"cool 18C fan=high", 0x880834F},
  {"dry 24C fan=low",   0x8809902},
  {"power_off",         0x88C0051},
  {"jet (Po)",          0x8810089},
  {"light toggle",      0x88C00A6},
};
const size_t kFrameCount = sizeof(kFrames) / sizeof(kFrames[0]);

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  irsend.begin();
  irrecv.setUnknownThreshold(kMinUnknownSize);
  irrecv.enableIRIn();

  Serial.println();
  Serial.println("Sina IR closed-loop self-test");
  Serial.println("Transmitting each known frame and decoding it back.");
  Serial.println("------------------------------------------------------------");
}

// Send one frame, then wait for the receiver to hear it back.
bool runFrame(const TestFrame &frame) {
  irrecv.resume();
  Serial.printf("SEND %-18s 0x%07X ... ", frame.name, frame.value);

  irsend.sendLG2(frame.value, kLgAcBits);

  uint32_t deadline = millis() + 1000;
  while (millis() < deadline) {
    if (irrecv.decode(&results)) {
      uint32_t got = (uint32_t)results.value;
      bool match = (got == frame.value);
      Serial.printf("RECV 0x%07X  %s  [%s, %d bits]\n", got,
                    match ? "MATCH" : "MISMATCH",
                    typeToString(results.decode_type, results.repeat).c_str(),
                    results.bits);
      if (!match) {
        // Raw timings let the Mac-side decoder adjudicate when the library
        // mislabels an otherwise clean frame.
        Serial.println(resultToTimingInfo(&results));
      }
      return match;
    }
    delay(5);
  }

  Serial.println("NO ECHO (receiver heard nothing)");
  return false;
}

void loop() {
  size_t passed = 0;

  for (size_t i = 0; i < kFrameCount; i++) {
    if (runFrame(kFrames[i])) passed++;
    delay(1200);  // let the AC settle and avoid frames running together
  }

  Serial.println("------------------------------------------------------------");
  Serial.printf("%u/%u frames echoed back correctly\n", (unsigned)passed,
                (unsigned)kFrameCount);
  Serial.println("Press RESET to run again.");
  Serial.println();

  while (true) delay(1000);  // run once, not on a loop
}
