# Pi edge unit (Phase 5+)

The end-state device. Self-contained Raspberry Pi 5 unit: mic in, IR out, no network calls at runtime. This is what gets cloned into every room.

## Status

Not yet started. Blocked on Phase 4 completion.

## Port targets (from Phase 4)

- `brain.py` → runs locally on Pi instead of Mac.
- IR transmission → moves from ESP32/Arduino to Pi GPIO via `pigpio` (microsecond pulse precision).
- Ollama + Whisper → re-install on Pi, re-benchmark.

## Design notes

- **Fully offline.** No internet at runtime. Verified with `tcpdump` and by disconnecting Wi-Fi after model downloads complete. Required by plan §2.
- **Stateless.** No persistent tracking of AC state. Each command carries the full intended state in the IR frame (which is how LG remotes work anyway). "What temp is it on?" is answered by querying the AC over IR if Phase 3 found a status code; otherwise the agent says "unknown" rather than maintaining a synthetic mirror of state.

## TODO before Phase 6 (always-on listening)

- Run baseline `tcpdump` with Wi-Fi connected and confirm zero outbound traffic during a full voice-command cycle. Needed for the privacy claim in plan §9.
