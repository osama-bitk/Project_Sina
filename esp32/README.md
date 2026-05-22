# ESP32 firmware (Phase 3–4)

Two Arduino sketches. The ESP32 is throwaway hardware — once Phase 5 lands and the Pi drives IR directly, this directory is dead code (kept for reference).

## Sketches (to be created)

- `ir_decoder/` — Phase 3 IR recon. Reads from VS1838B receiver, logs raw IR codes from the LG remote over serial.
- `ir_server/` — Phase 4 transmitter. Hosts HTTP endpoint on the LAN, fires captured IR codes on request.

## Phase 3 recon checklist

Capture every relevant button on the LG remote:

- Power on / off
- Every temperature step (16°C–30°C)
- Every fan mode (auto, low, med, high, turbo)
- Every operating mode (cool, heat, dry, fan-only)
- **Status / display button** — investigate whether the AC sends any IR response. If so, this is the path to on-demand state queries (per the stateless design — see plan §8).

Save the result to `../ir_codes/lg_ac.json`.

## Dependencies

- Arduino IDE with ESP32 board support
- [`IRremoteESP8266`](https://github.com/crankyoldgit/IRremoteESP8266) (works on ESP32)

## Hardware

3 jumper wires per module. No soldering — use pre-pinned dev boards and breakout modules. See main plan §6 for the BOM.
