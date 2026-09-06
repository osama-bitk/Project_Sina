#!/usr/bin/env python3
"""Send an LG frame to the ESP32 IR bridge over serial.

The brain builds the frame; the node just transmits it (invariant 4). This
is the serial stand-in for the eventual HTTP node, and deliberately speaks
the same "here is a finished frame" contract, so swapping the transport
later does not change either side's job.

    python ir_send.py --temp 22 --mode cool --fan auto
    python ir_send.py --off
    python ir_send.py --jet
    python ir_send.py --raw 0x8808754
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import serial

import lg_ir

CODEBOOK = Path(__file__).resolve().parent.parent / "ir_codes" / "lg_ac.json"
DEFAULT_PORT_GLOB = "/dev/cu.usbmodem*"
BAUD = 115200


def find_port() -> str:
    from glob import glob

    ports = sorted(glob(DEFAULT_PORT_GLOB))
    if not ports:
        raise SystemExit("no /dev/cu.usbmodem* found — is the board plugged into its USB port?")
    return ports[0]


def send_frame(
    port: str,
    value: int,
    bits: int = 28,
    settle: float = 2.0,
    repeat: float = 0.0,
    count: int = 0,
) -> None:
    """Open the port, wait for the board to boot, send the frame, echo replies.

    With repeat > 0, hold the port open and resend every `repeat` seconds —
    useful for aiming, since the port is opened (and the board reset) once.
    """
    with serial.Serial(port, BAUD, timeout=1) as ser:
        # Opening the port resets the board on most ESP32s; let it come up.
        time.sleep(settle)
        ser.reset_input_buffer()

        cmd = f"SEND 0x{value:X} {bits}\n"
        shot = 0
        while True:
            shot += 1
            print(f"> [{shot}] {cmd.strip()}", flush=True)
            ser.write(cmd.encode())
            ser.flush()

            deadline = time.time() + min(3, repeat or 3)
            while time.time() < deadline:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    print(f"< {line}", flush=True)
                    if line.startswith(("OK", "ERR")) and not repeat:
                        break
            if not repeat or (count and shot >= count):
                break
            time.sleep(max(0, repeat - 3) if repeat > 3 else 0)


def main() -> None:
    p = argparse.ArgumentParser(description="Send an LG IR frame via the ESP32 bridge")
    p.add_argument("--port", help="serial port (default: first /dev/cu.usbmodem*)")
    p.add_argument("--temp", type=int, help="target temperature 16-30")
    p.add_argument("--mode", default="cool", help="cool|dry|fan|auto")
    p.add_argument("--fan", default="auto", help="low|med|high|auto")
    p.add_argument("--off", action="store_true", help="power off")
    p.add_argument("--jet", action="store_true", help="jet / Po mode")
    p.add_argument("--light", action="store_true", help="toggle the display light")
    p.add_argument("--raw", help="send this frame verbatim, e.g. 0x8808754")
    p.add_argument("--repeat", type=float, default=0, help="resend every N seconds (for aiming)")
    p.add_argument("--count", type=int, default=0, help="stop after this many shots")
    args = p.parse_args()

    book = json.loads(CODEBOOK.read_text())
    commands = book["commands"]

    if args.raw:
        value = int(args.raw, 16)
    elif args.off:
        value = lg_ir.encode_power_off()
    elif args.jet:
        value = int(commands["jet"], 16)
    elif args.light:
        value = int(commands["light_toggle"], 16)
    elif args.temp is not None:
        try:
            value = lg_ir.encode_state(args.temp, args.mode, args.fan)
        except lg_ir.IRError as e:
            raise SystemExit(f"error: {e}")
    else:
        p.error("give one of --temp, --off, --jet, --light, or --raw")

    port = args.port or find_port()
    print(f"port {port}, frame 0x{value:07X}")
    send_frame(port, value, repeat=args.repeat, count=args.count)


if __name__ == "__main__":
    main()
