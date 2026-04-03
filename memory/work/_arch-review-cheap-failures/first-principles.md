# First-Principles Analysis: Making Failures Cheap in the Jarvis Dispatcher

**Date:** 2026-04-03
**Requested by:** Eric P (arch-review session)
**Data baseline:** 10 dispatcher runs, 3 failures, memory/learning/failures/ empty

---

## Ground Truth From the Code

Before analyzing proposals, here is what the system actually does today:

**On failure:** `handle_task_failure()` updates the task's `status`, `failure_reason`, and `failure_type` fields in the JSONL backlog. That is the entire failure artifact. Nothing is written to `memory/learning/`.

**`hook_learning_capture.py`** has a `--failure` flag that writes to `memory/learning/failures/`. It is never called by the dispatcher. It is an interactive CLI tool for human use only.

**`save_run_report()`** writes a JSON file to `data/dispatcher_runs/` with full task, ISC, and failure detail. This data is rich and complete. It is never read by any learning pipeline.

**`consolidate_overnight.py`** already reads today's dispatcher run reports via `get_dispatcher_reports()` and already produces a human-readable `.md` summary at `data/overnight_summary/YYYY-MM-DD.md`. It already runs (or is scheduled to run) after the dispatcher.

**The failure data from actual runs:**

| Run | Task | Status | Failure Type | Root Cause |
|-----|------|--------|--------------|------------|
| auto-40018 (04-02) | synthesize-signals | failed | rate_limited, misclassified as "No TASK_RESULT line" | Claude Max limit hit at 5:30am; rate limit detector did not fire because exit code was 1, not 0 |
| auto-40018 (04-03) | synthesize-signals | failed | worker_request | Worker wrote TASK_FAILED.md; ISC verified "pass" on a find command that returned empty output (false pass) |
| 5b-002 | synthesize-signals | failed | worker_request | No synthesis source data existed (signals dir was empty); worker correctly gave up |

All 3 failures trace to the same task: synthesize-signals (auto-40018 / 5b-002). The task repeatedly fails because there is no signal data to synthesize. This is a prerequisite gap, not a general dispatcher failure rate.

---

## Root Cause Analysis: The Learning Loop Stall

The learning loop stall is not a symptom of a missing Failure-to-Signal Producer. It is the upstream cause of one recurring task failure (synthesize-signals). The failures in `dispatcher_runs/` look like "3 failures across 10 runs" but are actually "1 task that has failed 3 times for the same environmental reason."

The loop has two broken links:

1. **Signal production is human-session-only.** `hook_learning_capture.py` runs interactively or via session hooks. Autonomous runs produce ISC pass/fail data in `dispatcher_runs/` that is never promoted to learning signals.

2. **The synthesize-signals task is picking itself up before its inputs exist.** The task's ISC checks whether `memory/learning/synthesis/*.md` exists -- that is the output it creates. When no signals exist, the worker has nothing to synthesize, writes TASK_FAILED.md, and the dispatcher correctly marks it failed. But there is no gate that prevents the task from being re-queued while the signal pipeline is dry.

The failures directory being empty is a consequence: the failure recording path was never wired. But fixing it does not fix the synthesize-signals task. That task needs a prerequisite dependency on "at least N signals exist" or a guard that prevents injection when the signal count is too low.

---

## Proposal 1: Failure-to-Signal Producer

**Fundamental problem it solves:** Dispatcher failures are thrown away. Rich failure context in `data/dispatcher_runs/` never enters the learning pipeline. The compound learning paradigm scores 0.65 because the only signals written are human-session signals.

**Assumptions that might be wrong:**

- "Failed runs become training data" assumes the failures contain actionable patterns. At current volume (3 failures, all the same task), the signal-to-noise is too low to synthesize anything. Writing 3 nearly identical signals about "synthesize-signals can't run without source data" teaches nothing new.
- The `hook_learning_capture.py` failure writer already exists. The gap is not tooling -- it is invocation. Building a new producer before fixing the invocation path adds complexity without fixing the root cause.
- This proposal assumes failures are interesting outliers. At 10 runs total, the base rate is too small to distinguish a pattern from a one-off.

**Simplest implementation that satisfies the need:**

Add 4 lines to `dispatch()` after `handle_task_failure()` is called:

```python
if task.get("status") in ("failed", "manual_review"):
    _write_failure_signal(task, report)
```

Where `_write_failure_signal()` calls `hook_learning_capture.py` with `--failure --no-interactive` flags, or more simply, directly calls the `_write_failure()` function imported from that module. No new file, no new concept. Uses the existing `memory/learning/failures/` path.

This is 15-20 lines of code. The output file already has a defined format. The metadata (task_id, failure_type, failure_reason, isc_results) already lives in the report dict.

