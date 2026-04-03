# Fallacy Detection: Unified Pipeline Architecture Proposal
# Generated: 2026-04-02
# Analyst: Adversarial Logical Analyst (Jarvis Arch Review)

---

## 1. SOUND REASONING

**The shared worktree library is a real structural win.**
Both dispatcher and overnight_runner already share tools/scripts/lib/worktree.py. This is
not speculative unification -- it already happened and works. The claim that convergence
reduces duplicated infrastructure is supported by observable code.

**The heartbeat-to-backlog pipeline is already validated.**
task auto-40018 shows the full loop working: heartbeat fires WARN, auto-proposes a task,
the task lands in task_backlog.jsonl with source="heartbeat", and the dispatcher picks it
up. This is not a vision claim -- it is a running system. The argument for keeping
heartbeat proposals as a first-class backlog source is sound.

**The shared claude lock prevents concurrent spawns.**
Both systems call acquire_claude_lock(). This is an actual architectural constraint, not
a preference. Any unification must respect this mutual exclusion. The proposal implicitly
assumes this -- and the assumption is correct.

**Priority + dependency resolution belongs in one place.**
The dispatcher has a mature candidate selection algorithm (priority, tier, deps, ISC
validation, deliverable pre-exists check). Duplicating this logic in the overnight
runner would be a maintenance hazard. The argument to centralize selection is valid.

**The JSONL format is already the right schema for this data.**
JSONL is append-friendly, easy to diff, tool-readable without a database. The existing
backlog shows it handles heterogeneous task types (seed tasks, auto-heals, heartbeat
proposals) cleanly. No format change is needed to support convergence.

**The quality gate idea has empirical backing.**
The current dispatcher already does ISC validation before execution and deliverable
pre-exists checks. Formalizing a pre-admission quality gate extends a working pattern,
not introduces a new one.

---

## 2. CATEGORY ERRORS

**Category Error A: Treating overnight dimensions as tasks.**
Overnight runner dimensions are NOT tasks in the dispatcher sense. A dispatcher task is:
  - Discrete, bounded, has a clear ISC, terminates in one run
  - Stateless: each run is independent, no memory of prior iterations
  - Priority-ordered: one task runs, then the next

An overnight dimension is:
  - Iterative: 20 iterations per run with revert-on-failure loops
  - Self-correcting: the agent measures, adjusts, and repeats within a single execution
  - Rotation-state-dependent: "what ran last night" determines "what runs tonight"

Converting dimensions to tasks requires either (a) a special task type with iteration
semantics built into the dispatcher, or (b) wrapping the entire overnight runner as a
single opaque task. Option (a) is a full redesign. Option (b) is just indirection with
extra steps. Neither is the "convergence" the proposal implies.

**Category Error B: Treating latency classes as equivalent.**
The proposal groups interactive session work with autonomous backlog work. These differ
on a fundamental axis: feedback latency tolerance.
  - Interactive: user is present, expects sub-second response, context is live
  - Async backlog: user is absent, hours of latency acceptable, context must be embedded

No queue design can serve both without partitioning them. Adding session work to the
backlog does not unify them -- it creates two consumer types with incompatible SLAs
sharing one queue.

**Category Error C: Conflating signal generation with task execution.**
Heartbeat collectors (signal_count, signal_velocity, etc.) generate OBSERVATIONS about
system state. The remediation_map then proposes tasks based on those observations. These
are two different operations. The proposal treats "heartbeat auto-proposes tasks" as one
step, but the step boundary matters: the sensing must remain stateless and non-mutating.
If heartbeat proposing and task execution share a pipeline, the sense/act boundary blurs.
This violates the three-layer pattern (SENSE -> DECIDE -> ACT) in the steering rules.

**Category Error D: Treating "learning" as pipeline-visible only.**
The proposal claims "learning only happens on work the pipeline can see" -- but the hooks
system (session_start, post-tool-use, pre-tool-use) generates signals on every
interactive session. The /learning-capture skill runs in human sessions. The synthesis
collector tracks memory/learning/synthesis recency. Session learning already exists
outside the pipeline. Claiming the pipeline must see all work to capture learning is
false on its face.

---

## 3. HIDDEN ASSUMPTIONS

**Hidden Assumption 1: The backlog is the bottleneck.**
The proposal assumes the silo problem is a routing problem -- if everything flows through
one queue, nothing gets lost. But the actual gaps in the system are not missing queue
entries. The real gaps are: (a) human sessions that produce insights but no learning
capture, (b) overnight dimensions that produce commits but no tasklist updates, (c)
heartbeat proposals that expire or stale out. These are capture and closure problems,
not routing problems. A unified backlog does not fix any of them.

