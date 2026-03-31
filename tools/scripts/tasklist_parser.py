#!/usr/bin/env python3
"""Tasklist parser -- structured extraction from orchestration/tasklist.md.

Deterministic CLI tool for skills that need tasklist data:
  /quality-gate, /project-orchestrator, /vitals, /telos-update

Usage:
    python tools/scripts/tasklist_parser.py                    # table summary
    python tools/scripts/tasklist_parser.py --json             # full JSON
    python tools/scripts/tasklist_parser.py --json --pretty    # indented JSON
    python tools/scripts/tasklist_parser.py --tier 1           # filter by tier
    python tools/scripts/tasklist_parser.py --status unchecked # unchecked only
    python tools/scripts/tasklist_parser.py --phase 4E         # filter by phase tag
    python tools/scripts/tasklist_parser.py --projects         # active projects table
    python tools/scripts/tasklist_parser.py --completion       # completion summary only

Output: JSON blob or ASCII table to stdout. Zero LLM tokens consumed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"


def parse_task_line(line: str) -> dict | None:
    """Parse a markdown task line into structured data.

    Handles:
      - [x] **Title** -- Description (date)
      - [ ] **Title** -- Description
      - [x] **Title** (date)
    """
    m = re.match(
        r"^[-*]\s+\[([ xX])\]\s+"
        r"(?:\*\*(.+?)\*\*)?"     # bold title (optional)
        r"\s*[-\u2014]*\s*"       # separator (-- or em-dash)
        r"(.*)",                   # rest of line
        line.strip(),
    )
    if not m:
        return None

    checked = m.group(1).lower() == "x"
    raw_title = (m.group(2) or "").strip()
    description = (m.group(3) or "").strip()

    # Extract date if present at end: (YYYY-MM-DD) or (date)
    date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)\s*$", description)
    completed_date = date_match.group(1) if date_match else None
    if date_match:
        description = description[: date_match.start()].strip().rstrip(".")

    # Extract phase tag from title: 4E-S1, 3C-5, 5-pre, etc.
    phase_match = re.match(r"^(\d[A-Z]?(?:-[A-Z]?\d+)?(?:-pre)?):?\s*", raw_title)
    phase_tag = phase_match.group(1) if phase_match else None
    title = raw_title[phase_match.end():].strip() if phase_match else raw_title

    # Strip strikethrough
    title = re.sub(r"~~(.+?)~~", r"\1", title)

    return {
        "checked": checked,
        "title": title,
        "raw_title": raw_title,
        "description": description,
        "phase_tag": phase_tag,
        "completed_date": completed_date,
    }


def parse_project_line(line: str) -> dict | None:
    """Parse a markdown table row for active projects."""
    parts = [c.strip() for c in line.split("|")]
    parts = [p for p in parts if p]
    if len(parts) < 4 or parts[0].startswith("---"):
        return None
    # Skip header row
    if parts[0].lower() in ("project", "---"):
        return None
    return {
        "name": parts[0],
        "status": parts[1] if len(parts) > 1 else "",
        "health": parts[2] if len(parts) > 2 else "",
        "owner": parts[3] if len(parts) > 3 else "",
        "next_action": parts[4] if len(parts) > 4 else "",
    }


def parse_completion_table(line: str) -> dict | None:
    """Parse a completion summary table row."""
    parts = [c.strip() for c in line.split("|")]
    parts = [p for p in parts if p]
    if len(parts) < 3 or parts[0].startswith("---"):
        return None
    if parts[0].lower() in ("phase", "---"):
        return None
    return {
        "phase": parts[0],
        "status": parts[1],
        "remaining": parts[2],
    }


def parse_tasklist(filepath: Path) -> dict:
    """Parse the full tasklist.md into structured data."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = {
        "source": str(filepath),
        "tiers": {},
        "phases": {},
        "projects": [],
        "completion_summary": [],
        "parked": [],
        "stats": {
            "total_tasks": 0,
            "checked": 0,
            "unchecked": 0,
            "by_tier": {},
        },
    }

    current_tier = None
    current_phase = None
    current_section = None
    in_projects_table = False
    in_completion_table = False
    in_parked = False

    for line in lines:
        stripped = line.strip()

        # Detect tier headers
        tier_match = re.match(r"^###\s+Tier\s+(\d+):\s*(.+)", stripped)
        if tier_match:
            tier_num = int(tier_match.group(1))
            tier_name = tier_match.group(2).strip()
            current_tier = tier_num
            current_section = "tier"
            in_projects_table = False
            in_completion_table = False
            in_parked = False
            if tier_num not in result["tiers"]:
                result["tiers"][tier_num] = {
                    "name": tier_name,
                    "tasks": [],
                }
            continue

        # Detect phase headers
        phase_match = re.match(r"^##\s+Phase\s+(\d+[A-Z]?):\s*(.+)", stripped)
        if phase_match:
            phase_id = phase_match.group(1)
            phase_name = phase_match.group(2).strip()
            current_phase = phase_id
            current_section = "phase"
            current_tier = None
            in_projects_table = False
            in_completion_table = False
            in_parked = False
            if phase_id not in result["phases"]:
                result["phases"][phase_id] = {
                    "name": phase_name,
                    "tasks": [],
                }
            continue

        # Detect sub-phase headers (### Phase 2A, etc.)
        subphase_match = re.match(
            r"^###\s+Phase\s+(\d+[A-Z]):\s*(.+)", stripped
        )
        if subphase_match:
            phase_id = subphase_match.group(1)
            phase_name = subphase_match.group(2).strip()
            current_phase = phase_id
            current_section = "phase"
            current_tier = None
            if phase_id not in result["phases"]:
                result["phases"][phase_id] = {
                    "name": phase_name,
                    "tasks": [],
                }
            continue

        # Detect "New Skills" as a section
        if re.match(r"^###\s+New Skills", stripped):
            current_section = "new_skills"
            current_tier = None
            in_parked = False
            continue

        # Detect Parked section
        if re.match(r"^###\s+Parked", stripped):
            in_parked = True
            current_section = "parked"
            current_tier = None
            continue

        # Detect Active Projects table
        if re.match(r"^##\s+Active Projects", stripped):
            in_projects_table = True
            current_section = "projects"
            current_tier = None
            in_parked = False
            continue

        # Detect Completion Summary table
        if re.match(r"^##\s+Completion Summary", stripped):
            in_completion_table = True
            current_section = "completion"
            current_tier = None
            in_parked = False
            continue

        # Detect any other ## header resets context
        if stripped.startswith("## ") and current_section not in (
            "projects",
            "completion",
        ):
            current_tier = None
            current_section = None
            in_parked = False
            continue

        # Parse project table rows
        if in_projects_table and "|" in stripped:
            proj = parse_project_line(stripped)
            if proj:
                result["projects"].append(proj)
            continue

        # Parse completion table rows
        if in_completion_table and "|" in stripped:
            comp = parse_completion_table(stripped)
            if comp:
                result["completion_summary"].append(comp)
            continue

        # Parse parked items (just bullet text, not checkboxes)
        if in_parked and stripped.startswith("- **"):
            title_m = re.match(r"^-\s+\*\*(.+?)\*\*\s*[-\u2014]*\s*(.*)", stripped)
            if title_m:
                result["parked"].append({
                    "title": title_m.group(1).strip(),
                    "description": title_m.group(2).strip(),
                })
            continue

        # Skip separator lines and non-task content
        if stripped.startswith("- **---"):
            continue

        # Parse task lines
        task = parse_task_line(stripped)
        if task is None:
            continue

        # Also try to parse from table rows (Phase 2 uses tables)
        # Table format: | # | Task | Build In | Notes |
        # Skip these -- they use strikethrough ~~DONE~~ patterns

        result["stats"]["total_tasks"] += 1
        if task["checked"]:
            result["stats"]["checked"] += 1
        else:
            result["stats"]["unchecked"] += 1

        # Assign to current tier or phase
        if current_tier is not None and current_tier in result["tiers"]:
            result["tiers"][current_tier]["tasks"].append(task)
            tier_key = f"tier_{current_tier}"
            if tier_key not in result["stats"]["by_tier"]:
                result["stats"]["by_tier"][tier_key] = {"checked": 0, "unchecked": 0}
            if task["checked"]:
                result["stats"]["by_tier"][tier_key]["checked"] += 1
            else:
                result["stats"]["by_tier"][tier_key]["unchecked"] += 1
        elif current_phase is not None and current_phase in result["phases"]:
            result["phases"][current_phase]["tasks"].append(task)
        elif current_section == "new_skills":
            # Put new skills in a virtual tier
            if "new_skills" not in result["tiers"]:
                result["tiers"]["new_skills"] = {
                    "name": "New Skills",
                    "tasks": [],
                }
            result["tiers"]["new_skills"]["tasks"].append(task)

    # Compute completion percentage
    total = result["stats"]["total_tasks"]
    result["stats"]["completion_pct"] = (
        round(result["stats"]["checked"] / total * 100, 1) if total > 0 else 0.0
    )

    return result


