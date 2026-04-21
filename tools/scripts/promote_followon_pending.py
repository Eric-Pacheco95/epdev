#!/usr/bin/env python3
"""promote_followon_pending.py -- CLI for 5E-3 FOLLOW_UP staging queue.

List pending rows or promote one into orchestration/task_backlog.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.followon_pending import DEFAULT_PATH, list_pending, promote_one  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Follow-on pending queue (5E-3)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="Print pending rows as JSON")
    ls.add_argument("--path", type=Path, default=None, help="Override jsonl path")

    pr = sub.add_parser("promote", help="Promote one row into backlog (pending_review)")
    pr.add_argument("row_id", help="Row id (fp-...)")
    pr.add_argument("--path", type=Path, default=None, help="Override jsonl path")

    args = p.parse_args()
    path = args.path or DEFAULT_PATH

    if args.cmd == "list":
        rows = list_pending(path)
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    result = promote_one(args.row_id, path=path)
    if result is None:
        print("ERROR: row not found, not pending, or backlog_append deduped", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
