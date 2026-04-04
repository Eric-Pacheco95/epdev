#!/usr/bin/env python3
"""Session start hook: banner, TELOS status, active tasks, signals, synthesis reminder, recent security.

Loads rich context so Jarvis starts every session with full awareness.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
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
ABSORBED_DIR = REPO_ROOT / "memory" / "learning" / "absorbed"
VALUE_FILE = REPO_ROOT / "data" / "autonomous_value.jsonl"
G2_STREAK_FILE = REPO_ROOT / "data" / "g2_streak.json"
CRYPTO_BOT_ROOT = Path("C:/Users/ericp/Github/crypto-bot")

# Signal filename keywords that indicate non-G2 activity
NON_G2_SIGNAL_KEYWORDS = [
    # G1: financial independence / side hustles
    "crypto", "trading", "revenue", "side-hustle", "income", "business",
    # G3: guitar / music
    "guitar", "music", "band", "practice", "song", "chord", "improv",
    # G4: health / gym
    "gym", "workout", "health", "fitness", "exercise",
    # G5: bank automation
    "bank-auto", "rpa", "corporate",
    # G6: self-discovery / balance
    "therapy", "balance", "social",
]

# Dynamic synthesis threshold:
#   >= 35 signals: always trigger (hard ceiling; raised from 20 for auto-signal producers)
#   >= 15 signals AND >= 48h since last synthesis: enough data + time
#   >= 10 signals AND >= 72h since last synthesis: stale signals lose context
SYNTHESIS_HARD_CEILING = 35
SYNTHESIS_TIERS = [
    (15, 48),  # (min_signals, min_hours_since_last_synthesis)
    (10, 72),
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
    """Check for BUILT items awaiting validation in the tasklist.

    Scans both the "Validate What's Built" tier (Priority Backlog Tier 1)
    and any remaining "Open Validations" section for unchecked items.
    Also picks up any Phase 4D items marked BUILT -- awaiting validation.
    """
    if not TASKLIST.is_file():
        return []

    text = TASKLIST.read_text(encoding="utf-8", errors="replace")
    validations = []

    in_section = False
    for line in text.splitlines():
        # Match both the old section name and the new Tier 1 header
        if "Open Validations" in line or "Validate What" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break  # end of section
        # Also stop at the next tier header
        if in_section and line.startswith("### Tier"):
            break
        if in_section and line.strip().startswith("- [ ]"):
            m = re.match(r"^- \[ \] \*\*(.+?)\*\*", line.strip())
            if m:
                validations.append(m.group(1))

    # Also scan for inline BUILT -- awaiting validation items anywhere
    for line in text.splitlines():
        if "BUILT -- awaiting validation" in line and "- [ ]" in line:
            m = re.match(r"^-\s*\[ \]\s*\*\*(.+?)\*\*", line.strip())
            if m:
                title = m.group(1)
                if title not in validations:
                    validations.append(title)

    return validations


def _count_pending_absorb_proposals() -> int:
    """Count absorbed files with status: PENDING in YAML frontmatter."""
    if not ABSORBED_DIR.is_dir():
        return 0
    count = 0
    for p in ABSORBED_DIR.iterdir():
        if not p.is_file() or p.suffix != ".md":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            # Check YAML frontmatter for status: PENDING
            if text.startswith("---"):
                end = text.find("---", 3)
                if end > 0:
                    front = text[3:end]
                    if re.search(r"^status:\s*PENDING", front, re.MULTILINE):
                        count += 1
        except OSError:
            continue
    return count


def _has_non_g2_activity_today() -> bool:
    """Return True if today has any non-G2 signal file or crypto-bot commit."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check signal filenames for non-G2 keywords
    if SIGNALS_DIR.is_dir():
        for p in SIGNALS_DIR.glob(f"{today_str}_*.md"):
            name_lower = p.name.lower()
            if any(kw in name_lower for kw in NON_G2_SIGNAL_KEYWORDS):
                return True

    # Check crypto-bot repo for today's commits
    if CRYPTO_BOT_ROOT.is_dir():
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"--since={today_str}"],
                capture_output=True, text=True, encoding="utf-8",
                timeout=5, cwd=str(CRYPTO_BOT_ROOT),
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass

    return False


