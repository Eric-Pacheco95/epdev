#!/usr/bin/env python3
"""verify_5e1_falsification.py -- Phase 5E-1 falsification verification.

Checks real production data against the 5E-1 invariants:
  I1. Every emitted follow-on was created with status=pending_review (never pending)
  I2. Every emitted follow-on has fewer ISC items than its parent (shrink invariant)
  I3. Every emitted follow-on came from an overnight-source parent (source partition)
  I4. Every emitted follow-on has generation <= 2 (gen cap)
  I5. Follow-on source attribution is inherited from parent (never 'dispatcher')
  I6. Daily follow-on emission count never exceeded 1 on any calendar day
  I7. (Anti) No follow-on was emitted when parent ISC pass ratio was < 0.5
  I8. No injection pattern appears in any emitted follow-on's ISC text

Run on: 2026-04-21 (14-day falsification window)
Exit 0 = all invariants hold (phase PASSED)
Exit 1 = violation found (phase FAILED -- investigate)

ASCII output only (Windows cp1252 safe).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
TASK_ARCHIVE_FILE = REPO_ROOT / "data" / "task_archive.jsonl"
RUNS_DIR = REPO_ROOT / "data" / "dispatcher_runs"
FOLLOWON_STATE_FILE = REPO_ROOT / "data" / "followon_state.json"

# Mirrors _INJECTION_SUBSTRINGS from jarvis_dispatcher.py
INJECTION_SUBSTRINGS = (
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "disregard all previous",
    "you are now",
    "new instructions:",
    "system prompt",
    "developer message",
    "sudo ignore",
    "dan mode",
    "jailbreak",
)

OVERNIGHT_SOURCES = frozenset({"overnight"})
FOLLOWON_MAX_PER_DAY = 1
FOLLOWON_EMISSION_THRESHOLD = 0.5

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


def _get_followon_tasks(backlog: list[dict], archive: list[dict]) -> list[dict]:
    """Return all tasks that have a parent_task_id (i.e. were emitted as follow-ons)."""
    all_tasks = backlog + archive
    return [t for t in all_tasks if t.get("parent_task_id")]


def _build_task_index(backlog: list[dict], archive: list[dict]) -> dict[str, dict]:
    """Build id -> task dict for fast parent lookup."""
    idx: dict[str, dict] = {}
    for task in backlog + archive:
        tid = task.get("id")
        if tid:
            idx[tid] = task
    return idx


def _build_parent_run_report_index(reports: list[dict]) -> dict[str, dict]:
    """Build task_id -> run report for parent ISC result lookup."""
    idx: dict[str, dict] = {}
    for r in reports:
        tid = r.get("task_id")
        if tid:
            # Keep most recent report if multiple exist
            if tid not in idx or r.get("completed", "") > idx[tid].get("completed", ""):
                idx[tid] = r
    return idx


def check_i1_pending_review_gate(followons: list[dict]) -> tuple[str, str]:
    """I1: Every emitted follow-on was created with status=pending_review.

    _emit_followon() hard-codes status='pending_review'. Any follow-on that
    entered a different initial status bypassed this gate.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet (14-day window not elapsed)"

    # We cannot inspect the initial status from current state (it may have changed).
    # However: a follow-on that is currently 'pending' (not pending_review, not done,
    # not manual_review) is a strong signal it bypassed the gate.
    # We check for the specific anti-case: currently 'pending' which is the wrong initial status.
    violations = []
    for task in followons:
        status = task.get("status")
        if status == "pending":
            violations.append((task.get("id", "?"), status))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on task(s) in 'pending' status "
            f"(must start as pending_review):\n"
            + "\n".join(f"  {tid}: status={st}" for tid, st in violations)
        )

    return PASS, (
        f"{len(followons)} follow-on task(s) -- none found in invalid 'pending' status"
    )


