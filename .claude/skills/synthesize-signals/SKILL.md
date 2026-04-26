# IDENTITY and PURPOSE

Signal synthesis engine. Distill accumulated learning signals into higher-order insights: raw observations → patterns → wisdom → steering rules.

# DISCOVERY

## One-liner
Distill accumulated signals into themes, patterns, and proposed steering rules

## Stage
LEARN

## Syntax
/synthesize-signals [--date-range <start> <end>] [--focus <category>]

## Parameters
- --date-range: optional start and end dates to scope signal selection (default: all unprocessed)
- --focus: optional category filter (pattern, insight, anomaly, improvement)

## Examples
- /synthesize-signals
- /synthesize-signals --focus anomaly
- /synthesize-signals --date-range 2026-03-20 2026-03-29

## Chains
- Before: /learning-capture (produces the signals to synthesize)
- After: /update-steering-rules (encode proven themes as rules), /telos-update (if identity-level insights emerge)
- Full: [session work] > /learning-capture > /synthesize-signals > /update-steering-rules > /telos-update

## Output Contract
- Input: unprocessed signals in memory/learning/signals/ (auto-read)
- Output: synthesis document + stdout summary (themes found, actions proposed)
- Side effects: writes synthesis doc, appends data/signal_lineage.jsonl, mirrors lineage to jarvis_index.db

## autonomous_safe
true

# STEPS

## Step 0.5: LOAD AUTONOMOUS STEERING RULES

- Read `orchestration/steering/autonomous-rules.md` — load producer behavior constraints and synthesis thresholds before processing signals

- `python tools/scripts/compress_signals.py --stats --json` — check unprocessed count/velocity (threshold: 35)
- `python tools/scripts/compress_signals.py --group --json` — pre-grouped signals by category with ratings
- Read: `memory/learning/failures/` (4x harm), `memory/learning/absorbed/` (/absorb insights), `memory/learning/synthesis/` (prior context)
- **Input sources** (all required): `signals/` + `failures/` + `absorbed/`; combined unprocessed ≥35 triggers synthesis
- Groups are script-output. Identify recurring themes: name pattern, list supporting signals, assign maturity (Confidence Model), state implication, propose action (steering rule / TELOS update / workflow change)
- **Harm multiplier**: failures weigh 4x
- Findings may warrant: steering rule (`/update-steering-rules` routing tree); TELOS update; skill change; failure prevention. Per rule: record target file, rule text, evidence signals, why it matters
- **Confidence decay**: unrevalidated >90d → downgrade one level; below candidate → archived
- Write synthesis doc to `memory/learning/synthesis/`
- Spawn fresh evaluator subagent (no shared context) with synthesis doc only. Model: `claude-sonnet-4-6`. Output must be `VERDICT: ACCEPT` or `VERDICT: REVISE + [one-sentence delta]`. If REVISE: targeted edit (not full rewrite); accept result. Max 1 pass; substantial delta → new dated file. Evaluator reads synthesis doc only.
- Record lineage: `python tools/scripts/compress_signals.py --lineage "YYYY-MM-DD_synthesis"`
- Mirror to SQLite: `python tools/scripts/sync_lineage.py` (idempotent; JSONL is source of truth if this fails)

# CONFIDENCE MODEL

Each synthesized theme carries a maturity level and confidence score. Inspired by CASS Memory System patterns.

## Maturity Ladder

| Level | Criteria | Action threshold |
|-------|----------|-----------------|
| **candidate** | 2-3 supporting signals, no contradictions | Note in synthesis, no steering rule yet |
| **established** | 4+ signals OR 2+ signals across different sessions/dates | Propose as steering rule or workflow change |
| **proven** | Established + survived 1+ synthesis cycles without contradiction | Encode as permanent steering rule or TELOS update |

## Confidence Decay

90-day half-life: proven → established → candidate → archived if no revalidating signal.

## Harm Multiplier

Failures count **4x** — one failure outweighs four successes.

## Anti-Pattern Inversion

