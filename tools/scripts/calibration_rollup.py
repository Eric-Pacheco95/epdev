#!/usr/bin/env python3
"""
calibration_rollup.py — Weekly calibration rollup for the four-axis Task Typing rubric.

Reads data/review_gate_log.jsonl and emits data/calibration_weekly.md with four
metrics, their current values, their thresholds, and a breach flag when a metric
has been red for 2 consecutive weeks.

Metrics:
  1. label_match_rate      — % of heuristic-proposed axes kept unchanged by Eric
  2. danger_cell_catch_rate — % of (solvability=low ∧ verifiability=low) runs using HITL
  3. vhigh_false_positive  — % of verifiability=high runs that bypassed script-oracle
  4. vlow_under_review     — % of verifiability=low runs that did NOT use HITL/opus

Usage:
    python tools/scripts/calibration_rollup.py
    python tools/scripts/calibration_rollup.py --log path/to/log.jsonl
    python tools/scripts/calibration_rollup.py --out path/to/output.md
    python tools/scripts/calibration_rollup.py --help
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_LOG = DATA_DIR / "review_gate_log.jsonl"
DEFAULT_OUT = DATA_DIR / "calibration_weekly.md"

MIN_SAMPLE = 10  # minimum N to compute a metric

THRESHOLDS = {
    "label_match_rate":       {"green": 0.60, "direction": ">=", "unit": "%"},
    "danger_cell_catch_rate": {"green": 0.80, "direction": ">=", "unit": "%"},
    "vhigh_false_positive":   {"green": 0.10, "direction": "<=", "unit": "%"},
    "vlow_under_review":      {"green": 0.20, "direction": "<=", "unit": "%"},
}

HITL_EVALUATORS = {"hitl", "opus-subagent", "second-opinion"}
VHIGH_ORACLE = "script-oracle"


def _load_log(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def _filter_four_axis(entries: list[dict]) -> list[dict]:
    """Only entries with all four Task Typing axes."""
    required = {"stakes", "ambiguity", "solvability", "verifiability"}
    return [e for e in entries if required.issubset(e.keys())]


def _metric_label_match_rate(entries: list[dict]) -> tuple[float | None, int]:
    """
    label_match_rate: % of entries where the proposed axes were kept unchanged.
    Tracked via entries with 'label_override: false' (no Eric edit) vs 'label_override: true'.
    If field absent in all entries, returns None (insufficient signal).
    """
    relevant = [e for e in entries if "label_override" in e]
    n = len(relevant)
    if n < MIN_SAMPLE:
        return None, n
    kept = sum(1 for e in relevant if not e.get("label_override", True))
    return kept / n, n


def _metric_danger_cell_catch_rate(entries: list[dict]) -> tuple[float | None, int]:
    """
    danger_cell_catch_rate: % of (solvability=low ∧ verifiability=low) runs
    that used a HITL evaluator.
    """
    danger = [
        e for e in entries
        if e.get("solvability") == "low" and e.get("verifiability") == "low"
        and not e.get("rate_limited", False)
    ]
    n = len(danger)
    if n < MIN_SAMPLE:
        return None, n
    caught = sum(1 for e in danger if e.get("evaluator") in HITL_EVALUATORS)
    return caught / n, n


def _metric_vhigh_false_positive(entries: list[dict]) -> tuple[float | None, int]:
    """
    vhigh_false_positive: % of verifiability=high runs that did NOT use the script-oracle
    (i.e., a Sonnet/Opus/HITL subagent was spawned when it wasn't needed).
    """
    vhigh = [
        e for e in entries
        if e.get("verifiability") == "high"
        and not e.get("rate_limited", False)
    ]
    n = len(vhigh)
    if n < MIN_SAMPLE:
        return None, n
    false_pos = sum(1 for e in vhigh if e.get("evaluator") != VHIGH_ORACLE)
    return false_pos / n, n


def _metric_vlow_under_review(entries: list[dict]) -> tuple[float | None, int]:
    """
    vlow_under_review: % of verifiability=low runs that did NOT use HITL/opus
    (missed escalation opportunity).
    """
    vlow = [
        e for e in entries
        if e.get("verifiability") == "low"
        and not e.get("rate_limited", False)
    ]
    n = len(vlow)
    if n < MIN_SAMPLE:
        return None, n
    under = sum(1 for e in vlow if e.get("evaluator") not in HITL_EVALUATORS)
    return under / n, n


def _status(metric_name: str, value: float | None) -> str:
    if value is None:
        return "INSUFFICIENT_DATA"
    thresh = THRESHOLDS[metric_name]
    pct = value * 100
    green_val = thresh["green"] * 100
    if thresh["direction"] == ">=":
        return "GREEN" if pct >= green_val else "RED"
    return "GREEN" if pct <= green_val else "RED"


def _fmt_value(value: float | None, n: int) -> str:
    if value is None:
        return f"insufficient data (N={n}<{MIN_SAMPLE})"
    return f"{value * 100:.1f}% (N={n})"


def _fmt_threshold(metric_name: str) -> str:
    thresh = THRESHOLDS[metric_name]
    return f"{thresh['direction']} {thresh['green'] * 100:.0f}%"


def generate_report(entries: list[dict]) -> str:
    four_axis = _filter_four_axis(entries)
    all_count = len(entries)
    four_axis_count = len(four_axis)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    m1_val, m1_n = _metric_label_match_rate(four_axis)
    m2_val, m2_n = _metric_danger_cell_catch_rate(four_axis)
    m3_val, m3_n = _metric_vhigh_false_positive(four_axis)
    m4_val, m4_n = _metric_vlow_under_review(four_axis)

    metrics = [
        ("label_match_rate",       "Label Match Rate",            m1_val, m1_n),
        ("danger_cell_catch_rate", "Danger-Cell Catch Rate",      m2_val, m2_n),
        ("vhigh_false_positive",   "V=high False-Positive Rate",  m3_val, m3_n),
        ("vlow_under_review",      "V=low Under-Review Rate",     m4_val, m4_n),
    ]

    rows = []
    breach_flags = []
    for name, label, val, n in metrics:
        status = _status(name, val)
        fmt_val = _fmt_value(val, n)
        fmt_thresh = _fmt_threshold(name)
        rows.append(f"| {label} | {fmt_val} | {fmt_thresh} | {status} |")
        if status == "RED":
            breach_flags.append(f"- **{label}** is RED ({fmt_val}, threshold: {fmt_thresh})")

    table = "\n".join(rows)

    breach_section = ""
    if breach_flags:
        breach_section = "\n## Breach Flags\n\n" + "\n".join(breach_flags) + "\n\n> **Action required:** if any metric is RED for 2 consecutive weekly rollups, revise the heuristic keyword lists in `orchestration/steering/task-typing.md` before the next build cycle.\n"

    return f"""# Calibration Rollup — {now}

## Summary

- Total log entries: {all_count}
- Entries with four-axis labels: {four_axis_count}
- Minimum sample threshold: N≥{MIN_SAMPLE} per metric

## Metrics

| Metric | Current Value | Threshold | Status |
|--------|---------------|-----------|--------|
{table}
{breach_section}
## Metric Definitions

| Metric | What it measures | Source field |
|--------|-----------------|--------------|
| Label Match Rate | % of heuristic-proposed axes kept unchanged by Eric during TSV review | `label_override` (bool) |
| Danger-Cell Catch Rate | % of (S=low ∧ V=low) runs that used HITL evaluator | `solvability`, `verifiability`, `evaluator` |
| V=high False-Positive Rate | % of V=high runs that bypassed the script-oracle (unnecessary subagent spawn) | `verifiability`, `evaluator` |
| V=low Under-Review Rate | % of V=low runs without HITL/opus escalation (missed escalation) | `verifiability`, `evaluator` |

## Next Steps

- If all metrics show insufficient data: calibration loop is operational — metrics will accumulate as PRDs ship with frontmatter.
- If Danger-Cell Catch Rate < 80% for 2 consecutive weeks: revise `orchestration/steering/autonomous-rules.md` fluent-bluff rules.
- If V=high False-Positive Rate > 10% for 2 consecutive weeks: update `orchestration/steering/verifiability-spectrum.md` V=high routing.
- If Label Match Rate < 60%: run stamper in Opus-subagent mode instead of keyword heuristic.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Weekly calibration rollup for the four-axis Task Typing rubric.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--log", type=Path, default=DEFAULT_LOG,
        help=f"Path to review_gate_log.jsonl (default: {DEFAULT_LOG})"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"Output path for calibration_weekly.md (default: {DEFAULT_OUT})"
    )
    args = parser.parse_args()

    entries = _load_log(args.log)
    if not entries:
        msg = f"insufficient data (N=0<{MIN_SAMPLE}) — log empty or not found: {args.log}"
        print(msg)

    report = generate_report(entries)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Calibration rollup written -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
