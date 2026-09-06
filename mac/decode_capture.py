#!/usr/bin/env python3
"""Decode LG2 AC frames from IRremoteESP8266 raw-timing dumps.

The library sometimes reports UNKNOWN even for clean frames (footer/gap
edge cases). The raw timings are trustworthy, so decode them directly:
LG2 header is ~3200us mark / ~9900us space, then 28 bits where a long
space (~1600us) is 1 and a short space (~550us) is 0.
"""
import re
import sys

HDR_MARK, HDR_SPACE = 3200, 9900
ONE_SPACE, ZERO_SPACE = 1600, 550
TOL = 0.30


def near(actual, expected):
    return abs(actual - expected) <= expected * TOL


def decode(timings):
    if len(timings) < 4:
        return None, "too short"
    if not (near(timings[0], HDR_MARK) and near(timings[1], HDR_SPACE)):
        return None, f"header mismatch: {timings[0]}, {timings[1]}"

    bits = ""
    # after the header, pairs are (mark, space); trailing mark has no space
    for i in range(2, len(timings) - 1, 2):
        space = timings[i + 1]
        if near(space, ONE_SPACE):
            bits += "1"
        elif near(space, ZERO_SPACE):
            bits += "0"
        else:
            return None, f"bad space at index {i+1}: {space}"

    value = int(bits, 2)
    return (bits, value), None


def lg_checksum_ok(value, nbits):
    """LG frames: low nibble is the sum of the preceding nibbles & 0xF."""
    data = value >> 4
    total = 0
    shifted = data
    while shifted:
        total += shifted & 0xF
        shifted >>= 4
    return (total & 0xF) == (value & 0xF)


def main():
    text = open(sys.argv[1]).read()
    # Each "Raw Timing[N]:" block is followed by signed values until a blank line.
    for block in re.finditer(r"Raw Timing\[(\d+)\]:(.*?)(?:\n\s*\n|\Z)", text, re.S):
        count, body = int(block.group(1)), block.group(2)
        timings = [abs(int(v)) for v in re.findall(r"[+-]\s*(\d+)", body)]
        print(f"--- raw block, {count} entries, {len(timings)} parsed ---")
        result, err = decode(timings)
        if err:
            print(f"  could not decode: {err}")
            continue
        bits, value = result
        nbits = len(bits)
        print(f"  bits    : {nbits}")
        print(f"  binary  : {bits}")
        print(f"  hex     : 0x{value:X}")
        print(f"  checksum: {'VALID' if lg_checksum_ok(value, nbits) else 'INVALID'}")


if __name__ == "__main__":
    main()