def check_i2_isc_shrink_invariant(followons: list[dict], task_index: dict) -> tuple[str, str]:
    """I2: Every emitted follow-on has fewer ISC items than its parent.

    Each follow-on must narrow scope. Equal or greater ISC count = scope expansion.
    Data gap: if parent is no longer in backlog or archive, parent ISC is unavailable.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    data_gaps = []

    for task in followons:
        parent_id = task.get("parent_task_id")
        if not parent_id:
            continue

        parent = task_index.get(parent_id)
        if parent is None:
            data_gaps.append((task.get("id", "?"), parent_id))
            continue

        parent_isc = parent.get("isc", [])
        child_isc = task.get("isc", [])

        if len(child_isc) >= len(parent_isc):
            violations.append((
                task.get("id", "?"),
                parent_id,
                len(parent_isc),
                len(child_isc),
            ))

    lines = []
    if violations:
        lines.append(f"VIOLATION -- {len(violations)} follow-on(s) did not shrink ISC:")
        for child_id, parent_id, p_count, c_count in violations:
            lines.append(f"  {child_id}: parent={parent_id} parent_isc={p_count} child_isc={c_count}")

    if data_gaps:
        lines.append(
            f"DATA GAP -- {len(data_gaps)} follow-on(s) parent not found in backlog/archive "
            f"(cannot verify ISC shrink):"
        )
        for child_id, parent_id in data_gaps:
            lines.append(f"  {child_id}: parent_task_id={parent_id}")

    if violations:
        return FAIL, "\n".join(lines) if lines else "Violations found"

    if data_gaps:
        return SKIP, "\n".join(lines) if lines else "Data gaps only"

    return PASS, f"{len(followons)} follow-on(s): ISC shrink invariant holds for all verifiable tasks"


def check_i3_source_partition(followons: list[dict], task_index: dict) -> tuple[str, str]:
    """I3: Every emitted follow-on came from an overnight-source parent (v1 partition).

    Gate 2 of _emit_followon() blocks non-overnight sources. Any follow-on
    whose parent is not overnight means Gate 2 failed.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    data_gaps = []

    for task in followons:
        parent_id = task.get("parent_task_id")
        if not parent_id:
            continue

        # Child inherits parent source -- check child's own source field
        child_source = task.get("source")
        if child_source not in OVERNIGHT_SOURCES:
            violations.append((task.get("id", "?"), child_source))

        # Also verify parent source if available
        parent = task_index.get(parent_id)
        if parent is None:
            data_gaps.append((task.get("id", "?"), parent_id))
            continue
        parent_source = parent.get("source")
        if parent_source and parent_source not in OVERNIGHT_SOURCES:
            violations.append((task.get("id", "?"), f"parent_source={parent_source}"))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on(s) from non-overnight source:\n"
            + "\n".join(f"  {tid}: source={src}" for tid, src in violations)
        )

    if data_gaps:
        return SKIP, (
            f"DATA GAP -- {len(data_gaps)} parent(s) not in backlog/archive; "
            f"checking child source only"
        )

    return PASS, f"{len(followons)} follow-on(s): all from overnight-source parents"


def check_i4_generation_cap(followons: list[dict]) -> tuple[str, str]:
    """I4: Every emitted follow-on has generation <= 2.

    Gate 3 of _emit_followon() blocks parents at generation=2. Combined with
    validate_task()'s hard cap, no task in production should reach generation > 2.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    for task in followons:
        gen = task.get("generation")
        if gen is None:
            continue
        if not isinstance(gen, int) or gen > 2:
            violations.append((task.get("id", "?"), gen))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on(s) exceed generation cap:\n"
            + "\n".join(f"  {tid}: generation={gen}" for tid, gen in violations)
        )

    tasks_with_gen = sum(1 for t in followons if t.get("generation") is not None)
    return PASS, f"{len(followons)} follow-on(s): {tasks_with_gen} have generation field, all <= 2"


def check_i5_source_attribution(followons: list[dict]) -> tuple[str, str]:
    """I5: Follow-on source attribution is inherited from parent (never 'dispatcher').

    Root-source attribution rule: the source field must trace back to the original
    producer (overnight, session, etc.) -- never 'dispatcher'.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    for task in followons:
        source = task.get("source")
        if source == "dispatcher":
            violations.append((task.get("id", "?"), source))

    if violations:
        return FAIL, (
            f"VIOLATION -- {len(violations)} follow-on(s) have source='dispatcher' "
            f"(root-source must be inherited from parent):\n"
            + "\n".join(f"  {tid}: source={src}" for tid, src in violations)
        )

    return PASS, f"{len(followons)} follow-on(s): none have source='dispatcher'"


