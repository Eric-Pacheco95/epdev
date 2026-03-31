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

    # Post session digest to #epdev — only if enough time has passed since last post.
    # Old approach used signal file mtime as a session-duration proxy, but signals
    # accumulate across sessions so every short restart looked like a long session.
    # New approach: cooldown-based — skip if last session-end post was < 15 min ago.
    _COOLDOWN_FILE = REPO_ROOT / "data" / ".last_session_end_post"
    _COOLDOWN_SECONDS = 900  # 15 minutes

    should_post_session = True
    try:
        if _COOLDOWN_FILE.is_file():
            last_post_ts = float(_COOLDOWN_FILE.read_text(encoding="utf-8").strip())
            elapsed = now.timestamp() - last_post_ts
            if elapsed < _COOLDOWN_SECONDS:
                should_post_session = False
    except (ValueError, OSError):
        pass  # corrupted file — allow post

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

    # Check for incomplete ISC items in active PRDs
    incomplete_iscs: dict[str, int] = {}
    if WORK_DIR.is_dir():
        for prd in WORK_DIR.glob("*/PRD.md"):
            try:
                prd_text = prd.read_text(encoding="utf-8")
            except OSError:
                continue
            unchecked = sum(
                1 for line in prd_text.splitlines()
                if re.match(r"^\s*-\s+\[ \]\s+", line)
            )
            if unchecked > 0:
                incomplete_iscs[prd.parent.name] = unchecked

    if should_post_session:
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        msg = f":brain: *Jarvis session ended* -- {ts}\n"
        msg += f"Stop reason: `{stop_reason}` | Learning signals on file: `{count}`"
        if count > 0:
            msg += "\n_Run `/learning-capture` to process signals._"
        if incomplete_iscs:
            isc_parts = [f"{proj}: {n} remaining" for proj, n in incomplete_iscs.items()]
            msg += f"\n:warning: *Incomplete ISCs:* {', '.join(isc_parts)}"
        posted = notify(msg)
        if posted:
            # Record timestamp to enforce cooldown
            try:
                _COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
                _COOLDOWN_FILE.write_text(str(now.timestamp()), encoding="utf-8")
            except OSError:
                pass

    sys.exit(0)


if __name__ == "__main__":
    main()
