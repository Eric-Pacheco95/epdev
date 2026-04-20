#!/usr/bin/env python3
"""verify_costs_rollup.py — ISC verification for costs_rollup.json.

Checks:
  1. File parses as valid JSON and has all 4 window keys
  2. Each window has required schema fields
  3. per_model share_pct sums to 100 ±1 in every non-empty window
  4. per_skill is non-empty (when transcripts have skill invocations) and sorted by cost_usd desc
  5. most_expensive.session_id exists as a real transcript file
  6. source_event_count > 0

Usage:
    python tools/scripts/verify_costs_rollup.py [--input-file path]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT_DIR / "data" / "costs_rollup.json"
TRANSCRIPT_DIR = Path.home() / ".claude" / "projects"

REQUIRED_WINDOWS = {"7d", "30d", "90d", "ytd"}
REQUIRED_WINDOW_KEYS = {
    "spend_usd", "spend_prev_window_usd", "input_tokens_total", "output_tokens_total",
    "cache_read_tokens_total", "cache_creation_tokens_total", "per_day_avg_usd",
    "daily_spend_usd", "budget", "per_model", "per_skill", "session_rollups",
}
REQUIRED_BUDGET_KEYS = {"monthly_usd", "mtd_usd", "pct"}
REQUIRED_SESSION_KEYS = {"avg_usd", "session_count", "most_expensive", "cost_per_1k_tokens_usd"}


def check(condition: bool, msg: str, failures: list[str]) -> bool:
    if not condition:
        failures.append(msg)
    return condition


def verify(input_path: Path) -> bool:
    failures: list[str] = []

    if not input_path.is_file():
        print(f"FAIL: {input_path} not found")
        return False

    try:
        rollup = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: JSON parse error: {exc}")
        return False

    # ISC-1: valid JSON with all 4 window keys
    check("windows" in rollup, "missing 'windows' key at top level", failures)
    if "windows" not in rollup:
        print("\n".join(f"FAIL: {f}" for f in failures))
        return False

    windows = rollup["windows"]
    missing_windows = REQUIRED_WINDOWS - set(windows.keys())
    check(not missing_windows, f"missing windows: {missing_windows}", failures)

    # ISC-2: each window has required schema
    for wkey in REQUIRED_WINDOWS:
        w = windows.get(wkey, {})
        missing_keys = REQUIRED_WINDOW_KEYS - set(w.keys())
        check(not missing_keys, f"window {wkey} missing keys: {missing_keys}", failures)
        if "budget" in w:
            missing_budget = REQUIRED_BUDGET_KEYS - set(w["budget"].keys())
            check(not missing_budget, f"window {wkey}.budget missing keys: {missing_budget}", failures)
        if "session_rollups" in w:
            missing_sr = REQUIRED_SESSION_KEYS - set(w["session_rollups"].keys())
            check(not missing_sr, f"window {wkey}.session_rollups missing keys: {missing_sr}", failures)

    # ISC-3: share_pct sums to 100 ±1 in non-empty windows
    for wkey in REQUIRED_WINDOWS:
        w = windows.get(wkey, {})
        per_model = w.get("per_model", [])
        if not per_model:
            continue
        total_share = sum(m.get("share_pct", 0) for m in per_model)
        check(
            abs(total_share - 100) <= 1,
            f"window {wkey}: per_model share_pct sum = {total_share} (expected 100 ±1)",
            failures,
        )

    # ISC-4: per_skill sorted by cost_usd desc
    for wkey in REQUIRED_WINDOWS:
        w = windows.get(wkey, {})
        per_skill = w.get("per_skill", [])
        if len(per_skill) < 2:
            continue
        costs = [s.get("cost_usd", 0) for s in per_skill]
        check(
            costs == sorted(costs, reverse=True),
            f"window {wkey}: per_skill not sorted by cost_usd desc",
            failures,
        )

    # ISC-5: most_expensive session_id exists as real transcript file
    for wkey in REQUIRED_WINDOWS:
        w = windows.get(wkey, {})
        sr = w.get("session_rollups", {})
        most_exp = sr.get("most_expensive")
        if not most_exp:
            continue
        session_id = most_exp.get("session_id", "")
        if not session_id:
            check(False, f"window {wkey}: most_expensive has empty session_id", failures)
            continue
        matches = list(TRANSCRIPT_DIR.glob(f"C--Users-ericp-Github-*/{session_id}.jsonl"))
        check(
            len(matches) > 0,
            f"window {wkey}: most_expensive session_id '{session_id}' not found as transcript file",
            failures,
        )

    # ISC-6: source_event_count > 0
    event_count = rollup.get("source_event_count", 0)
    check(event_count > 0, f"source_event_count = {event_count} (expected > 0)", failures)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return False

    transcript_count = rollup.get("source_transcript_count", 0)
    status = rollup.get("status", "unknown")
    print(
        f"PASS: {transcript_count} transcripts, {event_count} events, status={status}\n"
        f"      windows={list(windows.keys())}"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify costs_rollup.json ISC criteria")
    parser.add_argument("--input-file", default=str(DEFAULT_INPUT),
                        help="Path to costs_rollup.json")
    args = parser.parse_args()

    ok = verify(Path(args.input_file))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
