#!/usr/bin/env python3
"""Strategic analysis gate: only allows analysis when >=50 closed trades exist.

FR-005 of PRD_jarvis_crypto_manager.md.

This script is the gate-check for the overnight strategic analysis producer.
If the gate fails (<50 closed trades), exits with code 0 and logs the reason.
If the gate passes, exits with code 0 and prints GATE_PASS for the caller.

Usage:
    python tools/scripts/crypto_bot_analysis_gate.py
    python tools/scripts/crypto_bot_analysis_gate.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = REPO_ROOT / "data" / "crypto_bot_state.json"
HISTORY_FILE = REPO_ROOT / "data" / "crypto_bot_history.jsonl"

MIN_CLOSED_TRADES = 50


def _ascii_safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def check_gate() -> dict:
    """Check if strategic analysis gate conditions are met.

    Returns dict with:
        passed: bool
        closed_trades: int
        reason: str (why gate failed, empty if passed)
    """
    # Read current state
    if not STATE_FILE.is_file():
        return {
            "passed": False,
            "closed_trades": 0,
            "reason": "No crypto_bot_state.json found. Run collector first.",
        }

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "passed": False,
            "closed_trades": 0,
            "reason": "crypto_bot_state.json unreadable.",
        }

    closed = state.get("trade_count_closed", 0)

    if closed < MIN_CLOSED_TRADES:
        return {
            "passed": False,
            "closed_trades": closed,
            "reason": f"Only {closed} closed trades (need {MIN_CLOSED_TRADES}). Analysis deferred.",
        }

    return {
        "passed": True,
        "closed_trades": closed,
        "reason": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Crypto-bot strategic analysis gate")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = check_gate()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["passed"]:
            print(_ascii_safe(f"GATE_PASS: {result['closed_trades']} closed trades. Analysis enabled."))
        else:
            print(_ascii_safe(f"GATE_SKIP: {result['reason']}"))

    # Exit 1 when gate fails — callers use exit code to decide whether to run analysis
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
