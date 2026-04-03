# First-Principles Architecture Review: Unified Jarvis Task Pipeline
# Date: 2026-04-02
# Author: Jarvis (architect agent)
# Sources read: jarvis_dispatcher.py, overnight_runner.py, heartbeat_config.json,
#               orchestration/task_backlog.jsonl

---

## 1. FUNDAMENTAL PROBLEM -- What Convergence Actually Solves

### What exists today

Three separate execution surfaces that each handle "do work autonomously":

  A. jarvis_dispatcher.py
     - Reads task_backlog.jsonl, selects one task, runs it in a worktree, verifies ISC.
     - Triggered by Task Scheduler on a cadence (or manually).
     - Understands task schema: id, tier, priority, isc, autonomous_safe, model, status.

  B. overnight_runner.py
     - Six fixed dimensions (scaffolding, codebase_health, ...) defined in program.md.
     - Runs sequentially within a 100-min time budget, inside a single worktree.
     - Does NOT read from task_backlog.jsonl. Completely separate state (overnight_state.json).
     - Has its own claude lock, its own worktree directory (epdev-overnight vs epdev-dispatch).
     - Quality gate and security audit run once at the end, covering all dimensions.

  C. heartbeat_config.json remediation_map
     - When a metric threshold is crossed, heartbeat proposes a task and writes it to
       task_backlog.jsonl (field: source="heartbeat").
     - Remediation map entries carry: description, skills, isc, context_files, model.
     - This IS already writing into the shared backlog -- partial convergence exists.

### What the proposal claims to unify

All work -> task_backlog.jsonl -> quality gate -> dispatcher -> execution.

### The fundamental problem being solved

There are two real problems, not one:

  PROBLEM 1: Duplicated machinery.
  The overnight runner reinvents worktrees, claude lock, ISC verification, and Slack
  notification independently of the dispatcher. Any improvement to one (e.g., new
  security rules, better prompt assembly) must be applied twice. This is a maintenance
  and correctness risk.

  PROBLEM 2: No unified visibility.
  Heartbeat can see backlog health (backlog_pending_count, backlog_failed_count) but
  cannot see overnight runner state at all. A human must check two places (backlog +
  overnight_state.json) to understand what autonomous work is queued or running.
  The two systems can also conflict: overnight runner and dispatcher each acquire
  acquire_claude_lock(), so they will block each other, but neither reports WHY the
  other is blocked.

What convergence does NOT solve:
  - The fundamental difference in execution model: dispatcher is task-discrete
    (one task, verify, done), overnight runner is iterative (N improvement loops per
    dimension, discard bad iterations). These are NOT the same execution model and
    cannot share a single worker.
  - Claude API rate limits or cost. A shared backlog does not reduce model invocations;
    it only changes how they are scheduled.

---

## 2. IRREDUCIBLE REQUIREMENTS -- The Minimum a Unified System Must Satisfy

These requirements cannot be removed without degrading the system:

  R1. SINGLE SOURCE OF TRUTH FOR TASK STATE
      Any task, from any source, must have a canonical status (pending, running, done,
      failed, deferred) readable by any observer. Duplicating state across two files
      (overnight_state.json + task_backlog.jsonl) violates this.

  R2. EXCLUSIVE EXECUTION (no concurrent mutation)
      Only one autonomous worker may hold a worktree and invoke claude -p at a time
      (Claude Max is a single-user license; concurrent invocations contend on rate limits
      and worktree dirs). The dispatcher already has this via dispatcher.lock +
      acquire_claude_lock(). The overnight runner has it via acquire_claude_lock() alone.
      A unified system needs exactly one lock abstraction.

  R3. TASK SCHEMA COMPLETENESS
      Every task must carry: id, description, isc (>=1 executable criterion), tier,
      autonomous_safe, status, source, model, priority. Without these fields,
      select_next_task() cannot make a safe selection decision.

  R4. QUALITY GATE BEFORE EXECUTION
      Tasks without valid ISC, without autonomous_safe=true, or with dangerous verify
      commands must be rejected before a worktree is created -- not after.

  R5. SESSION WORK MUST NOT BLOCK INTERACTIVE FLOW
      Session-originated tasks are written asynchronously to the backlog. The dispatcher
      picks them up later. The human session does not wait for the dispatcher.

  R6. IDLE IS SUCCESS
      Zero pending tasks, zero threshold crossings, zero proposed tasks is a valid and
      healthy state. The system must not generate noise to justify its existence.

  R7. AUDIT TRAIL
      Every dispatch decision (selected, skipped, failed, why) must be logged.
      The dispatcher already does this via data/dispatcher_runs/. Overnight runner
      logs to memory/work/jarvis/autoresearch/overnight-DATE/. Unified logging must
      not lose either.

  R8. SECURITY ISOLATION
      Each task executes in its own worktree. No task may write to the main working
      tree. No task may read protected paths (.env, credentials, TELOS, constitutional
      rules). These rules are already enforced at worktree setup and in prompt assembly;
      a unified system must preserve them.

