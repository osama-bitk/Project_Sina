# Project Sina

A local, offline, voice-controlled AI agent for home appliance control. Listens for voice commands, runs a small language model locally, emits IR signals to control AC units. No cloud, no accounts, no telemetry.

See [`project_sina_plan.md`](./project_sina_plan.md) for the full plan, phasing, BOM, and risks.

## Status

**Phase 3 in progress: IR reconnaissance against the LG remote.**

- Phase 1: `sina-medium` (qwen2.5:3b) picked as production model, 83% on 87-case benchmark.
- Phase 2: `mac/voice.py` records, transcribes via `faster-whisper`, pipes to `brain.parse`. Interactive Enter-to-record loop plus `--audio FILE` for testing.
- Phase 3: ESP32 decoder sketch + capture procedure ready in `esp32/`. Awaiting captured codes in `ir_codes/lg_ac.json`.

See [`esp32/README.md`](./esp32/README.md) for the Phase 3 setup and capture procedure, [`mac/README.md`](./mac/README.md) for the brain, and [`project_sina_plan.md`](./project_sina_plan.md) for the full plan.

## Repo layout

| Path | Phase | Purpose |
|---|---|---|
| `project_sina_plan.md` | — | The full project plan. Start here. |
| `mac/` | 1–2 | Mac-hosted brain: Ollama tool-calling, Whisper STT, benchmark harness. |
| `esp32/` | 3–4 | ESP32 firmware: IR recon receiver, IR transmission HTTP server. |
| `pi/` | 5+ | Raspberry Pi edge unit — the end-state device. |
| `benchmarks/` | 1 | Tool-calling accuracy test suite. Phase 1 exit criteria depend on this. |
| `ir_codes/` | 3 | Captured LG AC IR codebook (JSON). |
