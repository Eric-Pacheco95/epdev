#!/usr/bin/env python3
"""
stamp_prd_axes.py — Retroactive four-axis Task Typing stamper for pre-frontmatter PRDs.

Usage:
    python tools/scripts/stamp_prd_axes.py --propose   # emit data/prd_axes_proposals.tsv
    python tools/scripts/stamp_prd_axes.py --apply     # apply TSV to PRD files
    python tools/scripts/stamp_prd_axes.py --apply --tsv path/to/custom.tsv
    python tools/scripts/stamp_prd_axes.py --help
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_TSV = DATA_DIR / "prd_axes_proposals.tsv"
TSV_HEADER = "path\tstakes\tambiguity\tsolvability\tverifiability\tconfidence\trationale"

FRONTMATTER_RE = re.compile(r"^\s*---\s*\n.*?---\s*(\n|$)", re.DOTALL)

# Keyword sets for heuristic classification
_STAKES_HIGH = {
    "production", "deploy", "billing", "credential", "secret", "auth", "security",
    "compliance", "osfi", "payment", "external api", "api key", "token", "webhook",
    "database", "migration", "schema change", "data loss", "irreversible",
}
_STAKES_LOW = {
    "script", "doc", "readme", "typo", "rename", "config", "log", "comment",
    "internal", "local", "draft", "prototype", "stub", "test fixture",
}

_AMBIGUITY_HIGH = {
    "explore", "options", "strategy", "figure out", "approach", "tradeoff",
    "should we", "might", "possibly", "design", "consider", "alternatives",
    "unclear", "tbd", "to be determined", "open question",
}
_AMBIGUITY_LOW = {
    "fix", "rename", "add", "remove", "update", "implement", "integrate",
    "create", "write", "emit", "read", "parse", "validate", "check",
}

_SOLVABILITY_HIGH = {
    "fix", "rename", "remove", "add", "update", "emit", "read", "parse",
    "check", "count", "list", "grep", "script", "cli", "command",
}
_SOLVABILITY_LOW = {
    "novel", "research", "ml", "machine learning", "training", "inference",
    "strategy", "design", "architecture", "figure out", "explore",
}

_VERIFIABILITY_HIGH = {
    "test", "pytest", "exit code", "grep", "file exists", "wc -", "head -",
    "awk", "count", "script", "cli", "--help", "assert", "schema", "validate",
    "isc_validator", "check-frontmatter", "git diff --stat",
}
_VERIFIABILITY_LOW = {
    "taste", "feel", "quality", "strategy", "experience", "judgment", "review",
    "narrative", "correct", "good", "better", "worse",
}


def _has_frontmatter(text: str) -> bool:
    return bool(FRONTMATTER_RE.match(text))


def _text_contains_any(text: str, keywords: set) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _score_axis(text: str, high_set: set, low_set: set) -> tuple[str, int]:
    """Return (tier, signal_count)."""
    high_hits = sum(1 for kw in high_set if kw in text.lower())
    low_hits = sum(1 for kw in low_set if kw in text.lower())
    if high_hits > low_hits:
        return "high", high_hits
    if low_hits > high_hits:
        return "low", low_hits
    return "medium", 0


def _classify_prd(content: str, prd_path: Path) -> dict:
    """Heuristically classify a PRD's four axes."""
    # Use OVERVIEW + PROBLEM AND GOALS + ACCEPTANCE CRITERIA for signal
    overview_match = re.search(r"## OVERVIEW\s*(.*?)(?=^##|\Z)", content, re.DOTALL | re.MULTILINE)
    goals_match = re.search(r"## PROBLEM AND GOALS\s*(.*?)(?=^##|\Z)", content, re.DOTALL | re.MULTILINE)
    isc_match = re.search(r"## ACCEPTANCE CRITERIA\s*(.*?)(?=^##|\Z)", content, re.DOTALL | re.MULTILINE)

    signal_text = " ".join(filter(None, [
        overview_match.group(1) if overview_match else "",
        goals_match.group(1) if goals_match else "",
        isc_match.group(1) if isc_match else "",
        prd_path.stem,
    ]))

    stakes_tier, stakes_n = _score_axis(signal_text, _STAKES_HIGH, _STAKES_LOW)
    ambiguity_tier, ambiguity_n = _score_axis(signal_text, _AMBIGUITY_HIGH, _AMBIGUITY_LOW)
    solvability_tier, solvability_n = _score_axis(signal_text, _SOLVABILITY_HIGH, _SOLVABILITY_LOW)
    verifiability_tier, verifiability_n = _score_axis(signal_text, _VERIFIABILITY_HIGH, _VERIFIABILITY_LOW)

    signal_total = stakes_n + ambiguity_n + solvability_n + verifiability_n
    if signal_total >= 8:
        confidence = "high"
    elif signal_total >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    rationale = (
        f"stakes:{stakes_n}sig/{stakes_tier} "
        f"ambiguity:{ambiguity_n}sig/{ambiguity_tier} "
        f"solvability:{solvability_n}sig/{solvability_tier} "
        f"verifiability:{verifiability_n}sig/{verifiability_tier}"
    )

    return {
        "stakes": stakes_tier,
        "ambiguity": ambiguity_tier,
        "solvability": solvability_tier,
        "verifiability": verifiability_tier,
        "confidence": confidence,
        "rationale": rationale,
    }