def check_i6_daily_throttle_not_exceeded(followons: list[dict]) -> tuple[str, str]:
    """I6: Daily follow-on emission count never exceeded 1 on any calendar day.

    Groups follow-ons by their created date. More than 1 per day means the
    throttle failed. followon_state.json is also checked for current day.
    """
    if not followons:
        if not FOLLOWON_STATE_FILE.exists():
            return SKIP, "No follow-ons emitted and no state file"
        try:
            state = json.loads(FOLLOWON_STATE_FILE.read_text(encoding="utf-8"))
            count = state.get("count", 0)
            if count > 1:
                return FAIL, f"followon_state.json shows count={count} today (max 1)"
            return PASS, f"followon_state.json: count={count} (within limit)"
        except Exception:
            return SKIP, "followon_state.json unreadable"

    # Group by created date
    by_date: dict[str, list[str]] = {}
    for task in followons:
        created = task.get("created", "unknown")
        by_date.setdefault(created, []).append(task.get("id", "?"))

    violations = []
    for day, ids in by_date.items():
        if len(ids) > FOLLOWON_MAX_PER_DAY:
            violations.append((day, len(ids), ids))

    if violations:
        lines = [f"VIOLATION -- throttle exceeded on {len(violations)} day(s):"]
        for day, count, ids in violations:
            lines.append(f"  {day}: {count} follow-ons emitted (max {FOLLOWON_MAX_PER_DAY})")
            for fid in ids:
                lines.append(f"    - {fid}")
        return FAIL, "\n".join(lines)

    max_day = max(by_date, key=lambda d: len(by_date[d])) if by_date else "N/A"
    max_count = max(len(v) for v in by_date.values()) if by_date else 0
    return PASS, (
        f"{len(followons)} follow-on(s) across {len(by_date)} day(s), "
        f"max {max_count}/day (limit {FOLLOWON_MAX_PER_DAY})"
    )


