# Model and Effort Routing — Steering Rules

> Behavioral constraints for model selection, advisor() use, and escalation routing in interactive sessions.
> Load when scoping a build, deciding whether to call advisor(), or choosing between advisor() and /architecture-review.
> Autonomous routing is in `orchestration/steering/autonomous-rules.md` — this file covers interactive sessions only.
> **Ceremony intensity (per-phase action profiles + HARD HALT points) is routed via `orchestration/steering/ceremony-tier.md`.** This file specifies *which* model/depth to invoke; ceremony-tier.md specifies *when* to invoke it across the 7 ALGORITHM phases. The advisor() and /architecture-review trigger sections below define WHEN-by-content; ceremony-tier.md defines WHEN-by-tier.

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

**Pre-BUILD trigger matrix (canonical — CLAUDE.md WD points here):**
- Pre-PRD design decision with 2+ viable paths and hard-to-reverse consequences
- Trust-boundary changes (auth, secret access, validator scope, autonomous-session write boundaries)
- MCP/tool class additions or extractions — see MCP-class taxonomy guard below
- Cross-cutting infrastructure changes (dispatcher, hooks, worktree machinery, prompt-assembly pipelines)
- Any decision crossing system boundaries (autonomous capabilities, production architecture)
- 2+ prior failed fixes on the same symptom — see `incident-triage.md#I1` (advisor() is NOT a substitute)

**MCP-class taxonomy guard (sub-rule for MCP extraction proposals):** Before proposing native extraction of any MCP, consult `memory/knowledge/harness/mcp_class_taxonomy.md`. Class 2 (`mcp__claude_ai_*` Anthropic-managed OAuth) is not extractable regardless of arch-review outcome. Class 3 (unknown origin) requires investigation before migration planning. Why: 2026-04-19 MCP-native migration proposal dissolved on arch-review — 5 wrong assumptions caught including OAuth ownership inversion; full native build would have cost ~2 weeks on MCPs Anthropic owns.

**ADHD-velocity rationale:** Build-first instinct produces premature "X is best / Y won't work" conclusions; three-agent convergence catches different failure classes independently (first-principles questions assumptions, fallacy detects motivated reasoning, red-team enumerates abuse paths).

**Boundary:** advisor() = plan review (reviews the HOW before execution); /architecture-review = design review (reviews the WHAT before planning). Run /architecture-review before the PRD, advisor() before BUILD.

## Parallel Agent Splitting

- **For plan-mode tasks touching both skill internals (SKILL.md, steering docs) and generated artifacts (scripts, manifests, runtime), default to 2 parallel Explore agents split along that seam — one reads each side.** Mixing both in a single Explore pass produces shallow coverage of both.

## "Opus-only" Tasks

There is no mid-session model switch in Claude Code — the session model is set at start. "Opus-only" means: start a fresh session with Opus configured OR use advisor() as the Opus-equivalent review gate.

**Scenarios that warrant a fresh Opus session (not advisor()):**
- Sonnet has failed 2+ times on the same bug (start fresh, advisor() in same broken context adds little)
- TELOS-level decisions (goal alignment, major project pivots, life direction) — full Opus reasoning from first token
- Pure architecture with no implementation (all judgment, no bulk code generation)

## Escalation Order

1. Sonnet handles the task normally
2. Triggers above → call advisor() before BUILD
3. 2+ failures → /architecture-review (mandatory per `incident-triage.md#I1`)
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
