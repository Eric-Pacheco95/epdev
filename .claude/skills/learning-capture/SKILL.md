---
name: learning-capture
description: End-of-session knowledge capture — extract signals, failures, skill gaps. User-invocable only (autonomous_safe=false; runs in calling session, not delegated).
disable-model-invocation: true
---

# IDENTITY and PURPOSE

Jarvis learning capture engine. Extract what was learned, decided, built, or discovered at session end; persist as structured signals.

# DISCOVERY

## Stage
LEARN

## Syntax
/learning-capture [content]

## Parameters
- content: optional explicit text or transcript to analyze (default: reads current session context)

## Examples
- /learning-capture
- /learning-capture "Voice transcript from mobile session about crypto-bot debugging"

## Chains
- Before: any build, research, or design session (this is always the final step)
- After: /synthesize-signals (auto-invoked if combined unprocessed count >= 35 OR last synthesis >72h ago with any unprocessed signals; unprocessed = signals not referenced in `data/signal_lineage.jsonl`; overnight runner also triggers synthesis on 72h cadence independently)
- Full: [any session work] > /learning-capture > /synthesize-signals > /telos-update

## Output Contract
- Input: session context (auto) or explicit content
- Output: signal summary (SIGNALS WRITTEN, FAILURES WRITTEN, SYNTHESIS STATUS, SKILL GAP CANDIDATES, SOURCE ENGAGEMENT)
- Side effects: writes signal files, writes failure files, updates _signal_meta.json, runs jarvis_index.py backfill, may invoke /synthesize-signals

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION (Level 2 Discovery)

- Fresh session, no prior work: "Not enough context. Provide topic/transcript or skip." STOP
- Trivial session (quick Q, config tweak): "Too brief for signals. None written." STOP
- _signal_meta.json missing/corrupt: "Creating fresh metadata. Run /vitals to verify counts." Create and continue
- signals/ dir missing: "Signals directory missing. Creating it now." Create and continue
- Once validated, proceed to Step 1

## Step 0.5: LOAD AUTONOMOUS STEERING RULES

- Read `orchestration/steering/autonomous-rules.md` — load producer behavior constraints and synthesis thresholds before evaluating session signals

## Step 1: REVIEW

