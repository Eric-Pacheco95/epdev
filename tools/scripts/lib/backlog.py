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
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Cross-platform file locking. msvcrt on Windows; fcntl on POSIX.
# Both offer advisory exclusive locks on an open file descriptor. The lock
# wraps the entire read-modify-write window in backlog_append so two
# producers calling concurrently cannot lose writes.
_IS_WINDOWS = sys.platform == "win32"
if _IS_WINDOWS:
    import msvcrt
else:
    import fcntl  # type: ignore[import-not-found]


@contextmanager
def _exclusive_file_lock(lock_path: Path, timeout_s: float = 30.0):
    """Acquire an exclusive lock on a sidecar file, yielding when held.

    Retries every 100ms up to timeout_s. On Windows, msvcrt.locking blocks
    ~10s per call and raises OSError on failure, so we catch and retry.
    On POSIX, fcntl.flock with LOCK_NB raises BlockingIOError when the lock
    is held elsewhere; same retry loop applies.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # "a+b" creates the file if absent, opens read/write, never truncates.
    fh = open(lock_path, "a+b")
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                if _IS_WINDOWS:
                    # Lock 1 byte at offset 0. LK_NBLCK = non-blocking exclusive.
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break  # acquired
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"could not acquire backlog lock at {lock_path} within {timeout_s}s"
                    )
                time.sleep(0.1)
        try:
            yield
        finally:
            try:
                if _IS_WINDOWS:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        try:
            fh.close()
        except OSError:
            pass

# Resolve repo root relative to this file (lib/ -> scripts/ -> tools/ -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BACKLOG_PATH = REPO_ROOT / "orchestration" / "task_backlog.jsonl"

# Valid status values (mirrors dispatcher usage)
VALID_STATUSES = frozenset({
    "pending", "executing", "verifying", "done", "failed",
    "manual_review", "deferred", "claimed", "pending_review",
})

# Statuses that count as "active" for dedup purposes
# pending_review is included so paradigm_health/overnight injectors don't
# create duplicate tasks when one already sits in the human review queue.
ACTIVE_STATUSES = frozenset({
    "pending", "executing", "verifying", "manual_review", "claimed", "pending_review",
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
        # At least one criterion must have an executable verify method --
        # UNLESS the task is pending_review (session captures use Review-type
        # ISC intentionally; they are not dispatcher-eligible)
        is_pending_review = task.get("status") == "pending_review"
        if not is_pending_review:
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

    # -- generation (5E-2 hard cap) --
    # Follow-on tasks track their generation: parent=0, G1=1, G2=2.
    # Hard-capped at 2 to prevent runaway _emit_followon() loops, scope drift,
    # and quality degradation. Direct backlog injection that bypasses the
    # dispatcher's _emit_followon() must still be blocked here.
    if "generation" in task:
        gen = task.get("generation")
        if not isinstance(gen, int) or gen < 0 or gen > 2:
            errors.append("'generation' must be int 0-2 (hard cap to prevent runaway loops)")

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
        import time as _time
        # Use microsecond-resolution float to avoid collisions when multiple
        # tasks are appended within the same second (e.g. batch routine injection)
        ts = int(_time.time() * 1_000_000)
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

    # -- Soft warning: autonomous_safe tasks should declare expected_outputs --
    # Without expected_outputs, the dispatcher's scope_creep gate cannot
    # verify the worker stayed in bounds and will route the task to
    # manual_review (see jarvis_dispatcher.detect_scope_creep). Producers
    # are encouraged to populate expected_outputs at intake to avoid that.
    # Tier 0 (read-only) and pending_review tasks are exempt.
    if (
        task.get("autonomous_safe")
        and task.get("tier", 0) >= 1
        and task.get("status") not in ("pending_review", "manual_review", "deferred")
        and not task.get("expected_outputs")
    ):
        import sys as _sys
        print(
            f"  WARNING [backlog_append]: task {task['id']} is autonomous_safe "
            f"tier {task.get('tier')} but has no expected_outputs -- "
            f"dispatcher will route to manual_review (scope undefined).",
            file=_sys.stderr,
        )

    # -- Acquire exclusive lock around the read-modify-write window --
    # Without this, two producers calling backlog_append concurrently can
    # both read the same existing_tasks snapshot and race on os.replace,
    # silently losing one write. Sidecar .lock file is never git-tracked.
    lock_path = backlog_path.with_suffix(backlog_path.suffix + ".lock")
    with _exclusive_file_lock(lock_path):
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
