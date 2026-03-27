#!/usr/bin/env python3
"""Jarvis heartbeat runner — stdlib only, no external deps.

Collects a lightweight system snapshot, diffs against the last run,
and posts a digest to #epdev if anything notable changed.

Usage:
    python tools/scripts/jarvis_heartbeat.py [--quiet]

    --quiet   Suppress Slack post; still writes snapshot file.

Environment:
    SLACK_BOT_TOKEN  xoxb-... required for Slack posts (see slack_notify.py)

Outputs:
    memory/work/jarvis/heartbeat_latest.json   — latest snapshot (overwritten each run)
    memory/work/jarvis/heartbeat_history.jsonl — append-only log of every run
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.slack_notify import notify, EPDEV  # noqa: E402

SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SECURITY_DIR = REPO_ROOT / "history" / "security"
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
STATE_DIR = REPO_ROOT / "memory" / "work" / "jarvis"
LATEST_PATH = STATE_DIR / "heartbeat_latest.json"
HISTORY_PATH = STATE_DIR / "heartbeat_history.jsonl"


def _count_files(directory: Path, ext: str = ".md") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.iterdir() if p.is_file() and p.suffix == ext)


def _count_open_tasks(tasklist: Path) -> int:
    import re
    if not tasklist.is_file():
        return 0
    count = 0
    for line in tasklist.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*-\s+\[([ ])\]", line)
        if m:
            count += 1
    return count


def collect_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signals": _count_files(SIGNALS_DIR),
        "failures": _count_files(FAILURES_DIR),
        "security_events": _count_files(SECURITY_DIR),
        "open_tasks": _count_open_tasks(TASKLIST),
    }


def load_previous() -> dict | None:
    if not LATEST_PATH.is_file():
        return None
    try:
        return json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_snapshot(snap: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_PATH.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap) + "\n")


def build_message(snap: dict, prev: dict | None) -> str:
    ts = snap["ts"]
    lines = [f":heartbeat: *Jarvis heartbeat* — `{ts}`"]
    lines.append(
        f"Signals: `{snap['signals']}` | Failures: `{snap['failures']}` | "
        f"Security events: `{snap['security_events']}` | Open tasks: `{snap['open_tasks']}`"
    )

    if prev:
        deltas = []
        for key in ("signals", "failures", "security_events", "open_tasks"):
            diff = snap[key] - prev[key]
            if diff != 0:
                arrow = "+" if diff > 0 else ""
                deltas.append(f"{key}: {arrow}{diff}")
        if deltas:
            lines.append("Changes since last run: " + ", ".join(deltas))
        else:
            lines.append("_No changes since last run._")
    else:
        lines.append("_First heartbeat — no previous snapshot to diff._")

    if snap["failures"] > 0:
        lines.append(f":warning: `{snap['failures']}` failure(s) logged — review `memory/learning/failures/`")
    if snap["signals"] >= 10:
        lines.append(f":bulb: `{snap['signals']}` signals accumulated — consider running `/synthesize-signals`")

    return "\n".join(lines)


def main() -> None:
    quiet = "--quiet" in sys.argv

    snap = collect_snapshot()
    prev = load_previous()
    save_snapshot(snap)

    msg = build_message(snap, prev)
    print(msg)  # always print to stdout for CLI visibility

    if not quiet:
        ok = notify(msg, EPDEV)
        if not ok:
            print("(Slack post skipped — set SLACK_BOT_TOKEN to enable)", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
