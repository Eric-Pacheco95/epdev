# Fallacy Detection: 5C-4 /backlog Skill Proposal

**Analyst role**: adversarial logic reviewer  
**Date**: 2026-04-02  
**Proposal summary**: A `/backlog` skill with two paths -- a fast path (bypasses task_gate) and a rich path (goes through task_gate). Fast path builds tasks with `autonomous_safe: false` and placeholder ISC, calling `backlog_append()` directly.

---

## 1. Category Errors

### "Human capture" vs. "machine capture" is a false categorization

The proposal treats the *origin* of a task (human vs. autonomous system) as sufficient to exempt it from gate validation. This is a category error. The gate checks are not about *who proposed the task* -- they are about *whether the task is well-formed enough to be reliable in the backlog*. The distinction the gate enforces is:

- Does the task have verifiable ISC? (quality, not origin)
- Are referenced skills safe for autonomous execution? (risk classification, not origin)
- Does the description imply an architectural decision? (scope, not origin)

None of those checks care about the proposer's identity. A human-originated task with bad ISC is just as unreliable in the backlog as a machine-originated one. Worse: because the backlog feeds the dispatcher (which trusts `autonomous_safe: false` as its primary execution gate), letting humans inject structurally weak tasks creates a low-quality accumulation problem that silently degrades backlog health over time.

**The valid distinction the proposal is reaching for** is: human-originated tasks don't need autonomous routing checks because they won't be auto-executed. That is a reasonable observation -- but it doesn't follow that the task therefore needs *no* structural validation. Those are different concerns and collapsing them is the error.

**Verdict**: False categorization. Gate bypass is unjustified by the origin argument; at most, it could justify skipping check 2 (skill-tier safety) while still enforcing checks 1 (ISC structure) and 3 (arch keyword heuristic).

---

## 2. Hidden Assumptions

### Assumption A: Placeholder ISC satisfies backlog_append() validation

The proposed fast-path ISC is: `"Task completed and validated by operator | Verify: grep -c 'done' ..."`.

This assumption is factually wrong. `backlog_append()` calls `validate_task()`, which calls `classify_verify_method()` from `isc_common.py`. That function returns `"executable"` for `grep` (it is on the `ISC_ALLOWED_COMMANDS` allowlist). So the placeholder *will pass* structural validation -- but only because it uses a grep command that searches for the literal string `'done'` in an unspecified file.

The real problem: `grep -c 'done'` verifies almost nothing. It matches any file containing the word "done" (a common word in markdown notes, commit messages, tasklists). The ISC gate was specifically designed to require *meaningful* verify methods; this placeholder exploits the grep allowlist to produce a technically-passing but semantically-empty criterion. The validator cannot distinguish `grep -c 'done' notes.md` from `grep -c 'AUDIT_COMPLETE' memory/learning/signals/audit-2026.md`. The proposal smuggles through the format while gutting the intent.

This is a **goodhart's law violation baked into the fast path**: the measure (a grep verify command) becomes the target, divorced from the goal (verifiable task completion).

### Assumption B: autonomous_safe: false is sufficient protection against dispatcher auto-execution

The assumption is correct as a point-in-time fact: the dispatcher filters on `autonomous_safe: true` before executing. But it treats a runtime access control as a design guarantee. The concern is:

- The flag is human-settable. A future enhancement (rich path, edit path, batch path) could toggle it without passing through the gate.
- The flag is the *only* thing protecting against dispatcher pickup. Once a task is in the backlog, the only check before auto-execution is that boolean. Weak ISC on an `autonomous_safe: false` task becomes dangerous if the flag is later flipped (manually or via a future `/backlog edit` command).

This assumption conflates "not immediately executable" with "safe to store in weak form." The proposal gives no mechanism for ISC refinement before a task is ever marked `autonomous_safe: true`, which means the refinement step is entirely informal.

### Assumption C: Eric will refine placeholder ISC later

This is the most operationally significant hidden assumption. The proposal implies a two-stage workflow: capture now, refine before execution. But there is no mechanism enforcing or triggering the refinement. The result is a backlog that accumulates tasks with placeholder ISC that are never refined, because:

- ADHD session patterns (per `user_adhd_session_patterns.md`) favor capturing and moving on
- There is no staleness signal for "captured but ISC not refined"
- The dispatcher will not pick these up (they are `autonomous_safe: false`), so there is no natural pressure to close them
- Human review queues with no enforcement tend to fill and rot

The proposal is implicitly assuming a discipline that the user's known working patterns contradict.

---

## 3. Scope Creep Risks

The fast path invites a specific and predictable feature expansion sequence:

