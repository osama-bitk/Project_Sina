# ESP32 firmware (Phase 3–4)

Two Arduino sketches. The board is an **ESP32-S3 N16R8** — not throwaway: after recon it becomes room node #1 (mic + wake word + IR emitter) in the central-brain architecture (plan §4, revised 2026-07-04). Phase 6 replaces these sketches with the node voice-satellite firmware.

| Dir | Phase | Purpose |
|---|---|---|
| `ir_decoder/` | 3 | Reads from VS1838B IR receiver, prints decoded protocol/bits/hex per button press. Used once to build the codebook. |
| `ir_server/` | 4 | (TBD) HTTP endpoint on the LAN, fires captured IR codes on request. |

## Phase 3: capture the LG remote — **done 2026-09-06**

Kept as the procedure of record; it is how the codebook in `../ir_codes/` was produced. Results and the decoded frame format live in the root `README.md` and plan §7.

### One-time setup (`arduino-cli`, no GUI)

The whole flash/monitor loop is scriptable, which matters when capturing dozens of button presses.

```sh
brew install arduino-cli
arduino-cli config init
arduino-cli config set board_manager.additional_urls \
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32      # large toolchain, several minutes
arduino-cli lib install IRremoteESP8266
```

### Board gotchas (ESP32-S3 N16R8 on a USB-C-only Mac)

These cost real time; read them before assuming the board is dead.

- **Use the port marked `USB`, not `COM`.** The COM port (USB-UART bridge) lacks the 5.1kΩ CC pull-down resistors, so a USB-C host delivers **no power at all** through it — no LED, no enumeration, nothing. The `USB` port goes to the S3's native USB and works. A dark power LED is a power problem, never a driver problem.
- **No driver needed.** Native USB enumerates as `/dev/cu.usbmodem*`, Espressif VID `0x303a`.
- **Manual bootloader entry.** Upload may fail with `No serial data received`. Hold **BOOT**, tap **RESET**, release **BOOT** — the board re-enumerates under a *different* port name, so rescan before uploading.
- **`CDCOnBoot=cdc` is required** or `Serial` output goes to the UART pins instead of the USB port you're watching.
- Pressing RESET drops the USB CDC device, which kills any attached serial reader — use one that reconnects.

```sh
FQBN="esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=cdc,USBMode=hwcdc,PSRAM=disabled"
arduino-cli board list                       # find the port
arduino-cli compile -b "$FQBN" ir_decoder/
arduino-cli upload -p /dev/cu.usbmodemXXXX -b "$FQBN" ir_decoder/
```

PSRAM is disabled here because this sketch doesn't need it; the wake-word work in Phase 4.5 will need `PSRAM=opi` for the N16R8.

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
- **`UNKNOWN` does not mean a bad capture.** `IRremoteESP8266` mislabels clean frames when the buffer ends right at the frame boundary with no trailing gap. Decode the raw timing array instead with `../mac/decode_capture.py`, which verifies the LG checksum — a valid checksum proves the frame was read correctly, which is stronger evidence than the library's label.
- Bit count is consistent across all buttons of one type (e.g. all temp values are the same bit count; LG ACs encode full state in one frame).

### Capture method that actually worked

Two rules removed all the ambiguity:

1. **Batch so that no two consecutive presses produce the same code** (e.g. sweep temp 16→30 rather than pressing one button repeatedly). Then a repeated code is provably a repeat frame from one press, not a second press. A monotonic sweep also self-validates: if the temp nibble increments exactly once per press with nothing else moving, the mapping cannot be misaligned.
2. **Isolate discrete buttons** — clear the log, one press, nothing else. A multi-press batch of jet/sleep produced an alternating pattern that supported two different explanations; a single isolated press settled it immediately.

For anything whose meaning depends on the display (fan labels, mode icons, whether a toggle went on or off), record what the remote showed — the IR alone cannot tell you which nibble means "medium".

### Exit criteria

~~`ir_codes/lg_ac.json` has every required command captured and the same button produces the same hex on repeated presses.~~ **Met 2026-09-06** — exceeded, in fact: the frame encoding was solved, so `../mac/lg_ir.py` constructs any state frame and reproduces all 23 captured samples as its self-test. See the main plan §7 Phase 3.

## Hardware

3 jumper wires per module. No soldering — use pre-pinned dev boards and breakout modules. See main plan §6 for the BOM.
