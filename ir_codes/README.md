# IR codebook

Captured IR codes from the LG AC remote (Phase 3 output). Used by the ESP32 transmitter (Phase 4) and later by the Pi's GPIO driver (Phase 5).

## Format

JSON keyed by command name. Exact schema TBD once Phase 3 captures the first set of codes — the `IRremoteESP8266` decoder dictates the field names.

```json
{
  "power_on":  {"protocol": "LG", "bits": 28, "raw": "0x88C0051"},
  "power_off": {"protocol": "LG", "bits": 28, "raw": "0x88C00A6"},
  "temp_22_cool_auto": {"protocol": "LG", "bits": 28, "raw": "..."}
}
```

LG remotes typically send the entire desired state in each frame (not deltas) — that's what makes the stateless design viable. Each captured code represents a full target state.

## Phase 3 investigation: status query

Check whether the LG remote / AC supports any form of two-way IR (status display button, "feel" mode response, etc.). If yes, capture as `query_state`. If no, the `get_state` tool returns "unknown" at runtime.

## Status

Empty. Populated during Phase 3 IR recon.
