#!/usr/bin/env python3
"""Prediction Review Task -- weekly surface of due/overdue predictions.

Scans data/predictions/ for open predictions approaching their due date
and posts a structured Slack notification to #epdev with resolution prompts.
Also surfaces unreviewed backtest predictions.

Eric resolves by replying to the Slack thread:
  "correct"          -- outcome occurred as predicted
  "wrong"            -- outcome did not occur
  "partial: [note]"  -- partially correct with note
  "defer: YYYY-MM-DD" -- extend horizon to new date

Slack poller (/absorb) picks up replies and calls prediction_resolver.py.

Usage:
    python tools/scripts/prediction_review_task.py           # normal run
    python tools/scripts/prediction_review_task.py --dry-run # show what would post
    python tools/scripts/prediction_review_task.py --window 60  # 60-day lookahead

Outputs:
    Slack #epdev -- review notification
    data/logs/prediction_review_{date}.log
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions"
BACKTEST_DIR    = PREDICTIONS_DIR / "backtest"
LOGS_DIR        = REPO_ROOT / "data" / "logs"

DEFAULT_WINDOW_DAYS = 30
TODAY = date.today()


# ---------------------------------------------------------------------------
# Prediction file parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a prediction markdown file."""
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        fm = yaml.safe_load(parts[1]) or {}
        fm["_content"] = parts[2].strip()
        fm["_path"] = path
        fm["_filename"] = path.name
        return fm
    except yaml.YAMLError:
        return {}


def load_forward_predictions() -> list[dict]:
    """Load open forward-looking predictions (not backtest)."""
    results = []
    for path in PREDICTIONS_DIR.glob("*.md"):
        fm = parse_frontmatter(path)
        if not fm:
            continue
        # Skip resolved, deferred, or backtest predictions
        status = str(fm.get("status", "open")).lower()
        if status in ("resolved", "done", "deferred"):
            continue
        if fm.get("backtested"):
            continue
        results.append(fm)
    return results


def load_backtest_pending_review() -> list[dict]:
    """Load backtest predictions awaiting Eric's review."""
    results = []
    if not BACKTEST_DIR.exists():
        return results
    for path in BACKTEST_DIR.glob("*.md"):
        fm = parse_frontmatter(path)
        if not fm:
            continue
        status = str(fm.get("status", "")).lower()
        if status == "pending_review":
            results.append(fm)
    return results


# ---------------------------------------------------------------------------
# Due date checking
# ---------------------------------------------------------------------------