**Hidden Assumption 2: The dispatcher can absorb overnight's temporal contract.**
The overnight runner has a hard temporal requirement: it must run within a nightly
window, consume a fixed time budget (100 min), and not collide with daytime dispatcher
runs. If dimensions become backlog tasks, the scheduling of those tasks must preserve
this contract. The proposal does not address how priority + scheduling interact. A
medium-priority "codebase_health" dimension task could silently get dequeued during a
morning dispatch run, burning the daily claude budget before the nightly window.

**Hidden Assumption 3: A quality gate can be defined statically.**
"Inadequate tasks" implies a known standard. But what is adequate? The dispatcher
already validates ISC structure (requires >= 1 executable Verify command, blocks
dangerous commands, checks autonomous_safe flag). That IS a quality gate, and it works
because the criteria are precise and binary. Generalizing to a "quality gate" that
filters "inadequate" tasks in the abstract requires defining adequacy for every task
type -- heartbeat proposals, session ideas, overnight dimensions, self-heal tasks. These
have different schemas and different quality signals. One gate cannot validate all of
them correctly without becoming a per-type switch, which is not a gate -- it is a router.

**Hidden Assumption 4: Unification reduces operational complexity.**
The proposal assumes one system is simpler than two. But operational complexity is not
linearly related to component count. Two focused systems with clean interfaces can be
simpler to debug than one general system with internal branching. The dispatcher is
currently ~500 lines with a clear single purpose. Adding overnight semantics would add
state management (rotation), time budget tracking, and multi-iteration execution. The
added complexity may exceed the value of having one codebase.

**Hidden Assumption 5: Session work benefits from being backlogged.**
The proposal suggests session work should enter the backlog. But the majority of session
work is: (a) decided interactively by Eric based on current state, (b) executed
immediately in the same session, (c) validated with Eric present. Backlogging this work
adds write latency, requires schema authoring during a live session, and produces queue
entries that will often be stale before any dispatcher run occurs. The value is only
realized if session ideas are explicitly deferred -- which is a small subset of session
work, not "all session work."

**Hidden Assumption 6: The learning loop is closed by pipeline visibility.**
The actual learning loop is: signal -> synthesis -> steering rule update. This loop
operates on signals, not on task completions. The heartbeat collector already tracks
synthesis recency (learning_loop_health). Making task completions visible to the
pipeline does not close the learning loop -- it adds a new input type that may or may
not ever become a signal. The proposal conflates task tracking with learning.

---

## 4. SCOPE CREEP RISKS

**Risk A: The backlog becomes a second tasklist.**
orchestration/tasklist.md already exists as Eric's primary trust tool. If task_backlog.jsonl
absorbs session work, ad-hoc ideas, and routine maintenance, it duplicates the
tasklist's role. Now there are two sources of truth for what needs to be done, with
different schemas, different consumers, and no defined ownership boundary. The steering
rules explicitly say "the tasklist is Eric's primary trust tool" -- the backlog is the
autonomous system's queue. Merging them erases a useful separation.

**Risk B: The quality gate becomes a bottleneck for autonomous healing.**
Self-heal tasks (like auto-heal-overnight-runner-20260401-040017) are auto-generated by
self_diagnose_wrapper with a known-valid schema. If those tasks must pass a general
quality gate, the gate adds latency to a healing path that is already time-sensitive.
A self-heal task for an import error should not wait for a gate that evaluates whether
its description is adequately detailed.

**Risk C: Overnight dimensions acquire backlog debt.**
If each dimension run adds a task entry, the backlog accumulates dimension-run history.
Over 6 dimensions * nightly runs = ~2000 entries/year. The backlog_pending_count
heartbeat metric would fire WARNs constantly unless dimension tasks are auto-closed
immediately. Managing this requires either (a) a separate task type with different
retention rules, or (b) post-run auto-closure logic -- both of which add system
complexity without adding value over the current overnight_state.json pattern.

**Risk D: One pipeline breaks the "Idle Is Success" doctrine.**
The overnight runner and dispatcher both implement "Idle Is Success": no work to do is
a valid outcome. A unified pipeline with a single success metric (tasks completed) makes
silence look like failure. The current design lets overnight silence mean "no
improvement found this dimension," and dispatcher silence mean "no eligible tasks." A
unified pipeline will pressure toward always having tasks in queue, which contradicts
the idle-is-success principle.