---

## 3. BOTTLENECK ANALYSIS -- Single Dispatcher Risks and Mitigations

### The bottleneck as stated

One dispatcher, one lock, one task at a time. What happens when the dispatcher is
busy (running a 2-hour Tier 1 task) and a new high-priority task arrives?

### What actually happens today

  a. New task enters backlog with status=pending.
  b. Dispatcher is locked (dispatcher.lock held, acquire_claude_lock() held).
  c. Task Scheduler fires dispatcher again on its cadence.
  d. Dispatcher reads lock, sees it is fresh (< 4h), exits immediately with "Lock held."
  e. New task waits until current task completes.
  f. On next run, new task is selected if it has highest priority.

This is correct serial behavior. The risk is latency, not correctness.

### Real bottleneck risks

  RISK A: A Tier 2 routine task (low priority, 20-min runtime) blocks a Tier 0
  security task (high priority) for the duration of the lock.
  CURRENT MITIGATION: MAX_TIER=2 env var allows caps; priority sort in select_next_task()
  ensures highest-priority pending task runs next. But "next" may be hours away.
  UNMITIGATED: No preemption. A running task cannot be interrupted.

  RISK B: The overnight runner and dispatcher both acquire_claude_lock(). If the
  overnight runner starts (e.g., midnight) and holds the lock for 100 minutes, any
  dispatcher task is blocked until 1:40am. The overnight runner does not write its
  state to task_backlog.jsonl, so the backlog health metric shows 0 running when one
  is actually running. False-clean heartbeat reading.
  UNMITIGATED: The two systems share a lock but not a visibility layer.

  RISK C: Long-running tasks that fail mid-execution leave the worktree in an unknown
  state. The dispatcher's finally block calls release_claude_lock() and worktree_cleanup(),
  so this is handled. But if the process is killed (Task Scheduler timeout, power loss),
  the stale lock threshold (4h) is the only recovery. A killed overnight run with a
  100-min budget could hold the lock for up to 4h after kill.

### Mitigations that are sufficient without parallelism

  M1. Priority-tiered scheduling: Tier 0 tasks always preempt Tier 1/2 AT SELECTION TIME
      (already implemented in select_next_task). Good enough for most cases.
  M2. Time-box tasks: enforce per-task timeout at dispatch level (not just claude -p level),
      so a runaway task doesn't hold the lock indefinitely.
  M3. Expose running state in backlog: when dispatcher claims a task, immediately write
      status=running to backlog. Heartbeat then sees running count, not just pending count.
  M4. Unified lock visibility: both overnight runner and dispatcher write their lock
      acquisition to a shared lock_registry.json so heartbeat can show "overnight running"
      as a distinct state.

### Is parallelism the right answer?

No. Not yet. Reasons:
  - Claude Max is a single-user license. Parallel claude -p invocations contend on the
    same rate limit pool. Two parallel tasks do not run in half the time; they run in
    the same time with higher error rates.
  - Worktrees for parallel tasks would need separate branch namespaces and merge
    sequencing. This adds git complexity for marginal gain.
  - The actual observed bottleneck (from backlog.jsonl data) is not "too many tasks
    waiting" but "one task fails ISC and retries." Parallelism doesn't help retries.

Parallelism becomes worth building when: (a) Claude Max expands to multi-session API
access, or (b) tasks are genuinely CPU-bound and don't use claude at all (collectors,
lint, test runs). Those can run outside the dispatcher lock entirely.

---

## 4. QUALITY GATE PLACEMENT -- Where Validation Belongs and Why

### Current state

