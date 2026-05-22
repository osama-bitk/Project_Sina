#!/usr/bin/env python3
"""Run commands.jsonl against multiple Ollama models, write CSV, print summary.

Phase 1 exit gate: choose the production model based on per-category accuracy.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

from brain import BrainError, parse

REPO = Path(__file__).resolve().parent.parent
DATASET = REPO / "benchmarks" / "commands.jsonl"
OUTPUT_DIR = REPO / "benchmarks" / "results"

MODELS = ["sina-small", "sina-medium"]


def _matches(expected, actual) -> bool:
    if not isinstance(actual, dict):
        return False
    if expected is None:
        return actual.get("tool") == "none"
    return (
        actual.get("tool") == expected.get("tool")
        and (actual.get("args") or {}) == (expected.get("args") or {})
    )


def _load(path: Path):
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def run(models=MODELS, dataset=DATASET, out_dir=OUTPUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"results-{time.strftime('%Y%m%d-%H%M%S')}.csv"

    entries = list(_load(dataset))
    print(f"Loaded {len(entries)} cases from {dataset.relative_to(REPO)}", file=sys.stderr)

    rows: list[dict] = []
    for model in models:
        print(f"\n=== {model} ===", file=sys.stderr)
        for i, entry in enumerate(entries, 1):
            t0 = time.perf_counter()
            actual, err = None, ""
            try:
                actual = parse(model, entry["input"])
            except BrainError as e:
                err = str(e)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            latency_ms = int((time.perf_counter() - t0) * 1000)

            ok = _matches(entry.get("expected"), actual)
            tag = "Y" if ok else "N"
            print(
                f"  [{tag}] {i:3d}/{len(entries)}  {entry['category']:<12} {entry['input'][:55]}",
                file=sys.stderr,
            )

            rows.append({
                "model": model,
                "input": entry["input"],
                "category": entry["category"],
                "expected": json.dumps(entry.get("expected")),
                "actual": json.dumps(actual) if actual is not None else "",
                "match": tag,
                "latency_ms": latency_ms,
                "error": err,
            })

    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {out_path.relative_to(REPO)}", file=sys.stderr)
    _summary(rows)
    return out_path


def _summary(rows: list[dict]) -> None:
    by_model: dict[str, dict[str, list[int]]] = {}
    for r in rows:
        cats = by_model.setdefault(r["model"], {})
        bucket = cats.setdefault(r["category"], [0, 0])
        bucket[1] += 1
        if r["match"] == "Y":
            bucket[0] += 1

    print("\n=== Summary ===")
    print(f"{'model':<14} {'category':<14} {'pass':>5} / {'total':>5}  {'pct':>4}")
    print("-" * 52)
    for model, cats in by_model.items():
        tp = tt = 0
        for cat in sorted(cats):
            p, t = cats[cat]
            tp += p
            tt += t
            print(f"{model:<14} {cat:<14} {p:>5} / {t:>5}  {100*p/t:>3.0f}%")
        print(f"{model:<14} {'OVERALL':<14} {tp:>5} / {tt:>5}  {100*tp/tt:>3.0f}%")
        print()


if __name__ == "__main__":
    run()
