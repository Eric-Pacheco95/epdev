#!/usr/bin/env python3
"""Learning pipeline bridge: reads crypto-bot performance data and writes Jarvis signals.

FR-004 of PRD_jarvis_crypto_manager.md.

Runs daily (overnight runner). Reads /api/signal-attribution + /api/paper-report +
/api/model-learning-summary. Writes structured signal to memory/learning/signals/
only when delta from last signal exceeds threshold:
- Win rate change >5pp
- Trade count milestone (50, 100, 200)
- CV accuracy change >3pp

Usage:
    python tools/scripts/crypto_bot_learning_bridge.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = REPO_ROOT / "data" / "crypto_bot_state.json"
LAST_SIGNAL_FILE = REPO_ROOT / "data" / "crypto_bot_last_learning_signal.json"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"

# Milestones for trade count
TRADE_MILESTONES = [50, 100, 200, 500, 1000]

# Delta thresholds
WIN_RATE_DELTA_PP = 5.0
CV_ACCURACY_DELTA_PP = 3.0


def _ascii_safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def _load_state() -> dict:
    """Load latest crypto_bot_state.json."""
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_last_signal() -> dict:
    """Load last signal state for delta comparison."""
    if not LAST_SIGNAL_FILE.is_file():
        return {}
    try:
        return json.loads(LAST_SIGNAL_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_last_signal(state: dict) -> None:
    """Save current values for next delta comparison."""
    LAST_SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_SIGNAL_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _check_thresholds(current: dict, last: dict) -> list[str]:
    """Check if any delta threshold is exceeded. Returns list of reasons."""
    reasons = []

    # Win rate delta
    cur_wr = current.get("win_rate", 0.0)
    last_wr = last.get("win_rate", 0.0)
    if abs(cur_wr - last_wr) >= WIN_RATE_DELTA_PP:
        direction = "up" if cur_wr > last_wr else "down"
        reasons.append(f"Win rate {direction} {abs(cur_wr - last_wr):.1f}pp ({last_wr:.1f}% -> {cur_wr:.1f}%)")

    # Trade count milestones
    cur_closed = current.get("trade_count_closed", 0)
    last_closed = last.get("trade_count_closed", 0)
    for milestone in TRADE_MILESTONES:
        if cur_closed >= milestone > last_closed:
            reasons.append(f"Trade count milestone: {milestone} closed trades reached")

    # CV accuracy delta (from signal-attribution or model-learning-summary)
    raw_api = current.get("raw_api", {})
    attribution = raw_api.get("signal_attribution", {})
    if isinstance(attribution, dict):
        cur_cv = attribution.get("cv_accuracy", attribution.get("model_accuracy"))
        last_cv = last.get("cv_accuracy")
        if cur_cv is not None and last_cv is not None:
            try:
                delta = abs(float(cur_cv) - float(last_cv))
                if delta >= CV_ACCURACY_DELTA_PP:
                    reasons.append(f"CV accuracy changed {delta:.1f}pp")
            except (ValueError, TypeError):
                pass

    return reasons


def _write_signal(current: dict, reasons: list[str]) -> str:
    """Write a learning signal file. Returns the file path."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    # Build signal content
    wr = current.get("win_rate", 0.0)
    pnl = current.get("realized_pnl", 0.0)
    t_open = current.get("trade_count_open", 0)
    t_closed = current.get("trade_count_closed", 0)

    # Top/bottom signals from attribution
    raw_api = current.get("raw_api", {})
    attribution = raw_api.get("signal_attribution", {})
    top_signals = ""
    if isinstance(attribution, dict):
        sources = attribution.get("sources", attribution.get("signal_sources", []))
        if isinstance(sources, list) and sources:
            top_signals = "\n".join(f"- {s}" for s in sources[:5])

    triggers = "; ".join(reasons)

    content = f"""---
date: {today}
category: trading-performance
rating: 7
source: crypto-bot
---

# Crypto-bot performance signal

Trigger: {triggers}

## Metrics
- Win rate: {wr:.1f}%
- Realized P&L: ${pnl:.2f}
- Trades: {t_open} open, {t_closed} closed
"""

    if top_signals:
        content += f"\n## Signal attribution (top sources)\n{top_signals}\n"

    # Find unique filename
    fname = f"{today}_crypto-bot-performance.md"
    fpath = SIGNALS_DIR / fname
    counter = 1
    while fpath.exists():
        counter += 1
        fname = f"{today}_crypto-bot-performance-{counter}.md"
        fpath = SIGNALS_DIR / fname

    fpath.write_text(content, encoding="utf-8")
    return str(fpath)


def main() -> int:
    state = _load_state()
    if not state:
        print(_ascii_safe("No crypto_bot_state.json found. Run collector first."))
        return 1

    if not state.get("status_reachable"):
        print(_ascii_safe("Crypto-bot API was unreachable at last poll. Skipping learning bridge."))
        return 0

    # Freshness check: skip if state is >30 min old
    try:
        poll_dt = datetime.fromisoformat(state.get("timestamp", ""))
        age_min = (datetime.now(timezone.utc) - poll_dt).total_seconds() / 60
        if age_min > 30:
            print(_ascii_safe(f"State file is {age_min:.0f} min old (>30 min). Skipping learning bridge."))
            return 0
    except (ValueError, TypeError):
        print(_ascii_safe("Cannot parse state timestamp. Skipping learning bridge."))
        return 0

    last = _load_last_signal()
    reasons = _check_thresholds(state, last)

    if not reasons:
        print(_ascii_safe("No delta thresholds exceeded. No signal written."))
        return 0

    fpath = _write_signal(state, reasons)
    print(_ascii_safe(f"Learning signal written: {fpath}"))
    print(_ascii_safe(f"Triggers: {'; '.join(reasons)}"))

    # Save current values for next comparison
    raw_api = state.get("raw_api", {})
    attribution = raw_api.get("signal_attribution", {})
    cv_accuracy = None
    if isinstance(attribution, dict):
        cv_accuracy = attribution.get("cv_accuracy", attribution.get("model_accuracy"))

    _save_last_signal({
        "win_rate": state.get("win_rate", 0.0),
        "trade_count_closed": state.get("trade_count_closed", 0),
        "cv_accuracy": cv_accuracy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return 0


if __name__ == "__main__":
    sys.exit(main())