**Stage 1 (as proposed)**: `/backlog description` -- quick capture  
**Stage 2**: `/backlog --edit ID` -- I captured something vague, now I want to fix it  
**Stage 3**: `/backlog --list` or `/backlog --status` -- I want to see what's in there  
**Stage 4**: `/backlog --search keyword` -- backlog has 50 items, I need to find mine  
**Stage 5**: `/backlog --prioritize` -- I have 20 unrefined tasks, help me triage  
**Stage 6**: `/backlog --batch file.txt` -- I have a lot to capture from a planning session  

Each of these is individually reasonable. But collectively they describe a backlog management UI, not a capture shortcut. The `task_gate.py` + `backlog_append()` architecture was deliberately designed to keep management concerns out of individual entry points. A `/backlog` skill that starts as a thin wrapper and accretes management commands will eventually duplicate or shadow the dispatcher's job view and create a second place where task state is mutated.

The inbox analogy (see section 4) accelerates this: people expect an inbox to have a triage view, not just an append endpoint.

**The specific risk to watch**: if `/backlog --list` is added, it will need to present task status. Once status is displayed, users will want to update it. Once update is in the skill, it becomes a second write path alongside the dispatcher -- two writers, no coordination protocol.

---

## 4. False Analogies

### The "inbox" analogy is misleading

The proposal frames the fast path as analogous to dropping a note in an inbox: low-friction, unstructured, processed later. Inbox items have these properties:

- No required structure
- No execution semantics
- No ISC or verify contracts
- Processed by a human who reads and decides

Backlog tasks have these properties:

- Required fields enforced by `validate_task()` (description, tier, autonomous_safe, isc with executable verify, priority)
- Direct execution path: the dispatcher reads this file and may auto-execute tasks
- ISC criteria are execution contracts, not notes
- Dedup logic runs on append

Even with `autonomous_safe: false`, a backlog task is not an inbox item. It is a structured record in a system that has a validator, an executor, a lock mechanism, dedup logic, and audit fields. Calling it an "inbox" frames it as something simpler than it is and creates the expectation that lightweight, informal capture is architecturally appropriate.

The correct analogy is closer to a *work order form with required fields and a sign-off checkbox*. Some fields can have reasonable defaults, but the form cannot be submitted blank with a note saying "fill in later."

The analogy also obscures a practical risk: inbox systems scale naturally (more items = more processing time, no correctness impact). Backlog systems have a different failure mode -- weak tasks that pass validation but fail at execution time, consuming a worker slot, producing a run report with an ISC miss, and requiring manual cleanup.

---

## 5. Reasoning Soundness

These parts of the proposal are logically solid:

**Fast path purpose is valid.** The friction of the rich path (`--tier 0 --skills X --isc "Y"`) is genuinely high for mobile or quick-capture scenarios. A lower-friction capture path serves a real need. This is not a contrived use case.

**`autonomous_safe: false` as default is correct.** For human-captured tasks without explicit skill/ISC review, defaulting to non-autonomous is the right conservative choice. The dispatcher will not touch them, which is the correct behavior for unreviewed tasks.

**Tier 2 default is reasonable.** Tier 2 is the most restrictive auto-execution tier; this is an appropriate conservative default for human captures.

**Rich path design is sound.** Sending tasks with explicit ISC, tier, and skills through task_gate is correct. The gate was built precisely for this: verifiable ISC + safe skills -> backlog; everything else -> Slack decision escalation. The rich path respects the gate's design intent.

**Calling backlog_append() directly is acceptable IF ISC is real.** The gate is a routing layer, not the only validation layer. `backlog_append()` calls `validate_task()` which enforces all structural requirements. So bypassing the gate on the fast path is not inherently wrong -- the question is whether placeholder ISC meets those requirements (it technically passes, but fails semantically; see assumption A above).

---

## Summary: Key Issues vs. Valid Design

| Issue | Severity | Verdict |
|---|---|---|
| "Human origin" justifies gate bypass | Medium | False categorization -- origin is irrelevant to task quality |
| Placeholder ISC passes validator but verifies nothing | High | Goodhart's law -- the form is met, the function is not |
| autonomous_safe: false is not a long-term safety guarantee | Medium | Valid concern if task editing is ever added |
| No refinement trigger for placeholder tasks | High | Contradicts known working patterns; creates backlog rot |
| Inbox analogy understates task structure requirements | Medium | Misleads about acceptable entry bar |
| Rich path design | Valid | Correctly routes through gate; no issues |
| autonomous_safe: false default | Valid | Correct conservative default |
| Fast path need | Valid | Real use case, not invented |

**Recommended fix**: Drop the placeholder ISC concept entirely. The fast path should either (a) generate a real, minimally-verifiable ISC from the description using a simple template (`"Description task complete | Verify: grep -c '{keyword}' orchestration/task_backlog.jsonl"` pointing at the task ID) or (b) store fast-path captures as a *staging file* (not the backlog JSONL) that requires explicit promotion. Option (b) is cleaner: it preserves the inbox metaphor where it is valid (unstructured staging area) while keeping the backlog a structured execution-ready record.
