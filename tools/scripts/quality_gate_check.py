#!/usr/bin/env python3
"""Quality gate checker -- deterministic deliverable verification.

Deterministic CLI tool for the /quality-gate and /implement-prd skills.
Reads tasklist, cross-references decision logs, checks file existence for
referenced deliverables, and reports gaps.

Usage:
    python tools/scripts/quality_gate_check.py                     # full report
    python tools/scripts/quality_gate_check.py --json              # JSON output
    python tools/scripts/quality_gate_check.py --json --pretty     # indented JSON
    python tools/scripts/quality_gate_check.py --phase 4E          # filter by phase
    python tools/scripts/quality_gate_check.py --check-files       # verify referenced files exist
    python tools/scripts/quality_gate_check.py --decisions         # show decision log coverage
    python tools/scripts/quality_gate_check.py --prd PATH          # check ISC items in a PRD

Output: Structured report to stdout. Zero LLM tokens consumed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
DECISIONS_DIR = REPO_ROOT / "history" / "decisions"
MEMORY_WORK = REPO_ROOT / "memory" / "work"


def _sanitize_ascii(text: str) -> str:
    """Replace common Unicode chars with ASCII equivalents for Windows cp1252."""
    replacements = {
        "\u2192": "->", "\u2014": "--", "\u2013": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "*", "\u00d7": "x",
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)
    return text


def extract_file_refs(text: str) -> list[str]:
    """Extract file path references from markdown text."""
    paths = []
    # Match backtick-wrapped paths
    for m in re.finditer(r"`([^`]+\.[a-zA-Z]{1,10})`", text):
        candidate = m.group(1)
        # Must look like a file path (has / or \ and extension)
        if "/" in candidate or "\\" in candidate:
            paths.append(candidate)
    # Match markdown links to local files
    for m in re.finditer(r"\[.*?\]\(([^)]+\.[a-zA-Z]{1,10})\)", text):
        candidate = m.group(1)
        if not candidate.startswith("http"):
            paths.append(candidate)
    return paths


def check_file_exists(ref: str) -> tuple[str, bool]:
    """Check if a referenced file exists, trying common base paths."""
    # Try as-is from repo root
    candidates = [
        REPO_ROOT / ref,
        REPO_ROOT / ref.lstrip("/"),
        REPO_ROOT / ref.replace("~/", ""),
    ]
    for c in candidates:
        if c.exists():
            return str(ref), True
    return str(ref), False


def parse_isc_items(filepath: Path) -> list[dict]:
    """Parse ISC criteria from a PRD file.

    Format: - [ ] Criterion text | Verify: method
    """
    if not filepath.exists():
        return []

    text = filepath.read_text(encoding="utf-8")
    items = []

    for line in text.splitlines():
        m = re.match(
            r"^\s*[-*]\s+\[([ xX])\]\s+(.+?)(?:\s*\|\s*Verify:\s*(.+))?$",
            line.strip(),
        )
        if m:
            checked = m.group(1).lower() == "x"
            criterion = m.group(2).strip()
            verify_method = (m.group(3) or "").strip()

            # Extract confidence tag [E], [I], [R]
            conf_match = re.search(r"\[([EIR])\]", criterion)
            confidence = conf_match.group(1) if conf_match else None

            # Extract verification type [M] or [A]
            vtype_match = re.search(r"\[([MA])\]", criterion)
            verify_type = vtype_match.group(1) if vtype_match else None

            items.append({
                "checked": checked,
                "criterion": criterion,
                "verify_method": verify_method,
                "confidence": confidence,
                "verify_type": verify_type,
            })

    return items


def get_decision_log() -> list[dict]:
    """Read all decision log entries."""
    if not DECISIONS_DIR.exists():
        return []

    entries = []
    for f in sorted(DECISIONS_DIR.glob("*.md")):
        # Extract date from filename: 2026-03-28_topic.md
        name = f.stem
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})_(.+)", name)
        date = date_match.group(1) if date_match else ""
        topic = date_match.group(2).replace("-", " ") if date_match else name

        # Read first few lines for title/summary
        try:
            text = f.read_text(encoding="utf-8")
            first_line = ""
            for line in text.splitlines():
                if line.strip().startswith("#"):
                    first_line = line.strip().lstrip("#").strip()
                    break
        except Exception:
            first_line = ""

        entries.append({
            "file": f.name,
            "date": date,
            "topic": topic,
            "title": first_line or topic,
        })

    return entries


def cross_ref_decisions(tasks: list[dict], decisions: list[dict]) -> list[dict]:
    """Find tasks that reference decisions and vice versa."""
    results = []
    decision_topics = {d["topic"].lower(): d for d in decisions}

    for task in tasks:
        title_lower = (task.get("raw_title") or task.get("title", "")).lower()
        desc_lower = (task.get("description") or "").lower()

        # Check if any decision topic keywords appear in the task
        matched_decisions = []
        for topic, dec in decision_topics.items():
            # Check for keyword overlap (at least 2 significant words match)
            topic_words = set(w for w in topic.split() if len(w) > 3)
            task_words = set(
                w for w in (title_lower + " " + desc_lower).split() if len(w) > 3
            )
            overlap = topic_words & task_words
            if len(overlap) >= 2:
                matched_decisions.append(dec["file"])

        results.append({
            "task": task.get("raw_title") or task.get("title", ""),
            "checked": task.get("checked", False),
            "has_decision": len(matched_decisions) > 0,
            "decisions": matched_decisions,
        })

    return results


def run_gate_check(
    phase_filter: str | None = None,
    check_files: bool = False,
    prd_path: str | None = None,
) -> dict:
    """Run the full quality gate check."""
    report = {
        "tasklist": {},
        "decisions": {},
        "file_checks": [],
        "isc_check": None,
        "issues": [],
    }

    # 1. Parse tasklist
    if TASKLIST.exists():
        # Import our own parser
        sys.path.insert(0, str(Path(__file__).parent))
        from tasklist_parser import parse_tasklist, filter_tasks

        data = parse_tasklist(TASKLIST)
        report["tasklist"] = {
            "total": data["stats"]["total_tasks"],
            "checked": data["stats"]["checked"],
            "unchecked": data["stats"]["unchecked"],
            "completion_pct": data["stats"]["completion_pct"],
        }

        # Get unchecked tasks
        unchecked = filter_tasks(data, None, "unchecked", phase_filter)
        report["tasklist"]["open_items"] = [
            {
                "title": t.get("raw_title") or t.get("title", ""),
                "phase_tag": t.get("phase_tag"),
                "tier": t.get("_tier"),
            }
            for t in unchecked
        ]

        # Cross-reference with decisions
        decisions = get_decision_log()
        report["decisions"] = {
            "total_decisions": len(decisions),
            "recent": [d for d in decisions if d["date"] >= "2026-03-27"],
        }

        # Check for completed tasks without decision logs
        all_tasks = filter_tasks(data, None, None, phase_filter)
        xref = cross_ref_decisions(all_tasks, decisions)
        checked_no_decision = [
            r for r in xref if r["checked"] and not r["has_decision"]
        ]
        if len(checked_no_decision) > 10:
            # Only flag this if the ratio is concerning
            ratio = len(checked_no_decision) / max(
                1, sum(1 for r in xref if r["checked"])
            )
            if ratio > 0.8:
                report["issues"].append({
                    "type": "low_decision_coverage",
                    "message": f"{len(checked_no_decision)} completed tasks have no matching decision log",
                    "severity": "info",
                })
    else:
        report["issues"].append({
            "type": "missing_tasklist",
            "message": f"Tasklist not found at {TASKLIST}",
            "severity": "high",
        })

    # 2. Check file references
    if check_files:
        if TASKLIST.exists():
            text = TASKLIST.read_text(encoding="utf-8")
            refs = extract_file_refs(text)
            for ref in refs:
                path, exists = check_file_exists(ref)
                report["file_checks"].append({
                    "path": path,
                    "exists": exists,
                })
            missing = [f for f in report["file_checks"] if not f["exists"]]
            if missing:
                report["issues"].append({
                    "type": "missing_files",
                    "message": f"{len(missing)} referenced files not found",
                    "severity": "medium",
                    "files": [f["path"] for f in missing],
                })

    # 3. Check PRD ISC items
    if prd_path:
        prd = Path(prd_path)
        if not prd.is_absolute():
            prd = REPO_ROOT / prd_path
        items = parse_isc_items(prd)
        if items:
            checked_count = sum(1 for i in items if i["checked"])
            total_count = len(items)
            report["isc_check"] = {
                "prd": str(prd_path),
                "total": total_count,
                "checked": checked_count,
                "unchecked": total_count - checked_count,
                "completion_pct": round(checked_count / total_count * 100, 1),
                "items": items,
            }

            # ISC quality checks
            no_verify = [i for i in items if not i["verify_method"]]
            if no_verify:
                report["issues"].append({
                    "type": "isc_no_verify",
                    "message": f"{len(no_verify)} ISC items missing Verify: method",
                    "severity": "high",
                    "items": [i["criterion"][:60] for i in no_verify],
                })

            if total_count < 3:
                report["issues"].append({
                    "type": "isc_too_few",
                    "message": f"Only {total_count} ISC items (minimum 3 required)",
                    "severity": "high",
                })
        else:
            report["issues"].append({
                "type": "no_isc_items",
                "message": f"No ISC items found in {prd_path}",
                "severity": "high",
            })

    return report


def format_report(report: dict) -> str:
    """Format report as ASCII table."""
    lines = []

    # Tasklist summary
    tl = report["tasklist"]
    if tl:
        lines.append(f"Tasklist: {tl['total']} tasks | {tl['checked']} done | {tl['unchecked']} open | {tl['completion_pct']}%")
        lines.append("")

        if tl.get("open_items"):
            lines.append("  Open items:")
            for item in tl["open_items"]:
                tag = f"({item['phase_tag']}) " if item.get("phase_tag") else ""
                tier = f"[T{item['tier']}] " if item.get("tier") else ""
                lines.append(f"    [ ] {tier}{tag}{item['title']}")
            lines.append("")

    # Decision log
    dec = report["decisions"]
    if dec:
        lines.append(f"Decision log: {dec['total_decisions']} entries | {len(dec.get('recent', []))} in last 3 days")
        lines.append("")

    # File checks
    if report["file_checks"]:
        missing = [f for f in report["file_checks"] if not f["exists"]]
        found = [f for f in report["file_checks"] if f["exists"]]
        lines.append(f"File references: {len(found)} found | {len(missing)} missing")
        if missing:
            for f in missing:
                lines.append(f"    MISSING: {f['path']}")
        lines.append("")

    # ISC check
    isc = report.get("isc_check")
    if isc:
        lines.append(f"ISC: {isc['total']} criteria | {isc['checked']} passed | {isc['completion_pct']}%")
        for item in isc["items"]:
            mark = "[x]" if item["checked"] else "[ ]"
            verify = f" | Verify: {item['verify_method']}" if item["verify_method"] else " | NO VERIFY"
            lines.append(f"    {mark} {item['criterion'][:70]}{verify}")
        lines.append("")

    # Issues
    if report["issues"]:
        lines.append("Issues found:")
        for issue in report["issues"]:
            sev = issue["severity"].upper()
            lines.append(f"    [{sev}] {issue['message']}")
        lines.append("")
    else:
        lines.append("No issues found.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic quality gate checker"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON")
    parser.add_argument("--phase", type=str, help="Filter by phase tag")
    parser.add_argument("--check-files", action="store_true", help="Verify referenced files exist")
    parser.add_argument("--decisions", action="store_true", help="Show decision log coverage")
    parser.add_argument("--prd", type=str, help="Path to PRD file for ISC checking")

    args = parser.parse_args()

    report = run_gate_check(
        phase_filter=args.phase,
        check_files=args.check_files,
        prd_path=args.prd,
    )

    if args.json:
        indent = 2 if args.pretty else None
        print(_sanitize_ascii(json.dumps(report, indent=indent, default=str)))
    else:
        print(_sanitize_ascii(format_report(report)))


if __name__ == "__main__":
    main()
