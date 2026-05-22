# Mac brain (Phase 1–2)

The Mac-hosted brain. Runs Ollama locally, validates SLM tool calls with Pydantic, sends commands downstream (Phase 1 dry-run; Phase 4 swaps in HTTP to ESP32).

## Setup

Ollama is already installed locally. Remaining setup:

```sh
# Pull the two base models we'll head-to-head
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b

# Build the Sina variants (system prompt + temperature=0 baked in)
ollama create sina-small  -f modelfiles/sina-small.Modelfile
ollama create sina-medium -f modelfiles/sina-medium.Modelfile

# Python env (Phase 1 deps: ollama + pydantic)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Phase 2 voice deps later — needs `brew install portaudio` first:
# pip install -r requirements-voice.txt
```

If your shell mangles multi-line pastes, run each command on its own line.

## Usage

```sh
# One-shot dry run
python brain.py --model sina-small "make it colder"
# -> {"tool": "set_temp", "args": {"delta": -2}}

python brain.py --model sina-medium "turn the AC off"
# -> {"tool": "set_power", "args": {"on": false}}

# Stdin works too
echo "what temp is it on" | python brain.py

# Full benchmark over ../benchmarks/commands.jsonl
python benchmark.py
# -> writes ../benchmarks/results/results-<timestamp>.csv + prints summary
```

## Files

- `brain.py` — CLI agent: text in → validated tool call out. Pydantic discriminated union over the 6 tools; one corrective retry on malformed JSON before failing.
- `benchmark.py` — runs both models against `../benchmarks/commands.jsonl`, writes timestamped CSV under `../benchmarks/results/`, prints per-category accuracy.
- `modelfiles/sina-small.Modelfile`, `modelfiles/sina-medium.Modelfile` — Ollama config. Single source of truth for the system prompt (don't duplicate it in Python).
- `requirements.txt` — Phase 1 essentials (`ollama`, `pydantic`).
- `requirements-voice.txt` — Phase 2 voice deps (`faster-whisper`, `pyaudio`). Install only when starting Phase 2.

## Tool schema

| Tool | Args |
|---|---|
| `set_power` | `{"on": bool}` |
| `set_temp` | `{"temp_c": 16..30}` **or** `{"delta": -10..10}` (exactly one) |
| `set_fan` | `{"speed": "auto"\|"low"\|"med"\|"high"}` |
| `set_mode` | `{"mode": "cool"\|"heat"\|"dry"\|"fan"}` |
| `get_state` | `{}` |
| `none` | `{}` — off-topic, ambiguous, out-of-range, or injection |

## Phase 1 result

**Production model: `sina-medium` (qwen2.5:3b).** 83% on the 87-case benchmark. Three prompt iterations; final prompt is a 3-step decision tree (state question? → command? → out of scope?). Wins per-category on literal (100%), state-query (100%), off-topic (100%), ties on colloquial (90%). Loses on adversarial (10% — model clamps out-of-range numbers despite explicit "none, do not clamp" instruction; effectively safe but not as specified).

Median latency 4.9s on this Mac (mean 9.7s; long tail from retry-on-malformed inference). Latency not gated for Phase 1.

See `project_sina_plan.md` §7 Phase 1 for the iteration log and decision rationale.
