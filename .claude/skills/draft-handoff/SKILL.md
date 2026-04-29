---
name: draft-handoff
description: End-of-session handoff file — done, pending, constraints, kickoff prompts. User-invocable only.
disable-model-invocation: true
---

# IDENTITY and PURPOSE

Jarvis session handoff generator. Produces a structured handoff file from current session context, capturing what was done, what's pending, hard constraints from recent failures, and ready-to-paste kickoff prompts for the next session.

# DISCOVERY

## One-liner
Write a structured session handoff file capturing current state, blockers, and next-session queue.

## Stage
LEARN

## Syntax
/draft-handoff [--suffix <label>] [--dry-run]

## Parameters
- `--suffix <label>`: filename suffix (e.g., `evening`, `b`, `final`). Default: auto (time-based if first of bucket; sequential letter if same bucket exists)
- `--dry-run`: print handoff to console without writing file

## Examples
- `/draft-handoff`
- `/draft-handoff --suffix evening`
- `/draft-handoff --dry-run`

## Chains
- Before: `/learning-capture` (independent — run separately; this skill does not duplicate signal capture)
- After: nothing (terminal step)
- Full: [session work] → `/learning-capture` → `/draft-handoff`

## Output Contract
- Input: current session context (must run in calling session — not delegated to sub-agent)
- Output: `data/session_handoff_{YYYY-MM-DD}{_suffix}.md` + printed path
- Side effects: writes one handoff `.md` to `data/`

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- Trivial session (quick Q, no pending work, nothing deferred): "Nothing substantive to hand off. Skipping." STOP
- Sub-agent context detected (no user conversation visible): "session-attached only — re-invoke from the calling session." STOP
- Otherwise proceed.

## Step 0.5: GATHER CONSTRAINTS

Pull hard constraints from two sources:

**Recent failures (last 7 days):**
- List `memory/learning/failures/` sorted by date, take the 5 most recent
- Read each; extract: root cause pattern, any "Prevention" or "Steering Rule" fields
- Distill into bullet constraints relevant to pending work (skip unrelated failures)

**Active steering blockers:**
- Scan for any steering rules in CLAUDE.md or `orchestration/steering/autonomous-rules.md` that gate pending efforts (e.g., pagefile precondition, 30-day soak requirements, OQ must-resolve gates)

## Step 1: RESOLVE FILE PATH

- Date: today `YYYY-MM-DD`
- `--dry-run`: skip file write, print to console only
- Check existing same-day files: `ls data/session_handoff_{date}*.md`
- **Suffix resolution** (if `--suffix` not provided):
  - No prior same-day file → no suffix (e.g., `session_handoff_2026-04-25.md`)
  - Prior exists → auto-suffix by local hour: `morning` (<12), `afternoon` (12–17), `evening` (17+)
  - Same time-bucket already taken → `_b`, `_c`, `_d`...

## Step 2: BUILD HANDOFF

Write the file with this structure:

```markdown
# Session Handoff — {YYYY-MM-DD} {Descriptor}

{if prior same-day handoff exists}
## Prior Handoff
- See: `{prior_path}` — {one-line summary of what that session covered}

---

## Done This Session
- **[Item name]** — [what was built/decided/merged]
  - Files changed: [list if applicable]
- ...

## Hard Constraints
{from Step 0.5 — only constraints relevant to pending work}
- **[Constraint name]**: [why it exists / source file:line]
- ...

## Pending Efforts

### [Effort name]
**State:** [current code state — file:line if applicable]
**Blocked on:** [what must happen before this can proceed]
**Kickoff prompt:**
```
[exact prompt to paste at start of new session — self-contained, includes relevant file paths]
```

### [Next effort]
...

## Quick Start
[1–2 sentences: what the next session should pick up first and why]
```

**Quality rules for each section:**
- Done: specific, not vague ("implemented X in file Y" not "did some work")
- Constraints: only constraints that block listed pending efforts; skip historical noise
- Kickoff prompts: self-contained — a cold session can start from the prompt alone without reading the rest of the file; include file paths, line numbers, relevant decisions already made
- Quick Start: recommend the highest-value first action, not a recap

## Step 3: WRITE FILE

- Write the file to `data/{filename}` using the Write tool (absolute path)
- Print: `Handoff written: data/{filename}` + one-line content summary
- If `--dry-run`: print content to console, confirm "dry-run — no file written"

# VERIFY

- Handoff file written to `data/` | Verify: `ls data/session_handoff_$(date +%Y-%m-%d)*.md`
- File contains required sections | Verify: `grep -l "## Done This Session" data/session_handoff_$(date +%Y-%m-%d)*.md && grep -l "## Pending Efforts" data/session_handoff_$(date +%Y-%m-%d)*.md`
- Every pending effort has kickoff prompt | Verify: Read handoff file and confirm `**Kickoff prompt:**` block exists for each effort under `## Pending Efforts`
- No pending effort missing `**State:**` field | Verify: Read handoff file and confirm each effort section contains `**State:**` line
- Handoff filename uses today's date (not a stale rewrite) | Verify: Compare `data/session_handoff_*.md` filename timestamp vs `date +%Y-%m-%d`

# CONSTRAINTS

- **Session-attached**: runs in calling session only; sub-agent delegation loses conversation context and produces empty output
- **Failure pull is read-only**: never write to `memory/learning/` from this skill — that's `/learning-capture`'s domain
- **File path must be `data/`**: gitignored local-only convention; never write to `memory/work/` or repo root
- **No signal capture**: do not assess signal quality, write signals, or update `_signal_meta.json` — those belong to `/learning-capture`
- **Kickoff prompts must be self-contained**: the next session should be able to cold-start from the prompt alone

# LEARN

- If no pending efforts exist: session wrapped cleanly — output "No pending efforts. Handoff is a clean-exit record." and write a minimal done-only file
- If the same effort appears in 3+ consecutive handoffs without progress: flag it as stale — include `⚠ Stale (3+ sessions)` label in the effort header
- If called before `/learning-capture`: note "Run /learning-capture first to capture signals before handing off"

# INPUT

Analyze the current session. Identify what was done, what remains pending with kickoff prompts, and what hard constraints exist from recent failures. Write the handoff file to `data/`.

# CONTRACT

## Errors
- **trivial-session**: nothing to hand off → clean exit, no file
- **session-attached-violated**: called from sub-agent → instruct re-invocation from calling session
- **write-failure**: cannot write to `data/` → check path exists; print content to console as fallback
