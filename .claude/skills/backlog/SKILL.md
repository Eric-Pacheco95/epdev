# IDENTITY and PURPOSE

You are Jarvis’s session task capture tool. Persist ideas from chat into the unified backlog with zero friction. Use `backlog_append()` directly (not `task_gate`) — session captures are human-in-session, not autonomous producer input.

# DISCOVERY

## One-liner
Capture task ideas from chat into the unified backlog with zero friction

## Stage
ORCHESTRATE

## Syntax
/backlog <description>

## Parameters
- description: free-text description of the task idea (required)

## Examples
- /backlog add voice-controlled task creation to Phase 6
- /backlog investigate why overnight runner skipped synthesis dimension last night
- /backlog crypto-bot: add trailing stop-loss to the paper trading strategy

## Chains
- Before: any interactive session (capture ideas as they arise)
- After: (leaf -- captured tasks are refined and promoted later)
- Full: [session work] > /backlog > [later: manual ISC refinement + promotion]

## Output Contract
- Input: task description (free text)
- Output: confirmation with task ID
- Side effects: appends task to orchestration/task_backlog.jsonl via backlog_append()
- **Output ordering (multi-section outputs only)**: if the skill emits both a safety/review-gate section (items requiring arch-review, risks, blockers) and a task-ready section (roadmap copy, backlog entries), the gate section must appear FIRST. Gate-last output is bypassed by ADHD build velocity.

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- No description: "Usage: /backlog <description>. Example: /backlog add rate limiting to the Slack poller" STOP
- <5 chars: "Too short -- give enough context that future-you can act on it." STOP
- Once validated, proceed to Step 1

## Step 1: BUILD AND APPEND

1. Build the task dict:

```python
task = {
    "description": "<the description Eric provided>",
    "project": "epdev",
    "repo_path": "C:/Users/ericp/Github/epdev",
    "tier": 2,
    "priority": 5,
    "autonomous_safe": False,
    "status": "pending_review",
    "isc": ["Task completed and validated by operator | Verify: Review -- confirm work is done before promoting"],
    "source": "session",
    "notes": "Session capture -- needs ISC refinement before autonomous execution",
}
```

2. Call `backlog_append(task)` from `tools.scripts.lib.backlog`.

3. If `backlog_append()` raises `ValueError` (validation failure), print the error and STOP. Do not retry or work around it.

4. If successful, print confirmation:
   ```
   Backlogged: <task_id> -- "<description>"
   Status: pending_review (dispatcher will not auto-execute)
   To promote: refine ISC + flip autonomous_safe in a future session
   ```

5. Return to the conversation. Do not ask follow-up questions, do not suggest next steps, do not break flow.

# CRITICAL RULES

- ALWAYS set `status: "pending_review"` -- this is the primary execution guard. The dispatcher ignores this status entirely.
- ALWAYS set `autonomous_safe: false` -- belt-and-suspenders with pending_review.
- ALWAYS use `Verify: Review` (not an executable command) in the placeholder ISC -- this classifies as manual_required so the dispatcher skips it even if somehow promoted.
- NEVER set status to "pending" -- that makes the task dispatcher-eligible.
- NEVER ask Eric to provide ISC, tier, skills, or priority at capture time -- that defeats the purpose. Defaults are deliberate.
- NEVER go through task_gate for fast captures -- task_gate's routing checks are for autonomous producers. Session captures bypass it intentionally. This is validated by architecture review (2026-04-02).
- The `source` field is metadata only -- it must NEVER be used as an authorization input anywhere in the pipeline.

# OUTPUT INSTRUCTIONS

- One-line confirmation after successful capture. No decorations, no suggestions, no follow-up.
- If validation fails, show the error clearly and stop.
- Do not print the full task JSON -- Eric doesn't need to see it.
- Return to conversation flow immediately.

# INPUT

Await description from Eric. If not provided, print usage and stop.

INPUT:


# VERIFY

- Task appended to `orchestration/backlog.json` without overwriting existing entries | Verify: `python -m json.tool orchestration/backlog.json` then confirm last entry matches submitted task
- Last entry in backlog.json has all required fields: id, title, priority, project, created_at | Verify: Read last entry in `orchestration/backlog.json`
- backlog.json is valid JSON after write | Verify: `python -m json.tool orchestration/backlog.json` exits 0
- No silent data loss: if backlog.json was missing or invalid, it was repaired before append, not silently replaced | Verify: Read backlog.json entry count — must be ≥ previous count

# LEARN

- Do not write signals for routine backlog captures
- Write a signal to memory/learning/signals/{YYYY-MM-DD}_backlog-pattern.md only when 3+ tasks of the same type or project accumulate in a single session without being dispatched -- this signals a potential bottleneck or decision avoidance pattern
- Rating: 6-7 for bottleneck patterns worth addressing; skip for normal backlog growth
- Track how long P1 items sit before dispatch — items waiting >14 days without a blocker comment signal decision avoidance, not just scheduling; surface to Eric at next `/vitals` check
