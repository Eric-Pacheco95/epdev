#!/usr/bin/env python3
"""FR-004: Sampler coverage verifier.

Reads data/logs/memory_timeseries.jsonl, computes tick completion rate over a
configurable window, and exits 1 if:
  - any contiguous gap exceeds 2× expected cadence (>4 min night / >20 min day)
  - tick completion rate < --min-rate

Cadence schedule (local time):
  Night 22:00-08:00 → 2-min ticks → max allowed gap = 4 min
  Day   08:00-22:00 → 10-min ticks → max allowed gap = 20 min

The PRD task description has these thresholds reversed (">20 min night / >4 min
day") but the 2× multiplier on the actual cadences is the correct definition.

Also reports pressure_gaps[] — gaps where an adjacent tick has commit_bytes_sum
> 70% of pagefile budget (flagged separately from standard gaps).

Usage:
    python tools/scripts/verify_sampler_coverage.py [--window 24h] [--min-rate 0.95]
    python tools/scripts/verify_sampler_coverage.py --window 48h --min-rate 0.95
    python tools/scripts/verify_sampler_coverage.py --log-file /path/to/file.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

import psutil

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_FILE = REPO_ROOT / "data" / "logs" / "memory_timeseries.jsonl"

NIGHT_START_HOUR = 22  # local hour, inclusive
NIGHT_END_HOUR = 8     # local hour, exclusive
NIGHT_CADENCE = timedelta(minutes=2)
DAY_CADENCE = timedelta(minutes=10)
GAP_MULTIPLIER = 2
PRESSURE_FRACTION = 0.70


# ---------------------------------------------------------------------------
# Pure helpers (importable for unit tests)
# ---------------------------------------------------------------------------

def parse_window(s: str) -> timedelta:
    s = s.strip().lower()
    if s.endswith("h"):
        return timedelta(hours=float(s[:-1]))
    if s.endswith("d"):
        return timedelta(days=float(s[:-1]))
    raise ValueError(f"unrecognized window format {s!r} — use e.g. '24h' or '7d'")


def is_night_local(dt_local: datetime) -> bool:
    """Return True if the local datetime falls in the 22:00-08:00 night window."""
    h = dt_local.hour
    return h >= NIGHT_START_HOUR or h < NIGHT_END_HOUR


def expected_cadence(dt_local: datetime) -> timedelta:
    return NIGHT_CADENCE if is_night_local(dt_local) else DAY_CADENCE


def expected_ticks_in_range(start_utc: datetime, end_utc: datetime) -> float:
    """Estimate expected tick count between two UTC datetimes.

    Walks in 1-minute steps, accumulating the fraction of a tick earned each
    minute based on the cadence in effect at that minute (night vs day local).
    O(window_minutes): 48h = 2880 iterations, acceptable.
    """
    total = 0.0
    t = start_utc
    one_minute = timedelta(minutes=1)
    while t < end_utc:
        t_local = t.astimezone()  # convert to local tz
        cad = expected_cadence(t_local)
        total += one_minute / cad
        t += one_minute
    return total


class GapRecord(NamedTuple):
    start_ts: str
    end_ts: str
    gap_minutes: float
    max_allowed_minutes: float


def find_gaps(ticks: list[dict], multiplier: int = GAP_MULTIPLIER) -> list[GapRecord]:
    """Return list of GapRecords where consecutive tick gap exceeds multiplier × cadence.

    For gaps that straddle the night/day boundary the midpoint determines
    which cadence applies — documented by design, see PRD FR-004.
    """
    gaps: list[GapRecord] = []
    for i in range(1, len(ticks)):
        prev = ticks[i - 1]
        curr = ticks[i]
        gap: timedelta = curr["_ts"] - prev["_ts"]
        midpoint = prev["_ts"] + gap / 2
        midpoint_local = midpoint.astimezone()
        max_allowed = expected_cadence(midpoint_local) * multiplier
        if gap > max_allowed:
            gaps.append(GapRecord(
                start_ts=prev["ts"],
                end_ts=curr["ts"],
                gap_minutes=round(gap.total_seconds() / 60, 1),
                max_allowed_minutes=round(max_allowed.total_seconds() / 60, 1),
            ))
    return gaps


def classify_pressure_gaps(
    gaps: list[GapRecord],
    ticks: list[dict],
    pagefile_budget_bytes: int,
) -> list[dict]:
    """Return gaps where at least one adjacent tick has commit_bytes_sum > 70% of pagefile budget.

    Empty result on a healthy system is the expected case and satisfies ISC #3
    (the criterion requires the key to exist and be computed, not to be non-empty).
    """
    threshold = pagefile_budget_bytes * PRESSURE_FRACTION
    ts_to_commit: dict[str, int] = {t["ts"]: t.get("commit_bytes_sum", 0) for t in ticks}
    pressure: list[dict] = []
    for g in gaps:
        before = ts_to_commit.get(g.start_ts, 0)
        after = ts_to_commit.get(g.end_ts, 0)
        if before > threshold or after > threshold:
            pressure.append({
                "start": g.start_ts,
                "end": g.end_ts,
                "gap_minutes": g.gap_minutes,
                "commit_bytes_before": before,
                "commit_bytes_after": after,
                "threshold_bytes": int(threshold),
            })
    return pressure


def load_ticks(log_file: Path, window: timedelta) -> list[dict]:
    """Load ticks from JSONL file within the given time window."""
    if not log_file.exists():
        raise FileNotFoundError(f"{log_file} does not exist")
    cutoff = datetime.now(timezone.utc) - window
    ticks: list[dict] = []
    with log_file.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
                ts_str = entry.get("ts", "")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts >= cutoff:
                    entry["_ts"] = ts
                    ticks.append(entry)
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
    ticks.sort(key=lambda e: e["_ts"])
    return ticks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify memory sampler coverage.")
    parser.add_argument("--window", default="24h", help="Analysis window, e.g. 24h or 48h")
    parser.add_argument("--min-rate", type=float, default=0.95, dest="min_rate",
                        help="Minimum required completion rate (0.0-1.0)")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_FILE,
                        help="Override path to memory_timeseries.jsonl (for testing)")
    args = parser.parse_args(argv)

    window = parse_window(args.window)

    try:
        ticks = load_ticks(args.log_file, window)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if len(ticks) < 2:
        print(f"ERROR: only {len(ticks)} tick(s) in window {args.window} — "
              f"insufficient data to compute gaps", file=sys.stderr)
        return 1

    pagefile_budget_bytes = psutil.swap_memory().total

    gaps = find_gaps(ticks)
    pressure_gaps = classify_pressure_gaps(gaps, ticks, pagefile_budget_bytes)

    window_start = datetime.now(timezone.utc) - window
    window_end = datetime.now(timezone.utc)
    expected = expected_ticks_in_range(window_start, window_end)
    actual = len(ticks)
    completion_rate = actual / expected if expected > 0 else 0.0

    result = {
        "window": args.window,
        "ticks_actual": actual,
        "ticks_expected": round(expected, 1),
        "completion_rate": round(completion_rate, 4),
        "min_rate_required": args.min_rate,
        "pagefile_budget_gb": round(pagefile_budget_bytes / (1024 ** 3), 2),
        "pressure_threshold_pct": int(PRESSURE_FRACTION * 100),
        "gaps": [g._asdict() for g in gaps],
        "pressure_gaps": pressure_gaps,
    }
    print(json.dumps(result, indent=2))

    exit_code = 0
    if gaps:
        print(f"\nFAIL: {len(gaps)} gap(s) exceed {GAP_MULTIPLIER}× expected cadence",
              file=sys.stderr)
        exit_code = 1
    if completion_rate < args.min_rate:
        print(f"\nFAIL: completion rate {completion_rate:.1%} < required {args.min_rate:.1%}",
              file=sys.stderr)
        exit_code = 1
    if exit_code == 0:
        print(f"\nOK: {actual} ticks, completion rate {completion_rate:.1%}, no gaps",
              file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
