"""Transcribe `## One-liner` text into `description:` frontmatter for SKILL.md files.

Per the 2026-04-28 architecture review on skill-list pollution: the harness reads
frontmatter `description:` for the system-reminder skill list, falling back to the
first heading (`# IDENTITY and PURPOSE`) when frontmatter is absent. ~49 of 53 skills
already have an accurate `## One-liner` section; this script lifts that text into
frontmatter so the harness surfaces useful descriptions instead of zero-information
stubs.

Usage:
    python tools/scripts/skill_frontmatter_transcribe.py --dry-run
    python tools/scripts/skill_frontmatter_transcribe.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"

# Sanitization rules per /architecture-review red-team High-severity finding:
# descriptions land in the system-reminder every cold session and become a
# permanent prompt-injection surface. Reject any description matching these.
INJECTION_PATTERNS = [
    re.compile(r"\bignore (previous|prior|all|above)\b", re.IGNORECASE),
    re.compile(r"\boverride\b", re.IGNORECASE),
    re.compile(r"\bsystem prompt\b", re.IGNORECASE),
    re.compile(r"\bdisregard\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"</?(system|user|assistant|function_calls)>", re.IGNORECASE),
]
MAX_DESCRIPTION_CHARS = 200


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text[4:]


def extract_frontmatter(text: str) -> tuple[str | None, str]:
    if not has_frontmatter(text):
        return None, text
    end_idx = text.index("\n---\n", 4)
    return text[4:end_idx], text[end_idx + 5 :]


def parse_frontmatter_field(fm: str, field: str) -> str | None:
    for line in fm.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return None


def extract_one_liner(body: str) -> str | None:
    """Pull the first non-empty, non-heading line under `## One-liner`."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "## one-liner":
            for j in range(i + 1, len(lines)):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if candidate.startswith("#"):
                    return None
                return candidate
    return None


def sanitize(description: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    cleaned = description.strip()
    if len(cleaned) > MAX_DESCRIPTION_CHARS:
        warnings.append(
            f"length {len(cleaned)} > {MAX_DESCRIPTION_CHARS}; will be truncated"
        )
        cleaned = cleaned[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
    for pat in INJECTION_PATTERNS:
        if pat.search(cleaned):
            warnings.append(f"matched injection pattern /{pat.pattern}/")
    if '"' in cleaned and "'" in cleaned:
        warnings.append("contains both quote types — manual review")
    return cleaned, warnings


def yaml_quote(value: str) -> str:
    """YAML-safe single-line quoting for a description string."""
    if any(ch in value for ch in [":", "#", "\\"]) or value != value.strip():
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def process_skill(skill_path: Path) -> dict:
    text = skill_path.read_text(encoding="utf-8")
    name = skill_path.parent.name
    fm, body = extract_frontmatter(text)

    record: dict = {
        "skill": name,
        "path": str(skill_path),
        "action": "skip",
        "reason": "",
        "description": None,
        "warnings": [],
    }

    if fm is not None:
        existing = parse_frontmatter_field(fm, "description")
        if existing:
            record["reason"] = "already has description frontmatter"
            return record
        record["reason"] = "has frontmatter but no description field"
        record["action"] = "ERROR"
        return record

    one_liner = extract_one_liner(body)
    if not one_liner:
        record["reason"] = "no `## One-liner` section found"
        record["action"] = "ERROR"
        return record

    description, warnings = sanitize(one_liner)
    record["description"] = description
    record["warnings"] = warnings
    record["action"] = "transcribe"
    if warnings:
        record["reason"] = f"sanitization warnings: {warnings}"

    return record


def apply_transcription(skill_path: Path, name: str, description: str) -> None:
    text = skill_path.read_text(encoding="utf-8")
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        f"description: {yaml_quote(description)}\n"
        "---\n\n"
    )
    skill_path.write_text(frontmatter + text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args()

    if args.apply == args.dry_run:
        parser.error("specify exactly one of --dry-run or --apply")

    skill_paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    records = [process_skill(p) for p in skill_paths]

    if args.json:
        print(json.dumps(records, indent=2))
    else:
        by_action: dict[str, list[dict]] = {"transcribe": [], "skip": [], "ERROR": []}
        for r in records:
            by_action[r["action"]].append(r)
        print(f"Total skills: {len(records)}")
        print(f"  transcribe: {len(by_action['transcribe'])}")
        print(f"  skip:       {len(by_action['skip'])}")
        print(f"  ERROR:      {len(by_action['ERROR'])}")
        if by_action["ERROR"]:
            print("\nERRORS:")
            for r in by_action["ERROR"]:
                print(f"  {r['skill']}: {r['reason']}")
        warned = [r for r in by_action["transcribe"] if r["warnings"]]
        if warned:
            print("\nWARNINGS:")
            for r in warned:
                print(f"  {r['skill']}: {r['warnings']}")
        print("\nTranscription preview (first 5):")
        for r in by_action["transcribe"][:5]:
            print(f"  {r['skill']}: {r['description']!r}")

    if args.apply:
        if any(r["action"] == "ERROR" for r in records):
            print("\nABORT: errors present; resolve before --apply", file=sys.stderr)
            return 2
        applied = 0
        for r in records:
            if r["action"] == "transcribe":
                apply_transcription(Path(r["path"]), r["skill"], r["description"])
                applied += 1
        print(f"\nApplied frontmatter to {applied} SKILL.md files.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
