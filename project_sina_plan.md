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

- **Tool-calling accuracy ≥ 95%** on the four categories that matter for real interaction (literal, colloquial, state-query, off-topic). Ambiguous and adversarial inputs must **fail safe** — resolve to `none` rather than fire a wrong IR command; they are not held to the 95% bar. (Revised 2026-07-03: the original blanket 95% target penalized categories whose correct behavior is refusal.)
- **End-to-end latency ≤ 2 seconds** from end-of-speech to IR emission for the Mac-hosted phase. ≤ 3 seconds for the Pi-hosted edge phase.
- **CPU thermal headroom.** No sustained 100% CPU. Model size and context window tuned to keep the host stable.
- **Zero internet calls at runtime.** Verified by running the system with Wi-Fi disabled (after initial setup downloads).
- **Graceful failure.** Malformed model output, hardware timeouts, or ambiguous commands all surface as clean error states, not silent failures.

---

## 4. System Architecture

**Revised 2026-07-04.** The original plan had two phases: Mac-hosted development, then a fully self-contained Pi per room. The end state is now **one central Pi brain + cheap per-room satellite nodes** — the per-room-Pi model didn't survive the cost math ($150/room vs ~$15–20/room for a node).

### Phase A — Centralized development (Mac-hosted)

```
[Mic] → [Whisper on Mac] → [Ollama+SLM on Mac] → [Python brain.py] → [Wi-Fi HTTP] → [ESP32 + IR LED] → [AC]
```

- The Mac stands in for the eventual Pi brain. ESP32s are dumb HTTP endpoints that fire IR codes on request.
- This phase exists to validate the software stack before committing to edge hardware.

### Phase B — Central brain + satellite nodes (the end goal)

```
Per room:
  [Mic] → [ESP32-S3 node: on-device wake word] → streams post-wake audio over LAN
       → [Pi 5: Whisper → SLM → validation gate] → command back over LAN
       → [ESP32-S3 fires IR] → [AC]
```

- **One Raspberry Pi 5 (8GB) is the brain** for the whole house: Whisper (STT), the SLM, the deterministic validation gate, and the node command router. Both models stay resident (load-on-demand costs 1–3s per cold command; only add eviction if memory pressure is measured).
- **Each room gets an ESP32-S3 node** (~$15–20): I2S mic, on-device wake word, IR emitter. No inference on the node. The Phase 3 recon board becomes room node #1 — no throwaway hardware.
- **Privacy invariant: only post-wake-word audio ever leaves the room.** Nodes never stream continuously.
- **Node ↔ Pi protocol:** don't invent one. The ESPHome voice-satellite firmware / Wyoming protocol (Rhasspy ecosystem) solve exactly this shape (S3 + INMP441 streaming post-wake audio to a Linux brain), offline-friendly. Even with custom firmware, adopt the Wyoming protocol. Discovery: static IPs + a config map first, mDNS later. Each node's config carries its room identity so commands route to the right AC.
- **Accepted tradeoffs:** Pi or Wi-Fi down = whole house down; simultaneous commands from different rooms queue (~5s each). Both acceptable at household scale. Nodes stay dumb and stateless, so a "promote a node to standalone unit" path remains open if the single point of failure ever bites.

---

## 5. Technology Stack

| Layer | Phase A (Mac) | Phase B (Edge) | Notes |
|---|---|---|---|
| Inference runtime | Ollama (native macOS) | Ollama or llama.cpp | llama.cpp may be preferred on Pi for raw speed |
| SLM | Qwen 2.5 (1.5B vs 3B, benchmarked) | Same model chosen in Phase A | Re-benchmark on Pi — performance characteristics differ |
| Speech-to-text | `faster-whisper` or `whisper.cpp` (tiny/base) | `whisper.cpp` (tiny) | Pi requires the smallest viable model |
| Wake word | Manual trigger (push-to-talk) initially | ESP-SR/WakeNet **on the node** | Custom "Sina" word needs Espressif's training pipeline — real risk, spike early (Phase 4.5). Avoid Picovoice (cloud licensing) |
| Agent middleware | Python 3.11+ (`ollama`, `pydantic`, `requests`, `pyaudio`) | Same | Pydantic non-negotiable for tool-call validation |
| Microcontroller | ESP32-S3 N16R8 dev board (no soldering — pre-pinned) | Same board = the room node | 8MB PSRAM (R8) required for on-device wake word; recon board becomes node #1 |
| Node mic | — | INMP441 I2S MEMS (~$3) | Jumper-wired to the S3 |
| Node firmware | Arduino sketch (dumb HTTP endpoint) | ESPHome voice satellite or custom + Wyoming protocol | Don't invent an audio protocol |
| IR receiver (recon) | VS1838B module | — | Used once to capture LG codes |
| IR emitter | IR transmitter module with built-in driver transistor | Same module, wired to Pi GPIO | Pre-built module to avoid soldering a driver circuit |
| IR library | `IRremoteESP8266` (works on ESP32) | `pigpio` + custom IR encoder, or `lirc` | Pi side requires more legwork than ESP32 |
| Edge host | — | **One** Raspberry Pi 5, 8GB, active cooling — per home, not per room | Pi 4 not recommended; Pi 5 NEON SIMD is the unlock |
| OS (Pi) | — | Raspberry Pi OS Lite (64-bit) | Headless, minimal footprint |
| Power | Standard USB-C charger | USB-C PD charger for Pi | Pi 5 needs the official 27W PSU for stability under load |