**Does the current system partially solve this?**

Yes. `data/dispatcher_runs/` contains every failure with more detail than `memory/learning/failures/` would hold. The data exists. The gap is that it is not in the learning directory where `paradigm_health.py` and synthesize-signals can find it.

**ROI given current data:**

Low immediate value, positive long-term infrastructure value. At 3 failures (same task), writing 3 failure signals adds noise. At 30+ failures across diverse tasks, pattern detection becomes meaningful. Build it, but do not expect it to move the paradigm health score this week.

---

## Proposal 2: Overnight Branch Auto-Consolidation

**Fundamental problem it solves:** 47 unreviewed commits on overnight branches that have never merged to main. Eric cannot review them individually without significant time cost. The overnight branch accumulation represents a trust debt: the system produced work that has no consumption path.

**Assumptions that might be wrong:**

- The consolidation script (`consolidate_overnight.py`) ALREADY EXISTS AND ALREADY DOES THIS. It merges `jarvis/auto-*` branches into `jarvis/review-YYYY-MM-DD`, produces a `.md` summary at `data/overnight_summary/YYYY-MM-DD.md`, and sends a Slack notification. The script is complete with self-tests.
- The actual problem is not that consolidation is missing. It is that `consolidate_overnight.py` is not being scheduled to run. The 47 unreviewed commits have accumulated because the scheduled consolidation job is either not set up in Task Scheduler or not running correctly.
- "2 minutes to review 47 commits" is already what `generate_summary_md()` produces: a table of branches, commit counts, file lists, and diff stats. This exists in the code.

**Simplest implementation that satisfies the need:**

Verify whether `consolidate_overnight.py` is scheduled and fix the scheduling gap. Run it manually today with `--dry-run` to confirm it finds the 47 commits, then run it without `--dry-run` to produce the review branch. No code changes needed.

```
python tools/scripts/consolidate_overnight.py --dry-run
python tools/scripts/consolidate_overnight.py
```

Then check `data/overnight_summary/` for today's `.md` file. If it produces a usable summary, the tool works and only the scheduling is broken.

**Does the current system partially solve this?**

The current system fully solves this if invoked. The tool exists and is complete.

**ROI given current data:**

High immediate value because the unreviewed branch debt is real and growing. But this is a scheduling/operations fix, not a code build. Confirm the scheduling setup in Task Scheduler before writing any new code.

---

## Proposal 3: Retry-from-Branch (Replay Log Approximation)

**Fundamental problem it solves:** On retry, the new worker agent starts from main, not from where the prior attempt left off. For tasks where the prior attempt did partial work (committed some files, ran some steps), the retry agent redoes completed steps instead of resuming from the last known-good state.

**Assumptions that might be wrong:**

- The actual 3 failures show zero evidence this problem exists in practice. The auto-40018 failures had zero useful partial work: one was a rate-limit abort (0 seconds of real work), one wrote only a TASK_FAILED.md. 5b-002 wrote only a TASK_FAILED.md. None of these failures produced partial work worth resuming from.
- "Start from the prior branch" assumes the partial work is additive. For many failures (rate limit, worker_request, no_output), the prior branch state is irrelevant or actively wrong -- starting from it could cause the retry agent to build on top of a broken state.
- The `handle_task_failure()` for `partial_work` type already routes to `manual_review` rather than retry -- correctly recognizing that partial work on a branch needs human judgment before a retry attempts to build on top of it.
- The `generate_worker_prompt()` already injects failure context via the `PREVIOUS ATTEMPT FAILED` advisory block, including type-specific guidance for timeouts vs ISC failures and the content of `TASK_FAILED.md`. The agent already has context about what failed; it does not need the prior branch state.

**Simplest implementation that satisfies the need:**

If this were worth building, the implementation is:

```python
# In worktree_setup(), pass an optional base_branch parameter:
existing_branch = f"jarvis/auto-{task['id']}"
result = subprocess.run(["git", "branch", "--list", existing_branch], ...)
if result.stdout.strip() and task.get("retry_count", 0) > 0:
    base = existing_branch  # resume from prior state
else:
    base = "main"
```

This is 8 lines and does not require new infrastructure. But building it now would be premature given that zero real-world failures have shown this is the gap.

**Does the current system partially solve this?**

Yes, through the `PREVIOUS ATTEMPT FAILED` advisory block and `_prior_task_failed_md` context injection. The retry agent is already informed of the failure. The missing piece (branch state) has not proven necessary at current failure types.

**ROI given current data:**

Low. Zero observed failures have been of the "partial work abandoned" type. The most recent retry scenario (auto-40018) was a rate limit abort followed by a worker_request failure -- neither benefits from branch continuity. Build this only when a real `partial_work` retry scenario occurs.

