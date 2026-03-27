#!/usr/bin/env python3
"""Session start hook: banner, TELOS status, active tasks, signals, synthesis reminder, recent security.

Loads rich context so Jarvis starts every session with full awareness.
"""

from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure stdout handles full Unicode regardless of Windows console code page
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SECURITY_DIR = REPO_ROOT / "history" / "security"
TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SYNTHESIS_TRIGGER = 10


def _unchecked_tasks(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)-\s+\[([ xX])\]\s+(.*)$", line)
        if m and m.group(2).lower() != "x":
            lines.append(m.group(3).strip())
    return lines


def _count_files(directory: Path, ext: str = ".md") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.iterdir() if p.is_file() and p.suffix == ext)


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
    return [f"  - {name}" for _, name in events[:10]]


def _load_telos_status() -> str:
    """Load key TELOS context for session awareness."""
    lines: list[str] = []

    # Current status
    status_path = TELOS_DIR / "STATUS.md"
    if status_path.is_file():
        text = status_path.read_text(encoding="utf-8", errors="replace")
        # Extract just the Current Focus and Active Mood sections
        in_section = False
        for line in text.splitlines():
            if line.startswith("## Current Focus") or line.startswith("## Active Mood"):
                in_section = True
                lines.append(line)
            elif line.startswith("## ") and in_section:
                in_section = False
            elif in_section and line.strip():
                lines.append(line)

    # Active projects
    projects_path = TELOS_DIR / "PROJECTS.md"
    if projects_path.is_file():
        text = projects_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "|" in line and "active" in line.lower():
                lines.append(f"  Active project: {line.strip()}")

    # Recent learnings count
    learned_path = TELOS_DIR / "LEARNED.md"
    if learned_path.is_file():
        text = learned_path.read_text(encoding="utf-8", errors="replace")
        entry_count = text.count("- 202")  # Count date-prefixed entries
        if entry_count > 0:
            lines.append(f"  LEARNED.md entries: {entry_count}")

    return "\n".join(lines) if lines else "(no TELOS status loaded)"


def main() -> None:
    now = datetime.now().astimezone()
    print()
    print("=" * 60)
    print("  EPDEV Jarvis - session start")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)
    print()

    # TELOS context
    print("TELOS Status")
    print("-" * 40)
    print(_load_telos_status())
    print()

    # Active tasks
    print("Active tasks (unchecked)")
    print("-" * 40)
    if TASKLIST.is_file():
        tasks = _unchecked_tasks(TASKLIST.read_text(encoding="utf-8", errors="replace"))
        if tasks:
            for t in tasks[:15]:  # Cap at 15 to avoid overwhelming
                print(f"  [ ] {t}")
            if len(tasks) > 15:
                print(f"  ... and {len(tasks) - 15} more")
        else:
            print("  (none)")
    else:
        print(f"  (missing: {TASKLIST})")
    print()

    # Signal and failure counts
    n_signals = _count_files(SIGNALS_DIR)
    n_failures = _count_files(FAILURES_DIR)
    print(f"Learning signals: {n_signals} | Failures logged: {n_failures}")
    if n_signals > SYNTHESIS_TRIGGER:
        print(
            f"  >>> Signal count exceeds synthesis threshold ({SYNTHESIS_TRIGGER})."
        )
        print("      Run synthesis when ready (or /learning-capture to process).")
    print()

    # Recent security events
    print("Recent security events (last 7 days)")
    print("-" * 40)
    sec = _recent_security_events()
    if sec:
        print("\n".join(sec))
    else:
        print("  (none logged)")
    print()

    # Skill registry grouped by use case
    print("Available Skills")
    print("-" * 40)
    print("  Orchestrate: /delegation  /workflow-engine  /project-orchestrator  /spawn-agent")
    print("  Thinking:    /first-principles  /red-team  /analyze-claims  /find-logical-fallacies")
    print("  Creating:    /create-prd  /create-pattern  /create-summary  /improve-prompt")
    print("  Learning:    /extract-wisdom  /learning-capture  /synthesize-signals  /telos-report")
    print("  Identity:    /telos-update")
    print("  Security:    /security-audit  /threat-model  /review-code")
    print("  System:      /self-heal  /update-steering-rules")
    print("  Mobile:      /voice-capture")
    print()
    print("  Tip: Just describe your task — /delegation will route it to the right skill")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
    sys.exit(0)
