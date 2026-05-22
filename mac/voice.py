#!/usr/bin/env python3
"""Voice → validated AC tool call.

Interactive: Enter to start recording, Enter again to stop. Transcribes
with faster-whisper, pipes the text into brain.parse, prints the tool call.

Or one-shot: --audio FILE transcribes a wav/mp3 and exits. Useful for
smoke-testing without a microphone.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import wave
from io import BytesIO
from pathlib import Path

import pyaudio
from faster_whisper import WhisperModel

import brain

SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024


class Recorder:
    def __init__(self) -> None:
        self._audio = pyaudio.PyAudio()
        self._frames: list[bytes] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._frames = []
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> BytesIO:
        self._running = False
        if self._thread:
            self._thread.join()
        buf = BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(CHANNELS)
            w.setsampwidth(self._audio.get_sample_size(FORMAT))
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"".join(self._frames))
        buf.seek(0)
        return buf

    def _loop(self) -> None:
        stream = self._audio.open(
            format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
            input=True, frames_per_buffer=CHUNK,
        )
        try:
            while self._running:
                self._frames.append(stream.read(CHUNK, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()

    def close(self) -> None:
        self._audio.terminate()


def transcribe(whisper: WhisperModel, audio) -> tuple[str, int]:
    t0 = time.perf_counter()
    segments, _ = whisper.transcribe(audio, beam_size=1, language="en")
    text = " ".join(s.text for s in segments).strip()
    return text, int((time.perf_counter() - t0) * 1000)


def process(text: str, model: str, stt_ms: int) -> None:
    if not text:
        print(f"(no speech detected, stt {stt_ms}ms)", file=sys.stderr)
        return
    print(f"> {text}  [stt {stt_ms}ms]", file=sys.stderr)
    t0 = time.perf_counter()
    try:
        call = brain.parse(model, text)
    except brain.BrainError as e:
        print(f"  error: {e}", file=sys.stderr)
        return
    llm_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  {json.dumps(call)}  [llm {llm_ms}ms]")


def main() -> None:
    p = argparse.ArgumentParser(description="Sina voice → validated tool call")
    p.add_argument("--model", default="sina-medium", help="Ollama model tag")
    p.add_argument("--whisper", default="base.en", help="faster-whisper model")
    p.add_argument("--audio", type=Path, help="Transcribe this file and exit (skip live mode)")
    args = p.parse_args()

    print(f"Loading whisper {args.whisper}... ", end="", flush=True, file=sys.stderr)
    whisper = WhisperModel(args.whisper, device="cpu", compute_type="int8")
    print("ready.", file=sys.stderr)

    if args.audio:
        text, stt_ms = transcribe(whisper, str(args.audio))
        process(text, args.model, stt_ms)
        return

    rec = Recorder()
    try:
        while True:
            try:
                cmd = input("\nEnter to record (q + Enter to quit): ").strip().lower()
            except EOFError:
                break
            if cmd == "q":
                break
            rec.start()
            try:
                input("[recording — Enter to stop]")
            except EOFError:
                pass
            audio = rec.stop()
            text, stt_ms = transcribe(whisper, audio)
            process(text, args.model, stt_ms)
    finally:
        rec.close()


if __name__ == "__main__":
    main()
