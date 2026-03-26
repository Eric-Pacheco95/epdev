#!/usr/bin/env python3
"""Stop hook: auto-capture session summary, refresh tasklist state, log session end.

Runs non-interactively at session end — no user input required.
Reads session context from stdin JSON provided by Claude Code.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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
    date_str = now.strftime("%Y-%m-%d")

    # Try to read stop context from stdin (Claude Code provides session info)
    stop_reason = "session-end"
    try:
        data = json.load(sys.stdin)
        stop_reason = data.get("stop_reason", "end_turn") or "end_turn"
    except (json.JSONDecodeError, EOFError):
        pass

    # Auto-log a lightweight session-end signal (no rating required)
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(f"session-end-{stop_reason}")
    path = _unique_path(SIGNALS_DIR, f"{date_str}_{slug}")

    body = f"""# Signal: Session ended ({stop_reason})
- Date: {date_str}
- Rating: (pending - rate with hook_learning_capture.py)
- Category: pattern
- Observation: Session ended via {stop_reason}. Review transcript and rate.
- Implication: Rate this session to feed the learning system.
"""
    path.write_text(body, encoding="utf-8")

    count = _update_signal_count()

    # Quick status to stderr (visible in hook output, doesn't interfere with JSON)
    print(f"Session captured. Signals: {count}. Rate with: python tools/scripts/hook_learning_capture.py --rating N \"description\"", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
