#!/usr/bin/env python3
"""Append one task proposal (stdin JSON object). Requires JARVIS_TASK_PROPOSALS_ENABLED=1.

Example:
  set JARVIS_TASK_PROPOSALS_ENABLED=1
  echo {\"title\":\"Fix X\",\"rationale\":\"signal S\",\"source\":\"manual\"} | python tools/scripts/task_proposal.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("stdin JSON required", file=sys.stderr)
        return 1
    try:
        rec = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"invalid json: {exc}", file=sys.stderr)
        return 1
    from tools.scripts.lib.task_proposals import proposal_append

    try:
        out = proposal_append(rec)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if out is None:
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
