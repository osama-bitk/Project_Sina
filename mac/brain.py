#!/usr/bin/env python3
"""Text in, validated AC tool call out.

Phase 1 dry-run: reads from argv or stdin, prints the parsed tool call
as JSON. Pydantic validates the shape; one corrective retry on
malformed output, then fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Annotated, Literal, Optional, Union

import ollama
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetPowerArgs(_Strict):
    on: bool


class SetTempArgs(_Strict):
    temp_c: Optional[int] = Field(default=None, ge=16, le=30)
    delta: Optional[int] = Field(default=None, ge=-10, le=10)

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.temp_c is None) == (self.delta is None):
            raise ValueError("set_temp requires exactly one of temp_c or delta")
        return self


class SetFanArgs(_Strict):
    speed: Literal["auto", "low", "med", "high"]


class SetModeArgs(_Strict):
    mode: Literal["cool", "heat", "dry", "fan"]


class _EmptyArgs(_Strict):
    pass


class _SetPower(_Strict):
    tool: Literal["set_power"]
    args: SetPowerArgs


class _SetTemp(_Strict):
    tool: Literal["set_temp"]
    args: SetTempArgs


class _SetFan(_Strict):
    tool: Literal["set_fan"]
    args: SetFanArgs


class _SetMode(_Strict):
    tool: Literal["set_mode"]
    args: SetModeArgs


class _GetState(_Strict):
    tool: Literal["get_state"]
    args: _EmptyArgs = _EmptyArgs()


class _NoTool(_Strict):
    tool: Literal["none"]
    args: _EmptyArgs = _EmptyArgs()


ToolCall = Annotated[
    Union[_SetPower, _SetTemp, _SetFan, _SetMode, _GetState, _NoTool],
    Field(discriminator="tool"),
]
_adapter: TypeAdapter = TypeAdapter(ToolCall)


class BrainError(Exception):
    pass


def _ollama_chat(model: str, messages: list[dict]) -> str:
    resp = ollama.chat(
        model=model,
        messages=messages,
        format="json",
        options={"temperature": 0},
    )
    return resp["message"]["content"]


def _validate(raw: str) -> dict:
    data = json.loads(raw)
    return _adapter.validate_python(data).model_dump(exclude_none=True)


def parse(model: str, user_input: str) -> dict:
    """Return validated tool call as a plain dict. One retry on malformed output, then BrainError."""
    messages: list[dict] = [{"role": "user", "content": user_input}]
    raw: str = ""

    try:
        raw = _ollama_chat(model, messages)
        return _validate(raw)
    except (json.JSONDecodeError, ValidationError) as first_err:
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": (
                f"Your previous response was invalid: {first_err}. "
                "Reply with one valid JSON tool call matching the schema. No prose."
            ),
        })
        try:
            raw = _ollama_chat(model, messages)
            return _validate(raw)
        except (json.JSONDecodeError, ValidationError) as second_err:
            raise BrainError(f"invalid tool call after retry: {second_err}") from second_err


def main() -> None:
    p = argparse.ArgumentParser(description="Sina brain — dry-run tool-call parser")
    p.add_argument("--model", default="sina-small", help="Ollama model tag (default: sina-small)")
    p.add_argument("input", nargs="*", help="User input; if omitted, reads stdin")
    args = p.parse_args()

    user_input = " ".join(args.input).strip() if args.input else sys.stdin.read().strip()
    if not user_input:
        print("error: no input", file=sys.stderr)
        sys.exit(2)

    try:
        call = parse(args.model, user_input)
    except BrainError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(call))


if __name__ == "__main__":
    main()
