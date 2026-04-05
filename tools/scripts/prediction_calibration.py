#!/usr/bin/env python3
"""Prediction Calibration Loop -- computes per-domain accuracy and bias adjustments.

Reads all resolved predictions, groups by domain, computes accuracy rate and
overconfidence/underconfidence bias, writes data/calibration.json and
data/calibration_narrative.md.

Triggers: when forward-looking resolved count >= 20 AND crosses a multiple of 5.
Can be forced with --force for testing.

Usage:
    python tools/scripts/prediction_calibration.py           # normal (checks threshold)
    python tools/scripts/prediction_calibration.py --force   # skip threshold, run anyway
    python tools/scripts/prediction_calibration.py --status  # show current calibration state
    python tools/scripts/prediction_calibration.py --dry-run # compute but don't write

Outputs:
    data/calibration.json              -- per-domain adjustments read by /make-prediction
    data/calibration_narrative.md      -- prose bias summary
    memory/learning/signals/           -- calibration signal
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions"
BACKTEST_DIR    = PREDICTIONS_DIR / "backtest"
CALIBRATION_FILE = REPO_ROOT / "data" / "calibration.json"
NARRATIVE_FILE   = REPO_ROOT / "data" / "calibration_narrative.md"
SIGNALS_DIR      = REPO_ROOT / "memory" / "learning" / "signals"
TRIGGER_FILE     = REPO_ROOT / "data" / "backlog_resolution_trigger.json"

TODAY = date.today().isoformat()

ADJUSTMENT_BOUNDS = (-0.15, 0.15)
THRESHOLD_RESOLVED = 20
THRESHOLD_MULTIPLE = 5


# ---------------------------------------------------------------------------
# Prediction loading
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter from a prediction markdown file."""
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
        return fm
    except yaml.YAMLError:
        return None


def load_resolved_predictions() -> tuple[list[dict], list[dict]]:
    """Load resolved predictions. Returns (forward, backtest_reviewed)."""
    forward = []
    backtest = []

    # Forward-looking predictions (top-level data/predictions/*.md)
    for path in PREDICTIONS_DIR.glob("*.md"):
        fm = parse_frontmatter(path)
        if not fm:
            continue
        status = str(fm.get("status", "")).lower()
        if status != "resolved":
            continue
        if fm.get("backtested"):
            continue
        forward.append(fm)

    # Reviewed backtests (data/predictions/backtest/*.md with status: reviewed)
    if BACKTEST_DIR.exists():
        for path in BACKTEST_DIR.glob("*.md"):
            fm = parse_frontmatter(path)
            if not fm:
                continue
            status = str(fm.get("status", "")).lower()
            if status != "reviewed":
                continue
            backtest.append(fm)

    return forward, backtest


# ---------------------------------------------------------------------------
# Calibration computation
# ---------------------------------------------------------------------------

