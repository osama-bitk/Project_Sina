# ESP32 firmware (Phase 3–4)

Two Arduino sketches. The ESP32 is throwaway hardware — once Phase 5 lands and the Pi drives IR directly, this directory is dead code (kept for reference).

| Dir | Phase | Purpose |
|---|---|---|
| `ir_decoder/` | 3 | Reads from VS1838B IR receiver, prints decoded protocol/bits/hex per button press. Used once to build the codebook. |
| `ir_server/` | 4 | (TBD) HTTP endpoint on the LAN, fires captured IR codes on request. |

## Phase 3: capture the LG remote

### One-time setup

1. **Arduino IDE.** Install Arduino IDE 2.x ([arduino.cc/downloads](https://arduino.cc/en/software)).
2. **ESP32 board support.** File → Preferences → Additional Boards Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
   Then Tools → Board → Boards Manager → search "esp32" → install Espressif's package.
3. **IRremoteESP8266 library.** Sketch → Include Library → Manage Libraries → search "IRremoteESP8266" → install.
4. **Select board + port.** Tools → Board → ESP32 → pick your dev-board variant (DevKit V1 / WROOM-32 / NodeMCU-32S all work). Tools → Port → the new `/dev/cu.usbserial-*` that appears when you plug in the ESP32.

### Wiring (VS1838B → ESP32, 3 wires, no solder)

| VS1838B pin | ESP32 pin |
|---|---|
| VCC (or `+`)   | 3.3V (most modules tolerate 5V; check yours) |
| GND (or `-`)   | GND |
| OUT (or `S`, `DAT`) | **GPIO15** |

GPIO15 is the pin the sketch listens on. If you use a different GPIO, change `kRecvPin` in `ir_decoder/ir_decoder.ino`.

### Capture procedure

1. Open `ir_decoder/ir_decoder.ino` in the Arduino IDE.
2. Click Upload. Wait for the "Done uploading" message.
3. Open Serial Monitor (Tools → Serial Monitor) at **115200 baud**. You should see:
   ```
   Sina IR decoder ready.
   Point the LG remote at the VS1838B and press a button.
   ```
4. Point the LG AC remote directly at the VS1838B (1-3 ft, line of sight). Press a button. Expect one line like:
   ```
   LG2 | 28 bits | 0x88C0051
   ```
5. Press every button the brain will need to drive. Minimum set:
   - Power **on**, power **off**
   - Every temperature step 16°C → 30°C
   - Each fan speed: auto, low, med, high
   - Each mode: cool, heat, dry, fan
   - **Status / Display** button — capture it; if the AC echoes IR back when you press it (some LG units do), this is the path for `get_state`. If not, `get_state` returns "unknown" at runtime, which is fine.
6. For each capture, append an entry to `../ir_codes/lg_ac.json`:
   ```json
   {
     "power_on":     {"protocol": "LG2", "bits": 28, "hex": "0x88C0051"},
     "power_off":    {"protocol": "LG2", "bits": 28, "hex": "0x88C00A6"},
     "temp_22":      {"protocol": "LG2", "bits": 28, "hex": "..."},
     "...": "..."
   }
   ```

### What "good capture" looks like

- Same button → same hex value every time. Reproducibility is the smoke test.
- Protocol field consistently reads `LG`, `LG2`, or similar — not `UNKNOWN`. If you see `UNKNOWN`, the sketch will also print a raw timing array; we'll fall back to replaying timings directly in Phase 4.
- Bit count is consistent across all buttons of one type (e.g. all temp values are the same bit count; LG ACs encode full state in one frame).

### Exit criteria

`ir_codes/lg_ac.json` has every required command captured and the same button produces the same hex on repeated presses. See the main plan §7 Phase 3.

## Hardware

3 jumper wires per module. No soldering — use pre-pinned dev boards and breakout modules. See main plan §6 for the BOM.
