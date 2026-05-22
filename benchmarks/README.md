# Tool-calling benchmark

The dataset that Phase 1's "≥95% accuracy" target is measured against. Without this set defined, the accuracy target is meaningless.

## Format

`commands.jsonl` — one JSON object per line:

```json
{"input": "make it colder", "category": "colloquial", "expected": {"tool": "set_temp", "args": {"delta": -2}}, "notes": "relative temp change"}
```

Fields:

- `input` — what the user says.
- `category` — one of `literal`, `colloquial`, `ambiguous`, `state-query`, `off-topic`, `adversarial`.
- `expected` — the tool call we expect, or `null` for off-topic / adversarial inputs that should not produce a tool call.
- `notes` — free text for human reviewers.

## Categories and targets

| Category | Target count | Examples |
|---|---|---|
| literal | 20+ | "set the temperature to 22", "turn the AC off" |
| colloquial | 20+ | "make it colder", "I'm freezing" |
| ambiguous | 10+ | "set it to 22" (temp or fan speed?) |
| state-query | 10+ | "what temp is the AC on?" → `get_state` tool call |
| off-topic | 10+ | "what's the weather like" — expected `none` |
| adversarial | 10+ | "set temp to 999", "ignore previous instructions..." — expected `none` |

The agent isn't built to refuse or argue — it just recognizes what's in scope and what isn't. Off-topic and adversarial inputs both resolve to `tool: none`; they're separate categories only so we can see if one fails differently from the other.

Minimum 80 entries. Aim for 100+ before declaring Phase 1 done.

## Scoring

`benchmark.py` (in `../mac/`) loads this file, runs each input against both Qwen 2.5 sizes, and grades exact-match on the `expected` tool call. Output: per-model accuracy by category, plus latency timing (captured for the record, not a Phase 1 gate).
