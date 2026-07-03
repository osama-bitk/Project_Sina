# Project Sina

A local, offline, voice-controlled AI agent for home appliance control. Listens for voice commands, runs a small language model locally, emits IR signals to control AC units. No cloud, no accounts, no telemetry.

See [`project_sina_plan.md`](./project_sina_plan.md) for the full plan, phasing, BOM, risks, and next steps.

## Status

**Phase 3 in progress: IR reconnaissance against the LG remote.**

- Phase 1: `sina-medium` (qwen2.5:3b) picked as production model, 83% on the benchmark (100% literal/state-query/off-topic, 90% colloquial).
- Phase 2: `mac/voice.py` records, transcribes via `faster-whisper`, pipes to `brain.parse`.
- 2026-07-03 hardening: structured outputs (schema-constrained generation), out-of-range clamp guard, `set_preset` tool backed by `mac/config.json`.
- Phase 3: ESP32 decoder sketch + capture procedure ready in [`esp32/README.md`](./esp32/README.md). Awaiting captured codes in `ir_codes/lg_ac.json`.

## Repo layout

| Path | Phase | Purpose |
|---|---|---|
| `project_sina_plan.md` | — | The full project plan. Start here. |
| `CLAUDE.md` | — | Project conventions and design invariants. |
| `mac/` | 1–2 | Mac-hosted brain: Ollama tool-calling, Whisper STT, benchmark harness. |
| `esp32/` | 3–4 | ESP32 firmware: IR recon receiver, IR transmission HTTP server. Has its own README (hands-on wiring + capture procedure). |
| `pi/` | 5+ | Raspberry Pi edge unit — the end-state device. Not started; blocked on Phase 4. |
| `benchmarks/` | 1+ | Tool-calling accuracy test suite + results. |
| `ir_codes/` | 3 | Captured LG AC IR codebook (JSON). Empty until Phase 3 capture. |

## Setup (Mac brain)

```sh
# Base models + Sina variants (system prompt + temperature=0 baked in)
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
ollama create sina-small  -f mac/modelfiles/sina-small.Modelfile
ollama create sina-medium -f mac/modelfiles/sina-medium.Modelfile

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

# Text in, validated tool call out (dry run)
python brain.py --model sina-medium "make it colder"
# -> {"tool": "set_temp", "args": {"delta": -2}}

# Voice: Enter to record, Enter to stop
python voice.py
# File-based smoke test (no mic):
say "make it colder" -o /tmp/sina-test.aiff && python voice.py --audio /tmp/sina-test.aiff

# Benchmark both models over benchmarks/commands.jsonl → CSV + summary
python benchmark.py
```

**8GB Mac note:** Whisper-base.en + sina-medium concurrently forces Ollama to repage (100–200s/call). Use `python voice.py --model sina-small --whisper tiny.en` if RAM-constrained.

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

JSON keyed by command, produced by the Phase 3 capture session (procedure in `esp32/README.md`):

```json
{"power_on": {"protocol": "LG2", "bits": 28, "hex": "0x88C0051"}}
```

LG remotes send the entire desired state in each frame — that's what makes the stateless design viable.
