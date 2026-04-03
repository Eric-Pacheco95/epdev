# First-Principles Analysis: 5C-4 Session Task Capture (/backlog skill)

**Date**: 2026-04-02
**Reviewer**: Jarvis (claude-sonnet-4-6, architecture-review mode)
**Proposal**: `/backlog` skill for capturing tasks from interactive sessions into the unified pipeline
**Codebase references**: `tools/scripts/lib/backlog.py`, `tools/scripts/task_gate.py`, `tools/scripts/jarvis_dispatcher.py`

---

## 1. What Is the Fundamental Problem Being Solved?

During interactive chat sessions, Eric generates task ideas faster than they can be formally specified. Without a capture mechanism, these ideas dissipate -- they are never acted on, never refined, and never enter the pipeline. The problem is:

**Cognitive offload at the moment of insight without breaking session flow.**

This is not a routing problem, a validation problem, or an ISC problem. Those are secondary concerns. The primary problem is: how does a human-in-session idea become a durable artifact that survives context loss?

Two properties define a successful solution:

1. **Minimum friction at capture time** -- the time between "Eric has an idea" and "the idea is persisted" must be near-zero. Friction at capture kills the behavior.
2. **Maximum fidelity at execution time** -- when the idea is eventually executed (autonomously or manually), it must be unambiguous, verifiable, and safe.

These two properties are in tension. The three alternatives represent different points on that tradeoff curve.

---

## 2. Irreducible Requirements for Session Task Capture

These are requirements that cannot be traded away without breaking the core purpose:

**R1 -- Ideas must survive the session.** Captured tasks must be written atomically and durably to a file that persists after the session ends. In-memory state is not sufficient.

**R2 -- Backlog must never be silently corrupted.** Any write that fails must either succeed completely or leave the backlog unchanged. This is already guaranteed by `backlog_append()`'s atomic write (tempfile + `os.replace`).

**R3 -- The dispatcher must never auto-execute a human capture task without Eric's review.** Session ideas are exploratory. The quality of ISC is not known at capture time. Autonomous execution against placeholder ISC is a correctness and safety violation.

**R4 -- Capture must not require pre-existing ISC.** Requiring verifiable ISC at capture time is the same as requiring the idea to be fully specified before it can be saved. This defeats the point of the skill.

**R5 -- Capture must not add Slack noise.** A Slack message for every quick capture creates a notification channel that Eric will train himself to ignore. Slack is reserved for decisions that require a human response.

**R6 -- Backlog integrity must be observable.** Tasks captured from sessions must be distinguishable from autonomously-proposed tasks. This enables auditing, filtering, and prioritization.

---

## 3. Assumptions in Each Alternative That May Be Wrong

### Alternative 1: Fast Capture (direct backlog_append, bypass task_gate)

**What it gets right:**
- Satisfies R1, R2, R4, R5.
- Low friction at capture time.
- The dispatcher honors `autonomous_safe: false` -- a human-capture task with this flag will never be auto-executed, satisfying R3.

**Assumptions that may be wrong:**

**A1.1 -- "Placeholder ISC is harmless because autonomous_safe=false blocks execution."**
Partially correct but incomplete. `autonomous_safe: false` prevents the dispatcher from *running* the task, but the task still appears in the backlog with `status: pending`. If Eric later flips `autonomous_safe: true` without updating the ISC (which is likely under ADHD session patterns), the dispatcher will execute against the placeholder ISC, which will trivially pass (e.g., `grep -c 'done' ...` returns 0 but exits 0). This is a latent correctness trap.

The actual risk is not at capture time -- it is at the promote-to-autonomous moment, which has no defined workflow. The proposal mentions "Eric can later refine ISC and flip autonomous_safe" but provides no mechanism to enforce that this happens correctly.

**A1.2 -- "Bypassing task_gate does not create inconsistency."**
Incorrect. The entire Phase 5C architecture rests on the invariant that *all tasks in the backlog arrived through a defined path with a known trust level*. Bypassing task_gate breaks this invariant. The dispatcher currently uses `source` as a metadata field, not a gate, so no existing code enforces the invariant -- but the architecture depends on it. Direct bypass establishes a precedent that other producers (heartbeat, overnight runner) could follow to avoid gate checks.

