#!/usr/bin/env python3
"""Success-gate verifier for orphan-prevention-oom PRD-1.

Reads `data/logs/orphan_python_snapshot.jsonl` and exits 1 if:
- Fewer than 7 entries exist (not enough days observed yet), OR
- Any of the last 7 entries has `count >= 20`.

Exits 0 only if the last 7 daily snapshots all show < 20 python.exe processes.

Usage:
    python tools/scripts/verify_orphan_streak.py
    python tools/scripts/verify_orphan_streak.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "data" / "logs" / "orphan_python_snapshot.jsonl"

THRESHOLD = 20
REQUIRED_STREAK = 7


def load_entries() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    entries: list[dict] = []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        entries = load_entries()
    except json.JSONDecodeError as exc:
        msg = f"FAIL: malformed JSON in {LOG_FILE}: {exc}"
        if args.json:
            print(json.dumps({"status": "fail", "reason": msg}))
        else:
            print(msg)
        return 1

    if not LOG_FILE.exists():
        msg = f"FAIL: {LOG_FILE} does not exist (Jarvis-OrphanSnapshot task not registered yet?)"
        if args.json:
            print(json.dumps({"status": "fail", "reason": msg, "entries": 0}))
        else:
            print(msg)
        return 1

    if len(entries) < REQUIRED_STREAK:
        msg = f"FAIL: only {len(entries)} snapshot entries; need at least {REQUIRED_STREAK}"
        if args.json:
            print(json.dumps({
                "status": "fail", "reason": msg, "entries": len(entries),
                "required": REQUIRED_STREAK,
            }))
        else:
            print(msg)
        return 1

    last_n = entries[-REQUIRED_STREAK:]
    violations = [e for e in last_n if int(e.get("count", 10**9)) >= THRESHOLD]

    if violations:
        if args.json:
            print(json.dumps({
                "status": "fail",
                "reason": f"{len(violations)} of last {REQUIRED_STREAK} days have count >= {THRESHOLD}",
                "violations": violations,
                "last_n": last_n,
            }))
        else:
            print(f"FAIL: {len(violations)} of last {REQUIRED_STREAK} days have count >= {THRESHOLD}:")
            for e in violations:
                print(f"  {e}")
        return 1

    if args.json:
        print(json.dumps({
            "status": "pass",
            "reason": f"last {REQUIRED_STREAK} days all count < {THRESHOLD}",
            "last_n": last_n,
        }))
    else:
        print(f"PASS: last {REQUIRED_STREAK} days all count < {THRESHOLD}:")
        for e in last_n:
            print(f"  {e.get('date')}: {e.get('count')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
