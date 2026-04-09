#!/usr/bin/env python3
"""Prediction Resolver -- parses Slack resolution replies and writes outcomes.

Called by the Slack poller (/absorb) when a resolution reply is detected
in a #epdev thread, or invoked directly to resolve a prediction by file path.

Resolution syntax (Eric replies in Slack thread):
  correct                    -- prediction correct
  wrong                      -- prediction incorrect
  partial: outcome 1 correct, outcome 3 wrong  -- partially correct with note
  defer: 2026-12-31          -- extend horizon to new date
  reviewed: geo-btc-2021     -- accept a backtest prediction (mark reviewed)
  rejected: geo-btc-2021     -- reject a backtest (discard from calibration)

Usage:
    python tools/scripts/prediction_resolver.py --file <path> --verdict correct
    python tools/scripts/prediction_resolver.py --file <path> --verdict "partial: note"
    python tools/scripts/prediction_resolver.py --file <path> --verdict "defer: 2026-12-31"
    python tools/scripts/prediction_resolver.py --event <event_id> --verdict reviewed
    python tools/scripts/prediction_resolver.py --slack-text "correct" --file <path>
    python tools/scripts/prediction_resolver.py --count  # show resolved count

Outputs:
    Updated prediction file (frontmatter + resolution section appended)
    data/backlog_resolution_trigger.json  -- signals dispatcher to check calibration
    memory/learning/signals/{date}_prediction-resolved-*.md  -- accuracy signal
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions"
BACKTEST_DIR    = PREDICTIONS_DIR / "backtest"
SIGNALS_DIR     = REPO_ROOT / "memory" / "learning" / "signals"
BACKLOG_PATH    = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
TRIGGER_FILE    = REPO_ROOT / "data" / "backlog_resolution_trigger.json"

TODAY = date.today().isoformat()

# Verdict types and their normalized forms
VERDICT_MAP = {
    "correct":  "correct",
    "right":    "correct",
    "yes":      "correct",
    "wrong":    "wrong",
    "incorrect": "wrong",
    "no":       "wrong",
}


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------

def parse_verdict(text: str) -> tuple[str, str]:
    """Parse a resolution reply. Returns (verdict_type, note).

    verdict_type: correct | wrong | partial | defer | reviewed | rejected
    note: additional text (for partial/defer)
    """
    text = text.strip()
    lower = text.lower()

    if lower.startswith("partial:"):
        return "partial", text[8:].strip()

    if lower.startswith("defer:"):
        new_date = text[6:].strip()
        # Validate date format
        try:
            datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid defer date format '{new_date}' -- use YYYY-MM-DD")
        return "defer", new_date

    if lower.startswith("reviewed:"):
        return "reviewed", text[9:].strip()

    if lower.startswith("rejected:"):
        return "rejected", text[9:].strip()

    normalized = VERDICT_MAP.get(lower)
    if normalized:
        return normalized, ""

    raise ValueError(
        f"Unknown verdict '{text}'. "
        "Valid: correct, wrong, partial: [note], defer: YYYY-MM-DD, "
        "reviewed: [event_id], rejected: [event_id]"
    )


# ---------------------------------------------------------------------------
# Prediction file I/O
# ---------------------------------------------------------------------------

def find_prediction_file(identifier: str) -> Path | None:
    """Find a prediction file by path, filename, or event_id."""
    # Try as direct path first
    p = Path(identifier)
    if p.exists():
        return p
    if (REPO_ROOT / identifier).exists():
        return REPO_ROOT / identifier

    # Search by filename in predictions dir
    for candidate in PREDICTIONS_DIR.rglob("*.md"):
        if candidate.name == identifier or candidate.stem == identifier:
            return candidate

    # Search by event_id in frontmatter
    for candidate in PREDICTIONS_DIR.rglob("*.md"):
        try:
            content = candidate.read_text(encoding="utf-8")
            if f"event_id: {identifier}" in content or f"event_id: '{identifier}'" in content:
                return candidate
        except OSError:
            pass

    return None


def read_prediction(path: Path) -> tuple[dict, str, str]:
    """Read prediction file. Returns (frontmatter, frontmatter_raw, body)."""
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return {}, "", content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, "", content

    fm_raw = parts[1]
    body = parts[2]
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, fm_raw, body


def write_resolution(path: Path, fm: dict, fm_raw: str, body: str,
                     verdict: str, note: str) -> None:
    """Update prediction file with resolution outcome."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Update frontmatter fields
    fm["status"] = "resolved" if verdict in ("correct", "wrong", "partial") else (
        "deferred" if verdict == "defer" else "reviewed" if verdict == "reviewed" else "rejected"
    )
    fm["resolved_date"] = TODAY if verdict not in ("defer",) else None
    fm["outcome_label"] = verdict
    fm["resolution_note"] = note or ""
    if verdict == "defer":
        fm["horizon"] = note  # note holds new date for defer

    # Rebuild frontmatter YAML manually to preserve existing fields
    # Update key lines in fm_raw
    def update_fm_line(raw: str, key: str, value) -> str:
        pattern = rf"^{key}:.*$"
        replacement = f"{key}: {json.dumps(value) if isinstance(value, str) else value}"
        updated = re.sub(pattern, replacement, raw, flags=re.MULTILINE)
        if key not in updated:
            updated = updated.rstrip() + f"\n{key}: {json.dumps(str(value)) if isinstance(value, str) else value}"
        return updated

    new_fm_raw = fm_raw
    new_fm_raw = update_fm_line(new_fm_raw, "status", fm["status"])
    if fm.get("resolved_date"):
        new_fm_raw = update_fm_line(new_fm_raw, "resolved_date", fm["resolved_date"])
    new_fm_raw = update_fm_line(new_fm_raw, "outcome_label", verdict)
    if note:
        new_fm_raw = update_fm_line(new_fm_raw, "resolution_note", note)

    # Append resolution section to body
    resolution_section = f"""

---

## Resolution ({TODAY})

**Verdict**: {verdict.upper()}
**Date resolved**: {TODAY}
**Note**: {note or '(none)'}
**Resolved by**: Eric (via Slack reply)
*Logged at {now_str}*
"""
    new_content = f"---{new_fm_raw}---{body}{resolution_section}"
    path.write_text(new_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Signal writing
# ---------------------------------------------------------------------------

def write_resolution_signal(fm: dict, path: Path, verdict: str, note: str) -> Path:
    """Write accuracy signal to learning loop."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    domain = fm.get("domain", "unknown")
    question = fm.get("question") or path.stem
    backtested = fm.get("backtested", False)
    weight = 0.5 if backtested else 1.0

    # Rating based on verdict and whether it was a backtest
    rating = 7 if verdict == "correct" else (6 if verdict == "partial" else 5)
    if backtested:
        rating = max(5, rating - 1)  # backtest signals rated slightly lower

    safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", path.stem[:40])
    signal_path = SIGNALS_DIR / f"{TODAY}_prediction-resolved-{safe_slug}.md"
    counter = 2
    while signal_path.exists():
        signal_path = SIGNALS_DIR / f"{TODAY}_prediction-resolved-{safe_slug}-{counter}.md"
        counter += 1

    backtest_note = "\n**[BACKTESTED]** This was a date-injection backtest. Weight: 0.5.\n" if backtested else ""

    content = f"""---
date: {TODAY}
rating: {rating}
category: prediction-accuracy
source: resolution
domain: {domain}
outcome_label: {verdict}
weight: {weight}
backtested: {str(backtested).lower()}
---

# Prediction Resolved: {verdict.upper()}
{backtest_note}
**Question**: {question}
**Domain**: {domain}
**Verdict**: {verdict}
**Note**: {note or '(none)'}
**Weight**: {weight} ({'backtest -- half weight' if backtested else 'forward-looking -- full weight'})
**File**: {path.name}

This resolution contributes to domain calibration for `{domain}`.
Calibration loop checks for threshold (20 forward-looking resolved) after each resolution.
"""
    signal_path.write_text(content, encoding="utf-8")
    return signal_path


# ---------------------------------------------------------------------------
# Post-resolution analysis
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT_TEMPLATE = """\
You are a prediction calibration analyst. Compare a prediction against its known outcome
and extract reasoning lessons.

PREDICTION FILE:
{prediction_content}

VERDICT: {verdict}
RESOLUTION NOTE: {note}

Analyze this prediction and produce EXACTLY this format (no other text):

## Prediction Analysis

**Verdict**: {verdict}
**Calibration error**: [Was the model overconfident, underconfident, or well-calibrated?
State the probability assigned to the actual outcome vs what happened.]

**Key reasoning errors**: [What did the model get wrong? What factors were
over/underweighted? Be specific -- name the exact reasoning step that failed.]

**What worked**: [What reasoning was correct? What factors were properly identified?]

**Lesson for future predictions**: [One concrete, actionable rule that would improve
the next prediction in this domain. Format as: "When [condition], [do X instead of Y]."
This must be specific enough to apply, not generic advice.]

**Signpost accuracy**: [Which signposts from the prediction turned out to be useful
predictors? Which were noise?]
"""


def generate_analysis(prediction_path: Path, verdict: str, note: str) -> str | None:
    """Run claude -p to generate post-resolution analysis. Returns analysis text or None."""
    try:
        content = prediction_path.read_text(encoding="utf-8", errors="replace")
        # Truncate to avoid massive prompts (keep first 4000 chars)
        if len(content) > 4000:
            content = content[:4000] + "\n...[truncated]"

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            prediction_content=content,
            verdict=verdict,
            note=note or "(none)",
        )

        result = subprocess.run(
            [CLAUDE_BIN, "-p", "--model", "sonnet", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )

        if result.returncode != 0:
            print(f"  WARN: analysis claude exited {result.returncode}", file=sys.stderr)
            return None

        output = result.stdout.strip()

        # Rate limit guard
        rate_limit_phrases = ["hit your limit", "rate limit", "quota exceeded"]
        if any(phrase in output.lower() for phrase in rate_limit_phrases):
            print("  WARN: rate limit during analysis -- skipping", file=sys.stderr)
            return None

        return output if output else None

    except subprocess.TimeoutExpired:
        print("  WARN: analysis claude timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  WARN: claude CLI not found for analysis", file=sys.stderr)
        return None


def append_analysis(path: Path, analysis_text: str) -> None:
    """Append analysis section to the prediction file."""
    content = path.read_text(encoding="utf-8", errors="replace")

    # Don't duplicate if analysis already exists
    if "## Prediction Analysis" in content:
        print("  Analysis already exists -- skipping append")
        return

    content += f"\n\n{analysis_text}\n"
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Calibration trigger
# ---------------------------------------------------------------------------

def trigger_calibration_check(verdict: str) -> None:
    """Write trigger file so dispatcher knows to check calibration threshold."""
    if verdict not in ("correct", "wrong", "partial"):
        return  # only forward-resolved predictions count for calibration

    existing = {}
    if TRIGGER_FILE.exists():
        try:
            existing = json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    existing["last_resolution"] = TODAY
    existing["pending_check"] = True

    TRIGGER_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def count_resolved(forward_only: bool = True) -> int:
    """Count resolved forward-looking predictions."""
    count = 0
    for path in PREDICTIONS_DIR.glob("*.md"):
        try:
            content = path.read_text(encoding="utf-8")
            if "status: resolved" not in content and 'status: "resolved"' not in content:
                continue
            if forward_only and "backtested: true" in content:
                continue
            count += 1
        except OSError:
            pass
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Resolver")
    parser.add_argument("--file", metavar="PATH", help="Prediction file path or filename")
    parser.add_argument("--event", metavar="EVENT_ID", help="Backtest event_id to resolve")
    parser.add_argument("--verdict", metavar="TEXT", help="Resolution verdict text")
    parser.add_argument("--slack-text", metavar="TEXT", help="Raw Slack reply text to parse")
    parser.add_argument("--count", action="store_true", help="Show resolved prediction count")
    args = parser.parse_args()

    if args.count:
        forward = count_resolved(forward_only=True)
        total = count_resolved(forward_only=False)
        print(f"Resolved predictions: {forward} forward-looking, {total} total")
        print(f"Calibration threshold: 20 forward-looking (currently {forward}/20)")
        return 0

    # Parse verdict
    verdict_text = args.verdict or args.slack_text
    if not verdict_text:
        parser.error("--verdict or --slack-text required")

    try:
        verdict, note = parse_verdict(verdict_text)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Find prediction file
    identifier = args.file or args.event
    if not identifier:
        parser.error("--file or --event required")

    path = find_prediction_file(identifier)
    if path is None:
        print(f"ERROR: prediction file not found for '{identifier}'", file=sys.stderr)
        return 1

    # Read, update, write
    fm, fm_raw, body = read_prediction(path)
    current_status = str(fm.get("status", "open")).lower()

    if current_status == "resolved":
        print(f"WARN: {path.name} is already resolved -- overwriting with new verdict")

    write_resolution(path, fm, fm_raw, body, verdict, note)

    # Write signal and trigger calibration check (for non-defer/non-backtest verdicts)
    if verdict not in ("defer",):
        signal_path = write_resolution_signal(fm, path, verdict, note)
        print(f"  Signal: {signal_path.relative_to(REPO_ROOT)}")

    if verdict in ("correct", "wrong", "partial"):
        trigger_calibration_check(verdict)
        resolved_count = count_resolved(forward_only=True)
        print(f"  Resolved count: {resolved_count}/20 (calibration threshold)")
        if resolved_count >= 20 and resolved_count % 5 == 0:
            print(f"  >> Calibration threshold met ({resolved_count})! Run prediction_calibration.py")

    print(f"Resolved: {path.name} -> {verdict.upper()}" + (f" ({note})" if note else ""))

    # Post-resolution analysis -- extract reasoning lessons
    if verdict in ("correct", "wrong", "partial"):
        print("  Generating post-resolution analysis...")
        analysis = generate_analysis(path, verdict, note)
        if analysis:
            append_analysis(path, analysis)
            print("  Analysis appended to prediction file")
        else:
            print("  WARN: analysis generation failed -- file saved without analysis")

    return 0


if __name__ == "__main__":
    sys.exit(main())
