# Project Sina — Full Project Plan

**A local, offline, voice-controlled AI agent for home appliance control. No cloud, no vendor lock-in, no telemetry.**

---

## 1. Vision

Build a self-contained AI device that lives in each room of the house. It listens for voice commands, runs a small language model locally to understand intent, and emits infrared signals to control the AC (and eventually other IR-controlled appliances). No internet, no cloud APIs, no smart-home accounts.

The end state is a **plug-and-play unit**: a small box with a microphone, a microcontroller, and an IR emitter, all running off USB power, that you can drop into any room and have working voice-controlled climate within minutes.

---

## 2. Strategic Goals

- **Fully offline.** The entire pipeline — wake word, speech recognition, intent parsing, hardware control — runs locally with zero internet dependency.
- **Vendor-independent.** Bypass LG ThinQ, Amazon Alexa, Google Home, etc. Treat the AC as a dumb IR receiver and own every layer above it.
- **Software-first, hardware-pragmatic.** Use off-the-shelf, no-solder hobbyist components (ESP32 dev boards, breakout modules, jumper wires, breadboards). Learn the hardware layer without becoming an electrical engineer.
- **Reproducible and modular.** Every room gets an identical unit. Adding a third, fourth, or tenth room is a hardware-clone operation, not a software re-architecture.
- **Replicable build.** A clean repo + bill of materials means anyone (including future-you) can rebuild the system from scratch.

---

## 3. Technical Objectives

- **Tool-calling accuracy ≥ 95%** on a defined benchmark set of natural-language AC commands.
- **End-to-end latency ≤ 2 seconds** from end-of-speech to IR emission for the Mac-hosted phase. ≤ 3 seconds for the Pi-hosted edge phase.
- **CPU thermal headroom.** No sustained 100% CPU. Model size and context window tuned to keep the host stable.
- **Zero internet calls at runtime.** Verified by running the system with Wi-Fi disabled (after initial setup downloads).
- **Graceful failure.** Malformed model output, hardware timeouts, or ambiguous commands all surface as clean error states, not silent failures.

---

## 4. System Architecture

The project goes through **two distinct architectural phases**, each a complete working system in its own right.

### Phase A — Centralized (Mac-hosted)

```
[Mic] → [Whisper on Mac] → [Ollama+SLM on Mac] → [Python brain.py] → [Wi-Fi HTTP] → [ESP32 + IR LED] → [AC]
```

- One Mac, many ESP32 IR nodes (one per room).
- Mac does all the heavy lifting (ASR + SLM inference).
- ESP32s are dumb HTTP endpoints that fire IR codes on request.
- This phase exists to validate the software stack before committing to edge hardware.

### Phase B — Distributed Edge (Pi-hosted, the end goal)

```
Per-room unit:
[Mic] → [Whisper on Pi] → [Ollama+SLM on Pi] → [Python agent] → [GPIO/IR LED] → [AC]
```

- One self-contained device per room. No central server.
- Raspberry Pi 5 (8GB) per unit, running the full stack locally.
- No cross-room dependencies. Each unit can be unplugged and moved without breaking the others.
- Optional: units can discover each other on the LAN for whole-home commands ("turn off all ACs"), but each unit functions standalone.

**Why this split exists:** Phase A lets us iterate the software stack on a much faster machine (the Mac) before re-deploying to constrained edge hardware. Phase B is the actual product.

---

## 5. Technology Stack