def filter_tasks(data: dict, tier: int | None, status: str | None, phase: str | None) -> list[dict]:
    """Extract filtered task list from parsed data."""
    tasks = []

    # Collect from tiers
    for tier_id, tier_data in data["tiers"].items():
        for t in tier_data["tasks"]:
            t["_tier"] = tier_id
            tasks.append(t)

    # Collect from phases
    for phase_id, phase_data in data["phases"].items():
        for t in phase_data["tasks"]:
            t["_phase"] = phase_id
            tasks.append(t)

    # Apply filters
    if tier is not None:
        tasks = [t for t in tasks if t.get("_tier") == tier]

    if status == "checked":
        tasks = [t for t in tasks if t["checked"]]
    elif status == "unchecked":
        tasks = [t for t in tasks if not t["checked"]]

    if phase is not None:
        phase_upper = phase.upper()
        tasks = [
            t
            for t in tasks
            if (t.get("phase_tag") or "").upper().startswith(phase_upper)
            or (t.get("_phase") or "").upper().startswith(phase_upper)
        ]

    return tasks


def format_table(data: dict, tier: int | None, status: str | None, phase: str | None) -> str:
    """Format as ASCII table."""
    lines = []

    # Stats header
    s = data["stats"]
    lines.append(f"Tasklist: {s['total_tasks']} tasks | {s['checked']} done | {s['unchecked']} open | {s['completion_pct']}% complete")
    lines.append("")

    # Tier breakdown
    for tier_id, tier_data in sorted(
        data["tiers"].items(),
        key=lambda x: (isinstance(x[0], str), x[0]),
    ):
        if tier is not None and tier_id != tier:
            continue
        tier_label = f"Tier {tier_id}" if isinstance(tier_id, int) else str(tier_id).title()
        tier_tasks = tier_data["tasks"]

        # Apply status filter
        if status == "checked":
            tier_tasks = [t for t in tier_tasks if t["checked"]]
        elif status == "unchecked":
            tier_tasks = [t for t in tier_tasks if not t["checked"]]

        # Apply phase filter
        if phase is not None:
            phase_upper = phase.upper()
            tier_tasks = [
                t for t in tier_tasks
                if (t.get("phase_tag") or "").upper().startswith(phase_upper)
            ]

        if not tier_tasks:
            continue

        checked = sum(1 for t in tier_data["tasks"] if t["checked"])
        total = len(tier_data["tasks"])
        lines.append(f"  {tier_label}: {tier_data['name']} ({checked}/{total})")

        for t in tier_tasks:
            mark = "[x]" if t["checked"] else "[ ]"
            tag = f"({t['phase_tag']}) " if t.get("phase_tag") else ""
            date = f" [{t['completed_date']}]" if t.get("completed_date") else ""
            lines.append(f"    {mark} {tag}{t['title']}{date}")

        lines.append("")

    # Projects
    if data["projects"] and tier is None and phase is None:
        lines.append("  Active Projects:")
        for p in data["projects"]:
            health_icon = {"green": "OK", "yellow": "!!", "red": "XX"}.get(
                p["health"], "??"
            )
            lines.append(f"    [{health_icon}] {p['name']} -- {p['status']}")
        lines.append("")

    # Completion summary
    if data["completion_summary"] and tier is None and phase is None:
        lines.append("  Phase Completion:")
        for c in data["completion_summary"]:
            lines.append(f"    {c['phase']:6s} {c['status']:20s} remaining: {c['remaining']}")

    return "\n".join(lines)


