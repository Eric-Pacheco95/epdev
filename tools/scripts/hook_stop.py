#!/usr/bin/env python3
"""Stop hook: auto-capture session summary, refresh tasklist state, log session end.

Runs non-interactively at session end — no user input required.
Reads session context from stdin JSON provided by Claude Code.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add repo root to path so slack_notify is importable
_REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))
from tools.scripts.slack_notify import notify  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
META_PATH = REPO_ROOT / "memory" / "learning" / "_signal_meta.json"
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
WORK_DIR = REPO_ROOT / "memory" / "work"


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return (s[:60] if s else "session-end") or "session-end"


def _unique_path(directory: Path, stem: str) -> Path:
    base = directory / f"{stem}.md"
    if not base.exists():
        return base
    n = 2
    while True:
        p = directory / f"{stem}_{n}.md"
        if not p.exists():
            return p
        n += 1


def _update_signal_count() -> int:
    count = 0
    if SIGNALS_DIR.is_dir():
        count = sum(1 for p in SIGNALS_DIR.iterdir() if p.is_file() and p.suffix == ".md")
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "signal_file_count": count,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return count


def main() -> None:
    now = datetime.now(timezone.utc)

    # Try to read stop context from stdin (Claude Code provides session info)
    stop_reason = "session-end"
    session_id = now.strftime("%Y%m%d%H%M%S")
    try:
        data = json.load(sys.stdin)
        stop_reason = data.get("stop_reason", "end_turn") or "end_turn"
        session_id = data.get("session_id", session_id)
    except (json.JSONDecodeError, EOFError):
        pass

    # Update signal count metadata (don't create stub signals — use /learning-capture skill instead)
    count = _update_signal_count()

    # Log session end to stderr (visible in hook output)
    print(f"Session ended ({stop_reason}). Signals on file: {count}. Run /learning-capture to capture learnings.", file=sys.stderr)

    # Run ISC engine heartbeat with --session-end flag
    heartbeat_script = REPO_ROOT / "tools" / "scripts" / "jarvis_heartbeat.py"
    if heartbeat_script.is_file():
        try:
            subprocess.run(
                [sys.executable, str(heartbeat_script), "--session-end", "--quiet"],
                timeout=15,
                capture_output=True,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"Heartbeat skipped: {exc}", file=sys.stderr)

    # Write session_costs row to manifest DB
    try:
        from tools.scripts.manifest_db import write_session_cost
        write_session_cost(
            session_id=session_id,
            date=now.strftime("%Y-%m-%d"),
            session_type="interactive",
        )
    except Exception:
        pass  # graceful fallback

    # Session-end Slack notifications to #epdev are disabled (too noisy)

    sys.exit(0)


if __name__ == "__main__":
    main()
