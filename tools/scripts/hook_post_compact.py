#!/usr/bin/env python3
"""PostCompact hook: surface dynamic working state after context compaction.

Prints active tasks and in-progress ISC items so Claude can resume without
re-orientation. Output is capped at 500 chars to avoid context bloat.

Runs non-interactively -- no user input required.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
WORK_DIR = REPO_ROOT / "memory" / "work"
MAX_OUTPUT = 500


def _unchecked_items(text: str) -> list[str]:
    """Extract unchecked checkbox items from markdown text."""
    items: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)-\s+\[([ ])\]\s+(.*)$", line)
        if m:
            items.append(m.group(3).strip())
    return items


def _active_tasks() -> list[str]:
    """Get unchecked items from tasklist."""
    if not TASKLIST.is_file():
        return []
    try:
        text = TASKLIST.read_text(encoding="utf-8")
    except OSError:
        return []
    return _unchecked_items(text)


def _incomplete_iscs() -> dict[str, list[str]]:
    """Scan memory/work/*/PRD.md for unchecked ISC items."""
    results: dict[str, list[str]] = {}
    if not WORK_DIR.is_dir():
        return results
    for prd in WORK_DIR.glob("*/PRD.md"):
        try:
            text = prd.read_text(encoding="utf-8")
        except OSError:
            continue
        items = _unchecked_items(text)
        if items:
            project = prd.parent.name
            results[project] = items
    return results


def main() -> None:
    parts: list[str] = []

    # Active tasks from tasklist
    tasks = _active_tasks()
    if tasks:
        # Show first 3 unchecked tasks
        shown = tasks[:3]
        task_str = "; ".join(shown)
        if len(tasks) > 3:
            task_str += f" (+{len(tasks) - 3} more)"
        parts.append(f"Active tasks: {task_str}")

    # Incomplete ISCs from PRDs
    iscs = _incomplete_iscs()
    for project, items in iscs.items():
        count = len(items)
        # Show first 2 items as preview
        shown = items[:2]
        preview = "; ".join(shown)
        if count > 2:
            preview += f" (+{count - 2} more)"
        parts.append(f"ISC [{project}] {count} remaining: {preview}")

    if not parts:
        sys.exit(0)

    output = " | ".join(parts)
    # Hard cap to avoid context bloat
    if len(output) > MAX_OUTPUT:
        output = output[: MAX_OUTPUT - 3] + "..."

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
