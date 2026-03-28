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


def _ascii_safe(text: str) -> str:
    """Replace common Unicode chars with ASCII equivalents for Windows cp1252 safety."""
    result = (
        text
        .replace("\u2014", "--")   # em-dash
        .replace("\u2013", "-")    # en-dash
        .replace("\u2018", "'")    # left single quote
        .replace("\u2019", "'")    # right single quote
        .replace("\u201c", '"')    # left double quote
        .replace("\u201d", '"')    # right double quote
        .replace("\u2026", "...")  # ellipsis
        .replace("\u2265", ">=")   # >=
        .replace("\u2264", "<=")   # <=
        .replace("\u2022", "-")    # bullet
        .replace("\u2192", "->")   # right arrow
        .replace("\u2190", "<-")   # left arrow
    )
    # Catch-all: replace any remaining non-ASCII chars with ?
    return result.encode("ascii", errors="replace").decode("ascii")
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SECURITY_DIR = REPO_ROOT / "history" / "security"
TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
VALUE_FILE = REPO_ROOT / "data" / "autonomous_value.jsonl"

# Dynamic synthesis threshold:
#   >= 20 signals: always trigger (hard ceiling)
#   >= 10 signals AND >= 48h since last synthesis: enough data + time
#   >= 8 signals AND >= 72h since last synthesis: stale signals lose context
SYNTHESIS_HARD_CEILING = 20
SYNTHESIS_TIERS = [
    (10, 48),  # (min_signals, min_hours_since_last_synthesis)
    (8, 72),
]


def _hours_since_last_synthesis() -> float:
    """Return hours since newest synthesis file was modified, or inf if none."""
    if not SYNTHESIS_DIR.is_dir():
        return float("inf")
    newest = None
    for p in SYNTHESIS_DIR.iterdir():
        if p.is_file() and p.suffix == ".md" and not p.name.startswith("miessler"):
            mtime = p.stat().st_mtime
            if newest is None or mtime > newest:
                newest = mtime
    if newest is None:
        return float("inf")
    elapsed = (datetime.now(timezone.utc) - datetime.fromtimestamp(newest, tz=timezone.utc)).total_seconds()
    return elapsed / 3600


def _synthesis_due(n_signals: int) -> tuple[bool, str]:
    """Check if synthesis should be triggered. Returns (due, reason)."""
    if n_signals >= SYNTHESIS_HARD_CEILING:
        return True, f"signal count ({n_signals}) >= hard ceiling ({SYNTHESIS_HARD_CEILING})"
    hours = _hours_since_last_synthesis()
    for min_signals, min_hours in SYNTHESIS_TIERS:
        if n_signals >= min_signals and hours >= min_hours:
            return True, f"{n_signals} signals + {hours:.0f}h since last synthesis (threshold: {min_signals} signals / {min_hours}h)"
    return False, ""


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
            if line.startswith("## Current Focus"):
                in_section = True
                lines.append(line)
            elif line.startswith("## ") and in_section:
                in_section = False  # stop after Current Focus — skip mood/energy
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


# -- Autonomous value tracking -----------------------------------------------

MORNING_BRIEF_PHRASES = [
    "from today's morning slack brief",
    "from the morning feed",
    "from the morning brief",
    "that idea from overnight",
    "morning briefing",
    "morning proposal",
]


def _check_morning_brief_reference(user_prompt: str) -> None:
    """Check if user's prompt references a morning briefing proposal.

    If a match is found, update the most recent unacted proposal in
    autonomous_value.jsonl to acted_on=true.
    """
    if not user_prompt or not VALUE_FILE.is_file():
        return

    prompt_lower = user_prompt.lower()
    matched = any(phrase in prompt_lower for phrase in MORNING_BRIEF_PHRASES)
    if not matched:
        return

    # Find today's proposals and mark the first unacted one
    today = datetime.now().strftime("%Y-%m-%d")
    lines = VALUE_FILE.read_text(encoding="utf-8").strip().splitlines()
    updated = False
    new_lines = []

    for line in lines:
        if not updated:
            try:
                entry = json.loads(line)
                if (entry.get("date") == today
                        and not entry.get("acted_on", False)):
                    entry["acted_on"] = True
                    entry["reference_session"] = datetime.now().isoformat()
                    line = json.dumps(entry)
                    updated = True
            except (json.JSONDecodeError, KeyError):
                pass
        new_lines.append(line)

    if updated:
        VALUE_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# -- Open validations reminder -----------------------------------------------

def _check_open_validations() -> list[str]:
    """Check for BUILT items awaiting validation in the tasklist."""
    if not TASKLIST.is_file():
        return []

    text = TASKLIST.read_text(encoding="utf-8", errors="replace")
    validations = []

    # Look for the Open Validations section
    in_section = False
    for line in text.splitlines():
        if "Open Validations" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break  # end of section
        if in_section and line.strip().startswith("- [ ]"):
            # Extract just the bold title
            m = re.match(r"^- \[ \] \*\*(.+?)\*\*", line.strip())
            if m:
                validations.append(m.group(1))

    return validations


_PROMPT_TS_FILE = Path(__file__).resolve().parents[2] / ".claude" / "prompt_ts.json"


def _stamp_prompt_ts() -> None:
    """Write current UTC timestamp so hook_notification.py can gate on elapsed time."""
    import time
    try:
        _PROMPT_TS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROMPT_TS_FILE.write_text(json.dumps({"ts": time.time()}), encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    _stamp_prompt_ts()

    # Read user prompt from stdin (hook receives JSON with prompt content)
    user_prompt = ""
    try:
        if not sys.stdin.isatty():
            hook_input = sys.stdin.read()
            if hook_input.strip():
                try:
                    data = json.loads(hook_input)
                    user_prompt = data.get("prompt", data.get("input", ""))
                except json.JSONDecodeError:
                    user_prompt = hook_input
    except Exception:
        pass

    # Check for morning brief references (autonomous value tracking)
    if user_prompt:
        _check_morning_brief_reference(user_prompt)

    now = datetime.now().astimezone()
    print()
    print("=" * 60)
    print("  EPDEV Jarvis - session start")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)
    print()

    # TELOS context (focus only — mood/energy omitted to save context)
    print("TELOS Status")
    print("-" * 40)
    print(_ascii_safe(_load_telos_status()))
    print()

    # Active tasks
    print("Active tasks (unchecked)")
    print("-" * 40)
    if TASKLIST.is_file():
        tasks = _unchecked_tasks(TASKLIST.read_text(encoding="utf-8", errors="replace"))
        if tasks:
            for t in tasks[:5]:  # Cap at 5 — top priorities only
                print(f"  [ ] {_ascii_safe(t)}")
            if len(tasks) > 5:
                print(f"  ... and {len(tasks) - 5} more")
        else:
            print("  (none)")
    else:
        print(f"  (missing: {TASKLIST})")
    print()

    # Signal and failure counts
    n_signals = _count_files(SIGNALS_DIR)
    n_failures = _count_files(FAILURES_DIR)
    print(f"Learning signals: {n_signals} | Failures logged: {n_failures}")
    due, reason = _synthesis_due(n_signals)
    if due:
        print(f"  >>> Synthesis due: {reason}")
        print("      Run /synthesize-signals when ready.")
    print()

    # Open validations reminder
    validations = _check_open_validations()
    if validations:
        print("Open validations (BUILT -- awaiting confirmation)")
        print("-" * 40)
        for v in validations:
            print(f"  >>> {_ascii_safe(v)}")
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

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
    sys.exit(0)
