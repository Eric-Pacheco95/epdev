#!/usr/bin/env python3
"""Session start hook: banner, active tasks, signals, synthesis reminder, recent security."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
SECURITY_DIR = REPO_ROOT / "history" / "security"
SYNTHESIS_TRIGGER = 10


def _unchecked_tasks(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)-\s+\[([ xX])\]\s+(.*)$", line)
        if m and m.group(2).lower() != "x":
            lines.append(m.group(3).strip())
    return lines


def _count_signal_files() -> int:
    if not SIGNALS_DIR.is_dir():
        return 0
    return sum(1 for p in SIGNALS_DIR.iterdir() if p.is_file() and p.suffix == ".md")


def _recent_security_events(days: int = 7) -> list[str]:
    if not SECURITY_DIR.is_dir():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events: list[tuple[float, str]] = []
    for p in SECURITY_DIR.glob("*.md"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if datetime.fromtimestamp(mtime, tz=timezone.utc) >= cutoff:
            events.append((mtime, p.name))
    events.sort(reverse=True)
    return [f"  - {name}" for _, name in events[:20]]


def main() -> None:
    now = datetime.now().astimezone()
    print()
    print("=" * 60)
    print("  EPDEV Jarvis - session start")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)
    print()

    print("Active tasks (unchecked)")
    print("-" * 40)
    if TASKLIST.is_file():
        tasks = _unchecked_tasks(TASKLIST.read_text(encoding="utf-8", errors="replace"))
        if tasks:
            for t in tasks:
                print(f"  [ ] {t}")
        else:
            print("  (none)")
    else:
        print(f"  (missing: {TASKLIST})")
    print()

    n_signals = _count_signal_files()
    print(f"Learning signals pending (files in memory/learning/signals/): {n_signals}")
    if n_signals > SYNTHESIS_TRIGGER:
        print(
            f"  >>> Reminder: signal count exceeds synthesis threshold ({SYNTHESIS_TRIGGER})."
        )
        print("      Run synthesis (memory/learning/synthesis/) when ready.")
    print()

    print("Recent security events (last 7 days, history/security/)")
    print("-" * 40)
    sec = _recent_security_events()
    if sec:
        print("\n".join(sec))
    else:
        print("  (none logged in this window)")
    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
    sys.exit(0)