| Layer | Phase A (Mac) | Phase B (Edge) | Notes |
|---|---|---|---|
| Inference runtime | Ollama (native macOS) | Ollama or llama.cpp | llama.cpp may be preferred on Pi for raw speed |
| SLM | Qwen 2.5 (1.5B vs 3B, benchmarked) | Same model chosen in Phase A | Re-benchmark on Pi — performance characteristics differ |
| Speech-to-text | `faster-whisper` or `whisper.cpp` (tiny/base) | `whisper.cpp` (tiny) | Pi requires the smallest viable model |
| Wake word | Manual trigger (push-to-talk) initially → `openWakeWord` | `openWakeWord` | Avoid Picovoice (cloud licensing) |
| Agent middleware | Python 3.11+ (`ollama`, `pydantic`, `requests`, `pyaudio`) | Same | Pydantic non-negotiable for tool-call validation |
| Microcontroller | ESP32 dev board (no soldering — pre-pinned) | Replaced by Pi GPIO | ESP32 phase is throwaway hardware once Pi handles IR directly |
| IR receiver (recon) | VS1838B module | — | Used once to capture LG codes |
| IR emitter | IR transmitter module with built-in driver transistor | Same module, wired to Pi GPIO | Pre-built module to avoid soldering a driver circuit |
| IR library | `IRremoteESP8266` (works on ESP32) | `pigpio` + custom IR encoder, or `lirc` | Pi side requires more legwork than ESP32 |
| Edge host | — | Raspberry Pi 5, 8GB RAM, active cooling | Pi 4 not recommended; Pi 5 NEON SIMD is the unlock |
| OS (Pi) | — | Raspberry Pi OS Lite (64-bit) | Headless, minimal footprint |
| Power | Standard USB-C charger | USB-C PD charger for Pi | Pi 5 needs the official 27W PSU for stability under load |

---

## 6. Bill of Materials (per room, Phase B)

| Item | Approx. cost (USD) | Notes |
|---|---|---|
| Raspberry Pi 5 (8GB) | $80 | The minimum viable spec; 4GB is not enough |
| Official Pi 5 PSU (27W USB-C) | $12 | Don't skimp — voltage drops cause SLM crashes |
| MicroSD 64GB (A2 rated) | $12 | Or NVMe HAT if you want longevity |
| Active cooler for Pi 5 | $10 | Mandatory under sustained inference load |
| USB microphone (e.g. MiniDSP UMA-8 or any decent USB mic) | $15-30 | Quality directly impacts Whisper accuracy |
| IR transmitter module (with driver) | $3 | Pre-built breakout board |
| Jumper wires + breadboard | $5 | One-time purchase, supplies multiple units |
| Pi case with cooler cutout | $10 | Cosmetic but useful |
| **Per-unit total** | **~$150** | Vs. $200+/yr for cloud-locked alternatives |

**Phase A prototyping additions (one-time):**

| Item | Approx. cost (USD) |
|---|---|
| ESP32 dev board (with pre-soldered headers) | $8 |
| VS1838B IR receiver module | $1 |

---

## 7. Execution Roadmap

### Phase 1 — Software core on the Mac (no hardware)

**Goal:** Prove the SLM can reliably translate natural language into structured AC commands.

- Install Ollama natively on macOS.
- Pull both `qwen2.5:1.5b` and `qwen2.5:3b` for head-to-head benchmarking.
- Author two Modelfiles (`sina-small`, `sina-medium`) with strict system prompts and low temperature.
- Build `brain.py` — a CLI agent that takes typed input, calls Ollama with a tool schema, and prints the resulting tool call to stdout (dry-run mode).
- Build `benchmark.py` — runs a JSONL test suite (literal commands, colloquial, ambiguous, off-topic, adversarial) against both models and outputs a CSV comparing accuracy and latency.
- Add a Pydantic validation layer for tool-call output. Malformed JSON triggers a single retry with a corrective prompt; second failure logs and aborts.
- **Exit criteria:** Decision made on which model goes into production. Decision is data-driven (CSV in hand), not vibes.

**Result (2026-05-22): production model is `sina-medium` (qwen2.5:3b).**

87-case benchmark across literal / colloquial / ambiguous / state-query / off-topic / adversarial inputs. Three prompt iterations:

| Iteration | Change | sina-small | sina-medium |
|---|---|---:|---:|
| 1 | Scope-framed prompt; "AC commands only, anything else → none" | 63% | 77% |
| 2 | Added "relief direction" rule for delta sign (user is cold → warmer) | 82% | 83% |
| 3 | Reordered as 3-step decision tree (query? → command? → none?) | 72% | **83%** |

Final per-category for `sina-medium`: literal 100%, colloquial 90%, state-query 100%, off-topic 100%, ambiguous 60%, adversarial 10%. The 95% target wasn't met overall, but it was met on the four categories that matter for real interaction. The two failing categories are mostly degenerate cases:

