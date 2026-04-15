#!/usr/bin/env python3
"""Tripwire: detect learning data loss.

Two checks:
1. Every signal filename referenced in ``data/signal_lineage.jsonl`` must
   exist under ``memory/learning/signals/`` (or be present in compressed
   archives — checked via name match against gz filenames).
2. Current signal file count must be >= the previous high-water mark
   recorded in ``data/signal_retention_state.json`` (monotonically
   non-decreasing — minus an allowance for the sanctioned 180d gzip
   path in compress_signals.py).

Exit codes:
    0 = OK
    1 = retention violation (missing lineage-referenced file or count drop)
    2 = crash

Wire into heartbeat and the backlog. Per CLAUDE.md anti-criterion rule,
this script exits nonzero on the forbidden state.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LINEAGE_PATH = REPO_ROOT / "data" / "signal_lineage.jsonl"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
STATE_PATH = REPO_ROOT / "data" / "signal_retention_state.json"

# If current count drops below high-water by more than this ratio, fail.
# compress_signals.py legitimately gzips files older than 180d; allow some
# monotonic slack for that path without letting silent destruction hide.
DROP_TOLERANCE_RATIO = 0.10


def list_signal_names() -> set[str]:
    if not SIGNALS_DIR.is_dir():
        return set()
    names = set()
    for p in SIGNALS_DIR.iterdir():
        if p.name.startswith("_"):
            continue
        if p.suffix in (".md", ".gz"):
            # strip .gz for compressed archives: 2026-03-28_foo.md.gz -> 2026-03-28_foo.md
            name = p.name[:-3] if p.suffix == ".gz" else p.name
            names.add(name)
    return names


def load_lineage_references() -> list[tuple[str, str]]:
    """Return list of (synthesis_id, signal_filename) tuples."""
    out: list[tuple[str, str]] = []
    if not LINEAGE_PATH.is_file():
        return out
    for line in LINEAGE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = row.get("synthesis_id", "?")
        for name in row.get("signals", []) or []:
            out.append((sid, name))
    return out


def load_state() -> dict:
    if not STATE_PATH.is_file():
        return {"high_water_count": 0, "last_check_utc": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"high_water_count": 0, "last_check_utc": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    present = list_signal_names()
    current_count = len(present)

    refs = load_lineage_references()
    missing: list[tuple[str, str]] = [
        (sid, name) for sid, name in refs if name not in present
    ]

    state = load_state()
    high_water = int(state.get("high_water_count", 0))
    tolerance = max(1, int(high_water * DROP_TOLERANCE_RATIO))
    count_violation = current_count < (high_water - tolerance)

    violations = []
    if missing:
        violations.append(
            f"{len(missing)} lineage-referenced signal(s) missing "
            f"(first 3: {missing[:3]})"
        )
    if count_violation:
        violations.append(
            f"signal count dropped: {current_count} < high_water {high_water} "
            f"(tolerance {tolerance})"
        )

    now = datetime.now(timezone.utc).isoformat()
    if not violations and current_count > high_water:
        state["high_water_count"] = current_count
    state["last_check_utc"] = now
    state["last_count"] = current_count
    save_state(state)

    if violations:
        print("LEARNING RETENTION VIOLATION:")
        for v in violations:
            print(f"  - {v}")
        print(f"  current_count={current_count} high_water={high_water} "
              f"lineage_refs={len(refs)}")
        return 1

    print(f"OK: {current_count} signals, {len(refs)} lineage refs, "
          f"high_water={state['high_water_count']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"verify_learning_retention crashed: {exc}", file=sys.stderr)
        sys.exit(2)
