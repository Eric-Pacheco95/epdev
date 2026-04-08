# Falsification Runbook: Phase 5E-1 and 5E-2

## When to Run

| Phase | Date | Window | Command |
|-------|------|--------|---------|
| 5E-2  | 2026-04-14 | 7-day  | `python tools/scripts/verify_5e2_falsification.py` |
| 5E-1  | 2026-04-21 | 14-day | `python tools/scripts/verify_5e1_falsification.py` |

Run from repo root. Exit 0 = PASSED (keep implementation). Exit 1 = FAILED (investigate).

Both scripts are idempotent reads -- safe to re-run at any time.

---

## Phase 5E-2 Invariants (pending_review TTL + branch lifecycle + generation cap)

| ID | Invariant | Real violation? |
|----|-----------|-----------------|
| I1 | No pending_review task >= 7d lacks coverage (alert zone check) | Yes if task is >= 7d and sweep never ran |
| I2 | No pending_review task >= 14d still in active backlog | Yes -- TTL sweep failed to fire |
| I3 | Every TTL-expired task has a JSON record in data/pending_review_expired/ | Yes -- silent disappearance |
| I4 | No task has generation > 2 in backlog or archive | Yes -- validate_task cap bypassed |
| I5 | Tasks with failure_type=branch_lifecycle are in manual_review or failed | Yes -- routing bug |
| I6 | Follow-on tasks in run reports all have generation <= 2 | Yes -- Gate 3 in _emit_followon bypassed |
| I7 | No follow-on task ever entered status=pending directly | Yes -- pending_review gate bypassed |
| I8 | followon_state.json daily count never > 1 | Yes -- throttle failed |

---

## Phase 5E-1 Invariants (deterministic follow-on emission, 9 gates)

| ID | Invariant | Real violation? |
|----|-----------|-----------------|
| I1 | Every follow-on created with status=pending_review | Yes -- autonomy bypass |
| I2 | Every follow-on has fewer ISC than parent (shrink invariant) | Yes -- Gate 9 failed |
| I3 | Every follow-on source is overnight (v1 partition) | Yes -- Gate 2 failed |
| I4 | Every follow-on has generation <= 2 | Yes -- Gate 3 failed |
| I5 | Follow-on source never equals 'dispatcher' | Yes -- root-source attribution broken |
| I6 | Max 1 follow-on emitted per calendar day | Yes -- Gate 6 (throttle) failed |
| I7 | No follow-on emitted when parent pass ratio < 0.5 | Yes -- Gate 4 failed |
| I8 | No injection pattern in any emitted follow-on ISC text | Yes -- Gate 8 failed |

---

## Known Edge Cases (not real violations)

- **SKIP output**: A check shows SKIP when no follow-on tasks exist yet or no TTL-expired tasks
  exist. This is expected before the falsification window elapses. SKIP is not FAIL.
- **Data gap (I2, I7)**: If a parent task was archived before the follow-on was created, the
  parent's ISC or run report may be unavailable. This is a data gap, not a violation -- the
  check will SKIP that specific follow-on with a "DATA GAP" note.
- **I1 showing alert-zone tasks**: pending_review tasks 7-13d old in the active backlog are
  normal; they are in the alert zone and will get a Slack notification on the next dispatcher
  run. Only tasks >= 14d that are still pending_review are actual violations (caught by I2).
- **Duplicate routine task IDs in backlog**: The backlog currently contains 5 duplicate entries
  for task-1775467802350228 (routine source). This is a pre-existing dedup issue unrelated to
  5E-2 and does not affect any invariant.

---

## If a Violation Is Found

### Severity: FAIL on I2 (stale pending_review)
The TTL sweep did not fire. Check if the dispatcher ran at all during the window:
look at data/dispatcher_runs/ for recent timestamps. If the dispatcher was paused,
the invariant is not falsified -- it means the sweep only runs when dispatch() is called.
**Action**: Resume dispatcher; re-run verification in 24h.

### Severity: FAIL on I3 (no archive record)
A task was auto-failed but its archive record is missing. Check for disk write errors.
**Action**: Manually create the missing record from the task's backlog entry; patch
`archive_expired_pending_review()` if the write path is broken.

### Severity: FAIL on I4 (generation > 2)
The `validate_task()` hard cap was bypassed. This means a task was injected directly
into the backlog JSON without going through `backlog_append()`. Check git history for
manual edits to task_backlog.jsonl.
**Action**: Remove the offending task; audit who wrote it.

### Severity: FAIL on I7 (follow-on emitted below 0.5 ratio)
Gate 4 in `_emit_followon()` failed. This is a code bug -- roll back to commit `26e90d0`
and investigate before re-enabling the dispatcher.
**Action**: `git revert 26e90d0` or patch Gate 4; add a unit test for the specific case.

### Severity: FAIL on I8 (injection in ISC text)
Gate 8 failed to block a tainted ISC string. This is a security event.
**Action**: Log to history/security/; remove the tainted follow-on task from backlog;
review the parent task for compromise; run `/security-audit`.

---

## Data Gaps That Block Full Falsification

1. **No Slack receipt log**: I1 checks alert coverage structurally (task age) but cannot
   verify that the Slack notification was actually delivered. To close this gap, add a
   `data/pending_review_alerts.jsonl` log written by `apply_pending_review_sweep()`.

2. **Parent tasks archived before follow-on**: If a parent task rolls off the active backlog
   into `data/task_archive.jsonl` before the follow-on is created, I2 and I7 cannot verify
   ISC counts or pass ratios from the run report. To close: ensure parent run reports are
   retained for 30d (currently no TTL on dispatcher_runs/).

3. **No historical throttle log**: I6 checks current-day state via followon_state.json but
   cannot audit prior days unless run reports are cross-referenced by created date.
   followon_state.json only stores current day; prior days are reconstructed from task.created.