def compute_domain_stats(predictions: list[dict], weight: float = 1.0) -> dict:
    """Compute per-domain accuracy and bias stats.

    Returns {domain: {n, correct, wrong, partial, accuracy, mean_confidence_correct,
                      mean_confidence_incorrect, overconfidence_delta, weight}}
    """
    domains: dict[str, dict] = {}

    for fm in predictions:
        domain = str(fm.get("domain", "other")).lower()
        if domain not in domains:
            domains[domain] = {
                "n_resolved": 0,
                "correct": 0,
                "wrong": 0,
                "partial": 0,
                "confidence_correct": [],
                "confidence_incorrect": [],
                "weight": weight,
            }
        d = domains[domain]
        d["n_resolved"] += 1

        outcome = str(fm.get("outcome_label", "")).lower()
        confidence = _extract_confidence(fm)

        if outcome == "correct":
            d["correct"] += 1
            if confidence is not None:
                d["confidence_correct"].append(confidence)
        elif outcome == "wrong":
            d["wrong"] += 1
            if confidence is not None:
                d["confidence_incorrect"].append(confidence)
        elif outcome == "partial":
            d["partial"] += 1
            # Partial counts as 0.5 correct for accuracy
            if confidence is not None:
                d["confidence_correct"].append(confidence)
                d["confidence_incorrect"].append(confidence)

    # Compute derived stats
    for domain, d in domains.items():
        total = d["n_resolved"]
        effective_correct = d["correct"] + 0.5 * d["partial"]
        d["accuracy"] = round(effective_correct / total, 3) if total > 0 else 0.0

        mean_conf_correct = (
            sum(d["confidence_correct"]) / len(d["confidence_correct"])
            if d["confidence_correct"] else None
        )
        mean_conf_incorrect = (
            sum(d["confidence_incorrect"]) / len(d["confidence_incorrect"])
            if d["confidence_incorrect"] else None
        )
        d["mean_confidence_correct"] = (
            round(mean_conf_correct, 3) if mean_conf_correct is not None else None
        )
        d["mean_confidence_incorrect"] = (
            round(mean_conf_incorrect, 3) if mean_conf_incorrect is not None else None
        )

        # Overconfidence delta: positive means overconfident (stated prob > actual accuracy)
        if mean_conf_correct is not None and total >= 3:
            d["overconfidence_delta"] = round(mean_conf_correct - d["accuracy"], 3)
        else:
            d["overconfidence_delta"] = 0.0

        # Clean up intermediate lists
        del d["confidence_correct"]
        del d["confidence_incorrect"]

    return domains


def _extract_confidence(fm: dict) -> float | None:
    """Extract primary confidence from frontmatter or content."""
    # Try frontmatter field first
    conf = fm.get("primary_confidence")
    if conf is not None:
        try:
            return float(conf)
        except (ValueError, TypeError):
            pass
    return None


def compute_adjustments(forward_stats: dict, backtest_stats: dict) -> dict:
    """Merge forward and backtest stats, compute bounded adjustments.

    Forward predictions have weight 1.0, backtests have weight 0.5.
    """
    merged: dict[str, dict] = {}

    for domain, stats in forward_stats.items():
        merged[domain] = {
            "n_forward": stats["n_resolved"],
            "n_backtest": 0,
            "accuracy_forward": stats["accuracy"],
            "accuracy_backtest": None,
            "overconfidence_delta": stats["overconfidence_delta"],
        }

    for domain, stats in backtest_stats.items():
        if domain not in merged:
            merged[domain] = {
                "n_forward": 0,
                "n_backtest": 0,
                "accuracy_forward": None,
                "accuracy_backtest": None,
                "overconfidence_delta": 0.0,
            }
        merged[domain]["n_backtest"] = stats["n_resolved"]
        merged[domain]["accuracy_backtest"] = stats["accuracy"]

        # Blend overconfidence delta: forward weight 1.0, backtest weight 0.5
        fwd_delta = merged[domain].get("overconfidence_delta", 0.0)
        bt_delta = stats.get("overconfidence_delta", 0.0)
        n_fwd = merged[domain]["n_forward"]
        n_bt = stats["n_resolved"]
        total_weight = n_fwd * 1.0 + n_bt * 0.5
        if total_weight > 0:
            blended = (fwd_delta * n_fwd * 1.0 + bt_delta * n_bt * 0.5) / total_weight
            merged[domain]["overconfidence_delta"] = round(blended, 3)

    # Compute final adjustment (negative of overconfidence delta, clamped)
    for domain, m in merged.items():
        raw_adjustment = -m["overconfidence_delta"]
        clamped = max(ADJUSTMENT_BOUNDS[0], min(ADJUSTMENT_BOUNDS[1], raw_adjustment))
        m["adjustment"] = round(clamped, 3)
        m["clamped"] = abs(raw_adjustment - clamped) > 0.001
        m["n_resolved"] = m["n_forward"] + m["n_backtest"]

    return merged


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def write_calibration_json(merged: dict, version: int) -> None:
    """Write data/calibration.json."""
    output = {
        "version": version,
        "updated": TODAY,
        "threshold": THRESHOLD_RESOLVED,
        "bounds": list(ADJUSTMENT_BOUNDS),
        "domains": {},
    }
    for domain, m in merged.items():
        output["domains"][domain] = {
            "adjustment": m["adjustment"],
            "n_resolved": m["n_resolved"],
            "n_forward": m["n_forward"],
            "n_backtest": m["n_backtest"],
            "accuracy_forward": m.get("accuracy_forward"),
            "accuracy_backtest": m.get("accuracy_backtest"),
            "overconfidence_delta": m["overconfidence_delta"],
            "clamped": m["clamped"],
        }

    CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CALIBRATION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(output, indent=2), encoding="utf-8")
    tmp.replace(CALIBRATION_FILE)


