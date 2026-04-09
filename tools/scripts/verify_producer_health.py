#!/usr/bin/env python3
"""verify_producer_health.py -- exit 1 when any producer is unhealthy.

Used as an executable ISC verify command for the heartbeat remediation map.
Exits 0 when all producers are healthy, 1 when one or more are stale/failed.

Usage:
    python tools/scripts/verify_producer_health.py
    python tools/scripts/verify_producer_health.py --max-age-hours 26
"""
import argparse
import sys
from pathlib import Path

# repo root is two levels up from tools/scripts/
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.scripts.manifest_db import query_producer_health  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check producer health via manifest_db")
    parser.add_argument("--max-age-hours", type=float, default=26.0,
                        help="Hours before a producer run is considered stale (default: 26)")
    args = parser.parse_args()

    issues = query_producer_health(max_age_hours=args.max_age_hours)
    if not issues:
        print("all producers healthy")
        return 0

    print(f"{len(issues)} unhealthy producer(s):")
    for issue in issues:
        producer = issue.get("producer", "unknown")
        kind = issue.get("issue", "unknown")
        hours = issue.get("hours_ago", "?")
        status = issue.get("last_status", "?")
        print(f"  {producer}: {kind} ({hours:.1f}h ago, last_status={status})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
