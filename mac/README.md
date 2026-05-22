# Mac brain (Phase 1–2)

The Mac-hosted brain. Runs Ollama + Whisper locally, validates SLM tool calls with Pydantic, sends commands downstream (initially dry-run; later HTTP to ESP32 in Phase 4).

## Setup

Ollama is already installed locally. Remaining setup:

```sh
ollama serve &
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Files (to be created)

- `brain.py` — CLI agent: text in, validated tool call out. Phase 1 dry-run; Phase 4 fires HTTP to ESP32.
- `benchmark.py` — Runs `../benchmarks/commands.jsonl` against both models, outputs CSV with accuracy + latency per category.
- `modelfiles/sina-small.Modelfile`, `modelfiles/sina-medium.Modelfile` — Ollama system prompts, low temperature, strict tool schema.
- `voice.py` — Phase 2. Push-to-talk loop wrapping `faster-whisper`, pipes transcript into `brain.py`.

## Phase 1 exit criteria

Production model decision is data-driven from `benchmark.py` output. See `../benchmarks/README.md` for the test set spec — the 95% accuracy target is meaningless without it. Latency is captured but not gated.

## Phase 2 exit criteria

Spoken command produces a correct, validated tool call. Latency measured but not a priority right now.
