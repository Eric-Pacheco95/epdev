# Model and Effort Routing — Steering Rules

> Behavioral constraints for model selection, advisor() use, and escalation routing in interactive sessions.
> Load when scoping a build, deciding whether to call advisor(), or choosing between advisor() and /architecture-review.
> Autonomous routing is in `orchestration/steering/autonomous-rules.md` — this file covers interactive sessions only.

## Default

Sonnet + normal effort. No change needed for routine tasks (file ops, status checks, single-file edits, skill execution, `/research`, `/quality-gate`). No steering rule needed to document the default — it's the absence of a trigger.

## advisor() — When to Call

`advisor()` sends full conversation history to Opus for a single-shot plan sanity check. It is NOT a structural analysis tool — it reviews the current conversation state, not the design.

**Call advisor() when:**
- PRD contains unannotated main-thread ISC items with `[I]` or `[R]` confidence tags (inferred/reverse-engineered = lower-confidence criteria where plan review adds signal)
- PRD contains irreversible verify methods (production deploys, external API writes, credential changes, git push to shared branches)
- About to complete a multi-session build (before declaring COMPLETE, not mid-build)
- Eric explicitly requests a second opinion mid-session

**Do NOT call advisor() when:**
- `/architecture-review` has already run on this proposal (it IS the multi-angle Opus-equivalent; advisor on top is redundant review)
- Task is routine execution with no ambiguous criteria
- Session has already compacted — see Compaction Caveat below

**Compaction caveat:** advisor() authorization expires on context compaction. If the session has compacted since the advisor() call, treat the authorization as expired: re-read the PRD from disk and call advisor() again if the triggers above still apply. A decision record that says "advisor consulted" with compacted context is misleading — not protective.

## /architecture-review — When to Use Instead

`/architecture-review` runs 3 parallel adversarial agents (first-principles + fallacy + red-team). It is a structural analysis tool, not a conversation sanity check.

**Use /architecture-review when:**
- Pre-PRD design decision with 2+ viable paths and hard-to-reverse consequences
- 2+ prior failed fixes on the same system (existing CLAUDE.md steering rule governs this — advisor() is NOT a substitute here)
- Any decision crossing system boundaries (autonomous capabilities, trust-boundary changes, production architecture)

**Boundary:** advisor() = plan review (reviews the HOW before execution); /architecture-review = design review (reviews the WHAT before planning). Run /architecture-review before the PRD, advisor() before BUILD.

## "Opus-only" Tasks

There is no mid-session model switch in Claude Code — the session model is set at start. "Opus-only" means: start a fresh session with Opus configured OR use advisor() as the Opus-equivalent review gate.

**Scenarios that warrant a fresh Opus session (not advisor()):**
- Sonnet has failed 2+ times on the same bug (start fresh, advisor() in same broken context adds little)
- TELOS-level decisions (goal alignment, major project pivots, life direction) — full Opus reasoning from first token
- Pure architecture with no implementation (all judgment, no bulk code generation)

## Escalation Order

1. Sonnet handles the task normally
2. Triggers above → call advisor() before BUILD
3. 2+ failures → /architecture-review (mandatory per Workflow Discipline rule)
4. Repeated arch-review failures or TELOS-level → fresh Opus session

## Catch-Rate Logging (non-optional after every advisor() call)

The PostToolUse hook already writes a stub entry (`event: advisor_called`) to `data/advisor_log.jsonl` with the word count. After processing the advisor's response and deciding what (if anything) to change, append a model-assessment entry via Bash **before** taking any action:

```bash
python -c "
import json; from pathlib import Path; from datetime import datetime, timezone
entry = {
    'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    'session_id': 'SESSION_ID_HERE',
    'event': 'advisor_assessed',
    'task': 'TASK_SLUG_3_WORDS',
    'advisor_changed_plan': False,
    'catch_summary': 'none'
}
p = Path('data/advisor_log.jsonl'); p.parent.mkdir(exist_ok=True)
with open(p, 'a') as f: f.write(json.dumps(entry) + '\n')
"
```

- `advisor_changed_plan: true` = advice caused a concrete plan change (ISC revision, approach switch, scope trim)
- `catch_summary`: one sentence describing what changed, or `'none'`
- The hook entry and model entry share a date — correlation is date + sequential order
- **Kill switch**: after 20 `advisor_assessed` entries, compute catch rate = `true` count / total. If <10%, the advisor() trigger conditions are too broad — tighten them via `/update-steering-rules`

## Loaded by

- Load explicitly when scoping a build, reviewing ISC quality, or deciding on escalation
- `/implement-prd` SKILL.md — ISC_QUALITY_GATE step (risk-signal trigger guidance)
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
