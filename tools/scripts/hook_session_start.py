#!/usr/bin/env python3
"""Session start hook: banner, TELOS status, active tasks, signals, synthesis reminder, recent security.

Loads rich context so Jarvis starts every session with full awareness.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
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
    return result


_W = 58  # inner box width


def _box_line(text: str = "") -> str:
    return f"║  {text:<{_W - 2}}║"


def _section(label: str) -> str:
    bar = "─" * max(2, _W - len(label) - 3)
    return f"\n◈ {label} {bar}"


CLAUDE_PROJ_DIR = Path.home() / ".claude" / "projects" / str(REPO_ROOT).replace("\\", "-").replace(":", "-")
CONTEXT_LIMIT_TOKENS = 200_000

# Empirical token weights per JSONL entry type (from session analysis 2026-04-16)
_CTX_TOKENS_PER_TYPE = {
    "user": 2_500,
    "assistant": 1_500,
    "attachment": 1_200,
    "system": 800,
}

TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SECURITY_DIR = REPO_ROOT / "history" / "security"
TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
ABSORBED_DIR = REPO_ROOT / "memory" / "learning" / "absorbed"
LINEAGE_FILE = REPO_ROOT / "data" / "signal_lineage.jsonl"
VALUE_FILE = REPO_ROOT / "data" / "autonomous_value.jsonl"
G2_STREAK_FILE = REPO_ROOT / "data" / "g2_streak.json"
BANNER_CACHE_FILE = REPO_ROOT / "data" / "banner_cache.json"
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


def _synthesized_signal_names() -> set:
    """Read lineage JSONL to get set of signal filenames already consumed by synthesis."""
    if not LINEAGE_FILE.is_file():
        return set()
    names = set()
    try:
        for line in LINEAGE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                # Lineage rows use "signals" array of filenames
                for name in row.get("signals", []):
                    if name:
                        names.add(name)
            except (json.JSONDecodeError, TypeError):
                continue
    except OSError:
        pass
    return names


def _count_unprocessed_signals() -> tuple:
    """Count total and unprocessed signals using lineage for dedup.

    Returns (total, unprocessed) counts.
    """
    if not SIGNALS_DIR.is_dir():
        return 0, 0
    all_signals = [p for p in SIGNALS_DIR.iterdir() if p.is_file() and p.suffix == ".md"]
    total = len(all_signals)
    synthesized = _synthesized_signal_names()
    unprocessed = sum(1 for p in all_signals if p.name not in synthesized)
    return total, unprocessed


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


def _crypto_bot_status() -> list[str]:
    """Load crypto-bot status from data/crypto_bot_state.json for morning briefing (FR-003)."""
    state_file = REPO_ROOT / "data" / "crypto_bot_state.json"
    if not state_file.is_file():
        return []
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ["  (state file unreadable)"]

    ts = state.get("timestamp", "unknown")
    # Staleness check: >30 min = stale
    lines: list[str] = []
    try:
        poll_dt = datetime.fromisoformat(ts)
        age_min = (datetime.now(timezone.utc) - poll_dt).total_seconds() / 60
        if age_min > 30:
            lines.append(f"  STALE -- last poll {ts} ({age_min:.0f} min ago)")
    except (ValueError, TypeError):
        lines.append(f"  Last poll: {ts}")

    api_ok = state.get("api_reachable", False)
    status_ok = state.get("status_reachable", False)
    lines.append(f"  API: {'OK' if api_ok else 'PARTIAL' if status_ok else 'DOWN'}")

    # Process health
    procs = state.get("processes", {})
    if isinstance(procs, dict) and procs:
        alive = [k for k, v in procs.items() if v]
        dead = [k for k, v in procs.items() if not v]
        if dead:
            lines.append(f"  Processes DOWN: {', '.join(dead)}")
        else:
            lines.append(f"  Processes: {len(alive)} alive")
    else:
        lines.append("  Processes: unknown")

    # Trade summary
    t_open = state.get("trade_count_open", 0)
    t_closed = state.get("trade_count_closed", 0)
    pnl = state.get("realized_pnl", 0.0)
    wr = state.get("win_rate", 0.0)
    dd = state.get("drawdown_pct", 0.0)
    lines.append(f"  Trades: {t_open} open, {t_closed} closed | P&L: ${pnl:.2f} | WR: {wr:.1f}% | DD: {dd:.1f}%")

    # Overnight alerts/patches
    n_alerts = state.get("new_alerts_count", 0)
    n_patches = state.get("new_patches_count", 0)
    if n_alerts or n_patches:
        lines.append(f"  Since last poll: {n_alerts} alerts, {n_patches} patches")

    # Log errors
    errs = state.get("log_errors", {})
    if errs:
        err_parts = [f"{k}: {v}" for k, v in errs.items()]
        lines.append(f"  Log errors: {', '.join(err_parts)}")

    return lines


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


def _compute_ctx_metrics() -> dict | None:
    """Read most recent session JSONL and return raw context metrics, or None on error."""
    try:
        if not CLAUDE_PROJ_DIR.is_dir():
            return None
        files = [p for p in CLAUDE_PROJ_DIR.iterdir() if p.suffix == ".jsonl"]
        if not files:
            return None
        path = max(files, key=lambda p: p.stat().st_mtime)

        entries: list = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

        last_compact_ts = None
        compact_count = 0
        for e in entries:
            if e.get("isMeta"):
                compact_count += 1
                ts = e.get("timestamp", "")
                if ts and (last_compact_ts is None or ts > last_compact_ts):
                    last_compact_ts = ts

        live = [e for e in entries if e.get("timestamp", "") > last_compact_ts] if last_compact_ts else entries
        est_tokens = sum(_CTX_TOKENS_PER_TYPE.get(e.get("type", ""), 300) for e in live)
        user_turns = sum(1 for e in live if e.get("type") == "user")
        pct = min(99, int(est_tokens / CONTEXT_LIMIT_TOKENS * 100))

        return {
            "session_id": path.stem,
            "pct": pct,
            "compact_count": compact_count,
            "est_tokens_k": est_tokens // 1_000,
            "user_turns": user_turns,
        }
    except Exception:
        return None


def _context_status_line() -> str:
    """Format CTX banner line from computed metrics."""
    m = _compute_ctx_metrics()
    if m is None:
        return "CTX [----------] ~?%"
    pct = m["pct"]
    filled = pct // 10
    bar = "#" * filled + "-" * (10 - filled)
    compact_str = f" /{m['compact_count']}cx" if m["compact_count"] > 0 else ""
    limit_k = CONTEXT_LIMIT_TOKENS // 1_000
    return f"CTX [{bar}] ~{pct}% ~{m['est_tokens_k']}K/{limit_k}K{compact_str} {m['user_turns']}t"


def _log_context_metrics() -> None:
    """Append one metrics row to data/context_metrics.jsonl for trend tracking."""
    m = _compute_ctx_metrics()
    if m is None:
        return
    try:
        log_file = REPO_ROOT / "data" / "context_metrics.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "date": datetime.now().astimezone().strftime("%Y-%m-%d"),
            "ts": datetime.now().astimezone().isoformat(),
            **m,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


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

    # 2. Check TCP connection count + identify top process holders.
    # Per-process attribution prevents misattributing leaks to Claude when
    # the actual culprit is another dev server on the same host
    # (2026-04-08: dashboard.app:app uvicorn leaked 337 of 376 connections).
    try:
        from tools.scripts.lib.net_util import get_https_summary, format_top_holders
        https_count, holders = get_https_summary(top_n=3)
        if https_count is not None:
            top_str = format_top_holders(holders)
            if https_count >= 200:
                warnings.append(
                    f"  >>> {https_count} TCP connections active -- "
                    f"CRITICAL: top holders = {top_str}"
                )
                warnings.append(
                    "      ACTION: identify the top holder above and restart "
                    "or close it; this is rarely Claude itself"
                )
            elif https_count >= 100:
                warnings.append(
                    f"  >>> {https_count} TCP connections active -- "
                    f"elevated; top holders = {top_str}"
                )
    except (OSError, subprocess.TimeoutExpired, ImportError):
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


def _section_hash(rendered: str) -> str:
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:8]


def _load_banner_cache() -> dict | None:
    try:
        return json.loads(BANNER_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_banner_cache(cache: dict) -> None:
    tmp = BANNER_CACHE_FILE.with_suffix(".json.tmp")
    try:
        BANNER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(BANNER_CACHE_FILE))
    except OSError:
        pass


def _ismeta_newer_than_cache() -> bool:
    # No cache → no baseline for comparison → force full render (True = invalidate)
    if not BANNER_CACHE_FILE.exists():
        return True
    try:
        cache_mtime = BANNER_CACHE_FILE.stat().st_mtime
        if not CLAUDE_PROJ_DIR.is_dir():
            return False
        files = [p for p in CLAUDE_PROJ_DIR.iterdir() if p.suffix == ".jsonl"]
        if not files:
            return False
        path = max(files, key=lambda p: p.stat().st_mtime)
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("isMeta"):
                        ts = entry.get("timestamp", "")
                        if ts:
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if dt.timestamp() > cache_mtime:
                                return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


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

    # ── Banner header (always emitted — contains live timestamp) ──────────
    ctx_line = _context_status_line()
    _log_context_metrics()
    print()
    print(f"╔{'═' * _W}╗")
    print(_box_line("JARVIS :: NEURAL LINK ESTABLISHED"))
    print(_box_line(f"SESSION // {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"))
    print(_box_line(ctx_line))
    print(f"╚{'═' * _W}╝")

    # ── Delta-mode setup ──────────────────────────────────────────────────
    use_delta = False
    cache: dict = {}
    try:
        loaded = _load_banner_cache()
        if loaded is not None and not _ismeta_newer_than_cache():
            cache = loaded
            use_delta = True
    except Exception:
        pass

    new_cache: dict = {}
    sections_emitted = 0

    def _emit(key: str, lines: list) -> None:
        nonlocal sections_emitted
        rendered = "\n".join(lines) + ("\n" if lines else "")
        h = _section_hash(rendered)
        new_cache[key] = h
        if not use_delta or cache.get(key) != h:
            if rendered:
                sys.stdout.write(rendered)
                sections_emitted += 1

    # ── GIT SAFETY ────────────────────────────────────────────────────────
    git_lines: list = []
    git_warnings = _git_safety_check()
    if git_warnings:
        git_lines.append(_section("GIT SAFETY"))
        git_lines.extend(_ascii_safe(w) for w in git_warnings)
    _emit("GIT_SAFETY", git_lines)

    # ── GOAL BALANCE ──────────────────────────────────────────────────────
    goal_lines: list = []
    g2_warnings = _g2_streak_check()
    if g2_warnings:
        goal_lines.append(_section("GOAL BALANCE"))
        goal_lines.extend(_ascii_safe(w) for w in g2_warnings)
    _emit("GOAL_BALANCE", goal_lines)

    # ── CRYPTO-BOT ────────────────────────────────────────────────────────
    crypto_lines: list = []
    crypto_status = _crypto_bot_status()
    if crypto_status:
        crypto_lines.append(_section("CRYPTO-BOT"))
        crypto_lines.extend(_ascii_safe(line) for line in crypto_status)
    _emit("CRYPTO_BOT", crypto_lines)

    # ── TELOS ─────────────────────────────────────────────────────────────
    _emit("TELOS", [_section("TELOS"), _ascii_safe(_load_telos_status())])

    # ── ACTIVE TASKS (bundles tasks + validations + absorb + dream) ────────
    active_lines: list = [_section("ACTIVE TASKS")]
    if TASKLIST.is_file():
        tasks = _unchecked_tasks(TASKLIST.read_text(encoding="utf-8", errors="replace"))
        if tasks:
            for t in tasks[:5]:
                active_lines.append(f"  [ ] {_ascii_safe(t)}")
            if len(tasks) > 5:
                active_lines.append(f"  ... and {len(tasks) - 5} more")
        else:
            active_lines.append("  (none)")
    else:
        active_lines.append(f"  (missing: {TASKLIST})")

    validations = _check_open_validations()
    if validations:
        active_lines.append(_section("OPEN VALIDATIONS"))
        for v in validations:
            active_lines.append(f"  ⚡ {_ascii_safe(v)}")

    pending = _count_pending_absorb_proposals()
    if pending:
        active_lines.append(_section("PENDING /ABSORB"))
        active_lines.append(f"  ⚡ {pending} TELOS proposal(s) pending -- run `/absorb --review`")

    dream_report = REPO_ROOT / "data" / "dream_last_report.md"
    dream_last_run = REPO_ROOT / "data" / "dream_last_run.txt"
    if dream_report.exists():
        try:
            report_text = dream_report.read_text(encoding="utf-8", errors="replace")
            if any(k in report_text for k in ["[MERGE", "[STALE", "[DATES"]):
                last_run = dream_last_run.read_text().strip() if dream_last_run.exists() else "unknown"
                active_lines.append(_section("DREAM CONSOLIDATION"))
                active_lines.append(f"  ⚡ /dream ran at {last_run} -- run `/dream --dry-run` to review")
        except Exception:
            pass

    _emit("ACTIVE_TASKS", active_lines)

    # ── LEARNING ──────────────────────────────────────────────────────────
    n_total_signals, n_unprocessed = _count_unprocessed_signals()
    n_failures = _count_files(FAILURES_DIR)
    learn_lines: list = [
        _section("LEARNING"),
        f"  {n_total_signals} signals ({n_unprocessed} unprocessed) | {n_failures} failures",
    ]
    due, reason = _synthesis_due(n_unprocessed)
    if due:
        learn_lines.append(f"  ⚡ Synthesis due: {reason}")
        learn_lines.append("     Run /synthesize-signals when ready.")
    _emit("LEARNING", learn_lines)

    # ── SECURITY ──────────────────────────────────────────────────────────
    sec_lines: list = [_section("SECURITY (7d)")]
    sec = _recent_security_events()
    if sec:
        sec_lines.extend(sec)
    else:
        sec_lines.append("  (none logged)")
    _emit("SECURITY", sec_lines)

    # ── Save cache + conditional footer ───────────────────────────────────
    try:
        _save_banner_cache(new_cache)
    except Exception:
        pass

    if sections_emitted > 0:
        print(f"\n╚{'═' * _W}╝\n")


if __name__ == "__main__":
    main()
    sys.exit(0)