---

## 6. Bill of Materials (Phase B — revised 2026-07-04)

**Central brain (one per home):**

| Item | Approx. cost (USD) | Notes |
|---|---|---|
| Raspberry Pi 5 (8GB) | $80 | The minimum viable spec; 4GB is not enough |
| Official Pi 5 PSU (27W USB-C) | $12 | Don't skimp — voltage drops cause SLM crashes |
| MicroSD 64GB (A2 rated) | $12 | Or NVMe HAT for longevity |
| Active cooler for Pi 5 | $10 | Mandatory under sustained inference load |
| Pi case with cooler cutout | $10 | Cosmetic but useful |
| **Brain total** | **~$125** | Once, not per room |

**Per-room node:**

| Item | Approx. cost (USD) | Notes |
|---|---|---|
| ESP32-S3 **N16R8** dev board | $10 | 8MB PSRAM required for on-device wake word. **Check antenna variant before buying** (see §12) |
| INMP441 I2S MEMS mic | $3 | Jumper-wired, no solder |
| IR transmitter module (with driver transistor) | $3 | Not a bare KY-005 — driver matters for range |
| **Per-node total** | **~$16** | Vs. ~$150/room in the old per-room-Pi model |

**One-time prototyping:** VS1838B IR receiver ($1, recon only — not in the final node), breadboard + jumper wires (~$6), USB-C **data** cable ($3). See `hardware.md` for the shopping list.

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

- **Adversarial.** Model insists on clamping out-of-range numeric values (`"set temp to 999"` → `temp_c: 30`) despite the prompt forbidding clamping. Helpfulness training overrides system prompt — likely a model-side ceiling, not a prompt-engineering one. **Mitigated in code (2026-07-03):** `brain.py` now post-checks boundary `temp_c` values against the numbers in the utterance and downgrades clamped calls to `none`.
- **Ambiguous.** Phrases like "the usual" / "back to normal" have no defined baseline. **Resolved (2026-07-03):** added a `set_preset` tool backed by a per-room `default_preset` in `mac/config.json` — these phrases now map to a real, useful command. This is config, not tracked state, so the stateless design holds.

**Also changed 2026-07-03:** `brain.py` now passes the full Pydantic JSON schema as Ollama's `format` (structured outputs) instead of `format="json"`, constraining generation to the schema. This should eliminate most malformed-output retries — the driver of the p95 latency tail (27.5s). Re-benchmark before Phase 5.

**Latency** (sina-medium, 87-case run): median 4.9s, p95 27.5s, mean 9.7s. Long tail driven by the retry-on-malformed-JSON path doubling inference cost. Not gated for Phase 1; will revisit in Phase 5 on Pi hardware.

### Phase 2 — Mac voice input

**Goal:** Replace the keyboard with the Mac's microphone.

- Integrate `faster-whisper` with a small English model (`tiny.en` or `base.en`).
- Add a push-to-talk loop (spacebar to record, release to transcribe).
- Pipe Whisper's output text directly into the existing `brain.py` pipeline.
- Measure end-to-end latency: speech-end → tool-call extracted.
- **Exit criteria:** You can speak to the Mac and see correct, validated tool calls appear in the terminal.

**Result (2026-05-23): Phase 2 exit criteria met.** `mac/voice.py` records via PyAudio, transcribes with `faster-whisper` (base.en default), pipes the text into `brain.parse`. Two modes: interactive Enter-to-record/Enter-to-stop, and `--audio FILE` one-shot for file-based testing. End-to-end verified with `say "make it colder"` → `/tmp/sina-test.aiff` → `voice.py --audio` returning `{"tool":"set_temp","args":{"delta":-2}}`. Implementation note: chose Enter-toggle over spacebar push-to-talk to avoid pynput's macOS Accessibility-permission requirement; functionally equivalent for a CLI tool.