def parse_date_field(value) -> date | None:
    """Parse a date from various formats."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def is_due_for_review(fm: dict, window_days: int) -> tuple[bool, str]:
    """Check if a prediction is due for review. Returns (is_due, reason)."""
    horizon = parse_date_field(fm.get("horizon") or fm.get("due_date"))
    cutoff = TODAY + timedelta(days=window_days)

    if horizon:
        days_until = (horizon - TODAY).days
        if days_until <= 0:
            return True, f"OVERDUE by {abs(days_until)}d (horizon: {horizon})"
        if days_until <= window_days:
            return True, f"Due in {days_until}d (horizon: {horizon})"

    # Check signpost dates in content
    content = fm.get("_content", "")
    signpost_dates = _extract_signpost_dates(content)
    for sp_date in signpost_dates:
        if sp_date <= cutoff:
            days_until = (sp_date - TODAY).days
            if days_until <= 0:
                return True, f"Signpost date passed: {sp_date}"
            if days_until <= window_days:
                return True, f"Signpost approaching in {days_until}d: {sp_date}"

    # Surface all old open predictions (no horizon set but > 30 days old)
    created = parse_date_field(fm.get("date"))
    if created and (TODAY - created).days > 90:
        return True, f"Open for {(TODAY - created).days}d with no horizon set"

    return False, ""


def _extract_signpost_dates(content: str) -> list[date]:
    """Extract dates from signpost sections in prediction content."""
    import re
    dates = []
    # Look for "By YYYY" or "By YYYY-MM-DD" patterns in Watch for/Signpost sections
    for m in re.finditer(r"By (\d{4})(?:-(\d{2})-(\d{2}))?", content):
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else 12
        day = int(m.group(3)) if m.group(3) else 31
        try:
            d = date(year, month, min(day, 28))  # clamp to avoid Feb 31 etc.
            dates.append(d)
        except ValueError:
            pass
    return dates


# ---------------------------------------------------------------------------
# Slack message composition
# ---------------------------------------------------------------------------

def compose_slack_message(due_predictions: list[tuple[dict, str]], backtest_pending: list[dict]) -> str:
    if not due_predictions and not backtest_pending:
        return ""

    lines = [f"*Prediction Review -- {TODAY}*"]

    if due_predictions:
        lines.append(f"\n*{len(due_predictions)} Forward Prediction(s) for Review*")
        lines.append("Reply to this thread: `correct` / `wrong` / `partial: note` / `defer: YYYY-MM-DD`\n")

        for fm, reason in due_predictions:
            question = fm.get("question") or fm.get("_filename", "Unknown")
            domain = fm.get("domain", "unknown")
            status = fm.get("status", "open")

            # Extract top outcome with confidence if available
            content = fm.get("_content", "")
            top_outcome = _extract_top_outcome(content)

            lines.append(f"*{question}*")
            lines.append(f"  Domain: {domain} | Status: {status} | Reason: {reason}")
            if top_outcome:
                lines.append(f"  Top prediction: {top_outcome}")
            lines.append(f"  File: `{fm.get('_filename', '?')}`")
            lines.append("")

    if backtest_pending:
        lines.append(f"\n*{len(backtest_pending)} Backtest(s) Awaiting Review*")
        lines.append("Reply `reviewed: <event_id>` to accept, or `rejected: <event_id>` to discard.\n")

        for fm in backtest_pending:
            event_id = fm.get("event_id", "?")
            domain = fm.get("domain", "?")
            suspect = fm.get("suspect_leakage", False)
            conf = fm.get("primary_confidence")
            conf_str = f"{float(conf):.0%}" if conf else "unknown"
            flag = " :warning: SUSPECT LEAKAGE" if suspect else ""

            lines.append(f"`{event_id}` [{domain}] conf={conf_str}{flag}")
            lines.append(f"  Known outcome: {str(fm.get('known_outcome', ''))[:100]}")
            lines.append("")

    return "\n".join(lines)


def _extract_top_outcome(content: str) -> str:
    """Extract the highest-probability outcome from prediction content."""
    import re
    # Look for lines with % that look like outcome listings
    lines = content.split("\n")
    best_pct = 0
    best_line = ""
    for line in lines:
        m = re.search(r"(\d{1,3})\s*%", line)
        if m:
            pct = int(m.group(1))
            if pct > best_pct and pct <= 100:
                best_pct = pct
                best_line = line.strip().lstrip("*-# ")
    if best_line and best_pct > 0:
        return f"{best_line[:80]}..." if len(best_line) > 80 else best_line
    return ""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_log(due_predictions: list, backtest_pending: list, posted: bool) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"prediction_review_{TODAY}.log"
    lines = [
        f"Prediction Review Task -- {TODAY}",
        f"Forward predictions due: {len(due_predictions)}",
        f"Backtest pending review: {len(backtest_pending)}",
        f"Slack posted: {posted}",
        "",
    ]
    for fm, reason in due_predictions:
        lines.append(f"  DUE: {fm.get('_filename', '?')} -- {reason}")
    for fm in backtest_pending:
        lines.append(f"  BACKTEST: {fm.get('event_id', '?')}")
    log_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Weekly Review Task")
    parser.add_argument("--dry-run", action="store_true", help="Show what would post without posting")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW_DAYS,
                        help=f"Lookahead window in days (default: {DEFAULT_WINDOW_DAYS})")
    args = parser.parse_args()

    forward = load_forward_predictions()
    backtest = load_backtest_pending_review()

    due_predictions = []
    for fm in forward:
        is_due, reason = is_due_for_review(fm, args.window)
        if is_due:
            due_predictions.append((fm, reason))

    # Sort: overdue first, then by days until due
    due_predictions.sort(key=lambda x: x[1])

    if not due_predictions and not backtest:
        print(f"Idle: no predictions due within {args.window}d and no backtest reviews pending.")
        write_log([], [], False)
        return 0

    print(f"Prediction Review -- {TODAY}")
    print(f"  Forward due: {len(due_predictions)}")
    print(f"  Backtest pending review: {len(backtest)}")

    message = compose_slack_message(due_predictions, backtest)

    if args.dry_run:
        print("\n[DRY RUN] Would post to #epdev:")
        print(message)
        return 0

    posted = False
    try:
        from tools.scripts.slack_notify import notify
        notify(message, severity="routine")
        posted = True
        print("  Slack notification posted to #epdev")
    except Exception as exc:
        print(f"  WARN: Slack post failed: {exc}", file=sys.stderr)
        # Fallback: write to log
        fallback = LOGS_DIR / f"prediction_review_slack_fallback_{TODAY}.md"
        fallback.write_text(message, encoding="utf-8")
        print(f"  Fallback saved to {fallback}")

    write_log(due_predictions, backtest, posted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