Quality gate logic lives INSIDE the dispatcher (select_next_task function):
  - autonomous_safe check
  - MAX_TIER check
  - dependency resolution (all_deps_met)
  - deliverable pre-existence check
  - context_files path safety check (validate_context_files)
  - ISC command classification (classify_verify_method, sanitize_isc_command)
  - verifiable_count >= 1 check

There is no separate pre-processor. Tasks written to backlog by heartbeat or by session
are not validated at write time -- only at dispatch time.

### The problem with gate-at-dispatch

  - An invalid task (missing ISC, dangerous verify command) sits in backlog at status=pending
    indefinitely. It is never executed but also never explicitly marked invalid.
  - A human writing a session task to backlog gets no feedback until the dispatcher runs
    (potentially hours later).
  - The heartbeat remediation_map writes tasks with well-formed ISC (heartbeat is trusted
    code), but a manually added task or a future "chat idea -> backlog" pathway has no
    validation at write time.

### Where the gate belongs: BOTH

The right design has two stages, not one-or-the-other:

  STAGE 1: WRITE GATE (at task creation, any source)
  Validates: schema completeness (required fields present), ISC syntax (| Verify: present),
  autonomous_safe field present (can be false -- the gate doesn't require true, just that
  the field exists), tier in [0,1,2].
  On failure: task is written with status=invalid, notes explains why.
  Purpose: fast feedback, clean backlog, no zombie pending tasks.

  STAGE 2: DISPATCH GATE (at selection time, inside dispatcher)
  Validates: autonomous_safe=true, tier <= MAX_TIER, deps met, deliverable doesn't
  pre-exist, context_files safe, ISC commands safe and executable.
  On failure: task is skipped this run (not permanently rejected -- MAX_TIER may change,
  deps may complete).
  Purpose: runtime safety, correct selection from a pre-cleaned pool.

  The current design collapses both into Stage 2. Adding Stage 1 as a lightweight
  backlog_writer.py (or inline validation in any write path) is the simplest fix.

### Quality gate should NOT be a separate long-running service

A pre-processor that polls the backlog introduces its own scheduling, its own lock,
its own failure modes. The Stage 1 gate is a synchronous function called at write time,
not a daemon. This is simpler and has no new moving parts.

---

## 5. SESSION INTEGRATION -- How Interactive Work Enters the Async Pipeline

### The tension

Interactive sessions are synchronous and latency-sensitive. A human is waiting.
The backlog is an async queue consumed by a scheduled process.
These must not be coupled: writing to the backlog must never block the session.

### What "session-originated task" actually means

Three distinct cases with different integration needs:

  CASE A: Human says "add this to the backlog for later."
  Session writes a task to task_backlog.jsonl and confirms the write. Done.
  No execution in the session. No blocking. This is the clean case.
  Currently works: the human (or Jarvis in session) manually appends to backlog.

  CASE B: Human completes a partial task and says "the rest can run autonomously."
  Session commits current state, writes a follow-up task to backlog, closes.
  Dispatcher picks up follow-up on next run.
  This requires the session-created task to have a valid ISC before writing.
  The Stage 1 write gate (Section 4) is the solution here.

  CASE C: Session wants to delegate a subtask to the dispatcher DURING the session
  and wait for the result.
  THIS IS THE ANTI-PATTERN. Do not build it. Reasons:
  - Dispatcher runs in a worktree (separate git branch). Session runs on main tree.
    Results cannot be merged back into the session context safely.
  - Dispatcher uses claude -p (stateless). Session is stateful interactive.
    Coordinating them requires a polling loop, which violates the no-polling principle.
  - If the session invokes claude -p directly (as a sub-agent), that is already supported
    via the /spawn-agent skill -- no new plumbing needed.

### Recommended session integration pattern

  1. Session identifies work that is autonomous-safe and out-of-band.
  2. Session calls a backlog_append() helper (one function, ~20 lines):
     - Validates schema (Stage 1 gate).
     - Assigns an ID (session-YYYYMMDD-HHMMSS-NNN).
     - Sets source="session".
     - Writes atomically to task_backlog.jsonl.
     - Returns the new task ID for human confirmation.
  3. Session continues without waiting.
  4. Dispatcher picks up the task on its next scheduled run.
  5. Human checks backlog or heartbeat to see result.

  The backlog_append() function should exist as a shared library function in
  tools/scripts/lib/backlog.py, callable from both skills (SKILL.md) and scripts.

