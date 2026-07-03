# Hardware Shopping List

What to buy, by phase. Prices approximate USD. No-solder rule applies: pre-pinned dev boards and breakout modules only.

Architecture (revised 2026-07-04): **one central Pi 5 brain + one ESP32-S3 node per room**. The recon board below becomes room node #1 — nothing is throwaway.

## Buy now — Phase 3–4 (recon board = future room node #1)

| # | Item | Qty | ~Cost | Notes |
|---|---|---|---|---|
| 1 | ESP32-S3 **N16R8** dev board, pre-soldered headers | 1 | $10 | The R8 (8MB PSRAM) is **required** for on-device wake word. ⚠️ **Check the antenna before buying:** squiggle PCB trace = onboard antenna, good; small metal u.FL connector = needs a separate external antenna or Wi-Fi is crippled |
| 2 | VS1838B IR receiver module (3-pin breakout) | 1 | $1 | Recon only — captures the LG remote once, not in the final node |
| 3 | IR transmitter module **with driver transistor** (3-pin breakout) | 1 | $3 | Not a bare KY-005 — the driver matters for range |
| 4 | INMP441 I2S MEMS microphone | 1 | $3 | The node's mic. Not needed for recon, needed the moment this board becomes a real node — order with everything else |
| 5 | Breadboard (half-size fine) | 1 | $3 | One-time |
| 6 | Jumper wires, M-M + M-F + F-F assortment | 1 pack | $3 | A 40-pack covers everything forever |
| 7 | USB-C **data** cable | 1 | $3 | Must be data, not charge-only — common gotcha |

**Subtotal: ~$26**

## Buy at Phase 5 — central brain (one per home, NOT per room)

| # | Item | Qty | ~Cost | Notes |
|---|---|---|---|---|
| 8 | Raspberry Pi 5, **8GB** | 1 | $80 | 4GB is not enough for SLM + Whisper resident together |
| 9 | Official Pi 5 PSU (27W USB-C) | 1 | $12 | Non-negotiable — voltage drops crash inference |
| 10 | Active cooler for Pi 5 (official) | 1 | $10 | Mandatory under sustained inference load |
| 11 | MicroSD 64GB, **A2-rated** | 1 | $12 | Or NVMe HAT + SSD (~$35) for longevity |
| 12 | Pi 5 case with cooler cutout | 1 | $10 | Optional but tidy |

**Subtotal: ~$125, once**

No USB microphone needed — the nodes are the ears.

## Per additional room (Phase 7)

| Item | ~Cost |
|---|---|
| ESP32-S3 N16R8 + INMP441 + IR transmitter module | **~$16/room** |

## Phase 6+ additions

| # | Item | Qty | ~Cost | Notes |
|---|---|---|---|---|
| 13 | LED (pre-wired module) | 1/room | $1 | Listening-state indicator |
| 14 | MAX98357A I2S amp + small speaker | 1/room | $3–5 | Only if Phase 6.5 TTS feedback per room is wanted — decide later |

## Already have / no purchase needed

- Mac (Phase 1–4 stand-in brain) — done.
- LG AC remote — the capture source.
- Home Wi-Fi router — LAN only; no internet used at runtime.

## Buying tips

- ESP32-S3 boards and IR modules are cheapest in multi-packs (AliExpress/Amazon) — but buy **one** S3 first: the Phase 4.5 wake-word spike decides whether this exact board is the right node before you buy five.
- Verify the S3 listing says N16R8 (16MB flash / 8MB PSRAM); N8R2 and no-PSRAM variants look identical.
- Skip Pi 4 deals — Pi 5's SIMD is what makes on-device inference viable (plan §5).
