#!/usr/bin/env python3
"""ISC helper: snapshot.jsonl has a row dated today (UTC)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SNAP = ROOT / "data" / "financial" / "snapshot.jsonl"


def main() -> int:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not SNAP.is_file():
        print("MISSING:", SNAP)
        return 1
    ok = False
    for line in SNAP.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(row.get("ts", ""))
        if ts.startswith(day):
            ok = True
            break
    if ok:
        print("OK: snapshot row for", day)
        return 0
    print("NO_ROW_FOR_DATE:", day)
    return 1


if __name__ == "__main__":
    sys.exit(main())
