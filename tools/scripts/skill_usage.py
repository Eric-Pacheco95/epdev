#!/usr/bin/env python3
"""Skill usage tracker -- scans Claude Code conversation logs for Skill invocations.

Outputs JSON compatible with the heartbeat snapshot format (metrics dict with
value/unit/detail keys).

Usage:
    python tools/scripts/skill_usage.py          # human-readable
    python tools/scripts/skill_usage.py --json    # heartbeat-compatible JSON
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJ_DIR = Path.home() / ".claude" / "projects" / "C--Users-ericp-Github-epdev"


def scan_skill_invocations(proj_dir: Path = PROJ_DIR) -> list[tuple[str, datetime]]:
    """Scan JSONL conversation logs for Skill tool_use blocks.

    Returns list of (skill_name, timestamp) tuples.
    """
    results: list[tuple[str, datetime]] = []
    pattern = str(proj_dir / "**" / "*.jsonl")
    for fpath in glob.glob(pattern, recursive=True):
        try:
            fh = open(fpath, "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
                for line in fh:
                    line = line.strip()
                    if not line or '"Skill"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if obj.get("type") != "assistant":
                        continue
                    ts_str = obj.get("timestamp", "")
                    content = obj.get("message", {}).get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if (isinstance(block, dict)
                                and block.get("type") == "tool_use"
                                and block.get("name") == "Skill"):
                            skill = block.get("input", {}).get("skill", "")
                            if not skill:
                                continue
                            try:
                                ts = datetime.fromisoformat(
                                    ts_str.replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                continue
                            results.append((skill, ts))
    return results


def aggregate_usage(
    invocations: list[tuple[str, datetime]],
) -> dict:
    """Aggregate invocation counts over 7d and 30d windows.

    Returns dict with per-skill counts and tier assignments.
    """
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    counts_7d: Counter[str] = Counter()
    counts_30d: Counter[str] = Counter()

    for skill, ts in invocations:
        if ts >= cutoff_30d:
            counts_30d[skill] += 1
        if ts >= cutoff_7d:
            counts_7d[skill] += 1

    # Tier assignment based on 30d counts
    all_skills = set(counts_30d.keys())
    ranked = counts_30d.most_common()
    tiers: dict[str, str] = {}
    for i, (skill, count) in enumerate(ranked):
        if count >= 10:
            tiers[skill] = "top"
        elif count >= 4:
            tiers[skill] = "mid"
        else:
            tiers[skill] = "low"

    return {
        "counts_7d": dict(counts_7d.most_common()),
        "counts_30d": dict(counts_30d.most_common()),
        "tiers": tiers,
        "total_invocations_7d": sum(counts_7d.values()),
        "total_invocations_30d": sum(counts_30d.values()),
        "unique_skills_30d": len(all_skills),
    }


def to_heartbeat_metrics(usage: dict) -> dict:
    """Convert aggregated usage to heartbeat snapshot metric format."""
    top_5 = list(usage["counts_30d"].items())[:5]
    top_str = ", ".join(f"{s}({n})" for s, n in top_5) if top_5 else "none"

    return {
        "skill_invocations_7d": {
            "value": usage["total_invocations_7d"],
            "unit": "count",
        },
        "skill_invocations_30d": {
            "value": usage["total_invocations_30d"],
            "unit": "count",
        },
        "unique_skills_30d": {
            "value": usage["unique_skills_30d"],
            "unit": "count",
        },
        "skill_top5_30d": {
            "value": top_str,
            "unit": "histogram",
            "detail": usage["counts_30d"],
        },
        "skill_tiers": {
            "value": len(usage["tiers"]),
            "unit": "count",
            "detail": usage["tiers"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis skill usage tracker")
    parser.add_argument("--json", action="store_true", help="Output heartbeat-compatible JSON")
    args = parser.parse_args()

    invocations = scan_skill_invocations()
    usage = aggregate_usage(invocations)

    if args.json:
        metrics = to_heartbeat_metrics(usage)
        print(json.dumps({"metrics": metrics, "raw": usage}, indent=2))
    else:
        print(f"Skill Usage (trailing 30d / 7d)")
        print("-" * 45)
        print(f"Total invocations: {usage['total_invocations_30d']} (30d) / "
              f"{usage['total_invocations_7d']} (7d)")
        print(f"Unique skills used: {usage['unique_skills_30d']}")
        print()
        for skill, count in usage["counts_30d"].items():
            tier = usage["tiers"].get(skill, "?")
            c7 = usage["counts_7d"].get(skill, 0)
            print(f"  [{tier:>3}] {skill:<28} {count:>3} (30d)  {c7:>3} (7d)")


if __name__ == "__main__":
    main()