def _g2_streak_check() -> list[str]:
    """Warn if G2-only streak >= 5 consecutive days. Updates state once per day."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    state: dict = {"last_checked_date": "", "current_streak_days": 0, "last_non_g2_date": ""}
    if G2_STREAK_FILE.is_file():
        try:
            state = json.loads(G2_STREAK_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Update once per day only
    if state.get("last_checked_date") != today_str:
        if _has_non_g2_activity_today():
            state["current_streak_days"] = 0
            state["last_non_g2_date"] = today_str
        else:
            state["current_streak_days"] = state.get("current_streak_days", 0) + 1
        state["last_checked_date"] = today_str
        try:
            G2_STREAK_FILE.parent.mkdir(parents=True, exist_ok=True)
            G2_STREAK_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError:
            pass

    streak = state.get("current_streak_days", 0)
    last_non_g2 = state.get("last_non_g2_date") or "none recorded"

    if streak >= 5:
        return [
            f"  >>> G2-only streak: {streak} days (last non-G2 activity: {last_non_g2})",
            "      S14: confirm G1/G3/G4 have capture paths before continuing G2 work",
        ]
    return []


_PROMPT_TS_FILE = Path(__file__).resolve().parents[2] / ".claude" / "prompt_ts.json"


# -- Git safety for parallel sessions ----------------------------------------

def _git_safety_check() -> list[str]:
    """Detect parallel Claude sessions and uncommitted changes.

    Returns warning lines (empty list = nothing to warn about).
    """
    warnings: list[str] = []

    # 1. Count parallel claude.exe processes (excluding this hook's ancestry)
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq claude.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0:
            # Each running claude.exe produces a CSV line
            sessions = [
                ln for ln in result.stdout.strip().splitlines()
                if "claude.exe" in ln.lower()
            ]
            if len(sessions) >= 2:
                warnings.append(
                    f"  >>> {len(sessions)} Claude sessions detected -- "
                    "risk of conflicting edits on the same files"
                )
                warnings.append(
                    "      TIP: consider working on separate branches "
                    "(git checkout -b feature/xxx) per terminal"
                )
    except (OSError, subprocess.TimeoutExpired):
        pass

    # 2. Check HTTPS connection count (network impact from MCP servers)
    try:
        result = subprocess.run(
            ["netstat", "-n"],
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        if result.returncode == 0:
            https_count = sum(
                1 for ln in result.stdout.splitlines()
                if "ESTABLISHED" in ln and ":443" in ln
            )
            if https_count >= 70:
                warnings.append(
                    f"  >>> {https_count} HTTPS connections active -- "
                    "CRITICAL network impact; close idle Claude sessions immediately"
                )
            elif https_count >= 40:
                warnings.append(
                    f"  >>> {https_count} HTTPS connections active -- "
                    "elevated network usage; consider closing idle sessions"
                )
    except (OSError, subprocess.TimeoutExpired):
        pass

    # 3. Check for uncommitted changes
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8",
            timeout=5, cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            changed = [
                ln.strip() for ln in result.stdout.strip().splitlines()
                if ln.strip()
            ]
            n_changed = len(changed)
            if n_changed > 0:
                warnings.append(
                    f"  >>> {n_changed} uncommitted change(s) in working tree"
                )
                # Show up to 5 changed files
                for ln in changed[:5]:
                    warnings.append(f"      {ln}")
                if n_changed > 5:
                    warnings.append(f"      ... and {n_changed - 5} more")
    except (OSError, subprocess.TimeoutExpired):
        pass

    return warnings


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

    # Git safety check (parallel sessions + uncommitted changes)
    git_warnings = _git_safety_check()
    if git_warnings:
        print("Git Safety")
        print("-" * 40)
        for w in git_warnings:
            print(_ascii_safe(w))
        print()

    # G2 streak warning (fires at >= 5 consecutive G2-only days)
    g2_warnings = _g2_streak_check()
    if g2_warnings:
        print("Goal Balance Warning")
        print("-" * 40)
        for w in g2_warnings:
            print(_ascii_safe(w))
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

    # Pending /absorb TELOS proposals
    pending = _count_pending_absorb_proposals()
    if pending:
        print(f"Pending /absorb TELOS proposals: {pending}")
        print("-" * 40)
        print(f"  >>> {pending} TELOS proposal(s) pending from /absorb -- run `/absorb --review`")
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
