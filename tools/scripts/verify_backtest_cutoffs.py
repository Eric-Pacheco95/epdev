#!/usr/bin/env python3
"""verify_backtest_cutoffs -- ISC anti-criterion verifier for prediction backtests.

Confirms every event in data/backtest_events.yaml has a knowledge_cutoff_date
strictly before an effective threshold derived from the active prediction
model's training cutoff minus a safety buffer (per-model dynamic policy).

Exit codes:
    0 -- all events pass the leakage guard
    1 -- one or more events violate the guard, or input file missing/unparseable

Used by task-1775554202462869 ISC #3. Sanitizer-clean (repo-relative python
script under tools/scripts/), so the dispatcher can execute it directly.

Policy:
    Active model: Opus 4.6 (knowledge cutoff 2025-05)
    Buffer: 24 months (events resolved within the buffer window are
            assumed to be present in training data and would leak the outcome)
    => effective threshold: knowledge_cutoff_date < 2023-05-01

Update MODEL_KNOWLEDGE_CUTOFF / BUFFER_MONTHS below when the active prediction
model changes. The verifier is the single source of truth for the leakage guard.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import yaml

EVENTS_FILE = Path(__file__).resolve().parents[2] / "data" / "backtest_events.yaml"

# -- Per-model policy ---------------------------------------------------------
MODEL_KNOWLEDGE_CUTOFF = date(2025, 5, 1)  # Opus 4.6
BUFFER_MONTHS = 24


def _effective_threshold() -> date:
    y = MODEL_KNOWLEDGE_CUTOFF.year
    m = MODEL_KNOWLEDGE_CUTOFF.month - BUFFER_MONTHS
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _parse_cutoff(value) -> date | None:
    """Parse a knowledge_cutoff_date value to a date.

    Accepts datetime.date (already parsed by yaml), or strings in YYYY-MM-DD
    form, including those wrapped in straight or smart quotes (which yaml
    returns as plain strings after stripping its own quoting).
    """
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip().strip('"').strip("'")
    # Strip Unicode smart quotes if present (U+201C/U+201D, U+2018/U+2019)
    s = s.strip("\u201c\u201d\u2018\u2019")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def main() -> int:
    threshold = _effective_threshold()

    if not EVENTS_FILE.exists():
        print(f"FAIL: {EVENTS_FILE} not found")
        return 1

    try:
        data = yaml.safe_load(EVENTS_FILE.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"FAIL: cannot parse {EVENTS_FILE.name}: {exc}")
        return 1

    if not isinstance(data, dict) or "events" not in data:
        print(f"FAIL: {EVENTS_FILE.name} missing top-level 'events' key")
        return 1

    events = data.get("events") or []
    if not events:
        print(f"FAIL: no events found in {EVENTS_FILE.name}")
        return 1

    violations: list[tuple[str, str]] = []
    missing: list[str] = []
    for e in events:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("event_id", "<no event_id>"))
        raw = e.get("knowledge_cutoff_date")
        if raw is None:
            missing.append(eid)
            continue
        cutoff = _parse_cutoff(raw)
        if cutoff is None:
            violations.append((eid, f"unparseable cutoff: {raw!r}"))
            continue
        if cutoff >= threshold:
            violations.append((eid, cutoff.isoformat()))

    if missing:
        print(f"FAIL: {len(missing)} event(s) missing knowledge_cutoff_date:")
        for eid in missing:
            print(f"  - {eid}")
        return 1

    if violations:
        print(
            f"FAIL: {len(violations)} event(s) with cutoff >= {threshold.isoformat()} "
            f"(model {MODEL_KNOWLEDGE_CUTOFF.isoformat()}, buffer {BUFFER_MONTHS}mo):"
        )
        for eid, info in violations:
            print(f"  - {eid}: {info}")
        return 1

    print(
        f"PASS: all {len(events)} backtest event cutoffs are before {threshold.isoformat()} "
        f"(model {MODEL_KNOWLEDGE_CUTOFF.isoformat()}, buffer {BUFFER_MONTHS}mo)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