def format_completion_only(data: dict) -> str:
    """Just the completion summary."""
    lines = []
    s = data["stats"]
    lines.append(f"Total: {s['total_tasks']} tasks | {s['checked']} done | {s['unchecked']} open | {s['completion_pct']}%")
    lines.append("")
    for tier_id, tier_data in sorted(
        data["tiers"].items(),
        key=lambda x: (isinstance(x[0], str), x[0]),
    ):
        if isinstance(tier_id, int):
            checked = sum(1 for t in tier_data["tasks"] if t["checked"])
            total = len(tier_data["tasks"])
            lines.append(f"  Tier {tier_id}: {checked}/{total}")
    lines.append("")
    for c in data["completion_summary"]:
        lines.append(f"  {c['phase']:6s} {c['status']}")
    return "\n".join(lines)


def _sanitize_ascii(text: str) -> str:
    """Replace common Unicode chars with ASCII equivalents for Windows cp1252."""
    replacements = {
        "\u2192": "->",   # right arrow
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00d7": "x",    # multiplication sign
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Parse orchestration/tasklist.md into structured data"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    parser.add_argument("--tier", type=int, help="Filter by tier number (1, 2, 3)")
    parser.add_argument("--status", choices=["checked", "unchecked", "all"], default="all",
                        help="Filter by check status")
    parser.add_argument("--phase", type=str, help="Filter by phase tag (e.g., 4E, 3C)")
    parser.add_argument("--projects", action="store_true", help="Show active projects only")
    parser.add_argument("--completion", action="store_true", help="Show completion summary only")
    parser.add_argument("--file", type=str, help="Path to tasklist.md (default: orchestration/tasklist.md)")

    args = parser.parse_args()

    filepath = Path(args.file) if args.file else TASKLIST
    if not filepath.exists():
        print(f"ERROR: tasklist not found at {filepath}", file=sys.stderr)
        sys.exit(1)

    data = parse_tasklist(filepath)

    if args.json:
        # Apply filters to produce filtered view
        if args.tier or args.status != "all" or args.phase:
            filtered = filter_tasks(data, args.tier, args.status if args.status != "all" else None, args.phase)
            output = {"tasks": filtered, "count": len(filtered), "stats": data["stats"]}
        elif args.projects:
            output = {"projects": data["projects"]}
        elif args.completion:
            output = {"completion_summary": data["completion_summary"], "stats": data["stats"]}
        else:
            output = data

        indent = 2 if args.pretty else None
        out = json.dumps(output, indent=indent, default=str)
        print(_sanitize_ascii(out))
    else:
        if args.projects:
            for p in data["projects"]:
                health_icon = {"green": "OK", "yellow": "!!", "red": "XX"}.get(p["health"], "??")
                print(_sanitize_ascii(f"  [{health_icon}] {p['name']} -- {p['status']}"))
        elif args.completion:
            print(_sanitize_ascii(format_completion_only(data)))
        else:
            status_filter = args.status if args.status != "all" else None
            print(_sanitize_ascii(format_table(data, args.tier, status_filter, args.phase)))


if __name__ == "__main__":
    main()
