#!/usr/bin/env python3
"""ISC helper: morning briefing log exists for local UTC date."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT / "data" / "logs"


def main() -> int:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = LOG_DIR / f"morning_briefing_{day}.log"
    if path.is_file() and path.stat().st_size > 0:
        print("OK:", path)
        return 0
    print("MISSING:", path)
    return 1


if __name__ == "__main__":
    sys.exit(main())
