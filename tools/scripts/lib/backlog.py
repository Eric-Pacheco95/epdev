#!/usr/bin/env python3
"""backlog -- shared library for backlog task validation and append.

Provides:
    validate_task(task)       -- lightweight validation, returns list of errors
    backlog_append(task, ...)  -- validate + auto-fill + atomic append to backlog

Zero external dependencies (stdlib only).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Resolve repo root relative to this file (lib/ -> scripts/ -> tools/ -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BACKLOG_PATH = REPO_ROOT / "orchestration" / "task_backlog.jsonl"

# Valid status values (mirrors dispatcher usage)
VALID_STATUSES = frozenset({
    "pending", "executing", "verifying", "done", "failed",
    "manual_review", "deferred", "claimed",
})

# Statuses that count as "active" for dedup purposes
ACTIVE_STATUSES = frozenset({
    "pending", "executing", "verifying", "manual_review", "claimed",
})

# Optional field defaults applied during auto-fill
_OPTIONAL_DEFAULTS: dict = {
    "dependencies": [],
    "context_files": [],
    "skills": [],
    "model": "sonnet",
    "review_model": None,
    "status": "pending",
    "completed": None,
    "branch": None,
    "run_report": None,
    "failure_reason": None,
    "notes": "",
    "retry_count": 0,
}


def validate_task(task: dict) -> list[str]:
    """Run lightweight validation checks on a task dict.

    Returns a list of error strings. Empty list means validation passed.
    Does NOT modify the task dict.
    """
    # Import here to avoid circular imports and keep dependency explicit
    from tools.scripts.lib.isc_common import SECRET_PATH_PATTERNS, classify_verify_method

    errors: list[str] = []

    # -- id --
    task_id = task.get("id")
    if task_id is None:
        # id absence is allowed; backlog_append will auto-generate
        pass
    elif not isinstance(task_id, str) or not task_id.strip():
        errors.append("'id' must be a non-empty string when provided")

    # -- description --
    desc = task.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("'description' is required and must be a non-empty string")

    # -- tier --
    tier = task.get("tier")
    if tier is None:
        errors.append("'tier' is required")
    elif not isinstance(tier, int) or tier < 0 or tier > 2:
        errors.append("'tier' must be an integer 0-2")

    # -- status --
    status = task.get("status")
    if status is None:
        # status absence is allowed; backlog_append will default to "pending"
        pass
    elif status not in VALID_STATUSES:
        errors.append(
            f"'status' must be one of: {', '.join(sorted(VALID_STATUSES))}; got '{status}'"
        )

    # -- autonomous_safe --
    autonomous_safe = task.get("autonomous_safe")
    if autonomous_safe is None:
        errors.append("'autonomous_safe' is required")
    elif not isinstance(autonomous_safe, bool):
        errors.append("'autonomous_safe' must be a boolean")

    # -- isc --
    isc = task.get("isc")
    if isc is None:
        errors.append("'isc' is required")
    elif not isinstance(isc, list):
        errors.append("'isc' must be a list")
    elif len(isc) == 0:
        errors.append("'isc' must have at least 1 item")
    else:
        # At least one criterion must have an executable verify method
        has_executable = False
        for criterion in isc:
            if not isinstance(criterion, str):
                continue
            if "| Verify:" in criterion:
                classification = classify_verify_method(criterion)
                if classification == "executable":
                    has_executable = True
                    break
        if not has_executable:
            errors.append(
                "at least one ISC criterion must have an executable '| Verify:' method"
            )

        # No ISC criterion may reference a secret path
        for criterion in isc:
            if not isinstance(criterion, str):
                continue
            if SECRET_PATH_PATTERNS.search(criterion):
                errors.append(
                    f"ISC criterion references a secret path: {criterion[:80]}"
                )

    # -- priority --
    priority = task.get("priority")
    if priority is None:
        errors.append("'priority' is required")
    elif not isinstance(priority, int):
        errors.append("'priority' must be an integer")

    # -- created --
    created = task.get("created")
    if created is None:
        # created absence is allowed; backlog_append will auto-fill
        pass
    elif not isinstance(created, str) or not created.strip():
        errors.append("'created' must be a non-empty string when provided")

    return errors


def backlog_append(
    task: dict,
    backlog_path: Optional[Path] = None,
) -> Optional[dict]:
    """Validate and append a task to the backlog.

    Auto-fills optional fields with defaults. Auto-generates 'id' if absent.
    Auto-fills 'created' with today's date if absent.

    Dedup: if a task with the same routine_id already exists with an active
    status (pending, executing, verifying, manual_review, claimed), skip and
    return None.

    Uses atomic write (temp file + os.replace) to avoid backlog corruption.

    Args:
        task:         Task dict to validate and append. Must contain at minimum:
                      description, tier, autonomous_safe, isc, priority.
        backlog_path: Path to the JSONL backlog file. Defaults to
                      orchestration/task_backlog.jsonl in the repo root.

    Returns:
        The validated + auto-filled task dict, or None if deduped.

    Raises:
        ValueError: if validation fails (with all error messages joined).
    """
    if backlog_path is None:
        backlog_path = DEFAULT_BACKLOG_PATH

    # Work on a copy so we don't mutate the caller's dict
    task = dict(task)

    # -- Auto-generate id if absent --
    if "id" not in task or not task.get("id"):
        ts = int(datetime.now(timezone.utc).timestamp())
        task["id"] = f"task-{ts}"

    # -- Auto-fill created if absent --
    if "created" not in task or not task.get("created"):
        task["created"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # -- Auto-fill optional fields with defaults --
    for field, default in _OPTIONAL_DEFAULTS.items():
        if field not in task:
            # Deep-copy mutable defaults
            task[field] = list(default) if isinstance(default, list) else default

    # -- Validate --
    errors = validate_task(task)
    if errors:
        raise ValueError("Task validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    # -- Load existing backlog for dedup check --
    existing_tasks: list[dict] = []
    if backlog_path.exists():
        with open(backlog_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_tasks.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines (do not corrupt backlog)
                    continue

    # -- Dedup by routine_id --
    routine_id = task.get("routine_id")
    if routine_id:
        for existing in existing_tasks:
            if (
                existing.get("routine_id") == routine_id
                and existing.get("status") in ACTIVE_STATUSES
            ):
                return None

    # -- Atomic append --
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(backlog_path.parent),
        suffix=".tmp",
        prefix="backlog_append_",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # Write existing lines
            for existing in existing_tasks:
                f.write(json.dumps(existing, ensure_ascii=False) + "\n")
            # Append new task
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
        os.replace(tmp_path, str(backlog_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return task