Caveat: on a Mac Air with 8GB RAM, running Whisper-base.en and `sina-medium` concurrently produced 100–200s LLM latency per call (vs. ~5s headless benchmark). Ollama is repaging the model under memory pressure. Workaround: `--model sina-small --whisper tiny.en`. The dedicated Pi unit in Phase 5 won't share this constraint, though latency on Pi 5 will be its own story.

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
  - Requires a shared static token (`X-Sina-Token` header) on every request. ~5 lines of firmware; stops a misbehaving IoT device or guest on the LAN from cycling the AC. Token lives in config, not in the repo.
  - On request, fires the matching IR code from the captured codebook.
- Test from the Mac with `curl`. Confirm the AC physically responds.
- Update `brain.py` to send HTTP requests to the ESP32 instead of printing dry-run logs.
- **Exit criteria:** End-to-end speech → AC control working through the Mac + ESP32 stack.

### Phase 4.5 — Wake-word spike (de-risk before buying more nodes)

**Goal:** Prove (or disprove) on-device wake word on the ESP32-S3 before committing to five of them.

- Flash the ESPHome voice-satellite firmware (or a minimal ESP-SR sketch) on the recon S3 + INMP441.
- Test a stock WakeNet wake word first; then assess the path to a custom "Sina" word (Espressif's training pipeline — known to be non-trivial).
- **Decision point:** custom "Sina" / acceptable stock word / fallback. The fallback (continuous audio streaming to the Pi) breaks both the centralization economics and the post-wake-only privacy invariant — treat it as last resort.
- **Exit criteria:** A wake word demonstrably runs on the node, and the wake-word choice is made.

### Phase 5 — Central Pi brain

**Goal:** Replace the Mac with the one-per-home Pi 5 brain.

- Provision a Raspberry Pi 5 (8GB) with Raspberry Pi OS Lite (64-bit).
- **Default to `llama.cpp` with a Q4 quant of the chosen model** (not Ollama) — expect ~5–8 tok/s for qwen2.5:3b on Pi 5; a short tool-call output lands in ~2–4s, but there's no headroom for repaging. If Ollama is used, set `OLLAMA_KEEP_ALIVE=-1` so the model stays resident — the Mac Air memory-pressure incident (100–200s latencies) is the failure mode to avoid.
- Install `whisper.cpp` with `tiny.en` (upgrade to `base.en` only if accuracy demands it and latency allows). Keep **both** models resident — load-on-demand costs 1–3s per cold command.
- Run `free -h` with the SLM and Whisper both loaded — the one measurement that decides usability. If it thrashes: shrink the Whisper model first, then consider eviction.
- Re-run the Phase 1 benchmark on the Pi for real accuracy/latency numbers.
- Port `brain.py` + validation gate; commands go out over LAN to the node (same HTTP+token contract as Phase 4).
- Add `systemd` service for auto-start on boot.
- **Exit criteria:** Pi is the brain — voice command via the node's audio path (or Mac mic as interim), AC responds, no Mac in the loop.

### Phase 6 — Node firmware: ambient listening

**Goal:** Remove push-to-talk; the room node becomes the ears.

- Wake word runs **on the node** (per the Phase 4.5 decision); node streams only post-wake command audio to the Pi (Wyoming protocol / ESPHome satellite).
- Node receives the resulting command back and fires IR.
- Tune VAD to minimize false positives; add an LED indicator showing listening state.
- **Exit criteria:** Saying "Sina, set the bedroom to 22" anywhere in the room triggers the AC — no button, no Mac.

### Phase 6.5 — Voice feedback (TTS)

**Goal:** Close the interaction loop — the system confirms what it did.

- Integrate [Piper](https://github.com/rhasspy/piper) on the Pi (fully offline TTS, runs comfortably on Pi 5).
- Speak short confirmations: "set to 22", "AC off", "sorry, I didn't get that".
- `get_state` responses become spoken ("I don't know the current state" until/unless two-way IR exists).
- Open question: audio out on the node needs a small I2S speaker/amp (~$3, e.g. MAX98357A) — decide whether feedback is worth the extra part per room.
- **Exit criteria:** Every accepted command gets a spoken confirmation; every rejection a spoken error, all offline.

### Phase 7 — Multi-room replication

**Goal:** Clone the node. Drop it in another room.

- Document the full node build (firmware + wiring + config).
- Flash a second ESP32-S3 node; set its room identity in config; register it with the Pi (config map).
- Verify both rooms work independently against the one Pi.
- **Exit criteria:** Two rooms live off one brain; adding a third is a documented ~$16 clone.

### Phase 8 (optional, future) — Whole-home commands & the No-Internet-Home platform

**Goal:** Let units talk to each other for cross-room actions, and lay the LAN foundation that future offline-home projects (lighting, TV, sensors) plug into instead of reinventing.

**8a — Whole-home AC commands (the original scope):**

- With the central-brain architecture this is nearly free: the Pi already knows every node, so "turn off all ACs" is a fan-out from the Pi to each registered node.
- Add a `broadcast` tool (or room scope `all`) to the SLM schema.
- Optional: move node registration from the static config map to mDNS/Zeroconf (`_sina._tcp.local`) so new nodes self-announce.
- **Exit criteria:** Saying "Sina, turn everything off" from any room kills every AC in the house.

**8b — Scalability groundwork (design now, build later):**

- **Capability manifest.** Each unit's mDNS advertisement lists what it can do (`ac.set_temp`, `ac.set_power`, …). A future lighting or TV node advertises its own verbs. The voice unit's tool schema is generated from discovered capabilities, not hardcoded.
- **One wire protocol.** All device nodes speak the same authenticated HTTP+JSON command shape as the Phase 4 ESP32. New appliance = new node implementing the same contract; the brain doesn't change.
- **Room addressing.** Commands carry a room scope (`bedroom`, `all`), resolved against the mDNS registry — this is what makes "turn off the living room AC" from the bedroom possible.
- Follow-on projects (explicitly out of scope for Sina, but designed-for): IR lighting/TV nodes, 433MHz RF sockets, local sensor nodes (temp/humidity feeding smarter presets).

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
| Pi SD card corruption from frequent writes | Medium | Medium | Use A2-rated card; minimize logging to disk; consider NVMe HAT for the brain |
| Custom "Sina" wake word infeasible on ESP32-S3 | Medium | High | ESP-SR custom words need Espressif's training pipeline. Phase 4.5 spike decides: custom / stock word / rethink — **before** buying multiple nodes |
| Central Pi or Wi-Fi down = whole house down | Low | Medium | Accepted tradeoff of centralizing. Nodes are dumb+stateless, so a promote-to-standalone path stays open |
| Wake word false positives | Medium | Low | Tune sensitivity; require post-wake-word grammar match |
| Power outage kills units | Low | Low | USB PSUs are cheap to back up with a small UPS if it matters |

---

## 9. Security & Privacy Posture

- **No data leaves the LAN.** All inference is local. No cloud APIs, no telemetry, no analytics.
- **No accounts required.** No vendor logins, no OAuth, no tokens to rotate.
- **Microphone always-on (Phase 6).** Wake-word detection runs **on the node**; only post-wake-word audio ever leaves the room (over the LAN to the Pi). No continuous recording or streaming — this is an invariant, not an optimization.
- **LAN exposure.** Node endpoints and node↔Pi traffic are protected by a shared static token (Phase 4); beyond that the home LAN is trusted. If the LAN is hostile, this needs rethinking.
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
- **ESP32-S3 antenna variant (blocks the hardware order):** N16R8 boards ship with either a printed PCB antenna (squiggle trace — good) or a u.FL connector needing a separate external antenna. Confirm from the listing photo before buying.
- **Custom "Sina" wake word on the S3:** Espressif's ESP-SR training pipeline, stock word, or fallback. Phase 4.5 spike decides.
- **Node audio-out for TTS feedback:** needs an I2S amp/speaker (~$3/room). Decide at Phase 6.5.
- ~~Multi-unit sync (Phase 8): mDNS vs. MQTT broker on a master unit.~~ **Decided 2026-07-03: mDNS + peer-to-peer HTTP.** A broker creates a master unit, which violates the no-cross-room-dependency principle. See Phase 8.
- **`get_state`:** LG ACs almost universally have no two-way IR. Working assumption: `get_state` returns "unknown" permanently (Phase 6.5 speaks it). Keep the tool — it correctly absorbs state questions that would otherwise misroute — but don't build anything expecting real state.

---

## 13. Next Steps (as of 2026-07-04)

1. **Order the Phase 3–4 hardware** (see `hardware.md`): one ESP32-S3 N16R8 (check antenna variant), VS1838B, IR transmitter module, INMP441, breadboard/jumpers/data cable. The recon board becomes room node #1.
2. **Phase 3 capture session** when parts arrive: wire the VS1838B, flash `esp32/ir_decoder/`, capture the LG remote into `ir_codes/lg_ac.json`. Critical path.
3. **Phase 4:** node IR server sketch with token auth; point `brain.py` at it.
4. **Phase 4.5 wake-word spike** before buying more nodes.
5. Re-run the benchmark as a regression gate after **every** prompt or model change — it's a one-liner (`python benchmark.py`), treat it like a test suite. (2026-07-03 changes — structured outputs, clamp guard, `set_preset` — benchmarked 2026-07-04.)
