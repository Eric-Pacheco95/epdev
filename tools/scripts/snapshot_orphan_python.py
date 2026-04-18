#!/usr/bin/env python3
"""Daily orphan-python snapshot. Appends JSONL entry to
`data/logs/orphan_python_snapshot.jsonl` with today's `python.exe` process count.

Registered as Windows scheduled task `Jarvis-OrphanSnapshot` (00:05 daily).
Used by the orphan-prevention-oom success gate (PRD-1 Phase 4).

Usage:
    python tools/scripts/snapshot_orphan_python.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "data" / "logs" / "orphan_python_snapshot.jsonl"


def count_python_procs() -> int:
    """Count running python.exe processes (all PPIDs)."""
    n = 0
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name")
            if name and name.lower() in {"python.exe", "python"}:
                n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return n


def main() -> int:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"date": date.today().isoformat(), "count": count_python_procs()}
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
