#!/usr/bin/env python3
"""collect_sources.py -- Collect publishable source material from the Jarvis system.

Gathers signals (rating >= 7, last 7 days), synthesis docs (last 7 days),
arch review outputs (last 14 days), and research briefs (last 14 days).
Runs a safety filter to skip any file containing employer/bank keywords.

Output: tools/scripts/content_pipeline/staging/weekly_sources.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]  # epdev/
STAGING = Path(__file__).resolve().parent / "staging"
OUTPUT_FILE = STAGING / "weekly_sources.json"

SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
WORK_DIR = REPO_ROOT / "memory" / "work"

# ---------------------------------------------------------------------------
# Safety filter keywords
# Short/common words use whole-word match (\b) to avoid false positives
# (e.g. "td" inside "standard", "client" inside "clients" is fine but
#  "TD" as an abbreviation or "bank" as a standalone word are not)
# ---------------------------------------------------------------------------
# Whole-word, case-sensitive (abbreviations and proper nouns)
_SAFETY_EXACT = re.compile(
    r"\b(TD|MNPI|RBC|CIBC|BMO|OSFI|SOX|PCI)\b"
)
# Whole-word, case-insensitive (common words that need context boundary)
_SAFETY_WORD = re.compile(
    r"\b(bank|employer|confidential|material|proprietary|insider)\b",
    re.IGNORECASE,
)
# Phrase match (multi-word, case-insensitive)
_SAFETY_PHRASE = re.compile(
    r"(work laptop|my employer|the bank|at the bank|at TD|for TD|inside TD)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safety_check(content: str, path: str) -> tuple[bool, Optional[str]]:
    """Return (passes, reason). passes=True means safe to include."""
    for pattern in (_SAFETY_EXACT, _SAFETY_WORD, _SAFETY_PHRASE):
        match = pattern.search(content)
        if match:
            return False, f"Safety filter hit: '{match.group(0)}' in {Path(path).name}"
    return True, None


def parse_frontmatter_date(content: str) -> Optional[datetime]:
    """Parse 'date: YYYY-MM-DD' from content (frontmatter or inline)."""
    m = re.search(r"^[-\s]*[Dd]ate:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def parse_rating(content: str) -> Optional[int]:
    """Parse 'rating: N' or 'Signal rating: N' from content."""
    m = re.search(r"(?:Signal\s+)?[Rr]ating:\s*(\d+)", content)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def file_mtime(path: Path) -> datetime:
    """Return file modification time as UTC datetime."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def within_days(dt: Optional[datetime], days: int, fallback: datetime) -> bool:
    """Return True if dt (or fallback) is within the last N days."""
    ref = dt if dt is not None else fallback
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return ref >= cutoff


