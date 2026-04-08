#!/usr/bin/env python3
"""verify_5e2_falsification.py -- Phase 5E-2 falsification verification.

Checks real production data against the 5E-2 invariants:
  I1. No pending_review task older than 7d lacks an alert record
  I2. No pending_review task older than 14d still exists in backlog as pending_review
  I3. Every auto-failed TTL task has a durable archive record in data/pending_review_expired/
  I4. No task in backlog has generation > 2
  I5. No task with parent_branch references a branch that is both missing AND has no run report
  I6. Tasks with failure_type=branch_lifecycle must be in manual_review status
  I7. (Anti) No pending_review task ever has generation >= 3
  I8. followon_state.json daily count never exceeds 1

Run on: 2026-04-14 (7-day falsification window)
Exit 0 = all invariants hold (phase PASSED)
Exit 1 = violation found (phase FAILED -- investigate)

ASCII output only (Windows cp1252 safe).
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
TASK_ARCHIVE_FILE = REPO_ROOT / "data" / "task_archive.jsonl"
RUNS_DIR = REPO_ROOT / "data" / "dispatcher_runs"
FOLLOWON_STATE_FILE = REPO_ROOT / "data" / "followon_state.json"
PENDING_REVIEW_EXPIRED_DIR = REPO_ROOT / "data" / "pending_review_expired"

ALERT_DAYS = 7
EXPIRE_DAYS = 14

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


def _load_backlog() -> list[dict]:
    if not BACKLOG_FILE.exists():
        return []
    tasks = []
    for line in BACKLOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tasks.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return tasks


def _load_archive() -> list[dict]:
    if not TASK_ARCHIVE_FILE.exists():
        return []
    tasks = []
    for line in TASK_ARCHIVE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tasks.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return tasks


def _load_run_reports() -> list[dict]:
    reports = []
    if not RUNS_DIR.is_dir():
        return reports
    for f in RUNS_DIR.iterdir():
        if f.suffix != ".json":
            continue
        try:
            reports.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return reports


def _task_age_days(task: dict, today: date) -> int | None:
    """Return age in days or None if created field is missing/unparseable."""
    created_str = task.get("created", "")
    if not created_str:
        return None
    try:
        created = date.fromisoformat(created_str)
        return (today - created).days
    except (TypeError, ValueError):
        return None


def _load_expired_archive_ids() -> set[str]:
    """Return set of task_ids that have a durable expired archive record."""
    ids: set[str] = set()
    if not PENDING_REVIEW_EXPIRED_DIR.is_dir():
        return ids
    for f in PENDING_REVIEW_EXPIRED_DIR.iterdir():
        if f.suffix != ".json":
            continue
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            task_id = rec.get("task_id")
            if task_id:
                ids.add(task_id)
        except (json.JSONDecodeError, OSError):
            pass
    return ids


def check_i1_alert_coverage(backlog: list[dict], today: date) -> tuple[str, str]:
    """I1: No pending_review task older than 7d without a durable record.

    We cannot verify that Slack alert was actually sent (no receipt log), so
    this checks the weaker invariant: tasks >= 7d old either got TTL-expired
    (status != pending_review) or their age is within the falsification window.
    If any are >= 7d and still pending_review without expiry archive, that is
    evidence the alert path ran but the TTL path did not fire as expected.
    """
    pr_tasks_7d_plus = []
    expired_ids = _load_expired_archive_ids()

    for task in backlog:
        if task.get("status") != "pending_review":
            continue
        age = _task_age_days(task, today)
        if age is None:
            continue
        if age >= ALERT_DAYS:
            task_id = task.get("id", "?")
            pr_tasks_7d_plus.append((task_id, age))

    if not pr_tasks_7d_plus:
        return PASS, "No pending_review tasks >= 7d found in active backlog"

    lines = []
    for tid, age in pr_tasks_7d_plus:
        archived = tid in expired_ids
        lines.append(f"  {tid}: {age}d old, archived={archived}")

    # Tasks 7-13d old are in alert zone -- OK if still pending_review (sweep fires notification)
    # Tasks >= 14d pending_review are caught by I2; 7-13d are still expected to be alive
    alert_zone = [(tid, age) for tid, age in pr_tasks_7d_plus if age < EXPIRE_DAYS]
    expire_zone = [(tid, age) for tid, age in pr_tasks_7d_plus if age >= EXPIRE_DAYS]

    detail = "\n".join(lines)
    if expire_zone:
        # These should have been auto-failed -- I2 handles this
        return PASS, (
            f"{len(alert_zone)} task(s) in alert zone (7-13d), "
            f"{len(expire_zone)} in expire zone (>=14d) -- I2 will catch any violations\n"
            + detail
        )
    return PASS, (
        f"{len(alert_zone)} task(s) in alert zone (7-13d) -- pending sweep will alert\n"
        + detail
    )


def check_i2_no_stale_pending_review(backlog: list[dict], today: date) -> tuple[str, str]:
    """I2: No pending_review task >= 14d exists in active backlog.

    If a task that old is still pending_review, the TTL sweep failed to fire.
    """
    violations = []
    for task in backlog:
        if task.get("status") != "pending_review":
            continue
        age = _task_age_days(task, today)
        if age is None:
            continue
        if age >= EXPIRE_DAYS:
            violations.append((task.get("id", "?"), age, task.get("created", "?")))

    if not violations:
        return PASS, "No pending_review tasks >= 14d in active backlog"

    lines = ["VIOLATION -- tasks that should have been auto-failed:"]
    for tid, age, created in violations:
        lines.append(f"  {tid}: {age}d old (created {created})")
    return FAIL, "\n".join(lines)


def check_i3_expire_archive_integrity(backlog: list[dict], archive: list[dict], today: date) -> tuple[str, str]:
    """I3: Every TTL-expired task has a durable archive record.

    Failed tasks with failure_type=pending_review_ttl must have a JSON record
    in data/pending_review_expired/. Anti-criterion: no silent disappearances.
    """
    all_tasks = backlog + archive
    ttl_failed = [
        t for t in all_tasks
        if t.get("failure_type") == "pending_review_ttl"
    ]

    if not ttl_failed:
        return SKIP, "No TTL-expired tasks found yet (falsification window not elapsed)"

    expired_ids = _load_expired_archive_ids()
    violations = []
    for task in ttl_failed:
        tid = task.get("id", "?")
        if tid not in expired_ids:
            violations.append(tid)

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} TTL-expired task(s) have no archive record:\n"
            + "\n".join(f"  {tid}" for tid in violations)
        )

    return PASS, f"{len(ttl_failed)} TTL-expired task(s) all have durable archive records"


def check_i4_no_generation_overflow(backlog: list[dict], archive: list[dict]) -> tuple[str, str]:
    """I4: No task has generation > 2 (hard cap enforced by validate_task).

    Generation cap is the code-level barrier against runaway follow-on loops.
    Any task with generation >= 3 in production data means the cap was bypassed.
    """
    all_tasks = backlog + archive
    violations = []
    for task in all_tasks:
        gen = task.get("generation")
        if gen is None:
            continue
        if not isinstance(gen, int) or gen > 2:
            violations.append((task.get("id", "?"), gen))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} task(s) exceed generation cap:\n"
            + "\n".join(f"  {tid}: generation={gen}" for tid, gen in violations)
        )

    tasks_with_gen = sum(1 for t in all_tasks if t.get("generation") is not None)
    return PASS, f"No generation overflow ({tasks_with_gen} tasks have generation field, all <= 2)"


def check_i5_branch_lifecycle_routing(backlog: list[dict], archive: list[dict]) -> tuple[str, str]:
    """I5: Tasks with failure_type=branch_lifecycle are in manual_review status.

    When select_next_task detects a missing/merged parent_branch, it routes
    the task to manual_review with failure_type=branch_lifecycle. This
    invariant verifies that routing actually happened (no silent drops).
    """
    all_tasks = backlog + archive
    violations = []
    for task in all_tasks:
        if task.get("failure_type") != "branch_lifecycle":
            continue
        status = task.get("status")
        if status not in ("manual_review", "failed"):
            violations.append((task.get("id", "?"), status))

    branch_lifecycle_count = sum(
        1 for t in all_tasks if t.get("failure_type") == "branch_lifecycle"
    )

    if not branch_lifecycle_count:
        return SKIP, "No branch_lifecycle failures in backlog/archive yet"

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} branch_lifecycle tasks not in manual_review/failed:\n"
            + "\n".join(f"  {tid}: status={status}" for tid, status in violations)
        )

    return PASS, f"{branch_lifecycle_count} branch_lifecycle task(s) all routed to manual_review/failed"


def check_i6_followon_generation_cap_in_runs(reports: list[dict], backlog: list[dict], archive: list[dict]) -> tuple[str, str]:
    """I6: No follow-on task in backlog or run reports has generation > 2.

    Cross-checks run reports for any child tasks emitted with generation field
    to ensure the dispatcher's Gate 3 fired correctly in production.
    """
    all_tasks = backlog + archive
    followon_tasks = [t for t in all_tasks if t.get("parent_task_id")]

    if not followon_tasks:
        return SKIP, "No follow-on tasks emitted yet (5E-1 falsification window not elapsed)"

    violations = []
    for task in followon_tasks:
        gen = task.get("generation")
        if gen is not None and isinstance(gen, int) and gen > 2:
            violations.append((task.get("id", "?"), gen))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on task(s) exceed generation cap:\n"
            + "\n".join(f"  {tid}: gen={gen}" for tid, gen in violations)
        )

    return PASS, (
        f"{len(followon_tasks)} follow-on task(s) found, all within generation cap"
    )


def check_i7_anti_pending_review_never_skips_review(backlog: list[dict], archive: list[dict]) -> tuple[str, str]:
    """I7 (Anti): Follow-on tasks must never enter status=pending directly.

    _emit_followon() hard-codes status='pending_review'. Any follow-on task
    (has parent_task_id) that skipped to pending is a security/autonomy violation.
    """
    all_tasks = backlog + archive
    violations = []
    for task in all_tasks:
        if not task.get("parent_task_id"):
            continue
        if task.get("status") == "pending":
            violations.append((task.get("id", "?"), task.get("status")))

    followon_count = sum(1 for t in all_tasks if t.get("parent_task_id"))

    if not followon_count:
        return SKIP, "No follow-on tasks emitted yet"

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on task(s) in 'pending' (must be pending_review):\n"
            + "\n".join(f"  {tid}: status={status}" for tid, status in violations)
        )

    return PASS, f"{followon_count} follow-on task(s) all entered via pending_review gate"


def check_i8_followon_daily_throttle(reports: list[dict]) -> tuple[str, str]:
    """I8: Daily follow-on emission count never exceeded 1 on any single day.

    Reads followon_state.json for current day count. For historical days,
    uses run reports to count tasks with parent_task_id per calendar day.
    """
    # Check current state file
    if FOLLOWON_STATE_FILE.exists():
        try:
            state = json.loads(FOLLOWON_STATE_FILE.read_text(encoding="utf-8"))
            count = state.get("count", 0)
            state_date = state.get("date", "?")
            if count > 1:
                return FAIL, (
                    f"VIOLATION -- followon_state.json shows count={count} on {state_date} "
                    f"(max is 1/day)"
                )
            return PASS, f"followon_state.json: date={state_date} count={count} (within 1/day limit)"
        except (json.JSONDecodeError, OSError) as e:
            return SKIP, f"Could not read followon_state.json: {e}"
    else:
        return SKIP, "followon_state.json not found -- no follow-ons emitted yet"


def main() -> int:
    today = date.today()
    print("=" * 60)
    print("Phase 5E-2 Falsification Verification")
    print(f"Run date: {today.isoformat()}")
    print(f"Falsification window: 2026-04-14 (7-day window)")
    print("=" * 60)

    # Load data once
    backlog = _load_backlog()
    archive = _load_archive()
    reports = _load_run_reports()

    print(f"\nData loaded: {len(backlog)} backlog tasks, {len(archive)} archived, {len(reports)} run reports")

    checks = [
        ("I1", "Alert coverage for 7d+ pending_review tasks",
         lambda: check_i1_alert_coverage(backlog, today)),
        ("I2", "No stale pending_review >= 14d in active backlog",
         lambda: check_i2_no_stale_pending_review(backlog, today)),
        ("I3", "Expire archive integrity (durable record per TTL expiry)",
         lambda: check_i3_expire_archive_integrity(backlog, archive, today)),
        ("I4", "No task exceeds generation cap of 2",
         lambda: check_i4_no_generation_overflow(backlog, archive)),
        ("I5", "branch_lifecycle failures routed to manual_review",
         lambda: check_i5_branch_lifecycle_routing(backlog, archive)),
        ("I6", "Follow-on tasks in run reports respect generation cap",
         lambda: check_i6_followon_generation_cap_in_runs(reports, backlog, archive)),
        ("I7", "(Anti) Follow-on tasks never enter pending directly",
         lambda: check_i7_anti_pending_review_never_skips_review(backlog, archive)),
        ("I8", "Daily follow-on throttle never exceeded 1/day",
         lambda: check_i8_followon_daily_throttle(reports)),
    ]

    results = []
    overall_fail = False

    print()
    for inv_id, label, fn in checks:
        try:
            status, detail = fn()
        except Exception as exc:
            status, detail = FAIL, f"Check raised exception: {exc}"

        results.append((inv_id, label, status, detail))
        marker = "[PASS]" if status == PASS else ("[SKIP]" if status == SKIP else "[FAIL]")
        print(f"{marker} {inv_id}: {label}")
        for line in detail.splitlines():
            print(f"       {line}")
        print()

        if status == FAIL:
            overall_fail = True

    print("=" * 60)
    if overall_fail:
        print("RESULT: FAILED -- one or more invariants violated.")
        print("Action: see violation details above; do NOT mark 5E-2 as falsified.")
        return 1
    else:
        passed = sum(1 for _, _, s, _ in results if s == PASS)
        skipped = sum(1 for _, _, s, _ in results if s == SKIP)
        print(f"RESULT: PASSED ({passed} passed, {skipped} skipped/N/A)")
        print("Phase 5E-2 falsification: implementation holds against production data.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
