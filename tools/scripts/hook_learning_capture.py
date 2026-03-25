#!/usr/bin/env python3
"""Learning capture: write signal or failure markdown; update signal count metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
META_PATH = REPO_ROOT / "memory" / "learning" / "_signal_meta.json"


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return (s[:60] if s else "signal") or "signal"


def _unique_path(directory: Path, stem: str) -> Path:
    base = directory / f"{stem}.md"
    if not base.exists():
        return base
    n = 2
    while True:
        p = directory / f"{stem}_{n}.md"
        if not p.exists():
            return p
        n += 1


def _prompt_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            v = int(raw)
        except ValueError:
            print(f"Enter an integer {lo}-{hi}.", file=sys.stderr)
            continue
        if lo <= v <= hi:
            return v
        print(f"Value must be between {lo} and {hi}.", file=sys.stderr)


def _prompt_text(label: str) -> str:
    return input(f"{label}: ").strip()


def _write_signal(date_str: str, title: str, rating: int, observation: str, category: str) -> Path:
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(title)
    path = _unique_path(SIGNALS_DIR, f"{date_str}_{slug}")
    body = f"""# Signal: {title}
- Date: {date_str}
- Rating: {rating}
- Category: {category}
- Observation: {observation}
- Implication: (fill in)
"""
    path.write_text(body, encoding="utf-8")
    return path


def _write_failure(
    date_str: str,
    title: str,
    severity: int,
    context: str,
    root_cause: str,
    fix: str,
    prevention: str,
) -> Path:
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(title)
    path = _unique_path(FAILURES_DIR, f"{date_str}_{slug}")
    body = f"""# Failure: {title}
- Date: {date_str}
- Severity: {severity}
- Context: {context}
- Root Cause: {root_cause}
- Fix Applied: {fix}
- Prevention: {prevention}
"""
    path.write_text(body, encoding="utf-8")
    return path


def _update_signal_count() -> int:
    count = 0
    if SIGNALS_DIR.is_dir():
        count = sum(1 for p in SIGNALS_DIR.iterdir() if p.is_file() and p.suffix == ".md")
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "signal_file_count": count,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture learning signal or failure.")
    parser.add_argument("description", nargs="?", default=None, help="Observation or failure summary")
    parser.add_argument("--rating", "-r", type=int, default=None, help="Signal outcome 1-10")
    parser.add_argument("--title", "-t", default=None, help="Short title")
    parser.add_argument(
        "--category",
        "-c",
        default="insight",
        choices=("pattern", "insight", "anomaly", "improvement"),
        help="Signal category",
    )
    parser.add_argument(
        "--failure",
        action="store_true",
        help="Write failure record instead of signal",
    )
    parser.add_argument("--severity", type=int, default=None, help="Failure severity 1-10")
    parser.add_argument("--context", default=None, help="Failure context")
    parser.add_argument("--root-cause", default=None, help="Failure root cause")
    parser.add_argument("--fix", default=None, help="Fix applied")
    parser.add_argument("--prevention", default=None, help="Prevention")
    args = parser.parse_args()
    interactive = sys.stdin.isatty()

    if args.failure:
        title = args.title or args.description
        if not title:
            title = _prompt_text("Failure title / summary") if interactive else None
        if not title:
            print("Failure mode requires a title or description.", file=sys.stderr)
            sys.exit(2)

        sev = args.severity
        if sev is None:
            sev = _prompt_int("Severity (1-10): ", 1, 10) if interactive else None
        if sev is None:
            print("Failure mode requires --severity when non-interactive.", file=sys.stderr)
            sys.exit(2)

        ctx = args.context
        rc = args.root_cause
        fix = args.fix
        prev = args.prevention
        if interactive:
            if ctx is None:
                ctx = _prompt_text("Context (what was happening)")
            if rc is None:
                rc = _prompt_text("Root cause")
            if fix is None:
                fix = _prompt_text("Fix applied")
            if prev is None:
                prev = _prompt_text("Prevention")
        ctx = ctx or "(not provided)"
        rc = rc or "(not provided)"
        fix = fix or "(not provided)"
        prev = prev or "(not provided)"

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = _write_failure(date_str, title, sev, ctx, rc, fix, prev)
        print(f"Wrote failure: {path}")
        n = _update_signal_count()
        print(f"Signal files count (signals/): {n}")
        return

    rating = args.rating
    description = args.description
    if interactive:
        if rating is None:
            rating = _prompt_int("Outcome rating (1-10): ", 1, 10)
        if not description:
            description = _prompt_text("Observation / signal description")
    else:
        if rating is None or not description:
            print("Non-interactive mode requires --rating and a description argument.", file=sys.stderr)
            sys.exit(2)

    title = args.title or (description[:80] + ("…" if len(description) > 80 else ""))
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = _write_signal(date_str, title, rating, description, args.category)
    print(f"Wrote signal: {path}")
    n = _update_signal_count()
    print(f"Signal files count (signals/): {n}")


if __name__ == "__main__":
    main()
