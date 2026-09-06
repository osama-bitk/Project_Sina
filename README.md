# Project Sina

A local, offline, voice-controlled AI agent for home appliance control. Listens for voice commands, runs a small language model locally, emits IR signals to control AC units. No cloud, no accounts, no telemetry.

End-state architecture (revised 2026-07-04): **one central Raspberry Pi 5 brain** (Whisper + SLM + validation) and a **~$16 ESP32-S3 node per room** (mic, on-device wake word, IR emitter). Only post-wake-word audio ever leaves a room.

See [`project_sina_plan.md`](./project_sina_plan.md) for the full plan, phasing, BOM, risks, and next steps; [`hardware.md`](./hardware.md) for the shopping list.

## Status

**Phase 4 in progress (2026-09-07): the AC responds to frames we build. Range is the open problem.**

- Phase 1: benchmark harness + prompt built on qwen2.5. **Re-evaluated 2026-07-04: production model is `sina-medium-v2` (qwen3:4b)** — 93% overall, ≥96% on all four core categories, the first model to meet the plan §3 objective. `sina-small-v2` (qwen3:1.7b, 81%, ~3.4s/call) is the Mac interactive default; the 4B is the Pi-brain target.
- Phase 2: `mac/voice.py` records, transcribes via `faster-whisper`, pipes to `brain.parse`.
- 2026-07-03 hardening: structured outputs (schema-constrained generation), out-of-range clamp guard, `set_preset` tool backed by `mac/config.json`, `think=False` for qwen3 (hidden reasoning tokens otherwise cost ~60s/call).
- **Phase 3: LG remote captured and the frame encoding solved** — see [IR codebook](#ir-codebook-ir_codes) below. `mac/lg_ir.py` builds any frame from a target state; its self-test reproduces all 23 captured frames.
- **Phase 4 in progress: the AC physically obeys frames we construct.** `esp32/ir_bridge/` takes a finished frame over serial and transmits it; `mac/ir_send.py` drives it from the Mac. Confirmed on real hardware: `power_off` shuts the unit down. The node holds no codebook — the brain builds the frame (invariant 4), so the eventual switch from serial to HTTP changes neither side's job.
- **Open: IR range.** Reliable at ~20cm, unreliable at 1m — an underdriven LED, not a protocol fault. Blocks room deployment, not the protocol work. See `esp32/README.md`.

## Repo layout

| Path | Phase | Purpose |
|---|---|---|
| `project_sina_plan.md` | — | The full project plan. Start here. |
| `CLAUDE.md` | — | Project conventions and design invariants. |
| `mac/` | 1–4 | Mac-hosted brain: Ollama tool-calling, Whisper STT, benchmark harness, LG IR frame encoder (`lg_ir.py`) and capture decoder (`decode_capture.py`). |
| `esp32/` | 3–4 | ESP32 firmware: IR recon receiver, serial IR bridge, diagnostics. Has its own README (wiring, capture procedure, emitter debugging). |
| `pi/` | 5+ | Raspberry Pi edge unit — the end-state device. Not started; blocked on Phase 4. |
| `benchmarks/` | 1+ | Tool-calling accuracy test suite + results. |
| `ir_codes/` | 3 | LG AC frame encoding + verified samples (`lg_ac.json`), raw serial captures (`raw/`). |

## Setup (Mac brain)

```sh
# Base models + Sina variants (system prompt + temperature=0 baked in)
ollama pull qwen3:1.7b
ollama pull qwen3:4b
ollama create sina-small-v2  -f mac/modelfiles/sina-small-v2.Modelfile
ollama create sina-medium-v2 -f mac/modelfiles/sina-medium-v2.Modelfile

# Python env
cd mac
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Voice (Phase 2) additionally needs:
brew install portaudio
pip install -r requirements-voice.txt
```

## Usage

```sh
cd mac

# Text in, validated tool call out (dry run; default model sina-small-v2)
python brain.py "make it colder"
# -> {"tool": "set_temp", "args": {"delta": -2}}

# Voice: Enter to record, Enter to stop
python voice.py
# File-based smoke test (no mic):
say "make it colder" -o /tmp/sina-test.aiff && python voice.py --audio /tmp/sina-test.aiff

# Benchmark both models over benchmarks/commands.jsonl → CSV + summary
python benchmark.py
```

**8GB Mac note:** this Intel Air runs all inference on CPU; the 4B production model is ~12s/call here, so interactive/voice use defaults to `sina-small-v2`. Whisper + LLM concurrently is RAM-tight — use `--whisper tiny.en` if latency balloons.

## Tool schema

| Tool | Args |
|---|---|
| `set_power` | `{"on": bool}` |
| `set_temp` | `{"temp_c": 16..30}` **or** `{"delta": -10..10}` (exactly one) |
| `set_fan` | `{"speed": "auto"\|"low"\|"med"\|"high"}` |
| `set_mode` | `{"mode": "cool"\|"heat"\|"dry"\|"fan"}` |
| `set_preset` | `{}` — "the usual" / "back to normal"; expands downstream from `mac/config.json` `default_preset` |
| `get_state` | `{}` — returns "unknown" unless Phase 3 finds two-way IR (unlikely) |
| `none` | `{}` — off-topic, ambiguous, out-of-range, or injection |

Validation lives in `mac/brain.py`: a Pydantic discriminated union (`extra="forbid"`), generation constrained to the JSON schema via Ollama structured outputs, one corrective retry, then failure. A post-parse guard downgrades model-clamped out-of-range temps (e.g. "set to 999" → 30) to `none`.

## Benchmark

`benchmarks/commands.jsonl` — one case per line: `{"input", "category", "expected", "notes"}`, where `expected` is the tool call or `null` (must resolve to `none`). Categories: `literal`, `colloquial`, `ambiguous`, `state-query`, `off-topic`, `adversarial`. 88 cases currently.

`mac/benchmark.py` runs every case against both models, writes a timestamped CSV to `benchmarks/results/` (gitignored), and prints per-category accuracy. **Run it after every prompt or model change** — it's the regression suite.

Accuracy target (plan §3): ≥95% on literal/colloquial/state-query/off-topic; ambiguous and adversarial must fail *safe* (→ `none`), not fail wrong.

## IR codebook (`ir_codes/`)

LG sends the entire desired state in every frame — that's what makes the stateless design viable. So the codebook is **not** a button lookup table: Phase 3 solved the encoding, and `mac/lg_ir.py` constructs whatever frame is needed.

Protocol **LG2**, 28 bits, 38 kHz:

```
0x88 <n3> <mode> <temp> <fan> <checksum>
  n3    0 = state frame, 1 = jet, C = special command
  temp  temp_c - 15        (16C -> 0x1 ... 30C -> 0xF)
  mode  cool 0x8, dry 0x9, fan 0xA, auto 0xB
  fan   low 0x0, med 0x2, high 0x4, auto 0x5
  csum  sum of the six preceding nibbles & 0xF
```

```sh
python mac/lg_ir.py --temp 22 --mode cool --fan auto   # -> 0x8808754
python mac/lg_ir.py --off                              # -> 0x88C0051
python mac/lg_ir.py --selftest                         # regenerate all 23 captured frames

# Actually fire it at the AC through the ESP32 bridge (Phase 4)
python mac/ir_send.py --temp 22 --mode cool --fan auto
python mac/ir_send.py --off
python mac/ir_send.py --off --repeat 2 --count 10      # resend while aiming
```

Discrete commands: `power_off` `0x88C0051`, `jet` ("Po") `0x8810089`, `light_toggle` `0x88C00A6`.

**There is no power-on frame.** The remote remembers the last state and resends it as a full frame, so "on" is just a state frame. Sina can't reproduce "last state" — tracking it is the synthetic state mirror invariant 2 forbids — so `set_power: on` fires the `default_preset` from `mac/config.json` (config, not state). Unverified: `0x8800606` from the power button doesn't parse as a state frame (mode nibble `0x0` is outside the valid `0x8`–`0xB`), so it's another command class; Phase 4 confirms.

`ir_codes/lg_ac.json` holds the field encodings plus every verified sample; `ir_codes/raw/` keeps the original serial captures as primary evidence. `mac/decode_capture.py` decodes raw timing dumps and checks the LG checksum — needed because `IRremoteESP8266` mislabels some clean frames as `UNKNOWN`.

**Two constraints this unit imposes:**

- **No heat mode** (cycle is cool → auto → dry → fan), so `set_mode: heat` has no frame to fire. Unresolved — see plan §7 Phase 4.
- **Light is a blind toggle**: one code, no on/off pair, no way to read state. Exposed as `toggle_light`, never `set_light(on=bool)` — the name has to admit the result is unknowable (invariant 3).
