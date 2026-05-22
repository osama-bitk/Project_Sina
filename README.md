# Project Sina

A local, offline, voice-controlled AI agent for home appliance control. Listens for voice commands, runs a small language model locally, emits IR signals to control AC units. No cloud, no accounts, no telemetry.

See [`project_sina_plan.md`](./project_sina_plan.md) for the full plan, phasing, BOM, and risks.

## Status

**Pre-Phase 1.** Scaffolding only — no software written yet. Plan is set; next step is the Mac-hosted brain (`mac/`).

## Repo layout

| Path | Phase | Purpose |
|---|---|---|
| `project_sina_plan.md` | — | The full project plan. Start here. |
| `mac/` | 1–2 | Mac-hosted brain: Ollama tool-calling, Whisper STT, benchmark harness. |
| `esp32/` | 3–4 | ESP32 firmware: IR recon receiver, IR transmission HTTP server. |
| `pi/` | 5+ | Raspberry Pi edge unit — the end-state device. |
| `benchmarks/` | 1 | Tool-calling accuracy test suite. Phase 1 exit criteria depend on this. |
| `ir_codes/` | 3 | Captured LG AC IR codebook (JSON). |
