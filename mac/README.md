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

# Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

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

## Tool schema

| Tool | Args |
|---|---|
| `set_power` | `{"on": bool}` |
| `set_temp` | `{"temp_c": 16..30}` **or** `{"delta": -10..10}` (exactly one) |
| `set_fan` | `{"speed": "auto"\|"low"\|"med"\|"high"}` |
| `set_mode` | `{"mode": "cool"\|"heat"\|"dry"\|"fan"}` |
| `get_state` | `{}` |
| `none` | `{}` — off-topic, ambiguous, out-of-range, or injection |

## Phase 1 exit criteria

Production model decision is data-driven from `benchmark.py` output. Latency is captured but not gated.
