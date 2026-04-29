#!/usr/bin/env python3
"""DEPRECATED: sync signal_lineage.jsonl -> SQLite lineage table.

Effectively a no-op since the warehouse migration: the per-line JSONL row
shape this script expects (signal_filename / synthesis_filename / date)
no longer matches what /synthesize-signals writes (signals: [] arrays).
Kept as a tombstone — see history/decisions/2026-04-29-arch-review-learning-loop.md.

Do not call from new code; the lineage table in jarvis_index.db is dead
data (70 rows vs 961 actual lineage records on disk). Authoritative
lineage lives in data/signal_lineage.jsonl.

Usage (legacy):
  python tools/scripts/sync_lineage.py          # sync all
  python tools/scripts/sync_lineage.py --dry-run # show what would sync
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

LINEAGE_JSONL = REPO_ROOT / "data" / "signal_lineage.jsonl"


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not LINEAGE_JSONL.exists():
        print("No signal_lineage.jsonl found.", file=sys.stderr)
        sys.exit(0)

    from tools.scripts.manifest_db import write_lineage, _get_conn

    # Count existing rows for delta reporting
    conn = _get_conn()
    if conn is None:
        print("ERROR: manifest DB unavailable.", file=sys.stderr)
        sys.exit(1)
    before = conn.execute("SELECT COUNT(*) FROM lineage").fetchone()[0]
    conn.close()

    synced = 0
    with LINEAGE_JSONL.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sig = row.get("signal_filename", "")
            syn = row.get("synthesis_filename", "")
            dt = row.get("date", "")
            if not (sig and syn and dt):
                continue
            if dry_run:
                print(f"  would sync: {sig} -> {syn}")
                synced += 1
            else:
                if write_lineage(sig, syn, dt):
                    synced += 1

    if dry_run:
        print(f"Dry run: {synced} rows would be synced.")
    else:
        conn = _get_conn()
        after = conn.execute("SELECT COUNT(*) FROM lineage").fetchone()[0] if conn else before
        if conn:
            conn.close()
        delta = after - before
        print(f"Lineage sync: {delta} new rows inserted ({after} total).")


if __name__ == "__main__":
    main()
