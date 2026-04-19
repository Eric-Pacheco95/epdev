#!/usr/bin/env python3
"""Verify vitals_collector.py output is additively compatible with an earlier schema version.

FR-010 — when SCHEMA_VERSION bumps (e.g. 1.0.0 -> 1.1.0), every top-level key from the
named baseline must still be present. New keys are fine; missing/renamed keys are a
breaking change and fail the check.

Usage:
    python tools/scripts/verify_vitals_schema.py --compat 1.0.0

Exit codes:
    0 — all baseline keys present
    1 — one or more baseline keys missing or renamed
    2 — collector failed to run or emitted invalid JSON
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = REPO_ROOT / "tools" / "scripts" / "vitals_collector.py"

BASELINE_KEYS: dict[str, set[str]] = {
    "1.0.0": {
        "_schema_version",
        "_provenance",
        "heartbeat",
        "heartbeat_meta",
        "skill_usage",
        "heartbeat_trend",
        "trend_averages",
        "overnight",
        "autonomous_value",
        "telos_introspection",
        "skill_evolution",
        "unmerged_branches",
        "overnight_deep_dive",
        "morning_feed",
        "session_usage",
        "overnight_streak",
        "external_monitoring_structured",
        "contradictions_structured",
        "proposals_structured",
        "isc_producer",
        "errors",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify vitals_collector.py retains all keys from a baseline schema version."
    )
    parser.add_argument(
        "--compat", required=True,
        help="Baseline schema version to check against (e.g. 1.0.0)",
    )
    args = parser.parse_args()

    if args.compat not in BASELINE_KEYS:
        print(
            f"Unknown baseline version '{args.compat}'. Known: {sorted(BASELINE_KEYS)}",
            file=sys.stderr,
        )
        return 2

    try:
        result = subprocess.run(
            [sys.executable, str(COLLECTOR)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("vitals_collector.py timed out after 60s", file=sys.stderr)
        return 2

    if result.returncode != 0 or not (result.stdout or "").strip():
        stderr_tail = (result.stderr or "")[-500:]
        print(
            f"vitals_collector.py failed (rc={result.returncode}) or emitted no stdout.\n"
            f"stderr tail: {stderr_tail}",
            file=sys.stderr,
        )
        return 2

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"vitals_collector.py output is not valid JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print(f"Expected JSON object at top level, got {type(payload).__name__}", file=sys.stderr)
        return 2

    expected = BASELINE_KEYS[args.compat]
    actual = set(payload.keys())
    missing = expected - actual
    added = actual - expected

    if missing:
        print(
            f"Schema compat FAIL vs {args.compat}: {len(missing)} key(s) missing: {sorted(missing)}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Schema compat OK vs {args.compat}: all {len(expected)} baseline keys present. "
        f"Added since baseline: {sorted(added) if added else '[]'}. "
        f"Current _schema_version: {payload.get('_schema_version')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
