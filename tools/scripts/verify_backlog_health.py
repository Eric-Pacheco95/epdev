#!/usr/bin/env python3
"""verify_backlog_health.py -- exit 1 when backlog has stale pending_review items.

Used as an executable ISC verify command for the weekly-backlog-health routine.
Exits 0 when no pending_review tasks are older than the threshold.
Exits 1 when stale pending_review items exist.

Usage:
    python tools/scripts/verify_backlog_health.py
    python tools/scripts/verify_backlog_health.py --max-age-days 7
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKLOG = ROOT / "orchestration" / "task_backlog.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check backlog for stale pending_review items")
    parser.add_argument("--max-age-days", type=int, default=7,
                        help="Days before a pending_review task is considered stale (default: 7)")
    args = parser.parse_args()

    if not BACKLOG.is_file():
        print("backlog not found: %s" % BACKLOG)
        return 1

    now = datetime.now(timezone.utc)
    pending = []
    stale = []
    total = 0
    status_counts: dict[str, int] = {}

    for line in BACKLOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        if status != "pending_review":
            continue
        pending.append(task)
        created = task.get("created", "")
        if not created:
            stale.append(task)
            continue
        try:
            created_dt = datetime.strptime(created[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_days = (now - created_dt).days
            if age_days > args.max_age_days:
                stale.append(task)
        except (ValueError, TypeError):
            pass

    # Print composition stats
    print("Backlog: %d total | %s" % (
        total,
        " | ".join("%s=%d" % (k, v) for k, v in sorted(status_counts.items()))
    ))
    print("Pending review: %d | Stale (>%dd): %d" % (len(pending), args.max_age_days, len(stale)))

    if stale:
        for t in stale:
            print("  STALE: %s (%s, created %s)" % (
                t.get("id", "?"), t.get("description", "?")[:60], t.get("created", "?")))
        return 1

    print("OK: no stale pending_review items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
