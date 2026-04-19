#!/usr/bin/env python3
"""Schema verifier for memory_timeseries.jsonl.

Reads the last 10 lines of `data/logs/memory_timeseries.jsonl` and exits 1 if
any required key is missing or null. Satisfies FR-001 / ISC #2 verify method.

Required keys: ts, commit_bytes_sum, pagefile_free_gb, ram_free_gb, top5_procs.

Exit codes:
    0  last 10 lines (or fewer, if file is shorter) all valid
    1  file missing, empty, unparseable, or any required key missing/null

Usage:
    python tools/scripts/verify_sampler_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "data" / "logs" / "memory_timeseries.jsonl"
REQUIRED = ("ts", "commit_bytes_sum", "pagefile_free_gb", "ram_free_gb", "top5_procs")


def main() -> int:
    if not LOG_FILE.exists():
        print(f"FAIL: {LOG_FILE} does not exist", file=sys.stderr)
        return 1

    with LOG_FILE.open("r", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]

    if not lines:
        print(f"FAIL: {LOG_FILE} is empty", file=sys.stderr)
        return 1

    recent = lines[-10:]
    failures: list[str] = []
    for offset, line in enumerate(recent):
        tag = f"line[-{len(recent) - offset}]"
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            failures.append(f"{tag}: JSON decode error: {e}")
            continue
        if not isinstance(entry, dict):
            failures.append(f"{tag}: not a JSON object")
            continue
        for key in REQUIRED:
            if key not in entry:
                failures.append(f"{tag}: missing key '{key}'")
            elif entry[key] is None:
                failures.append(f"{tag}: key '{key}' is null")

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1

    print(f"OK: {len(recent)} line(s) validated; all required keys non-null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