def write_narrative(merged: dict, version: int) -> None:
    """Write data/calibration_narrative.md -- prose bias summary."""
    lines = [
        f"# Prediction Calibration Report v{version}",
        f"",
        f"**Updated:** {TODAY}",
        f"**Threshold:** {THRESHOLD_RESOLVED} forward-looking resolved predictions",
        f"**Adjustment bounds:** [{ADJUSTMENT_BOUNDS[0]}, +{ADJUSTMENT_BOUNDS[1]}]",
        f"",
        f"---",
        f"",
    ]

    for domain, m in sorted(merged.items()):
        adj = m["adjustment"]
        direction = "overconfident" if adj < 0 else "underconfident" if adj > 0 else "well-calibrated"
        adj_pct = f"{abs(adj):.0%}"
        clamped_note = " (CLAMPED to bound)" if m["clamped"] else ""

        lines.append(f"## {domain.title()}")
        lines.append(f"")
        lines.append(f"- **Resolved:** {m['n_forward']} forward + {m['n_backtest']} backtest")

        if m.get("accuracy_forward") is not None:
            lines.append(f"- **Forward accuracy:** {m['accuracy_forward']:.0%}")
        if m.get("accuracy_backtest") is not None:
            lines.append(f"- **Backtest accuracy:** {m['accuracy_backtest']:.0%}")

        lines.append(f"- **Bias:** {direction} by {adj_pct}{clamped_note}")
        lines.append(f"- **Adjustment:** {adj:+.3f} applied to stated probabilities")
        lines.append(f"")

        if adj < -0.05:
            lines.append(
                f"Your {domain} predictions tend to state higher probabilities than "
                f"outcomes warrant. The calibration system reduces your stated confidence "
                f"by {adj_pct} in this domain."
            )
        elif adj > 0.05:
            lines.append(
                f"Your {domain} predictions are more conservative than outcomes suggest. "
                f"The calibration system increases your stated confidence by {adj_pct}."
            )
        else:
            lines.append(
                f"Your {domain} predictions are reasonably well-calibrated. "
                f"No significant adjustment needed."
            )
        lines.append(f"")

    NARRATIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    NARRATIVE_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_calibration_signal(merged: dict, version: int) -> Path:
    """Write calibration signal to learning loop."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    signal_path = SIGNALS_DIR / f"{TODAY}_calibration-update-v{version}.md"
    counter = 2
    while signal_path.exists():
        signal_path = SIGNALS_DIR / f"{TODAY}_calibration-update-v{version}-{counter}.md"
        counter += 1

    domain_lines = []
    for domain, m in sorted(merged.items()):
        domain_lines.append(
            f"- **{domain}**: adjustment {m['adjustment']:+.3f}, "
            f"{m['n_resolved']} resolved ({m['n_forward']} fwd + {m['n_backtest']} bt)"
        )

    content = f"""---
date: {TODAY}
rating: 7
category: prediction-accuracy
source: calibration
tier: A
---

# Calibration Update v{version}

Per-domain probability adjustments updated based on resolved prediction accuracy.

{chr(10).join(domain_lines)}