### What must NOT happen

  - Sessions must not poll for task completion.
  - Sessions must not hold the dispatcher lock.
  - Sessions must not create worktrees for tasks they intend to delegate.
  - The backlog write must not be gated on the dispatcher being idle.

---

## 6. SIMPLEST SUFFICIENT ARCHITECTURE -- The Minimum Viable Design

### Principle: converge state, not structure

The overnight runner and dispatcher do not need to share execution logic.
They need to share STATE visibility and schema.

The simplest sufficient architecture requires three changes to the current system,
not a rewrite:

  CHANGE 1: Overnight dimensions become tasks in the backlog (schema bridge)

  Currently: overnight_runner reads program.md (markdown, parsed at runtime).
  Proposed: each dimension is also representable as a task in task_backlog.jsonl
  with a special execution_type="iterative_improvement" field.
  The dispatcher routes iterative_improvement tasks to overnight_runner logic
  (or a thin wrapper around it), not to the standard worker prompt.

  This does NOT mean deleting overnight_runner.py. It means:
  a. overnight_runner.py becomes a callable function (run_dimension_task(task))
     rather than a standalone script.
  b. The dispatcher calls it for tasks with execution_type="iterative_improvement".
  c. overnight_state.json is replaced by task_backlog entries with source="overnight".
  d. A nightly schedule writes 1-N dimension tasks to backlog with overnight-specific
     ISC (metric-based).
  e. All existing overnight runner safety (command allowlist, program_unmodified check,
     time budget) is preserved -- it moves into the task execution path.

  Impact: one scheduler (dispatcher), one lock, one backlog, one Slack summary.
  Risk: overnight time budget (100 min) and serial dimension loop are harder to express
  as discrete tasks. Mitigation: a "batch task" schema that groups dimensions under
  a parent task ID, similar to existing parent_id field.

  CHANGE 2: Stage 1 write gate (backlog_append library function)

  Add tools/scripts/lib/backlog.py with:
  - backlog_append(task_dict) -> task_id
  - backlog_validate(task_dict) -> (valid: bool, errors: list[str])

  All write paths (heartbeat, session, overnight schedule) use this function.
  Invalid tasks get status=invalid immediately instead of zombie pending.

  CHANGE 3: Running state in backlog

  When dispatcher claims a task (acquires lock, creates worktree), immediately
  write status=running to the backlog entry. When done, write done/failed.
  This is a 3-line change to the dispatcher.

  Backlog then has complete state: pending, running, done, failed, invalid, deferred.
  Heartbeat can now report running tasks as part of backlog_health metrics.

### What NOT to build

  - Do NOT build a separate quality-gate service or daemon.
  - Do NOT build a task priority queue (priority sort in select_next_task is sufficient).
  - Do NOT build task result streaming back to sessions.
  - Do NOT build a multi-worker parallel dispatcher until Claude Max supports it.
  - Do NOT migrate overnight runner until the schema bridge (Change 1) is validated
    with at least one dimension running successfully through the dispatcher path.

### Migration order (lowest-risk path)

  PHASE A: Add backlog_append + Stage 1 write gate. (1 day, no behavior change)
  PHASE B: Add status=running to dispatcher claim step. (2-line change)
  PHASE C: Write overnight dimensions as backlog tasks nightly. Overnight runner runs
           as before but also writes its status to backlog. (observability bridge)
  PHASE D: Route one overnight dimension through dispatcher using iterative wrapper.
           Validate against existing overnight output. (proof of concept)
  PHASE E: Full overnight convergence once proof of concept passes ISC.

---

## 7. ASSUMPTIONS THAT MIGHT BE WRONG

### A7-1: "One task at a time is the binding constraint"

ASSUMPTION: Claude Max is single-session, so parallelism is wasteful.
MIGHT BE WRONG IF: Anthropic changes Claude Max to allow concurrent sessions
(already a roadmap item for Teams). If that happens, the single-lock model becomes
the bottleneck. Mitigation: design the lock layer to be replaceable (it already is --
acquire_claude_lock is in lib/worktree.py).

### A7-2: "Overnight dimensions and dispatcher tasks are structurally compatible"

ASSUMPTION: An overnight dimension (N-iteration improvement loop) can be expressed
as a task_backlog entry and routed through the dispatcher.
MIGHT BE WRONG IF: The iterative loop's state (baseline, iteration count, current
metric) does not map cleanly to the task ISC model (binary pass/fail per criterion).
The overnight model is continuous improvement; the dispatcher model is discrete
completion. These may require different abstractions.
Mitigation: treat overnight as a "batch task" with a separate execution handler,
not as a standard task. Do not force convergence of execution model, only of state.