- **Adversarial.** Model insists on clamping out-of-range numeric values (`"set temp to 999"` → `temp_c: 30`) despite the prompt forbidding clamping. Helpfulness training overrides system prompt — likely a model-side ceiling, not a prompt-engineering one.
- **Ambiguous.** Phrases like "the usual" / "back to normal" have no defined baseline. Probably belong in `none` but the model guesses.

**Latency** (sina-medium, 87-case run): median 4.9s, p95 27.5s, mean 9.7s. Long tail driven by the retry-on-malformed-JSON path doubling inference cost. Not gated for Phase 1; will revisit in Phase 5 on Pi hardware.

### Phase 2 — Mac voice input

**Goal:** Replace the keyboard with the Mac's microphone.

- Integrate `faster-whisper` with a small English model (`tiny.en` or `base.en`).
- Add a push-to-talk loop (spacebar to record, release to transcribe).
- Pipe Whisper's output text directly into the existing `brain.py` pipeline.
- Measure end-to-end latency: speech-end → tool-call extracted.
- **Exit criteria:** You can speak to the Mac and see correct, validated tool calls appear in the terminal.

### Phase 3 — Hardware reconnaissance (ESP32 + IR receiver)

**Goal:** Capture the exact IR protocol used by the LG AC remote.

- Order ESP32 dev board, VS1838B IR receiver, IR transmitter module, breadboard, jumper wires.
- Install Arduino IDE on the Mac, add ESP32 board support.
- Wire the IR receiver (3 jumper wires — no solder).
- Flash a raw IR decoder sketch using `IRremoteESP8266`.
- Point the physical LG remote at the receiver. Press every button. Capture and log: power on/off, every temperature setting 16°C–30°C, every fan mode, every preset.
- Confirm the LG protocol variant.
- Save the codes as a JSON dictionary keyed by command.
- **Exit criteria:** A complete IR codebook for the LG AC, validated against the receiver.

### Phase 4 — IR transmission (ESP32 as dumb endpoint)

**Goal:** Replicate the remote's behavior over Wi-Fi.

- Reflash the ESP32 with a sketch that:
  - Connects to home Wi-Fi on a static IP.
  - Hosts a tiny async HTTP server.
  - Exposes endpoints like `GET /ac?state=on&temp=22&fan=auto`.
  - On request, fires the matching IR code from the captured codebook.
- Test from the Mac with `curl`. Confirm the AC physically responds.
- Update `brain.py` to send HTTP requests to the ESP32 instead of printing dry-run logs.
- **Exit criteria:** End-to-end speech → AC control working through the Mac + ESP32 stack.

### Phase 5 — Edge migration (Raspberry Pi as full unit)

**Goal:** Replace the Mac + ESP32 split with a single self-contained Pi unit.

- Provision a Raspberry Pi 5 with Raspberry Pi OS Lite (64-bit).
- Install Ollama on the Pi. Re-pull the chosen model.
- Re-run the Phase 1 benchmark on the Pi to verify accuracy and measure new latency.
- Install `faster-whisper` or `whisper.cpp` on the Pi.
- Wire the IR emitter module directly to Pi GPIO (3 jumper wires, no solder).
- Port the IR transmission logic from Arduino C++ to Python using `pigpio` (which supports precise microsecond-level pulse timing required for IR).
- Port `brain.py` to run on the Pi with the same tool schema, but now executing GPIO calls instead of HTTP requests.
- Add `systemd` service for auto-start on boot.
- **Exit criteria:** A single Pi, plugged into the wall with a USB mic attached, controls the AC via voice. No Mac, no ESP32, no network calls.

### Phase 6 — Wake word + always-on listening

**Goal:** Remove push-to-talk; make the unit ambient.

- Integrate `openWakeWord` with a custom-trained "Sina" wake word.
- Tune VAD (voice activity detection) to minimize false positives.
- Add an LED indicator (one more jumper wire) showing listening state.
- **Exit criteria:** Saying "Sina, set the bedroom to 22" anywhere in the room triggers the AC, with no button presses.

