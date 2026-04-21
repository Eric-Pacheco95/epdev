#!/usr/bin/env python3
"""isc_template_monitor.py -- summarize isc_templates production usage (monitoring).

Reads data/isc_template_usage.jsonl (append-only) and prints counts by preset.
Optional: --since-days N to ignore older rows (default: all).

Exit 0 always unless file unreadable.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
USAGE_LOG = REPO_ROOT / "data" / "isc_template_usage.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="ISC template usage monitor")
    ap.add_argument(
        "--since-days",
        type=float,
        default=None,
        metavar="N",
        help="Only count rows newer than N days (UTC)",
    )
    args = ap.parse_args()

    if not USAGE_LOG.is_file():
        print("isc_template_usage.jsonl: (missing -- no presets logged yet)")
        return 0

    cutoff = None
    if args.since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.since_days)

    counts: Counter[str] = Counter()
    n = 0
    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = row.get("ts", "")
        if cutoff and ts:
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if t < cutoff:
                    continue
            except ValueError:
                pass
        preset = str(row.get("preset", "unknown"))
        counts[preset] += 1
        n += 1

    print(f"isc_template_usage.jsonl: {n} row(s)")
    for preset, c in counts.most_common():
        print(f"  {preset}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
