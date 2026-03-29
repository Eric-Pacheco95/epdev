#!/usr/bin/env python3
"""Stop hook: auto-capture session summary, refresh tasklist state, log session end.

Runs non-interactively at session end — no user input required.
Reads session context from stdin JSON provided by Claude Code.
"""

from __future__ import annotations

import json
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


def _slugify(title: str) -> str:
    import re
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
    try:
        data = json.load(sys.stdin)
        stop_reason = data.get("stop_reason", "end_turn") or "end_turn"
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

    # Post session digest to #epdev — only for sessions longer than 10 minutes
    # Short sessions (quick questions, typos, restarts) are noise
    session_start = None
    try:
        data_reread = {}
        # Check if session duration info is available from stdin data
        # Fall back to signal file timestamps as a proxy for session length
        oldest_signal_today = None
        if SIGNALS_DIR.is_dir():
            today_str = now.strftime("%Y-%m-%d")
            for p in SIGNALS_DIR.iterdir():
                if p.is_file() and p.name.startswith(today_str):
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                    if oldest_signal_today is None or mtime < oldest_signal_today:
                        oldest_signal_today = mtime
        # Estimate session duration from oldest signal written today vs now
        session_minutes = 0
        if oldest_signal_today:
            session_minutes = (now - oldest_signal_today).total_seconds() / 60
    except Exception:
        session_minutes = 0

    if session_minutes >= 10:
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f":brain: *Jarvis session ended* -- {ts}\n"
            f"Stop reason: `{stop_reason}` | Learning signals on file: `{count}`"
            f" | ~{int(session_minutes)}min session"
        )
        if count > 0:
            msg += "\n_Run `/learning-capture` to process signals._"
        notify(msg)

    sys.exit(0)


if __name__ == "__main__":
    main()