### Phase 7 — Multi-room replication

**Goal:** Clone the unit. Drop it in another room.

- Document the full build (firmware + OS image + IR codebook + config).
- Image the SD card from the first working unit.
- Flash the image to a second Pi.
- Update the unit's config with the room name and any room-specific IR variations.
- Verify second unit works standalone.
- **Exit criteria:** Two independent rooms, each with its own self-contained Sina unit.

### Phase 8 (optional, future) — Whole-home commands

**Goal:** Let units talk to each other for cross-room actions.

- Add lightweight LAN discovery (mDNS / Zeroconf).
- Add an inter-unit RPC protocol over local network.
- Add a "broadcast" tool to the SLM schema ("turn off all ACs").
- **Exit criteria:** Saying "Sina, turn everything off" from any room kills every AC in the house.

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SLM produces malformed tool calls | High | Medium | Pydantic validation + retry-once + clean failure |
| Whisper misrecognizes commands | Medium | Medium | Use `base.en` not `tiny`; tune mic gain; design schema to be forgiving |
| Pi 5 thermal throttling under sustained inference | Medium | Medium | Mandatory active cooler; monitor temps; cap context window |
| IR LED range insufficient | Medium | Low | Use pre-built module with driver transistor; physical placement matters more than power |
| LG AC has multiple IR protocol variants | Low | Medium | Phase 3 recon catches this; we record from the actual remote, not from a generic library |
| State drift (manual remote use desyncs system) | N/A | None | Stateless by design — system does not track AC state. Each command carries the full target state in the IR frame. Status queries (e.g. "what temp is it on?") are answered by IR query if Phase 3 finds a two-way code, otherwise the agent returns "unknown" |
| Pi SD card corruption from frequent writes | Medium | Medium | Use A2-rated card; minimize logging to disk; consider NVMe HAT for primary unit |
| Wake word false positives | Medium | Low | Tune sensitivity; require post-wake-word grammar match |
| Power outage kills units | Low | Low | USB PSUs are cheap to back up with a small UPS if it matters |

---

## 9. Security & Privacy Posture

- **No data leaves the LAN.** All inference is local. No cloud APIs, no telemetry, no analytics.
- **No accounts required.** No vendor logins, no OAuth, no tokens to rotate.
- **Microphone always-on (Phase 6).** Wake-word detection runs locally; only audio after the wake word is sent to Whisper. No continuous recording.
- **LAN exposure.** ESP32s in Phase A and inter-unit RPC in Phase 8 are unauthenticated by design (trust the home LAN). If the LAN is hostile, this needs rethinking.
- **Firmware reproducibility.** All firmware and config is version-controlled. SD card images are documented.

---

## 10. Out of Scope

To keep this focused, the following are explicitly **not** part of Project Sina:

- TV / streaming control (separate project, different protocol stack).
- Multi-zone audio.
- Lighting control.
- Anything requiring Wi-Fi-enabled smart appliances.
- Cloud backup, remote access from outside the home, mobile apps.
- Multi-user voice identification.
- Persistent state tracking of appliance state — commands are fire-and-forget; state is queried on-demand or returned as unknown.

These may become follow-on projects, but pollute the scope if mixed in now.

---

## 11. Success Criteria

The project is "done" (Phase 7 complete) when:

1. Two physical rooms each have a working Sina unit.
2. Voice commands work reliably for: turning AC on/off, setting temperature, changing fan mode.
3. The system functions with the home internet disconnected.
4. A third unit can be built and deployed in under 2 hours using documented procedures.
5. The full BOM and build steps live in this repo.

---

## 12. Open Questions

- **Whisper model size on the Pi:** `tiny.en` is fast but error-prone; `base.en` is more accurate but may push latency past 3s. Benchmark in Phase 5.
- **GPIO IR encoding library:** `pigpio` is the standard but the API is finicky. Worth a small spike before committing.
- **Wake word training:** Custom "Sina" wake word requires recording ~100 samples. Plan a focused recording session in Phase 6.
- **Multi-unit sync (Phase 8):** mDNS vs. a tiny MQTT broker on one designated "master" unit. Decide later when we actually need it.
