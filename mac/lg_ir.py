#!/usr/bin/env python3
"""Build LG AC IR frames from a target state.

LG encodes the full desired state in every frame, so there is no button
lookup table: the brain constructs the frame it wants. That is what makes
the stateless command model (invariant 2) work.

Frame: 0x88 <n3> <mode> <temp> <fan> <checksum>, 28 bits, protocol LG2.

Self-test (`python lg_ir.py --selftest`) regenerates every frame captured
from the physical remote in ../ir_codes/lg_ac.json. If the encoding were
wrong, those would not reproduce.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

CODEBOOK = Path(__file__).resolve().parent.parent / "ir_codes" / "lg_ac.json"

TEMP_MIN, TEMP_MAX = 16, 30
TEMP_OFFSET = 15

MODE_NIBBLE = {"cool": 0x8, "dry": 0x9, "fan": 0xA, "auto": 0xB}
FAN_NIBBLE = {"low": 0x0, "med": 0x2, "high": 0x4, "auto": 0x5}

POWER_OFF = 0x88C0051


class IRError(Exception):
    pass


def _checksum(nibbles: list[int]) -> int:
    return sum(nibbles) & 0xF


def encode_state(temp_c: int, mode: str = "cool", fan: str = "auto") -> int:
    """Return the 28-bit frame for this target state (also powers the unit on)."""
    if mode not in MODE_NIBBLE:
        raise IRError(f"unsupported mode {mode!r} (have: {sorted(MODE_NIBBLE)})")
    if fan not in FAN_NIBBLE:
        raise IRError(f"unsupported fan {fan!r} (have: {sorted(FAN_NIBBLE)})")
    if not TEMP_MIN <= temp_c <= TEMP_MAX:
        raise IRError(f"temp {temp_c} out of range {TEMP_MIN}..{TEMP_MAX}")

    nibbles = [0x8, 0x8, 0x0, MODE_NIBBLE[mode], temp_c - TEMP_OFFSET, FAN_NIBBLE[fan]]
    nibbles.append(_checksum(nibbles))

    value = 0
    for n in nibbles:
        value = (value << 4) | n
    return value


def encode_power_off() -> int:
    """LG uses one fixed command for off; state frames handle on."""
    return POWER_OFF


def _selftest() -> int:
    book = json.loads(CODEBOOK.read_text())
    samples = book["verified_samples"]
    failures = 0
    checked = 0

    def check(label: str, expected_hex: str, actual: int) -> None:
        nonlocal failures, checked
        checked += 1
        expected = int(expected_hex, 16)
        if expected != actual:
            failures += 1
            print(f"  FAIL {label}: captured {expected_hex}, encoder 0x{actual:07X}")
        else:
            print(f"  ok   {label}: 0x{actual:07X}")

    print("temp sweep (mode=cool, fan=auto):")
    for temp, hexval in samples["temp_sweep_cool_fanauto"].items():
        if temp.startswith("_"):
            continue
        check(f"{temp}C", hexval, encode_state(int(temp), "cool", "auto"))

    print("fan sweep (mode=cool, temp=18):")
    for fan in ("low", "med", "high", "auto"):
        check(fan, samples["fan_sweep_cool_18c"][fan], encode_state(18, "cool", fan))

    print("mode sweep:")
    modes = samples["mode_sweep"]
    check("auto 17C fan=auto", modes["auto_17c_fanauto"], encode_state(17, "auto", "auto"))
    check("dry 24C fan=low", modes["dry_24c_fanlow"], encode_state(24, "dry", "low"))
    check("fan 18C fan=high", modes["fan_18c_fanhigh"], encode_state(18, "fan", "high"))

    print("power off:")
    check("power_off", book["commands"]["power_off"], encode_power_off())

    print(f"\n{checked - failures}/{checked} frames reproduced")
    return 1 if failures else 0


def main() -> None:
    p = argparse.ArgumentParser(description="LG AC IR frame builder")
    p.add_argument("--selftest", action="store_true", help="regenerate every captured frame")
    p.add_argument("--temp", type=int, help="target temperature in C")
    p.add_argument("--mode", default="cool", help="cool|dry|fan|auto")
    p.add_argument("--fan", default="auto", help="low|med|high|auto")
    p.add_argument("--off", action="store_true", help="emit the power-off frame")
    args = p.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    try:
        value = encode_power_off() if args.off else encode_state(args.temp, args.mode, args.fan)
    except (IRError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    print(f"0x{value:07X}")


if __name__ == "__main__":
    main()
