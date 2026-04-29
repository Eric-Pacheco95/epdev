---
name: telos-update
description: Analyze inputs and propose updates to Eric's TELOS identity files — Jarvis proposes, Eric approves. User-invocable only (Tier 3 identity changes; autonomous path blocked by task_gate).
disable-model-invocation: true
---

# IDENTITY and PURPOSE

TELOS update engine. Analyze session transcripts, recordings, notes, and signals to propose updates to `memory/work/telos/`. **Jarvis proposes, Eric approves.** Never silently modify MISSION.md or BELIEFS.md.

# DISCOVERY

## Stage
LEARN

## Syntax
/telos-update [--consolidate]
/telos-update <input context>

## Parameters
- input (optional): Session transcript, voice recording, manual notes, or learning signals to analyze for TELOS-relevant content. If omitted, analyzes the current session.
- --consolidate: scan all TELOS files for duplicate entries, redundant goals, and cross-file inconsistencies; propose merges and cleanups without auto-writing

## Examples
- /telos-update -- analyze current session for TELOS-relevant signals
- /telos-update "Eric mentioned shifting focus from crypto to AI infrastructure"
- /telos-update memory/learning/signals/2026-04-01_guitar_insight.md

## Chains
- Before: /notion-sync journal (extracts signals that feed updates), /learning-capture (generates signals), /absorb (extracts TELOS-relevant content)
- After: /telos-report (reports on changes), /notion-sync push telos (syncs TELOS Mirror to Notion)
- Related: /red-team --thinking (suggested after monthly TELOS review)
- Full: /learning-capture > /telos-update > /telos-report > /notion-sync push telos

## Output Contract
- Input: Optional context string or file path
- Output: Proposed changes in before/after diff format per TELOS file, grouped by update frequency
- Side effects: TELOS files updated (after approval), TELOS Mirror synced to Notion, changes logged to history/changes/

## autonomous_safe
false

# STEPS

## Step 0: INPUT CHECK

- `--consolidate` flag: read all TELOS files, identify duplicates and cross-file overlaps, propose merge candidates; no writes until Eric confirms
- If no input is provided (empty invocation with no context after `/telos-update`): print usage hint `'Usage: /telos-update <session notes, observations, or updates to record>'` and STOP
- If input is < 10 words: ask Eric for more context before proceeding
- If an unknown flag (not --consolidate) is provided: print valid flags and STOP
- Never auto-write to TELOS files; all updates must be shown to Eric as proposals before any write

## Step 1: READ TELOS STATE

- Read the current state of relevant TELOS files (load only what you need based on the input)
- Analyze the input for signals that map to TELOS categories:
  - **LEARNED.md**: New observations about Eric's working style, communication preferences, decision patterns, energy patterns
  - **STATUS.md**: Changes to current focus, mood/energy, recent wins, blockers, life context
  - **GOALS.md**: New goals mentioned, goal priority shifts, goals achieved or abandoned
  - **CHALLENGES.md**: New blockers discovered, existing challenges resolved
  - **STRATEGIES.md**: New approaches that worked, strategies that failed
  - **PROJECTS.md**: New projects started, status changes, projects completed
  - **IDEAS.md**: New business/project/creative ideas mentioned
  - **MODELS.md**: New mental models adopted or referenced
  - **WISDOM.md**: Hard-won lessons expressed (look for "I learned that...", "turns out...", "I was wrong about...")
  - **WRONG.md**: Explicit admissions of past errors (append-only, never delete)
  - **PREDICTIONS.md**: Future predictions with confidence levels
  - **MUSIC.md**: Practice sessions, musical insights, genre explorations
  - **BELIEFS.md**: Fundamental value shifts (RARE — flag these prominently)
  - **MISSION.md**: Core purpose changes (VERY RARE — flag these prominently)
- Classify update frequency per TELOS FILE LOCATIONS table below; approval tier determines whether to auto-write or propose.
- Present all proposed changes in a clear diff format before writing
- After approval, write changes using the Edit tool (prefer surgical edits over full rewrites)
- Log the update to `history/changes/` with rationale

# TELOS FILE LOCATIONS

All files live in `memory/work/telos/`:

| File | Update Frequency | Auto or Approval |
|------|-----------------|------------------|
| LEARNED.md | Every session | Auto (show summary) |
| STATUS.md | Every session | Auto (show summary) |
| PROJECTS.md | Weekly | Auto (show summary) |
| IDEAS.md | Anytime | Auto (show summary) |
| GOALS.md | Monthly | Requires approval |
| CHALLENGES.md | Monthly | Requires approval |
| STRATEGIES.md | Monthly | Requires approval |
| MODELS.md | Monthly | Requires approval |
| FRAMES.md | Monthly | Requires approval |
| MUSIC.md | Anytime | Requires approval |
| BELIEFS.md | Quarterly | Requires EXPLICIT approval |
| MISSION.md | Rare | Requires EXPLICIT approval |
| WISDOM.md | User-driven | Only when Eric shares |
| WRONG.md | User-driven | Only when Eric shares |
| PREDICTIONS.md | User-driven | Only when Eric shares |
| HISTORY.md | Rare | Only when Eric shares |
| NARRATIVES.md | Monthly | Requires approval |

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Present changes as before/after diff per file, grouped by file name as heading
- LEARNED.md and STATUS.md: auto-approved (show what will be added)
- All other files: show proposed changes, wait for explicit approval
- After writing: "Updated N TELOS files: [list]"
- If no meaningful updates: say so, don’t force updates
- After monthly review of GOALS/CHALLENGES/BELIEFS: suggest /red-team --thinking
- WRONG.md is append-only — never delete content
- Relative dates → absolute ("last Thursday" → "2026-03-20")
- LEARNED.md entries added at top of relevant section with date prefix


# NOTION AUTO-WRITE (TELOS Mirror)

After all TELOS file updates are written, automatically sync the TELOS Mirror page in Notion:

1. Read the current state of key TELOS files: `MISSION.md`, `GOALS.md`, `STATUS.md`, `BELIEFS.md`, `PROJECTS.md`, `LEARNED.md`
2. Use `mcp__claude_ai_Notion__notion-fetch` to get the current content of page `32fbf5ae-a9e3-81dd-afaf-f94608fa0153`
3. Use `mcp__claude_ai_Notion__notion-update-page` with command `replace_content` to replace the entire page content with an updated mirror:
   - Keep the intro paragraph and "This is a mirror" note
   - Rebuild sections: Mission, Top Goals (with percentages), Current Focus, Key Beliefs, Active Projects (table), Who Eric Is
   - Update `*Last synced by Jarvis: YYYY-MM-DD*` at the bottom
4. Confirm to Eric: "TELOS Mirror synced to Notion."

If the Notion write fails, log the error but do not fail the skill — the local TELOS files are the primary deliverable.

# VERIFY

- Each approved update has snapshot in `memory/work/telos/.snapshots/` | Verify: recent timestamps present
- No verbatim external quotes without `[source: external]` | Verify: new entries have source tags
- Notion sync: success or logged failure | Verify: output shows sync result
- WRONG.md append-only | Verify: `git diff memory/work/telos/WRONG.md` shows only additions
- Absolute dates used (no relative phrases) | Verify: scan new entries

# LEARN

- Same TELOS file 3+ consecutive sessions: high-churn; assess real growth vs noise
- Track fastest-growing files — may need consolidation via /telos-update --consolidate
- Eric rejects update: note category — reveals identity model edges
- Notion sync fails repeatedly: log signal for diagnosis

# INPUT

Analyze the current session (or provided input) and propose TELOS updates.

INPUT:
