#!/usr/bin/env python3
"""Prediction Backtest Producer -- autonomous historical prediction calibration.

Selects unrun events from data/backtest_events.yaml, runs date-constrained
/make-prediction prompts via claude -p, scores outcomes, and writes accuracy
signals to the learning loop.

ALL backtest outputs are tagged: backtested=true, leakage_risk=HIGH, weight=0.5
Signals require Eric review (status: pending_review) before calibration promotion.

Usage:
    python tools/scripts/prediction_backtest_producer.py            # normal run (up to 3 events)
    python tools/scripts/prediction_backtest_producer.py --dry-run  # show what would run
    python tools/scripts/prediction_backtest_producer.py --event <event_id>  # run single event
    python tools/scripts/prediction_backtest_producer.py --status   # show run state table

Outputs:
    data/predictions/backtest/{date}-{event_id}.md   -- prediction record
    data/backtest_state.json                          -- tracks which events have run
    memory/learning/signals/{date}_prediction-backtest-{event_id}.md  -- accuracy signal
    Slack #epdev                                      -- summary (when events run)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from textwrap import dedent

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

EVENTS_FILE     = REPO_ROOT / "data" / "backtest_events.yaml"
STATE_FILE      = REPO_ROOT / "data" / "backtest_state.json"
PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions" / "backtest"
SIGNALS_DIR     = REPO_ROOT / "memory" / "learning" / "signals"
LOGS_DIR        = REPO_ROOT / "data" / "logs"

MAX_EVENTS_PER_RUN = 3
LEAKAGE_CONFIDENCE_THRESHOLD = 0.85  # flag if model confidence on winner > 85%

TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# Event loading
# ---------------------------------------------------------------------------

def load_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        print(f"ERROR: backtest_events.yaml not found at {EVENTS_FILE}", file=sys.stderr)
        return []
    data = yaml.safe_load(EVENTS_FILE.read_text(encoding="utf-8"))
    return data.get("events", [])


def select_unrun_events(events: list[dict], state: dict, limit: int) -> list[dict]:
    """Return up to `limit` events that have not yet been run."""
    run_ids = set(state.get("completed", {}).keys())
    unrun = [e for e in events if e["event_id"] not in run_ids]
    return unrun[:limit]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

BACKTEST_PROMPT_TEMPLATE = dedent("""\
    BACKTESTING MODE -- DATE INJECTION ACTIVE

    It is {cutoff_date}. You may only reference information that was publicly
    available before this date. Do not use knowledge of events that occurred
    after {cutoff_date}.

    CONTEXT (what was publicly known at {cutoff_date}):
    {at_time_context}

    ---

    You are a structured prediction engine. Produce a committed probability
    estimate for the following question as if you are answering on {cutoff_date}:

    QUESTION: {description}

    Format your response as:
    ## Outcomes
    List 2-5 mutually exclusive outcomes with committed probabilities that sum to 100%.
    For each outcome: state it clearly, give probability (%), explain your reasoning.

    ## Primary Prediction
    State your single most likely outcome and its probability.

    ## Signposts
    2-3 observable signals that would update your estimate significantly.

    ## Confidence Note
    Any important caveats about your knowledge boundary at {cutoff_date}.

    IMPORTANT: Do not reference events after {cutoff_date}. Commit to numbers.
    Do not hedge with "it depends" -- assign probabilities.