**A1.3 -- "The skill can construct a valid task dict without Eric's input."**
Partially correct. The skill can populate required fields mechanically (`autonomous_safe: false`, tier 2, source "session"). But `priority` is a required field with no sensible default for arbitrary session ideas. Priority 5 (medium) is a guess, not a signal.

### Alternative 2: Full Routing (through task_gate)

**What it gets right:**
- Preserves the gate-as-single-entry-point invariant.
- Forces ISC quality before backlog entry.

**Assumptions that may be wrong:**

**A2.1 -- "Routing to Slack when ISC is absent is the correct fallback."**
Wrong. The Slack escalation path was designed for autonomous producers (heartbeat, overnight runner) that need human triage. A session task capture is already happening *with* a human. Routing a session-originated idea to Slack and asking the human who just created the idea to respond to Slack is circular and adds latency with no value.

**A2.2 -- "Requiring verifiable ISC at capture time is a quality improvement."**
Incorrect for this use case. The task_gate ISC check exists because autonomous producers must prove a task is verifiable before the dispatcher commits to running it. Session captures are human-originated and not yet autonomous. Applying the same gate means the skill becomes unusable for the exact scenario it is designed for (quick idea capture).

**A2.3 -- "Full task_gate routing for session captures and autonomous proposals are the same problem."**
Wrong. The trust source is different. Autonomous producers are background jobs with no human in the loop; they *need* the gate to prevent garbage from accumulating. A session capture has Eric as the trust source; the gate adds friction without adding safety.

### Alternative 3: Hybrid (bare description = fast capture; flags = task_gate)

**What it gets right:**
- Matches UX to intent: quick idea vs. deliberate autonomous-ready task.
- Allows the skill to serve both capture and promotion in one interface.
- Does not create Slack noise for quick captures.

**Assumptions that may be wrong:**

**A3.1 -- "Eric will know when to use --tier and --isc flags."**
This is a discoverability problem. Under ADHD session patterns (see `memory/MEMORY.md`: "sporadic branching, mood-driven"), the flag-based path will rarely be used. The fast-capture path will be used almost exclusively. The hybrid design collapses to Alternative 1 in practice.

**A3.2 -- "Having two paths in the same skill does not create ambiguity in the backlog."**
Partially correct -- the `source` field distinguishes them. But the promotion workflow (turning a fast-capture into an autonomous-ready task) remains undefined in both paths. The hybrid does not solve the latent-ISC-quality risk from A1.1.

**A3.3 -- "The flag-based path adds no friction over direct task_gate use."**
Incorrect. Using `/backlog --tier 0 --isc "..." description` is not simpler than calling `task_gate.propose_task()` directly. If Eric is operating at that level of intent, he is already in a context where using the gate directly makes more sense.

---

## 4. Simplest Architecture That Satisfies the Requirements

The requirements separate cleanly into two distinct operations that should not be conflated:

**Operation A -- Capture**: persist an idea durably with minimum friction (R1, R2, R4, R5, R6).
**Operation B -- Promote**: turn a captured idea into a dispatcher-ready task with verifiable ISC and an explicit human-approval signal (R3).

The simplest architecture implements these as two separate, explicit steps:

### Step 1: `/backlog [description]` -- Pure Capture

The skill does exactly one thing: call `backlog_append()` directly with:
- `autonomous_safe: false` (hard-coded -- not a parameter)
- `status: pending_review` (a new status distinguishing human captures from dispatcher-ready tasks)
- `tier: 2` (most conservative default)
- `source: "session"`
- `priority: 5` (medium -- overridable at promotion time)
- ISC: a single placeholder: `"Task captured from session -- needs ISC refinement | Verify: Review"`

This satisfies R1-R6. The `pending_review` status is critical: it is **not in the dispatcher's eligible set** (`pending`, `claimed`, `executing`). The dispatcher ignores these tasks entirely. There is no need to check `autonomous_safe` because the status gate prevents execution before it can reach the autonomous_safe check.

This approach does not bypass task_gate in a philosophically inconsistent way -- it bypasses it intentionally because session captures are *definitionally* not autonomous. Task_gate is for autonomous-path routing decisions. It has no role in human-originated captures.

### Step 2: Explicit Promotion (separate workflow, not part of /backlog)