---

## Coupling Analysis

**Are the proposals independent?**

Mostly yes, with one dependency:

- Proposal 1 (failure signals) feeds Proposal 3 indirectly: if failure signals accumulate and show a pattern of partial-work failures, that would justify building Proposal 3. Without failure signal data, the decision to build Proposal 3 is based on speculation.
- Proposal 2 (consolidation scheduling) is fully independent. It is not a code change. It does not interact with failure signals or retry logic.
- Proposal 3 (retry-from-branch) is independent of Proposal 1 but logically follows from having enough failure data to know it is needed.

The practical coupling: fix Proposal 2 first because it requires no code and unblocks human review of 47 commits. This generates real feedback about what overnight work is doing, which is more valuable than any of the code proposals right now.

---

## Priority Order Based on Actual Pain Points

### 1. Verify and fix consolidation scheduling (Proposal 2 prerequisite -- same day)

The 47 unreviewed commits are the most concrete evidence of a broken feedback loop. Run `consolidate_overnight.py --dry-run` now to confirm the tool works. Then check Task Scheduler for whether the 6am consolidation job is configured. If not, set it up. This costs 30 minutes and unlocks the review path for weeks of accumulated work.

### 2. Wire failure signals into the dispatcher (Proposal 1 -- 1-2 hours)

The implementation is small (import `_write_failure` from `hook_learning_capture`, call it after `handle_task_failure`). This is the lowest-effort piece of infrastructure that closes the compound learning gap. It will not move the paradigm health score today, but every failure after this point produces a learning record. This is the kind of one-time wiring that compounds over time.

The key constraint: do NOT write a signal for rate_limited failures. Rate limiting is an environment event, not a task failure pattern. The signal should only fire for `isc_fail`, `no_output`, `worker_request`, and `scope_creep` types.

### 3. Fix the synthesize-signals prerequisite gate (not in the three proposals -- but the real fix)

All 3 failures trace to the same broken precondition: the synthesize-signals task runs when there is nothing to synthesize. The correct fix is a task-level guard, not a new producer. Options:

a. Add a `prerequisite_check` field to the task: `"min_signals": 5`. Dispatcher checks this before selecting the task.
b. Or: the synthesize-signals worker should check signal count at the start and exit cleanly (not fail) when below threshold, matching the "Idle Is Success" doctrine.

This is the actual root cause of 3/3 failures. Fixing it removes 100% of the observed failure rate.

### 4. Skip Proposal 3 until a real partial-work failure occurs

No observed failure pattern justifies this build. The advisory block already provides retry context. Revisit when a failure with `commit_count > 0 and retries_exhausted` appears in the run reports.

---

## Is the Learning Loop Stall the Root Cause?

Partially. Here is the cleaner causal chain:

```
synthesize-signals task has no prerequisite guard
  -> task is selected when signal pipeline is dry
    -> worker fails, writes TASK_FAILED.md
      -> failure is not written to memory/learning/failures/  [learning loop stall]
        -> compound learning paradigm score stays at 0.65
          -> paradigm_health reports unhealthy compound learning
            -> oversight: "system feels broken"
```

The learning loop stall makes the failure invisible at the memory layer. But removing it does not fix the synthesize-signals task. The root cause is the missing prerequisite gate on the task itself.

The 0.65 compound learning score reflects two real gaps: (1) no autonomous failure signals produced and (2) no synthesis happening. Fix (1) with Proposal 1. Fix (2) by adding the prerequisite guard so synthesize-signals runs only when there is source data to synthesize.

---

## ISC for a Minimal Implementation Sprint

If building Proposals 1 and 2 as a sprint:

- [ ] `dispatch()` calls `_write_failure_signal()` after `handle_task_failure()` for failure_type in (isc_fail, no_output, worker_request, scope_creep) | Verify: grep -c "_write_failure_signal" tools/scripts/jarvis_dispatcher.py
- [ ] Failure signal appears in memory/learning/failures/ after next dispatcher failure | Verify: ls memory/learning/failures/
- [ ] Rate-limited runs do NOT produce failure signals | Verify: Review logic in _write_failure_signal(), check rate_limited guard
- [ ] consolidate_overnight.py runs successfully via manual invocation | Verify: python tools/scripts/consolidate_overnight.py --dry-run
- [ ] Today's overnight summary exists at data/overnight_summary/YYYY-MM-DD.md | Verify: test -f data/overnight_summary/$(date +%Y-%m-%d).md
- [ ] synthesize-signals task has a prerequisite signal count guard that exits cleanly when count < 5 | Verify: Read worker logic or task definition; confirm no TASK_FAILED.md on next run with 0 signals
