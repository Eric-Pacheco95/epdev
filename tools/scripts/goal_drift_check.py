#!/usr/bin/env python3
"""Goal drift (G1 / G2) — alert when learning signals show no recent capture.

Scans memory/learning/signals/*.md mtime + keyword hit in head bytes.
Scope: G1 and G2 only (per tasklist). Threshold: JARVIS_GOAL_DRIFT_DAYS (default 14).

Posts to Slack (#epdev routine) at most once per goal per JARVIS_GOAL_DRIFT_ALERT_COOLDOWN_DAYS
(default 7). State: data/goal_drift_state.json (gitignored).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SIGNALS = ROOT / "memory" / "learning" / "signals"
STATE_FILE = ROOT / "data" / "goal_drift_state.json"
LOG_DIR = ROOT / "data" / "logs"

G1_RE = re.compile(
    r"\b(G1|financial|revenue|substack|side hustle|P&L|pnl|crypto|trading)\b",
    re.I,
)
G2_RE = re.compile(
    r"\b(G2|Jarvis|PAI|Miessler|skill pipeline|/research|synthesis|learning signal|"
    r"signal captured|TELOS)\b",
    re.I,
)

HEAD_BYTES = 8000


def _last_signal_date(goal: str) -> datetime | None:
    pat = G1_RE if goal == "G1" else G2_RE
    latest: datetime | None = None
    if not SIGNALS.is_dir():
        return None
    for p in sorted(SIGNALS.glob("*.md")):
        try:
            st = p.stat()
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        except OSError:
            continue
        try:
            chunk = p.read_text(encoding="utf-8", errors="replace")[:HEAD_BYTES]
        except OSError:
            continue
        if pat.search(chunk):
            if latest is None or mtime > latest:
                latest = mtime
    return latest


def _load_state() -> dict:
    if not STATE_FILE.is_file():
        return {"alerts": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"alerts": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    threshold = int(os.environ.get("JARVIS_GOAL_DRIFT_DAYS", "14"))
    cooldown = int(os.environ.get("JARVIS_GOAL_DRIFT_ALERT_COOLDOWN_DAYS", "7"))
    now = datetime.now(timezone.utc)

    lines: list[str] = []
    alerts_sent: list[str] = []

    state = _load_state()
    alerts = state.setdefault("alerts", {})

    for goal in ("G1", "G2"):
        last = _last_signal_date(goal)
        if last is None:
            age_days = 999
            last_s = "(no matching signals found)"
        else:
            age_days = (now - last).days
            last_s = last.strftime("%Y-%m-%d")

        lines.append(f"{goal}: last_capture={last_s} age_days={age_days} threshold={threshold}")

        if age_days < threshold:
            continue

        prev_raw = alerts.get(goal)
        if prev_raw:
            try:
                prev = datetime.fromisoformat(prev_raw.replace("Z", "+00:00"))
                if (now - prev).days < cooldown:
                    lines.append(f"  skip alert: cooldown active for {goal}")
                    continue
            except ValueError:
                pass

        try:
            from tools.scripts.slack_notify import notify
        except ImportError:
            print("goal_drift_check: slack_notify import failed", file=sys.stderr)
            return 1

        msg = (
            f":dart: *Goal drift* — `{goal}` has no signal capture in {age_days} days "
            f"(threshold {threshold}d). Last matching signal: {last_s}. "
            f"Consider a /learning-capture or TELOS-aligned task."
        )
        if notify(msg, severity="routine"):
            alerts[goal] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            alerts_sent.append(goal)

    if alerts_sent:
        _save_state(state)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"goal_drift_{now.strftime('%Y-%m-%d')}.log"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