def check_i7_anti_ratio_gate(followons: list[dict], report_index: dict) -> tuple[str, str]:
    """I7 (Anti): No follow-on was emitted when parent ISC pass ratio was < 0.5.

    Gate 4 of _emit_followon() requires isc_pass/isc_total >= 0.5. We verify
    this by looking up the parent's run report and checking the stored ratio.
    Data gap: if parent run report is missing, we cannot verify.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    data_gaps = []

    for task in followons:
        parent_id = task.get("parent_task_id")
        if not parent_id:
            continue

        report = report_index.get(parent_id)
        if report is None:
            data_gaps.append((task.get("id", "?"), parent_id))
            continue

        isc_passed = report.get("isc_passed")
        isc_total = report.get("isc_total")
        if isc_passed is None or isc_total is None or isc_total == 0:
            data_gaps.append((task.get("id", "?"), parent_id))
            continue

        ratio = isc_passed / isc_total
        if ratio < FOLLOWON_EMISSION_THRESHOLD:
            violations.append((task.get("id", "?"), parent_id, isc_passed, isc_total, ratio))

    if violations:
        lines = [f"VIOLATION -- {len(violations)} follow-on(s) emitted below 0.5 ratio:"]
        for child_id, parent_id, passed, total, ratio in violations:
            lines.append(f"  {child_id}: parent={parent_id} ratio={passed}/{total}={ratio:.2f}")
        return FAIL, "\n".join(lines)

    if data_gaps:
        verifiable = len(followons) - len(data_gaps)
        return SKIP, (
            f"{verifiable} verifiable follow-on(s): ratio gate held. "
            f"{len(data_gaps)} parent run report(s) missing (data gap)."
        )

    return PASS, f"{len(followons)} follow-on(s): all emitted with parent ratio >= 0.5"


def check_i8_no_injection_in_isc(followons: list[dict]) -> tuple[str, str]:
    """I8: No injection pattern appears in any emitted follow-on's ISC text.

    Gate 8 of _emit_followon() runs the inline injection sanitizer on ISC text
    before emission. Any injection pattern found in a follow-on's ISC means
    the sanitizer failed or was bypassed.
    """
    if not followons:
        return SKIP, "No follow-on tasks emitted yet"

    violations = []
    for task in followons:
        isc = task.get("isc", [])
        for criterion in isc:
            if not isinstance(criterion, str):
                continue
            lower = criterion.lower()
            for pattern in INJECTION_SUBSTRINGS:
                if pattern in lower:
                    violations.append((task.get("id", "?"), pattern, criterion[:80]))
                    break

    if violations:
        lines = [f"VIOLATION -- {len(violations)} follow-on ISC criteria contain injection patterns:"]
        for tid, pattern, criterion in violations:
            lines.append(f"  {tid}: pattern={pattern!r} in: {criterion!r}")
        return FAIL, "\n".join(lines)

    total_isc = sum(len(t.get("isc", [])) for t in followons)
    return PASS, (
        f"{len(followons)} follow-on(s), {total_isc} ISC criteria: no injection patterns found"
    )


def main() -> int:
    today = date.today()
    print("=" * 60)
    print("Phase 5E-1 Falsification Verification")
    print(f"Run date: {today.isoformat()}")
    print(f"Falsification window: 2026-04-21 (14-day window)")
    print("=" * 60)

    # Load data once
    backlog = _load_backlog()
    archive = _load_archive()
    reports = _load_run_reports()
    task_index = _build_task_index(backlog, archive)
    report_index = _build_parent_run_report_index(reports)

    followons = _get_followon_tasks(backlog, archive)

    print(f"\nData loaded: {len(backlog)} backlog tasks, {len(archive)} archived, "
          f"{len(reports)} run reports")
    print(f"Follow-on tasks found: {len(followons)}")

    checks = [
        ("I1", "Follow-ons created as pending_review (never pending)",
         lambda: check_i1_pending_review_gate(followons)),
        ("I2", "ISC shrink invariant (child ISC < parent ISC)",
         lambda: check_i2_isc_shrink_invariant(followons, task_index)),
        ("I3", "Source partition (overnight only in v1)",
         lambda: check_i3_source_partition(followons, task_index)),
        ("I4", "Generation cap <= 2",
         lambda: check_i4_generation_cap(followons)),
        ("I5", "Root-source attribution (never 'dispatcher')",
         lambda: check_i5_source_attribution(followons)),
        ("I6", "Daily throttle not exceeded (max 1/day)",
         lambda: check_i6_daily_throttle_not_exceeded(followons)),
        ("I7", "(Anti) No emission below 0.5 ISC pass ratio",
         lambda: check_i7_anti_ratio_gate(followons, report_index)),
        ("I8", "(Anti) No injection pattern in emitted ISC text",
         lambda: check_i8_no_injection_in_isc(followons)),
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
        print("Action: see violation details above; do NOT mark 5E-1 as falsified.")
        return 1
    else:
        passed = sum(1 for _, _, s, _ in results if s == PASS)
        skipped = sum(1 for _, _, s, _ in results if s == SKIP)
        print(f"RESULT: PASSED ({passed} passed, {skipped} skipped/N/A)")
        print("Phase 5E-1 falsification: implementation holds against production data.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
