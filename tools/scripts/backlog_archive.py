#!/usr/bin/env python3
"""Backlog Archive Helper -- Phase 5B Sprint 2.

Moves completed tasks older than N days from the active backlog to an
archive file. Keeps the active backlog lean for dispatcher scans.

Usage:
    python tools/scripts/backlog_archive.py              # archive done items >7 days old
    python tools/scripts/backlog_archive.py --dry-run    # show what would be archived
    python tools/scripts/backlog_archive.py --days 14    # custom age threshold

Importable:
    from tools.scripts.backlog_archive import archive_tasks
    count = archive_tasks(days=7, dry_run=False)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
ARCHIVE_FILE = REPO_ROOT / "data" / "task_archive.jsonl"

# Statuses that are NEVER auto-archived
NEVER_ARCHIVE = frozenset({"manual_review", "pending", "claimed", "executing", "verifying"})


def _read_jsonl(path: Path) -> list[dict]:
    """Read JSONL file into list of dicts."""
    if not path.exists():
        return []
    tasks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tasks.append(json.loads(line))
    return tasks


def _write_jsonl_atomic(path: Path, tasks: list[dict]) -> None:
    """Write JSONL atomically: temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix="backlog_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, tasks: list[dict]) -> None:
    """Append tasks to JSONL file (create if missing)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def archive_tasks(
    days: int = 7,
    dry_run: bool = False,
    backlog_path: Path | None = None,
    archive_path: Path | None = None,
) -> int:
    """Archive done tasks older than `days` days.

    Returns the number of tasks archived.
    Can be imported by the dispatcher for in-process archiving.
    """
    bp = backlog_path or BACKLOG_FILE
    ap = archive_path or ARCHIVE_FILE

    tasks = _read_jsonl(bp)
    if not tasks:
        return 0

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    to_archive = []
    remaining = []

    for task in tasks:
        status = task.get("status", "")

        # Never auto-archive protected statuses
        if status in NEVER_ARCHIVE:
            remaining.append(task)
            continue

        # Archive done items past the cutoff
        if status == "done":
            completed = task.get("completed", "")
            if completed and completed <= cutoff_str:
                task["archived"] = datetime.now().strftime("%Y-%m-%d")
                to_archive.append(task)
                continue

        # Archive terminal failed items past the cutoff too
        if status == "failed":
            completed = task.get("completed", "")
            created = task.get("created", "")
            ref_date = completed or created
            if ref_date and ref_date <= cutoff_str:
                task["archived"] = datetime.now().strftime("%Y-%m-%d")
                to_archive.append(task)
                continue

        remaining.append(task)

    if not to_archive:
        if not dry_run:
            print("Nothing to archive")
        return 0

    ids = [t.get("id", "?") for t in to_archive]

    if dry_run:
        print(f"Would archive {len(to_archive)} tasks: {', '.join(ids)}")
        return len(to_archive)

    # Append to archive first (safer -- if this fails, backlog untouched)
    _append_jsonl(ap, to_archive)

    # Then atomically rewrite the active backlog
    _write_jsonl_atomic(bp, remaining)

    print(f"Archived {len(to_archive)} tasks: {', '.join(ids)}")
    return len(to_archive)


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive completed backlog tasks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be archived")
    parser.add_argument("--days", type=int, default=7, help="Age threshold in days (default: 7)")
    parser.add_argument("--backlog", type=str, default=None, help="Override backlog file path")
    parser.add_argument("--archive", type=str, default=None, help="Override archive file path")
    args = parser.parse_args()

    bp = Path(args.backlog) if args.backlog else None
    ap = Path(args.archive) if args.archive else None

    archive_tasks(days=args.days, dry_run=args.dry_run, backlog_path=bp, archive_path=ap)


if __name__ == "__main__":
    main()
