#!/usr/bin/env python3
"""Verify the most recent synthesis doc actually recalls its source signals.

This is an ANTI-CRITERION verifier for the signal pipeline. It enforces that a
synthesis document is not merely "present" but actually cites real source
signals by filename and assigns themes to them. The forbidden state this
blocks: a synthesis doc that exists on disk but hallucinated its themes with
no traceable source signal -- a silent fidelity failure that verify_synthesis_routine.py
cannot detect because that check only asserts the file exists.

Design decisions (from 2026-04-09 /architecture-review on Memento-inspired
additions):
  - No LLM calls: deterministic parsing only. Avoids rate-limit lies and cost.
  - Multi-signal check: rejects "canary pass-through" where a single token
    survives while real content is dropped. We require N distinct citations.
  - Read-only on production: no tmpdir dance needed because this is post-hoc
    verification against already-committed output.
  - Idle Is Success: no recent synthesis doc -> PASS (the routine verifier
    owns the "was synthesis due" question; this verifier owns fidelity only).
  - Explicit sys.exit(1) on forbidden state (per CLAUDE.md anti-criterion rule).

Pass criteria (ALL must hold when a recent synthesis doc exists):
  1. The synthesis doc cites at least MIN_CITATIONS distinct source signal
     filenames via "Supporting signals:" lines.
  2. At least MIN_RESOLVABLE of those cited signals resolve to real files in
     memory/learning/signals/ or memory/learning/signals/processed/.
  3. At least MIN_THEMES_WITH_SIGNALS themes in the doc have a non-empty
     Supporting signals line.

Fail-fast modes (exit 1):
  - Synthesis doc references zero supporting signals.
  - None of the cited signals resolve to real files (hallucinated citations).
  - Fewer than MIN_THEMES_WITH_SIGNALS themes have signal attribution.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
PROCESSED_DIR = SIGNALS_DIR / "processed"
ABSORBED_DIR = REPO_ROOT / "memory" / "learning" / "absorbed"
ABSORBED_PROCESSED = ABSORBED_DIR / "processed"

# Consider a synthesis doc "recent" if created within this many days.
RECENCY_WINDOW_DAYS = 7

# Thresholds for the fidelity check.
MIN_CITATIONS = 2            # total distinct signal filenames cited
MIN_RESOLVABLE = 1           # citations that resolve to real files on disk
MIN_THEMES_WITH_SIGNALS = 2  # themes carrying a non-empty Supporting signals line

SUPPORTING_LINE = re.compile(r"^\s*-?\s*Supporting signals?:\s*(.+)$", re.IGNORECASE)
THEME_HEADER = re.compile(r"^###\s+Theme:", re.IGNORECASE)
FILENAME_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*\.md")


def most_recent_synthesis() -> Path | None:
    if not SYNTH_DIR.is_dir():
        return None
    candidates: list[tuple[float, Path]] = []
    for p in SYNTH_DIR.iterdir():
        if p.is_file() and p.suffix == ".md":
            try:
                candidates.append((p.stat().st_mtime, p))
            except OSError:
                continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def is_recent(path: Path) -> bool:
    try:
        mtime = date.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return False
    return (date.today() - mtime) <= timedelta(days=RECENCY_WINDOW_DAYS)


def resolve_signal(name: str) -> bool:
    """Return True if `name` matches a real file in signals/ or processed/ or absorbed/."""
    for base in (SIGNALS_DIR, PROCESSED_DIR, ABSORBED_DIR, ABSORBED_PROCESSED):
        if (base / name).is_file():
            return True
    return False


def parse_synthesis(path: Path) -> tuple[set[str], int]:
    """Return (unique cited filenames, count of themes with non-empty citation)."""
    cited: set[str] = set()
    themes_with_signals = 0
    current_theme_has_signal = False
    in_theme = False

    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if THEME_HEADER.match(line):
                if in_theme and current_theme_has_signal:
                    themes_with_signals += 1
                in_theme = True
                current_theme_has_signal = False
                continue
            m = SUPPORTING_LINE.match(line)
            if not m:
                continue
            payload = m.group(1).strip()
            if not payload or payload.lower() in {"none", "(none)", "n/a", "--"}:
                continue
            found = FILENAME_TOKEN.findall(payload)
            if found:
                current_theme_has_signal = True
                cited.update(found)
    if in_theme and current_theme_has_signal:
        themes_with_signals += 1
    return cited, themes_with_signals


def main() -> int:
    synth = most_recent_synthesis()
    if synth is None or not is_recent(synth):
        print("PASS: no recent synthesis doc in window (%d days); nothing to verify" % RECENCY_WINDOW_DAYS)
        return 0

    cited, themes_with_signals = parse_synthesis(synth)
    resolvable = {name for name in cited if resolve_signal(name)}

    problems: list[str] = []
    if len(cited) < MIN_CITATIONS:
        problems.append(
            "only %d cited signal(s); require >= %d" % (len(cited), MIN_CITATIONS)
        )
    if len(resolvable) < MIN_RESOLVABLE:
        problems.append(
            "only %d citation(s) resolve to real files; require >= %d (possible hallucinated citations)"
            % (len(resolvable), MIN_RESOLVABLE)
        )
    if themes_with_signals < MIN_THEMES_WITH_SIGNALS:
        problems.append(
            "only %d theme(s) have Supporting signals; require >= %d"
            % (themes_with_signals, MIN_THEMES_WITH_SIGNALS)
        )

    if problems:
        print("FAIL: synthesis fidelity check on %s" % synth.name)
        for p in problems:
            print("  - " + p)
        print("  cited=%d resolvable=%d themes_with_signals=%d" % (
            len(cited), len(resolvable), themes_with_signals,
        ))
        sys.exit(1)

    print(
        "PASS: %s cited=%d resolvable=%d themes_with_signals=%d"
        % (synth.name, len(cited), len(resolvable), themes_with_signals)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
