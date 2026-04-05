#!/usr/bin/env python3
"""Prediction Debrief Generator -- writes Substack draft from resolved predictions.

Every 5 resolved predictions, generates a "Prediction Debrief" draft file
in data/content/drafts/ for the Substack content pipeline.

Usage:
    python tools/scripts/prediction_debrief.py           # normal (checks threshold)
    python tools/scripts/prediction_debrief.py --force   # skip threshold, generate anyway
    python tools/scripts/prediction_debrief.py --status  # show debrief state
    python tools/scripts/prediction_debrief.py --dry-run # show what would generate

Outputs:
    data/content/drafts/prediction-debrief-{date}.md  -- Substack draft
    data/debrief_state.json                           -- tracks last debrief count
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions"
DRAFTS_DIR      = REPO_ROOT / "data" / "content" / "drafts"
STATE_FILE      = REPO_ROOT / "data" / "debrief_state.json"
CALIBRATION_FILE = REPO_ROOT / "data" / "calibration.json"

TODAY = date.today().isoformat()
DEBRIEF_EVERY = 5


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_debrief_at_count": 0, "debriefs_written": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# Prediction loading
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> dict | None:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1]) or {}
        fm["_path"] = path
        fm["_body"] = parts[2].strip()
        return fm
    except yaml.YAMLError:
        return None


def load_resolved() -> list[dict]:
    """Load all resolved forward-looking predictions, sorted by date."""
    results = []
    for path in PREDICTIONS_DIR.glob("*.md"):
        fm = parse_frontmatter(path)
        if not fm:
            continue
        status = str(fm.get("status", "")).lower()
        if status != "resolved":
            continue
        if fm.get("backtested"):
            continue
        results.append(fm)
    results.sort(key=lambda f: str(f.get("resolved_date", f.get("date", ""))))
    return results


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------

def generate_draft(predictions: list[dict], debrief_number: int) -> str:
    """Generate a Substack-ready prediction debrief draft."""
    lines = [
        f"---",
        f"title: \"Prediction Debrief #{debrief_number}: What I Got Right and Wrong\"",
        f"date: {TODAY}",
        f"status: draft",
        f"type: prediction-debrief",
        f"predictions_covered: {len(predictions)}",
        f"---",
        f"",
        f"# Prediction Debrief #{debrief_number}",
        f"",
        f"*{len(predictions)} predictions reviewed. Here's what the outcomes taught me.*",
        f"",
    ]

    # Summary stats
    correct = sum(1 for p in predictions if str(p.get("outcome_label", "")).lower() == "correct")
    wrong = sum(1 for p in predictions if str(p.get("outcome_label", "")).lower() == "wrong")
    partial = sum(1 for p in predictions if str(p.get("outcome_label", "")).lower() == "partial")
    accuracy = (correct + 0.5 * partial) / len(predictions) if predictions else 0

    lines.extend([
        f"## Scorecard",
        f"",
        f"| Outcome | Count |",
        f"|---------|-------|",
        f"| Correct | {correct} |",
        f"| Wrong | {wrong} |",
        f"| Partial | {partial} |",
        f"| **Accuracy** | **{accuracy:.0%}** |",
        f"",
    ])

    # Domain breakdown
    domains: dict[str, list] = {}
    for p in predictions:
        d = str(p.get("domain", "other")).lower()
        domains.setdefault(d, []).append(p)

    if len(domains) > 1:
        lines.append("## By Domain")
        lines.append("")
        for domain, preds in sorted(domains.items()):
            d_correct = sum(1 for p in preds if str(p.get("outcome_label", "")).lower() == "correct")
            d_acc = d_correct / len(preds) if preds else 0
            lines.append(f"- **{domain.title()}**: {d_correct}/{len(preds)} correct ({d_acc:.0%})")
        lines.append("")

    # Individual predictions
    lines.extend([
        f"## The Predictions",
        f"",
    ])

    for p in predictions:
        question = p.get("question", p.get("_path", Path("?")).stem)
        domain = str(p.get("domain", "?")).title()
        outcome = str(p.get("outcome_label", "?")).upper()
        note = p.get("resolution_note", "")
        pred_date = p.get("date", "?")
        resolved_date = p.get("resolved_date", "?")

        lines.append(f"### {question}")
        lines.append(f"")
        lines.append(f"**Domain:** {domain} | **Predicted:** {pred_date} | **Resolved:** {resolved_date}")
        lines.append(f"**Verdict:** {outcome}")
        if note:
            lines.append(f"**Note:** {note}")
        lines.append(f"")

        # Extract a lesson if present in body
        body = p.get("_body", "")
        if "## Resolution" in body:
            resolution_section = body.split("## Resolution")[-1]
            # Pull out any lessons or notes
            for line in resolution_section.split("\n"):
                if "lesson" in line.lower() or "missed" in line.lower():
                    lines.append(f"> {line.strip()}")
            lines.append(f"")

    # Calibration note
    if CALIBRATION_FILE.exists():
        try:
            cal = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
            lines.extend([
                f"## Calibration Status",
                f"",
                f"Current domain adjustments (v{cal.get('version', '?')}):",
                f"",
            ])
            for domain, d in cal.get("domains", {}).items():
                adj = d.get("adjustment", 0)
                direction = "overconfident" if adj < 0 else "underconfident" if adj > 0 else "calibrated"
                lines.append(f"- **{domain.title()}**: {direction} by {abs(adj):.0%} (n={d.get('n_resolved', '?')})")
            lines.append("")
        except (json.JSONDecodeError, OSError):
            pass

    lines.extend([
        f"---",
        f"",
        f"*Generated by prediction_debrief.py on {TODAY}. Edit before publishing.*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Debrief Generator")
    parser.add_argument("--force", action="store_true", help="Skip threshold check")
    parser.add_argument("--dry-run", action="store_true", help="Show what would generate")
    parser.add_argument("--status", action="store_true", help="Show debrief state")
    args = parser.parse_args()

    state = load_state()
    resolved = load_resolved()
    n_resolved = len(resolved)
    last_count = state.get("last_debrief_at_count", 0)

    if args.status:
        print(f"Debrief Status -- {TODAY}")
        print(f"  Resolved predictions: {n_resolved}")
        print(f"  Last debrief at count: {last_count}")
        print(f"  Debriefs written: {state.get('debriefs_written', 0)}")
        print(f"  Next debrief at: {last_count + DEBRIEF_EVERY}")
        eligible = n_resolved >= last_count + DEBRIEF_EVERY
        print(f"  Eligible: {'YES' if eligible else 'NO'}")
        return 0

    print(f"Debrief Generator -- {TODAY}")
    print(f"  Resolved: {n_resolved}, Last debrief at: {last_count}")

    if not args.force:
        if n_resolved < last_count + DEBRIEF_EVERY:
            print(f"  Below threshold (need {last_count + DEBRIEF_EVERY}, have {n_resolved}). Use --force.")
            return 0

    if n_resolved == 0:
        print("  No resolved predictions. Nothing to debrief.")
        return 0

    # Select predictions for this debrief (the batch since last debrief)
    # Sort by resolved_date and take the latest batch
    batch = resolved[last_count:] if last_count < n_resolved else resolved
    if not batch:
        batch = resolved[-DEBRIEF_EVERY:]  # fallback: last 5

    debrief_number = state.get("debriefs_written", 0) + 1
    draft = generate_draft(batch, debrief_number)

    if args.dry_run:
        print(f"\n[DRY RUN] Would write debrief #{debrief_number} covering {len(batch)} predictions:")
        print(draft[:500] + "..." if len(draft) > 500 else draft)
        return 0

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFTS_DIR / f"prediction-debrief-{TODAY}.md"
    draft_path.write_text(draft, encoding="utf-8")
    print(f"  Wrote: {draft_path.relative_to(REPO_ROOT)}")

    # Update state
    state["last_debrief_at_count"] = n_resolved
    state["debriefs_written"] = debrief_number
    state["last_debrief_date"] = TODAY
    save_state(state)

    print(f"  Debrief #{debrief_number} complete ({len(batch)} predictions).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