def read_file(path: Path) -> Optional[str]:
    """Read file content; return None on error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  [WARN] Could not read {path}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def collect_signals(sources: list, skipped: list) -> None:
    """Collect signal files with rating >= 7 and date within last 7 days."""
    if not SIGNALS_DIR.exists():
        print(f"[COLLECT] signals dir not found: {SIGNALS_DIR}")
        return

    for path in sorted(SIGNALS_DIR.glob("*.md")):
        content = read_file(path)
        if content is None:
            continue

        # Date check
        parsed_date = parse_frontmatter_date(content)
        mtime = file_mtime(path)
        if not within_days(parsed_date, 7, mtime):
            continue  # too old, silently skip

        # Rating check
        rating = parse_rating(content)
        if rating is None or rating < 7:
            continue

        # Safety filter
        ok, reason = safety_check(content, str(path))
        if not ok:
            skipped.append({"path": str(path), "reason": reason})
            print(f"  [SKIP] {path.name} -- {reason}")
            continue

        date_str = parsed_date.strftime("%Y-%m-%d") if parsed_date else mtime.strftime("%Y-%m-%d")
        sources.append({
            "type": "signal",
            "path": str(path),
            "date": date_str,
            "rating": rating,
            "content": content,
        })
        print(f"  [OK] signal: {path.name} (rating={rating})")


def collect_synthesis(sources: list, skipped: list) -> None:
    """Collect synthesis files dated within last 7 days."""
    if not SYNTHESIS_DIR.exists():
        print(f"[COLLECT] synthesis dir not found: {SYNTHESIS_DIR}")
        return

    for path in sorted(SYNTHESIS_DIR.glob("*.md")):
        content = read_file(path)
        if content is None:
            continue

        parsed_date = parse_frontmatter_date(content)
        mtime = file_mtime(path)
        if not within_days(parsed_date, 7, mtime):
            continue

        ok, reason = safety_check(content, str(path))
        if not ok:
            skipped.append({"path": str(path), "reason": reason})
            print(f"  [SKIP] {path.name} -- {reason}")
            continue

        date_str = parsed_date.strftime("%Y-%m-%d") if parsed_date else mtime.strftime("%Y-%m-%d")
        sources.append({
            "type": "synthesis",
            "path": str(path),
            "date": date_str,
            "content": content,
        })
        print(f"  [OK] synthesis: {path.name}")


def collect_arch_reviews(sources: list, skipped: list) -> None:
    """Collect arch review output dirs dated within last 14 days."""
    if not WORK_DIR.exists():
        print(f"[COLLECT] work dir not found: {WORK_DIR}")
        return

    for arch_dir in sorted(WORK_DIR.glob("_arch-review-*")):
        if not arch_dir.is_dir():
            continue

        # Collect all .md files in the arch review dir
        md_files = list(arch_dir.glob("*.md"))
        if not md_files:
            continue

        # Use directory mtime as fallback date
        dir_mtime = file_mtime(arch_dir)

        for path in sorted(md_files):
            content = read_file(path)
            if content is None:
                continue

            parsed_date = parse_frontmatter_date(content)
            file_mt = file_mtime(path)
            # Use whichever is more specific
            ref_date = parsed_date if parsed_date is not None else file_mt
            if not within_days(ref_date, 14, dir_mtime):
                continue

            ok, reason = safety_check(content, str(path))
            if not ok:
                skipped.append({"path": str(path), "reason": reason})
                print(f"  [SKIP] {path.name} -- {reason}")
                continue

            date_str = ref_date.strftime("%Y-%m-%d")
            sources.append({
                "type": "arch-review",
                "path": str(path),
                "date": date_str,
                "content": content,
            })
            print(f"  [OK] arch-review: {arch_dir.name}/{path.name}")


def collect_research_briefs(sources: list, skipped: list) -> None:
    """Collect research_brief.md files from work subdirs within last 14 days."""
    if not WORK_DIR.exists():
        print(f"[COLLECT] work dir not found: {WORK_DIR}")
        return

    for path in sorted(WORK_DIR.rglob("research_brief.md")):
        content = read_file(path)
        if content is None:
            continue

        parsed_date = parse_frontmatter_date(content)
        mtime = file_mtime(path)
        if not within_days(parsed_date, 14, mtime):
            continue

        ok, reason = safety_check(content, str(path))
        if not ok:
            skipped.append({"path": str(path), "reason": reason})
            print(f"  [SKIP] {path.name} -- {reason}")
            continue

        date_str = parsed_date.strftime("%Y-%m-%d") if parsed_date else mtime.strftime("%Y-%m-%d")
        sources.append({
            "type": "research",
            "path": str(path),
            "date": date_str,
            "content": content,
        })
        print(f"  [OK] research: {path.parent.name}/research_brief.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("[COLLECT] Starting source collection...")
    STAGING.mkdir(parents=True, exist_ok=True)

    sources: list = []
    skipped: list = []

    print("[COLLECT] Scanning signals (rating >= 7, last 7 days)...")
    collect_signals(sources, skipped)

    print("[COLLECT] Scanning synthesis docs (last 7 days)...")
    collect_synthesis(sources, skipped)

    print("[COLLECT] Scanning arch review outputs (last 14 days)...")
    collect_arch_reviews(sources, skipped)

    print("[COLLECT] Scanning research briefs (last 14 days)...")
    collect_research_briefs(sources, skipped)

    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "collected_at": collected_at,
        "sources": sources,
        "skipped": skipped,
    }

    try:
        OUTPUT_FILE.write_text(
            json.dumps(output, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[COLLECT] ERROR: Could not write output file: {exc}", file=sys.stderr)
        return 1

    print(
        f"[COLLECT] Done. {len(sources)} sources collected, "
        f"{len(skipped)} skipped. Output: {OUTPUT_FILE}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
