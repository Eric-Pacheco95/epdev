#!/usr/bin/env python3
"""Weekly cron: log tracked memory file count to data/memory_growth.jsonl.

Idempotent — running twice in the same minute produces two lines, but that
is harmless for trend analysis.  The Windows Task Scheduler wrapper runs
this once per week (Monday 08:00); see register_memory_growth_task.ps1.

Usage:
    python tools/scripts/log_memory_growth.py
"""
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.signal_writer import append_signal  # noqa: E402

SIGNAL_PATH = REPO_ROOT / "data" / "memory_growth.jsonl"


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "memory/"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"ERROR: git ls-files failed: {result.stderr.strip()}", file=sys.stderr)
        return 1

    file_count = len([l for l in result.stdout.strip().splitlines() if l.strip()])
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_count": file_count,
    }
    append_signal(SIGNAL_PATH, record)
    print(f"memory_growth: {file_count} tracked files -> {SIGNAL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