**Risk E: Cross-source task deduplication becomes a hard problem.**
Currently: heartbeat auto-proposes "synthesize-signals" tasks, human sessions add
similar tasks manually, and overnight knowledge_synthesis dimension also synthesizes.
In a unified pipeline, all three sources could queue the same logical work. Deduplication
requires either a semantic matching layer (expensive) or strict ID namespacing (brittle).
The deliverable_exists() check in the dispatcher handles some of this, but it only
catches cases where a specific file already exists -- not cases where a semantically
equivalent task is already pending.

---

## 5. FALSE ANALOGIES

**False Analogy A: "One backlog prevents silos" (from CI/CD pipelines)**
This borrows from software delivery pipelines where a single build queue prevents teams
from running parallel conflicting deploys. That analogy holds for teams where the silo
problem is coordination between people. Jarvis has no team coordination problem -- it
is a single-operator system. The silo problem here is signal loss and incomplete
learning capture, which is not solved by queue consolidation.

**False Analogy B: Overnight dimensions are like tasks with a higher iteration count**
This is superficially appealing but structurally false. A task completes when its ISC is
met. An overnight dimension completes when iterations are exhausted -- regardless of
whether metric improvement occurred. The overnight runner has a fundamentally different
termination condition: time-boxed exploration, not goal achievement. Tasks are
goal-seeking. Dimensions are exploratory. Treating them as the same type requires either
weakening ISC semantics for dimensions or adding a special "exploratory" task type that
does not map to any existing backlog schema field.

**False Analogy C: "Pipeline visibility = learning" (from ML training pipelines)**
ML training pipelines capture all training runs to improve the model. The analogy implies
that capturing all Jarvis work runs improves Jarvis. But Jarvis learning works through
signal -> synthesis -> CLAUDE.md. Task completions are not the primary learning signal
-- session insights, failures, and behavioral deviations are. Logging task completions
to the backlog does not feed the learning loop; it feeds a completion log, which is
already served by task `notes` fields and dispatcher_runs/.

**False Analogy D: Convergence implies simplification**
The proposal implicitly compares to software refactoring, where consolidating duplicated
code reduces maintenance burden. But the overnight runner and dispatcher share a worktree
library precisely because they have the same technical substrate (git worktrees, claude
-p invocations). They differ in execution semantics, temporal contracts, and output
schemas. The shared library is the right consolidation point. Merging the systems
themselves conflates code reuse with semantic unification.

---

## 6. VERDICT

**Overall Logical Soundness: Partially Sound -- 3 out of 6 key claims hold under scrutiny.**

What holds:
- The shared infrastructure (worktree library, claude lock, JSONL schema) is correctly
  identified as a convergence win. It already happened.
- Heartbeat -> backlog -> dispatcher is a validated, sound pipeline. Keep it.
- Centralizing priority resolution and ISC validation in the dispatcher is the right call.

What does not hold:
- "Everything through one pipeline" is a false generalization. Interactive session work,
  overnight exploration, and autonomous task execution have incompatible SLAs, termination
  semantics, and latency requirements. Forcing them into one queue requires partitioning
  that recreates the category boundaries the proposal tries to eliminate.
- "Overnight dims converge with dispatcher" requires either redesigning the dispatcher or
  wrapping the overnight runner as an opaque task. Neither is convergence -- one is
  overengineering, the other is naming.
- "Session work should enter the backlog" adds bureaucracy to interactive work that is
  already captured through hooks and /learning-capture. Value is limited to explicitly
  deferred ideas, which is a narrow use case.
- "Quality gate filters inadequate tasks" is under-specified. The dispatcher already IS
  the quality gate for backlog tasks. A second gate is redundant unless it handles
  non-backlog entry points -- which reverts to the real problem: session capture.

**Recommended action: Narrow the proposal.**
Instead of "unified pipeline," target three specific wins:
1. Formalize heartbeat -> backlog -> dispatcher as the canonical async work loop
   (already done; document it as the pattern)
2. Add one deferred-idea capture mechanism in sessions (a lightweight "queue this idea"
   command that writes a valid backlog entry) -- this is the only session-to-backlog
   path worth building
3. Keep overnight_runner as a separate system with its own scheduler slot; expose its
   outcomes as heartbeat signals (already happening via overnight_state.json) rather
   than converting it to tasks

The current architecture is sound at the boundaries. The risk is gold-plating the center.