When Eric is ready to make a captured task autonomous, he uses a separate mechanism (CLI subcommand, `/implement-prd`, or manual JSONL edit) to:
1. Provide real ISC with executable verify methods.
2. Set `autonomous_safe: true`.
3. Change `status` from `pending_review` to `pending`.

This is the gate that matters: the transition from human-captured to dispatcher-eligible. It should require evidence, not just a flag flip.

### Why Not a Single-Step Solution?

Because there is no zero-friction path that also guarantees ISC quality. Any design that tries to do both in one step either (a) accepts placeholder ISC and creates a latent correctness risk, or (b) requires ISC at capture time and kills the capture UX. The two-step design accepts this tradeoff explicitly: capture is frictionless, promotion is deliberate.

### Status Extension Needed

Add `pending_review` to `VALID_STATUSES` in `backlog.py`. Do not add it to `ACTIVE_STATUSES` (dedup set) or to the dispatcher's eligible set. This is a one-line change with no risk to existing behavior.

---

## 5. Does Bypassing task_gate for Human-Originated Tasks Create Architectural Debt?

**The short answer is: no, if the bypass is explicit about why it is correct.**

Task_gate's three checks are:

1. **Has verifiable ISC?** -- Exists to prevent the dispatcher from running tasks it cannot verify. A `pending_review` task cannot reach the dispatcher. This check is irrelevant.

2. **Skill tier is autonomous_safe?** -- Exists to prevent dangerous autonomous execution. A `pending_review` task cannot be autonomously executed. This check is irrelevant.

3. **No architectural keywords?** -- Exists to route architectural proposals to human review. Session captures *are* human-in-the-loop by definition. This check is irrelevant.

All three task_gate checks are routing decisions for the autonomous path. They were not designed to validate human-originated input. Routing session captures through task_gate would force every quick idea through checks designed for a different trust model. This is not a quality improvement; it is applying the wrong filter to the wrong input.

The architectural debt risk is not in bypassing the gate -- it is in:

1. **Not documenting the bypass contract.** If the rationale is not written into the code and into the CLAUDE.md steering rules, future producers may bypass task_gate without understanding why the bypass is valid (i.e., they may bypass it for reasons that are *not* valid). Add a comment in `backlog_append()` noting that direct callers accepting `pending_review` status are explicitly opting out of autonomous routing.

2. **Not enforcing the `pending_review` -> `pending` transition.** The current backlog schema allows any status. Without a validation rule that prevents `pending_review` tasks from being set to `pending` without verifiable ISC, Eric or a future automation could promote a task without meeting the quality bar. Consider adding a check in `backlog_append()` or a separate `backlog_promote()` function that enforces ISC quality before status promotion.

3. **Letting `autonomous_safe: false` carry the entire safety burden.** Alternative 1 relies on `autonomous_safe: false` as the execution guard. This is fragile because it is a data field that can be changed. `pending_review` status as an execution guard is better because it requires an explicit promotion step with observable state change.

---

## Summary Findings

| Criterion | Alt 1 (Direct) | Alt 2 (Full Gate) | Alt 3 (Hybrid) | Recommended |
|---|---|---|---|---|
| Satisfies R1 (durable write) | Yes | Yes | Yes | Yes |
| Satisfies R3 (no auto-exec) | Fragile (relies on autonomous_safe field) | Yes | Fragile | Yes (via pending_review status) |
| Satisfies R4 (no ISC required) | Yes | No | Partial | Yes |
| Satisfies R5 (no Slack noise) | Yes | No | Yes | Yes |
| Preserves architectural invariant | No | Yes | Partial | Yes (explicit bypass contract) |
| Promotion workflow defined | No | No | No | Required as separate step |

**Recommendation**: Implement a constrained version of Alternative 1 with two modifications:

1. Use `status: pending_review` (not `status: pending`) to prevent dispatcher eligibility -- this is stronger than `autonomous_safe: false`.
2. Define and document the promotion workflow as a separate explicit step, not an implicit flag flip.

Alternative 3 (hybrid) is acceptable as a UX layer on top of this recommendation -- the `--tier/--isc` flags can be a shortcut to the promotion step for when Eric has ISC ready at capture time. But the flag-based path should validate ISC quality before setting `status: pending`, not just pass through task_gate.

Do not implement Alternative 2. It applies the wrong trust model to human-originated input and creates friction that will cause the capture habit to fail.