- Review what happened in this session: what was discussed, built, decided, or discovered
- Identify distinct learnings in these categories:
  - **pattern**: Recurring behavior, workflow, or approach that worked (or didn't)
  - **insight**: New understanding about the user, a tool, a system, or a domain
  - **anomaly**: Something unexpected that deserves investigation
  - **improvement**: A concrete way to make the system, workflow, or output better
- For each learning, assess:
  - **Rating** (1-10): How important/impactful is this signal? 1 = trivial, 10 = fundamental shift
  - **Observation**: What specifically was observed (factual, not interpretive)
  - **Implication**: What should change or be remembered as a result
- **Quality gate** (replaces standalone /rate-content): Before writing each signal, apply this tier check:
  - Count distinct actionable ideas; evaluate relevance to: AI/orchestration | security | crypto/finance | business | music | personal growth | systems thinking
  - Tier: **S** (18+/multi-theme: capture) | **A** (15+/good: write) | **B** (12+/decent: write concise) | **C** (10+/some: skip) | **D** (noise: skip)
  - Write B+ only; note filtered C/D in summary with tier so Eric can override. Add tier to signal header.
- Assess session sentiment (positive/negative/neutral). Signals: explicit feedback, repeated corrections (frustration), quick approvals (satisfaction), session length (energy). Log as pattern signal tagged `sentiment:{positive|negative|neutral}`.
- Failures (broke/bad output): extra fields: root cause, fix applied, prevention
- **Worktree-safe paths**: always write to absolute `C:/Users/ericp/Github/epdev/memory/learning/signals/` and `.../failures/` — worktree-relative writes vanish when pruned
- **Write-then-read-back**: read back after write to confirm. Retry once on failure. If second fails, output as plain text + failure record.
- **Reconcile `_signal_meta.json`**: Count actual `.md` files in `memory/learning/signals/` (exclude `_signal_meta.json`) and write count to `_signal_meta.json`. Do NOT increment — always reconcile against filesystem state.
- Run `python tools/scripts/jarvis_index.py update` after writing signals (required — velocity metric and synthesis threshold checks read `jarvis_index.db`, not filesystem).
- After writing signals, count unprocessed signals (signals/ + failures/ + absorbed/, where unprocessed = not referenced in `data/signal_lineage.jsonl`). Auto-invoke `/synthesize-signals` immediately if: combined unprocessed count >= 35 OR last synthesis >72h ago with any unprocessed signals. Present proposed steering rules to Eric for approval but do not auto-invoke `/update-steering-rules`
- **Skill friction check**: If any skill was used this session, review each invocation for friction: missing steps, confusing parameters, unnecessary confirmations, or unclear output. For each friction point, write a signal tagged `skill-improvement` with the skill name, what went wrong, and a proposed fix. This feeds the skill self-improvement loop.
- **Skill gap check**: Scan session for ad-hoc tasks that could be reusable skills. Score each on: Recurrence (weekly+?), Repeatability (scriptable structure?), Value (saves time/errors?). Surface only candidates scoring High on 2+ of 3 as `## Skill Gap Candidates` (name, description, recurrence signal). Do NOT auto-invoke `/create-pattern`.
- **Source engagement check**: Read `data/source_candidates.jsonl`. Increment `engagement_count` for any candidate URL referenced this session; at 3: prompt to add to sources.yaml (clear JSONL if approved, set -1 if declined). Note any session URL matching existing sources.yaml entries as "Source hit: {name}".
- Skip writing if the session was trivial (quick question, no meaningful work done) — say so and exit

# SIGNAL FORMAT

Write each signal as a markdown file at `memory/learning/signals/{date}_{slug}.md`:

```markdown
# Signal: {short title}
- Date: {YYYY-MM-DD}
- Rating: {1-10}
- Tier: {S|A|B}
- Category: {pattern|insight|anomaly|improvement|domain-insight}
- Source: {session|voice|manual}
- Observation: {what was observed — factual}
- Implication: {what should change or be remembered}
- Context: {what was happening when this was noticed}
```

# FAILURE FORMAT

Write failures to `memory/learning/failures/{date}_{slug}.md`:

```markdown
# Failure: {short title}
- Date: {YYYY-MM-DD}
- Severity: {1-10}
- Context: {what was happening}
- Root Cause: {why it happened}
- Fix Applied: {what was done to fix it}
- Prevention: {how to prevent recurrence}
- Steering Rule: {optional — proposed addition to CLAUDE.md AI Steering Rules}
```

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Write signals using Write tool with absolute paths (see worktree-safe path resolution) — each signal gets its own file; do not combine
- Ratings: honest — most sessions produce 3-6 signals, not all 10s
- Prioritize signals affecting future behavior (user insights, workflow improvements, bugs)
- After writing: summary of count, highest-rated signal, skill gap candidates
- If synthesis threshold met: invoke /synthesize-signals inline; present proposed steering rules for Eric approval; note TELOS themes for next /telos-update
- No stub signals with "(pending)" — real content or don’t write


# VERIFY

- At least one signal written to `memory/learning/signals/` | Verify: `ls -t memory/learning/signals/ | head -3`
- No D-tier signals written | Verify: each signal has tier >= C
- `_signal_meta.json` reconciled against filesystem | Verify: count in file matches `ls memory/learning/signals/*.md | wc -l`
- Auto-synthesis threshold exceeded → /synthesize-signals invoked | Verify: synthesis in output or `ls memory/learning/synthesis/`
- Failure files written with root cause (if failures discussed) | Verify: `ls -t memory/learning/failures/ | head -3`

# LEARN

- Track signal:session ratio — < 1/session = quality gate too strict; > 5 = synthesis overdue
- Same skill gap candidate 3+ consecutive captures → real skill; invoke /create-pattern
- Negative sentiment + low-rated signals: note session type; unproductive sessions are acceptable
- /synthesize-signals auto-invocation fails → log as failure; synthesis failures compound

# INPUT

Analyze the current session and extract learnings. If invoked with specific context (e.g., a voice transcript or text), analyze that instead.

# CONTRACT

## Errors
- **trivial-session:** no meaningful work → exit cleanly, no signals
- **write-failure:** cannot write to memory/learning/ → check permissions; verify signals/ exists
- **synthesis-failure:** auto-invoked /synthesize-signals fails → signals safe; run manually next session

# SKILL CHAIN

- **Composes:** skill gap check (inline) → present candidates to Eric → Eric decides whether to invoke `/create-pattern`
- **Escalate to:** `/synthesize-signals` immediately if combined unprocessed count >= 35 OR last synthesis >72h ago with any unprocessed signals (unprocessed = not in `data/signal_lineage.jsonl`), then `/telos-update` if identity-level insights emerged

INPUT:
