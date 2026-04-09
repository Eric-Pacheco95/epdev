#!/usr/bin/env python3
"""check_suspend.py -- Exit non-zero if a producer has an active suspend sentinel.

Usage:
    python tools\\scripts\\check_suspend.py <producer_name>

Exit codes:
    0  -- no sentinel; producer may run
    2  -- wrong number of arguments
    3  -- sentinel exists; producer is intentionally suspended (distinct from crash exit 1)
"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: check_suspend.py <producer_name>")
        sys.exit(2)

    producer_name = sys.argv[1]
    repo_root = Path(__file__).resolve().parents[2]
    sentinel_path = repo_root / "data" / "producers" / f"{producer_name}.suspend"

    # Directory missing -> no sentinel -> allow run
    if not sentinel_path.parent.exists():
        sys.exit(0)

    if sentinel_path.exists():
        print("SUSPENDED: %s is suspended. Check #jarvis-decisions for details." % producer_name)
        print("Sentinel: %s" % sentinel_path)
        print("(Delete this file to resume: %s)" % sentinel_path)
        sys.exit(3)  # exit 3 = intentional suspend, distinct from crash (1) or usage error (2)

    sys.exit(0)


if __name__ == "__main__":
    main()