Failed actions become "Do NOT do X because Y" — store with `anti-pattern: true`.

# SYNTHESIS FORMAT

Write to `memory/learning/synthesis/{date}_synthesis.md`:
Synthesis docs accumulate permanently — each run writes a new dated file. Never delete, overwrite, or replace existing synthesis docs.


```markdown
# Signal Synthesis — {date}
- Signals processed: {count}
- Failures reviewed: {count}
- Period: {earliest signal date} to {latest signal date}

## Themes

### Theme: {theme name}
- Maturity: {candidate | established | proven}
- Confidence: {0-100}% (decays 50% per 90 days without revalidation)
- Anti-pattern: {false | true}
- Supporting signals: {list of signal filenames}
- Failure weight: {count of failure signals x4 multiplier}
- Pattern: {what the signals collectively show}
- Implication: {what should change}
- Action: {specific next step}

## Proposed Steering Rules

For each proposed rule, include:
- **Target file**: one of `CLAUDE.md`, `orchestration/steering/platform-specific.md`, `orchestration/steering/autonomous-rules.md`, `orchestration/steering/research-patterns.md`, `orchestration/steering/cross-project.md`, `orchestration/steering/trade-development.md`, or `security/constitutional-rules.md` — use the routing decision tree from `/update-steering-rules` to select
- **Rule text**: specific, actionable, testable — one sentence
- **Evidence**: signal filenames or failure records that support it
- **Why**: what breaks without this rule

Format:
```
1. **Target:** `orchestration/steering/platform-specific.md`
   **Rule:** [rule text]
   **Evidence:** [signal file(s)]
   **Why:** [consequence of absence]
```

If no rules are warranted: "(none proposed)"

## Proposed TELOS Updates

(Any updates for memory/work/telos/ files, or "none proposed")

## Confidence Decay Review

(List any prior themes whose last supporting signal is >90 days old. Downgrade or archive.)

| Theme | Previous maturity | New maturity | Last signal date | Reason |
|-------|-------------------|-------------|------------------|--------|

## Anti-Patterns

(Themes that were tried and failed — inverted into "do NOT" rules.)

## Meta-Observations

(Observations about the learning system itself — is it capturing the right things?)
```

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Read ALL signals before synthesizing — don't process partial batches
- Be honest about signal quality — if most signals are low-rated or vague, say so
- Propose specific, actionable steering rules (not vague guidelines)
- After writing synthesis, record lineage via `compress_signals.py --lineage` to mark which signals were consumed. Signals remain in `signals/` — they are never moved or deleted.
- Output a summary: signals processed, themes found, actions proposed
- If fewer than 3 signals exist, skip synthesis and say "insufficient signals for synthesis"

# CONTRACT

## Errors
- **insufficient-signals:** < 3 unprocessed signals → skip, print count
- **write-failure:** cannot write to memory/learning/synthesis/ → check permissions; stdout as backup

# SKILL CHAIN

- **Composes:** confidence decay review (inline), signal lineage tracking (inline)
- **Escalate to:** `/delegation` if synthesis reveals cross-project patterns requiring orchestration

# VERIFY

- Synthesis file written to `memory/learning/synthesis/YYYY-MM-DD_synthesis.md` | Verify: `ls -t memory/learning/synthesis/ | head -3`
- At least 3 signals processed | Verify: signal count in synthesis header
- Consumed signals in `data/signal_lineage.jsonl` | Verify: lineage file has synthesis run entry
- Required sections present (themes, insights, implications) | Verify: Read synthesis file headers

# LEARN

- Same 2-3 themes across multiple runs → strong TELOS promotion candidates via /telos-update
- Cross-project patterns (same insight across crypto-bot, jarvis, jarvis-app) → /project-orchestrator review
- Track which signal categories generate most themes — reveals highest-learning areas
- Synthesis > weekly → signal volume warrants dedicated synthesis schedule

# INPUT

Review accumulated signals and produce a synthesis. If specific signals or a date range is provided, focus on those.

INPUT:
