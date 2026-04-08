#!/usr/bin/env python3
"""Verify the weekly-synthesis routine outcome.

Two valid pass states:
  1) A new synthesis doc exists in memory/learning/synthesis/ created today.
  2) No unprocessed signals were queued at run time, so Idle Is Success.

Exit 0 on pass, 1 on fail. Designed to be the executable verifier for the
weekly-synthesis routine task ISC.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"


def synthesis_created_today() -> bool:
    if not SYNTH_DIR.is_dir():
        return False
    today = date.today()
    for p in SYNTH_DIR.iterdir():
        if not p.is_file() or p.suffix != ".md":
            continue
        try:
            mtime_date = date.fromtimestamp(p.stat().st_mtime)
        except OSError:
            continue
        if mtime_date == today:
            return True
    return False


def unprocessed_signals_queued() -> int:
    if not SIGNALS_DIR.is_dir():
        return 0
    return sum(1 for p in SIGNALS_DIR.iterdir() if p.is_file() and p.suffix == ".md")


def main() -> int:
    if synthesis_created_today():
        print("PASS: synthesis doc created today")
        return 0
    n_signals = unprocessed_signals_queued()
    if n_signals == 0:
        print("PASS: no unprocessed signals queued (Idle Is Success)")
        return 0
    print(
        "FAIL: %d unprocessed signals queued and no synthesis doc created today"
        % n_signals
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