These adjustments are injected into /make-prediction Step 0 when the domain matches.
Bounds: [{ADJUSTMENT_BOUNDS[0]}, +{ADJUSTMENT_BOUNDS[1]}] per domain.
"""
    signal_path.write_text(content, encoding="utf-8")
    return signal_path


def clear_trigger() -> None:
    """Clear the resolution trigger after calibration runs."""
    if TRIGGER_FILE.exists():
        try:
            data = json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))
            data["pending_check"] = False
            data["last_calibration"] = TODAY
            TRIGGER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status() -> int:
    forward, backtest = load_resolved_predictions()
    print(f"Calibration Status -- {TODAY}")
    print(f"  Forward resolved: {len(forward)}")
    print(f"  Backtest reviewed: {len(backtest)}")
    print(f"  Threshold: {THRESHOLD_RESOLVED} forward (every {THRESHOLD_MULTIPLE}th)")
    print(f"  Eligible: {'YES' if len(forward) >= THRESHOLD_RESOLVED else 'NO'}")

    if CALIBRATION_FILE.exists():
        try:
            cal = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
            print(f"\n  Current calibration v{cal.get('version', '?')} ({cal.get('updated', '?')}):")
            for domain, d in cal.get("domains", {}).items():
                print(f"    {domain}: {d['adjustment']:+.3f} ({d['n_resolved']} resolved)")
        except (json.JSONDecodeError, OSError):
            print("  calibration.json exists but is unreadable")
    else:
        print("  No calibration.json yet")

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Calibration Loop")
    parser.add_argument("--force", action="store_true", help="Skip threshold check")
    parser.add_argument("--dry-run", action="store_true", help="Compute but don't write")
    parser.add_argument("--status", action="store_true", help="Show calibration state")
    args = parser.parse_args()

    if args.status:
        return show_status()

    forward, backtest = load_resolved_predictions()
    n_forward = len(forward)

    print(f"Calibration Loop -- {TODAY}")
    print(f"  Forward resolved: {n_forward}")
    print(f"  Backtest reviewed: {len(backtest)}")

    if not args.force:
        if n_forward < THRESHOLD_RESOLVED:
            print(f"  Below threshold ({n_forward}/{THRESHOLD_RESOLVED}). Use --force to override.")
            return 0
        if n_forward % THRESHOLD_MULTIPLE != 0:
            print(f"  Not at multiple of {THRESHOLD_MULTIPLE} ({n_forward}). Use --force to override.")
            return 0

    if n_forward == 0 and len(backtest) == 0:
        print("  No resolved predictions at all. Nothing to calibrate.")
        return 0

    # Compute stats
    forward_stats = compute_domain_stats(forward, weight=1.0)
    backtest_stats = compute_domain_stats(backtest, weight=0.5)
    merged = compute_adjustments(forward_stats, backtest_stats)

    # Determine version
    version = 1
    if CALIBRATION_FILE.exists():
        try:
            existing = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
            version = existing.get("version", 0) + 1
        except (json.JSONDecodeError, OSError):
            pass

    # Display results
    print(f"\n  Calibration v{version}:")
    for domain, m in sorted(merged.items()):
        clamped = " [CLAMPED]" if m["clamped"] else ""
        print(
            f"    {domain}: adj={m['adjustment']:+.3f}{clamped} "
            f"(n={m['n_resolved']}, fwd_acc={m.get('accuracy_forward', '?')}, "
            f"bt_acc={m.get('accuracy_backtest', '?')})"
        )

    if args.dry_run:
        print("\n  [DRY RUN] Would write calibration.json, narrative, and signal.")
        return 0

    # Write outputs
    write_calibration_json(merged, version)
    print(f"\n  Wrote: {CALIBRATION_FILE.relative_to(REPO_ROOT)}")

    write_narrative(merged, version)
    print(f"  Wrote: {NARRATIVE_FILE.relative_to(REPO_ROOT)}")

    signal_path = write_calibration_signal(merged, version)
    print(f"  Wrote: {signal_path.relative_to(REPO_ROOT)}")

    clear_trigger()

    # Notify Slack
    try:
        from tools.scripts.slack_notify import notify
        domain_summary = ", ".join(
            f"{d}: {m['adjustment']:+.3f}" for d, m in sorted(merged.items())
        )
        notify(
            f"*Calibration Update v{version}* ({TODAY})\n"
            f"Domains: {domain_summary}\n"
            f"Forward: {n_forward} | Backtest: {len(backtest)}",
            severity="routine",
        )
    except Exception as exc:
        print(f"  WARN: Slack notify failed: {exc}", file=sys.stderr)

    print(f"\nCalibration v{version} complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