def cmd_propose(tsv_path: Path) -> int:
    """Walk memory/work/**/PRD*.md and emit proposals for PRDs without frontmatter."""
    work_dir = REPO_ROOT / "memory" / "work"
    if not work_dir.exists():
        print(f"ERROR: {work_dir} not found", file=sys.stderr)
        return 1

    prd_paths = sorted(work_dir.rglob("PRD*.md"))
    # Skip anything under archive/
    prd_paths = [p for p in prd_paths if not any(part.lower() == "archive" for part in p.parts)]

    rows = []
    skipped_with_frontmatter = 0
    for prd_path in prd_paths:
        content = prd_path.read_text(encoding="utf-8", errors="replace")
        if _has_frontmatter(content):
            skipped_with_frontmatter += 1
            continue
        classification = _classify_prd(content, prd_path)
        rel_path = prd_path.relative_to(REPO_ROOT).as_posix()
        rows.append(
            f"{rel_path}\t"
            f"{classification['stakes']}\t"
            f"{classification['ambiguity']}\t"
            f"{classification['solvability']}\t"
            f"{classification['verifiability']}\t"
            f"{classification['confidence']}\t"
            f"{classification['rationale']}"
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tsv_path.write_text(TSV_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"Proposed {len(rows)} PRDs -> {tsv_path}")
    print(f"Skipped {skipped_with_frontmatter} PRDs already carrying frontmatter")
    print(f"Review and edit {tsv_path}, then run --apply")
    return 0


def _build_frontmatter(stakes: str, ambiguity: str, solvability: str, verifiability: str) -> str:
    valid = {"low", "medium", "high"}
    for label, val in [("stakes", stakes), ("ambiguity", ambiguity), ("solvability", solvability), ("verifiability", verifiability)]:
        if val not in valid:
            raise ValueError(f"Invalid value for {label}: '{val}' — must be low|medium|high")
    return (
        "---\n"
        f"stakes:        {stakes}\n"
        f"ambiguity:     {ambiguity}\n"
        f"solvability:   {solvability}\n"
        f"verifiability: {verifiability}\n"
        "---\n\n"
    )


def cmd_apply(tsv_path: Path) -> int:
    """Read TSV and atomically prepend YAML frontmatter to named PRDs."""
    if not tsv_path.exists():
        print(f"ERROR: TSV not found at {tsv_path} — run --propose first", file=sys.stderr)
        return 1

    lines = tsv_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        print("ERROR: TSV is empty", file=sys.stderr)
        return 1

    # Validate header
    header = lines[0].split("\t")
    expected = ["path", "stakes", "ambiguity", "solvability", "verifiability", "confidence", "rationale"]
    if header[:7] != expected:
        print(f"ERROR: TSV header mismatch. Expected: {expected}", file=sys.stderr)
        return 1

    modified = 0
    skipped_exists = 0
    errors = []

    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            errors.append(f"Line {lineno}: too few columns ({len(parts)})")
            continue

        rel_path, stakes, ambiguity, solvability, verifiability = parts[:5]
        prd_path = REPO_ROOT / rel_path

        if not prd_path.exists():
            errors.append(f"Line {lineno}: file not found: {prd_path}")
            continue

        content = prd_path.read_text(encoding="utf-8", errors="replace")
        if _has_frontmatter(content):
            skipped_exists += 1
            continue  # anti-criterion: never modify a PRD that already has frontmatter

        try:
            frontmatter = _build_frontmatter(stakes.strip(), ambiguity.strip(), solvability.strip(), verifiability.strip())
        except ValueError as e:
            errors.append(f"Line {lineno}: {e}")
            continue

        new_content = frontmatter + content
        # Atomic write: write to temp in same directory, then rename
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=prd_path.parent,
            prefix=".stamp_tmp_", suffix=".md", delete=False
        ) as tmp:
            tmp.write(new_content)
            tmp_path = Path(tmp.name)

        tmp_path.replace(prd_path)
        modified += 1
        print(f"  stamped: {rel_path}")

    print(f"\nApplied frontmatter to {modified} PRDs")
    print(f"Skipped {skipped_exists} PRDs (frontmatter already present)")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stamp four-axis Task Typing frontmatter on pre-rubric PRDs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--propose", action="store_true", help="Emit data/prd_axes_proposals.tsv")
    mode.add_argument("--apply", action="store_true", help="Apply edited TSV to PRD files")
    parser.add_argument(
        "--tsv", type=Path, default=DEFAULT_TSV,
        help=f"TSV path (default: {DEFAULT_TSV})"
    )
    args = parser.parse_args()

    if args.propose:
        return cmd_propose(args.tsv)
    if args.apply:
        return cmd_apply(args.tsv)
    return 1


if __name__ == "__main__":
    sys.exit(main())