### A7-3: "The backlog file can handle concurrent writers safely"

ASSUMPTION: write_backlog() uses atomic temp+rename, so concurrent writes are safe.
MIGHT BE WRONG IF: Two processes write simultaneously on Windows. os.replace() is
atomic on the same volume, but if two processes both create temp files and then race
on os.replace(), one write wins and one is silently lost.
Mitigation: Add a file-level write lock (separate .lock file for backlog writes, not
just dispatcher execution). The dispatcher already has dispatcher.lock; extend it or
add backlog.lock for writes from other sources (heartbeat, session).

### A7-4: "Heartbeat's remediation_map is the right abstraction for task generation"

ASSUMPTION: Mapping collector names to task templates in heartbeat_config.json is
sufficient for all auto-proposed task sources.
MIGHT BE WRONG IF: The number of remediation conditions grows (new collectors, new
thresholds, conditional logic). A static JSON map does not support:
  - "only propose synthesis if signals > 10 AND last synthesis > 7 days ago" (compound)
  - "do not propose if a synthesis task is already pending" (dedup -- currently missing)
  Currently, auto-40018 was written even though 5b-002 (same goal) was already in backlog
  with status=done. Backlog shows one in pending state. The dedup check is absent.
  Mitigation: backlog_append() should check for existing pending/running tasks with
  the same description prefix or same source + skill combo before appending.

### A7-5: "Quality gate rejection is a permanent signal"

ASSUMPTION: A task that fails the dispatch gate (e.g., no verifiable ISC) is
simply skipped and stays pending.
MIGHT BE WRONG IF: The reason for failure is transient (deps not yet met) vs
permanent (no ISC at all). A task with no verifiable ISC will never be selected,
ever. It should be marked invalid at write time (Stage 1 gate), not silently skipped
at dispatch time forever. Currently this creates invisible zombie tasks.

### A7-6: "Program.md is the right config format for overnight dimensions"

ASSUMPTION: Markdown-parsed config (program.md) is maintainable for dimension
config.
MIGHT BE WRONG IF: The parse_program() regex is brittle (it is -- it relies on
"### N. name" header format and "- **key:** value" pairs). Adding new fields requires
updating the regex. A structured format (YAML or JSON) would be safer.
If overnight dimensions converge into backlog tasks (Change 1, Section 6), program.md
becomes obsolete and this assumption becomes moot.

### A7-7: "The dispatcher selects one task per invocation"

ASSUMPTION: Running one task per Task Scheduler invocation is sufficient throughput.
MIGHT BE WRONG IF: A burst of 10+ tasks arrives (e.g., after a multi-day session hiatus,
heartbeat fires multiple remediations, overnight adds dimension tasks). The dispatcher
runs once per scheduled interval; if that interval is 4h, a 10-task backlog takes 40h
to clear -- longer than most tasks are valid.
Mitigation: Add a --run-all flag to dispatcher that loops until backlog is empty or
time budget is exhausted. This is additive and doesn't change the current one-task model.

---

## SUMMARY TABLE

| Question                        | Answer                                                    |
|---------------------------------|-----------------------------------------------------------|
| Fundamental problem             | Duplicated machinery + no unified state visibility        |
| Key irreducible requirements    | R1 (single truth), R2 (lock), R4 (gate), R5 (no blocking)|
| Bottleneck risk                 | Real but manageable with priority sort + status=running   |
| Quality gate placement          | Stage 1 at write time + Stage 2 at dispatch time (both)  |
| Session integration pattern     | backlog_append() async; no polling; Case C is anti-pattern|
| Simplest sufficient design      | 3 changes: write gate, running state, schema bridge       |
| Highest-risk assumption         | A7-4 dedup missing (duplicate tasks already observed)     |

---

## RECOMMENDED FIRST ACTION

Fix A7-4 (dedup) before building any new unified pipeline machinery.
Reason: auto-40018 demonstrates it is already causing noise in the current system.
A dedup check in backlog_append() is a 10-line function that prevents the most
visible correctness failure. It costs nothing to add and cannot regress.

After dedup: implement Stage 1 write gate (Change 2, Section 6). This is the
load-bearing foundation for all other convergence work.

---