""")


def build_prompt(event: dict) -> str:
    return BACKTEST_PROMPT_TEMPLATE.format(
        cutoff_date=event["knowledge_cutoff_date"],
        at_time_context=event["at_time_context"].strip(),
        description=event["description"],
    )


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------

def run_claude(prompt: str, event_id: str) -> str | None:
    """Run claude -p with the backtest prompt. Returns stdout or None on failure."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            print(f"  WARN: claude exited {result.returncode} for {event_id}", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}", file=sys.stderr)
            return None

        output = result.stdout.strip()

        # Rate limit guard (steering rule)
        rate_limit_phrases = ["hit your limit", "rate limit", "quota exceeded", "too many requests"]
        if any(phrase in output.lower() for phrase in rate_limit_phrases):
            print(f"  WARN: rate limit detected for {event_id} -- skipping", file=sys.stderr)
            return None

        if not output:
            print(f"  WARN: empty output for {event_id}", file=sys.stderr)
            return None

        return output

    except subprocess.TimeoutExpired:
        print(f"  WARN: claude timed out for {event_id}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  ERROR: claude CLI not found in PATH", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def extract_primary_confidence(claude_output: str) -> float | None:
    """Extract the probability of the primary predicted outcome (0.0-1.0)."""
    # Look for patterns like "70%" or "70 percent" near "primary" or "most likely"
    primary_section = ""
    lines = claude_output.split("\n")
    in_primary = False
    for line in lines:
        if "## primary" in line.lower() or "primary prediction" in line.lower():
            in_primary = True
        if in_primary:
            primary_section += line + "\n"
            if line.startswith("##") and "primary" not in line.lower():
                break

    # Extract percentage from primary section or fallback to highest in outcomes
    pct_matches = re.findall(r"(\d{1,3})\s*%", primary_section or claude_output)
    if pct_matches:
        # Return the first percentage in primary section, or highest overall
        values = [int(p) for p in pct_matches if 0 < int(p) <= 100]
        if values:
            return max(values) / 100.0
    return None


def score_prediction(event: dict, claude_output: str) -> dict:
    """Score prediction against known outcome. Returns scoring metadata."""
    known_outcome = event.get("known_outcome", "")
    primary_confidence = extract_primary_confidence(claude_output)

    # Simple heuristic: check if claude_output contains keywords from known outcome
    # This is rough -- the human review step is the authoritative score
    outcome_words = set(re.findall(r"\b\w{4,}\b", known_outcome.lower()))
    output_lower = claude_output.lower()
    keyword_hits = sum(1 for w in outcome_words if w in output_lower)
    alignment_score = min(1.0, keyword_hits / max(len(outcome_words), 1))

    # Leakage detection: suspiciously high confidence on historical event
    suspect_leakage = (
        primary_confidence is not None
        and primary_confidence > LEAKAGE_CONFIDENCE_THRESHOLD
    )

    return {
        "primary_confidence": primary_confidence,
        "alignment_score": round(alignment_score, 3),
        "suspect_leakage": suspect_leakage,
        "leakage_flag": "[SUSPECT LEAKAGE]" if suspect_leakage else "",
        "score_method": "keyword-alignment-v1",
        "note": "Provisional score -- requires human review for authoritative accuracy",
    }


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def write_prediction_file(event: dict, claude_output: str, scoring: dict) -> Path:
    """Write prediction record to data/predictions/backtest/."""
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    event_id = event["event_id"]
    slug = f"{TODAY}-{event_id}"
    output_path = PREDICTIONS_DIR / f"{slug}.md"

    leakage_flag = scoring["leakage_flag"]
    suspect_note = (
        "\n**[SUSPECT LEAKAGE]** Model confidence > 85% on a historical event. "
        "This signal requires Eric review before calibration promotion. "
        "Exclude from calibration if leakage is confirmed.\n"
        if scoring["suspect_leakage"] else ""
    )

    content = f"""---
date: {TODAY}
event_id: {event_id}
domain: {event.get('domain', 'unknown')}
knowledge_cutoff_date: {event.get('knowledge_cutoff_date', '')}
backtested: true
leakage_risk: HIGH
weight: 0.5
status: pending_review
known_outcome: "{event.get('known_outcome', '').replace('"', "'")}"
difficulty: {event.get('difficulty', 'unknown')}
primary_confidence: {scoring.get('primary_confidence', 'null')}
alignment_score: {scoring.get('alignment_score', 'null')}
suspect_leakage: {str(scoring.get('suspect_leakage', False)).lower()}
score_method: {scoring.get('score_method', '')}
{leakage_flag}
---

# Backtest Prediction: {event.get('description', '')}

> **BACKTESTED** -- Knowledge constrained to {event.get('knowledge_cutoff_date', '')}.
> Leakage risk: HIGH. Weight: 0.5. Requires human review before calibration use.
{suspect_note}
## Known Outcome

{event.get('known_outcome', '')}

## Model Prediction (as of {event.get('knowledge_cutoff_date', '')})

{claude_output}

---
*Generated by prediction_backtest_producer.py on {TODAY}*
"""
    output_path.write_text(content, encoding="utf-8")
    return output_path


def write_accuracy_signal(event: dict, scoring: dict, prediction_path: Path) -> Path:
    """Write accuracy signal to learning loop. Requires reviewed status to be promoted."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    event_id = event["event_id"]
    domain = event.get("domain", "unknown")
    difficulty = event.get("difficulty", "unknown")
    confidence = scoring.get("primary_confidence")
    alignment = scoring.get("alignment_score", 0)
    suspect = scoring.get("suspect_leakage", False)

    # Rating: 6 for clean backtest, 7 for suspect leakage (needs attention)
    rating = 7 if suspect else 6

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", event_id)
    signal_path = SIGNALS_DIR / f"{TODAY}_prediction-backtest-{safe_id}.md"
    counter = 2
    while signal_path.exists():
        signal_path = SIGNALS_DIR / f"{TODAY}_prediction-backtest-{safe_id}-{counter}.md"
        counter += 1

    leakage_note = (
        "\n**[SUSPECT LEAKAGE]** Model confidence exceeded threshold. "
        "Requires Eric review before this signal affects calibration.\n"
        if suspect else ""
    )

    content = f"""---
date: {TODAY}
rating: {rating}
category: prediction-accuracy
source: backtest
domain: {domain}
event_id: {event_id}
backtested: true
weight: 0.5
status: pending_review
suspect_leakage: {str(suspect).lower()}
---

# Backtest Accuracy Signal: {event_id}
{leakage_note}
**Domain**: {domain}
**Difficulty**: {difficulty}
**Knowledge cutoff**: {event.get('knowledge_cutoff_date', '')}
**Primary confidence**: {f'{confidence:.0%}' if confidence is not None else 'unknown'}
**Alignment score**: {alignment:.0%} (keyword match vs known outcome -- provisional)
**Known outcome**: {event.get('known_outcome', '')}

**Scoring note**: This is a provisional alignment score based on keyword matching.
Human review required to assign authoritative accuracy label (correct/wrong/partial).
Do not promote to calibration until status is updated to `reviewed`.

**Prediction file**: {prediction_path.name}
"""
    signal_path.write_text(content, encoding="utf-8")
    return signal_path


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------

def notify_slack(results: list[dict]) -> None:
    if not results:
        return
    try:
        from tools.scripts.slack_notify import notify

        lines = [f"*Backtest Producer -- {TODAY}*", f"{len(results)} event(s) run\n"]
        for r in results:
            event = r["event"]
            scoring = r["scoring"]
            flag = " :warning: SUSPECT LEAKAGE" if scoring.get("suspect_leakage") else ""
            conf = scoring.get("primary_confidence")
            conf_str = f"{conf:.0%}" if conf is not None else "unknown"
            lines.append(
                f"- `{event['event_id']}` [{event['domain']}] "
                f"conf={conf_str} align={scoring.get('alignment_score', '?'):.0%}"
                f"{flag}"
            )
        lines.append(
            "\nAll outputs tagged `backtested=true, leakage_risk=HIGH`. "
            "Review in `data/predictions/backtest/` before calibration use."
        )
        notify("\n".join(lines), severity="routine")
    except Exception as exc:
        print(f"  WARN: Slack notify failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status(events: list[dict], state: dict) -> None:
    completed = state.get("completed", {})
    print(f"Backtest Event Status -- {TODAY}")
    print(f"{'Event ID':<40} {'Domain':<12} {'Difficulty':<10} {'Run Date':<12} Status")
    print("-" * 90)
    for event in events:
        eid = event["event_id"]
        domain = event.get("domain", "?")
        diff = event.get("difficulty", "?")
        run_info = completed.get(eid, {})
        run_date = run_info.get("date", "-")
        status = "DONE" if eid in completed else "PENDING"
        print(f"{eid:<40} {domain:<12} {diff:<10} {run_date:<12} {status}")
    total = len(events)
    done = len(completed)
    print(f"\nTotal: {total} | Done: {done} | Pending: {total - done}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Backtest Producer")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run, no execution")
    parser.add_argument("--event", metavar="EVENT_ID", help="Run a single specific event")
    parser.add_argument("--status", action="store_true", help="Show event run status table")
    parser.add_argument("--force", action="store_true", help="Re-run already-completed events")
    args = parser.parse_args()

    events = load_events()
    if not events:
        print("No events loaded -- check data/backtest_events.yaml")
        return 1

    state = load_state()

    if args.status:
        show_status(events, state)
        return 0

    # Event selection
    if args.event:
        selected = [e for e in events if e["event_id"] == args.event]
        if not selected:
            print(f"ERROR: event_id '{args.event}' not found in backtest_events.yaml")
            return 1
    elif args.force:
        selected = events[:MAX_EVENTS_PER_RUN]
    else:
        selected = select_unrun_events(events, state, MAX_EVENTS_PER_RUN)

    if not selected:
        print(f"Idle: all {len(events)} events already run. Use --force to re-run.")
        return 0

    print(f"Backtest Producer -- {TODAY}")
    print(f"Running {len(selected)} event(s): {[e['event_id'] for e in selected]}")

    if args.dry_run:
        print("\n[DRY RUN] Would run:")
        for e in selected:
            print(f"  - {e['event_id']} [{e['domain']}] cutoff={e['knowledge_cutoff_date']}")
        return 0

    results = []
    completed = state.setdefault("completed", {})

    for event in selected:
        event_id = event["event_id"]
        print(f"\n  Running: {event_id} [{event['domain']}]")

        prompt = build_prompt(event)
        claude_output = run_claude(prompt, event_id)

        if claude_output is None:
            print(f"  SKIP: claude invocation failed for {event_id}")
            continue

        scoring = score_prediction(event, claude_output)
        prediction_path = write_prediction_file(event, claude_output, scoring)
        signal_path = write_accuracy_signal(event, scoring, prediction_path)

        # Update state
        completed[event_id] = {
            "date": TODAY,
            "prediction_file": str(prediction_path.relative_to(REPO_ROOT)),
            "signal_file": str(signal_path.relative_to(REPO_ROOT)),
            "suspect_leakage": scoring["suspect_leakage"],
        }
        save_state(state)

        flag = " [SUSPECT LEAKAGE]" if scoring["suspect_leakage"] else ""
        conf = scoring.get("primary_confidence")
        conf_str = f"{conf:.0%}" if conf is not None else "unknown"
        print(f"  Done: conf={conf_str} align={scoring['alignment_score']:.0%}{flag}")
        print(f"  -> {prediction_path.relative_to(REPO_ROOT)}")

        results.append({"event": event, "scoring": scoring, "prediction_path": prediction_path})

    if results:
        notify_slack(results)
        print(f"\nProducer complete: {len(results)}/{len(selected)} events run.")
        print("All outputs require review before calibration promotion.")
    else:
        print("\nProducer complete: 0 events run (all failed or skipped).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
