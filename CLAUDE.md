# CLAUDE.md — Project Sina

Local, offline, voice-controlled AC agent. Mac-hosted brain now (Phase A); end state (Phase B, revised 2026-07-04) is **one central Raspberry Pi 5 brain + cheap ESP32-S3 satellite nodes per room** (mic + on-device wake word + IR emitter, ~$16/room). Read `project_sina_plan.md` before making design decisions; `README.md` for setup/usage.

## Design invariants — do not violate

1. **Offline-only at runtime.** Zero internet calls after initial setup downloads. No cloud APIs, no telemetry, no vendor accounts. Anything requiring the internet at runtime is wrong by definition.
2. **Stateless command model.** The system never tracks AC state. Every command carries its full target state in the IR frame (how LG remotes work anyway). `get_state` returns "unknown" — keep it that way rather than building a synthetic state mirror. Per-room `default_preset` in `mac/config.json` is *config*, not state.
3. **Fail safe, not fail helpful.** Ambiguous / out-of-range / adversarial input resolves to `tool: none`, never to a guessed or clamped command. Firing a wrong IR command is worse than doing nothing.
4. **Nodes are dumb and stateless.** All inference lives on the one Pi brain; nodes do wake word, audio capture, and IR only. No per-node smarts, no state, so any node can be reflashed/cloned trivially (and promoted to standalone later if ever needed).
5. **Only post-wake-word audio leaves the room.** Nodes never stream continuously to the Pi. This is a privacy invariant, not an optimization — the fallback of Pi-side wake word on a continuous stream is a last resort.
6. **No-solder hardware.** Pre-pinned dev boards, breakout modules, jumper wires only.

## Conventions

- Production model: `sina-medium-v2` (qwen3:4b, Pi-brain target); Mac interactive default: `sina-small-v2` (qwen3:1.7b). The qwen2.5-based `sina-small`/`sina-medium` are superseded (kept for comparison).
- The system prompt lives **only** in `mac/modelfiles/*.Modelfile` — never duplicate it in Python. After editing a Modelfile, rebuild: `ollama create sina-medium-v2 -f mac/modelfiles/sina-medium-v2.Modelfile`.
- Thinking models (qwen3+) must run with thinking disabled or every call burns ~700 hidden reasoning tokens (~60s on CPU): `brain.py` passes `think=False` (with cached fallback for models that reject it) and the v2 Modelfiles end the system prompt with `/no_think`.
- Grammar-constrained decoding (structured outputs) can override prompt-driven refusal — a weak model gets forced into a plausible-but-wrong tool call instead of `none`. If refusal categories regress after a decoding change, suspect the model, not the prompt (see plan §7, 2026-07-04 re-evaluation).
- Tool schema is defined once, in `mac/brain.py` (Pydantic discriminated union, `extra="forbid"`). Ollama generation is constrained to this schema via structured outputs. New tools: add the Pydantic model + union member, the Modelfile prompt rule, and benchmark cases — all three.
- `mac/benchmark.py` is the regression suite. Run it after every prompt, schema, or model change. Results CSVs go to `benchmarks/results/` (gitignored).
- Benchmark cases live in `benchmarks/commands.jsonl`; `expected: null` means the case must resolve to `none`.
- Branch-per-phase workflow (`phase-N`), merged to `main` via PR.
- Python 3.9-compatible on the Mac venv today (plan says 3.11+; don't use 3.10+ syntax until the venv is upgraded).
- Docs: root `README.md` + `project_sina_plan.md` are the two canonical docs. `esp32/README.md` is the only per-directory README (hands-on wiring/capture procedure) — don't add new per-directory READMEs; fold content into the root README or the plan.

## Current status / next steps

Phase 3 (IR capture) in progress. See plan §13 "Next Steps". Critical path: capture the LG remote into `ir_codes/lg_ac.json`.
