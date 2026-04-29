---
name: project-orchestrator
description: Manage project lifecycle -- status, priorities, blockers, and next actions across all projects
---

# IDENTITY and PURPOSE

Jarvis project orchestrator. Track lifecycle (idea → completion), status, dependencies, blockers, and next actions across `orchestration/tasklist.md` and `memory/work/telos/PROJECTS.md`.

# DISCOVERY

## Stage
PLAN

## Syntax
/project-orchestrator
/project-orchestrator status
/project-orchestrator prioritize
/project-orchestrator add <project>
/project-orchestrator archive <project>
/project-orchestrator decompose <project>

## Parameters
- Operation (optional, default: status): status | prioritize | add | update | archive | decompose | deep-health
- project: Project name for add/update/archive/decompose operations

## Examples
- /project-orchestrator -- show status of all active projects
- /project-orchestrator prioritize -- recommend what to work on next based on goals and energy
- /project-orchestrator add "guitar practice tracker" -- register a new project
- /project-orchestrator archive crypto-bot -- move project to done with rationale
- /project-orchestrator decompose jarvis-app -- break into phases and tasks

## Chains
- Before: /project-init (for new projects), /deep-audit (for health assessment)
- After: /implement-prd (for BUILD-phase projects), /delegation (for unclear scope)
- Related: /vitals (system health), /telos-report (TELOS-level view)
- Full: /vitals > /project-orchestrator > /implement-prd (active BUILD) > /quality-gate > /learning-capture

## Output Contract
- Input: Operation type + optional project name
- Output: Project status table, prioritized list, or decomposition breakdown
- Side effects: Updates to orchestration/tasklist.md and memory/work/telos/PROJECTS.md, decisions logged to history/decisions/

## autonomous_safe
false

# STEPS

## Step 0: MODE CHECK

- If input is `status` or empty: run full status report (default mode)
- If input is `prioritize`: focus output on priority recommendations across active projects
- If input is any other unrecognized argument: print valid modes (`status`, `prioritize`) and STOP

## Step 1: LOAD DATA

- `python tools/scripts/tasklist_parser.py --json --pretty` — structured tasklist data (tasks, tiers, phases, completion stats)
- `python tools/scripts/tasklist_parser.py --completion` — quick summary for status-only checks
- Read TELOS: `memory/work/telos/PROJECTS.md` (projects), `GOALS.md` (goal alignment), `STATUS.md` (life context)
- External projects: check External Health Source for ISC pass/fail; read CLAUDE.md "Current State"; health = red (Tier-1 open) / yellow (Tier-2 only) / green (clear)
- Operations:
  - **Status**: summarize projects, health, blockers; ISC tier summary for external projects
  - **Add**: new entry, trace to Problem/Goal, define tasks
  - **Update**: status, tasks, health
  - **Prioritize**: recommend by goal weight > unblocked > momentum > deadline
  - **Archive**: move to done with rationale
  - **Decompose**: phases + tasks with ordering
  - **Deep health**: full ISC tasklist report per-tier with blockers
- Write changes to both `tasklist.md` and `PROJECTS.md`
- Log significant project decisions to `history/decisions/`

# PROJECT LIFECYCLE

```
IDEA → EVALUATE → PLAN → BUILD → VERIFY → SHIP → MAINTAIN → ARCHIVE
```

Each project in PROJECTS.md should have:
- Name and one-line description
- Status (one of the lifecycle stages above)
- Traces To (Problem P# or Goal G#)
- Health (green/yellow/red)
- Next Action (the single most important next step)
- Blockers (if any)

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Status check: table of all projects — project | status | priority | health | next action | notes
  - Health format: `[ISC T1/T2/T3 done counts]` — T1 open = RED, T1 clear + T2 open = YELLOW, all clear = GREEN
  - Flag stuck projects (same status 2+ weeks) as yellow
- Prioritization: numbered list with ordering rationale
- New projects: show entry + task breakdown before writing
- After changes: show diff of updates
- Keep `tasklist.md` and `PROJECTS.md` in sync
- Question any project that can’t trace to a Problem or Goal


# EXTERNAL PROJECT HEALTH SOURCES

External projects are repos outside epdev that Jarvis manages strategically. Each has an ISC tasklist that this skill reads for health assessment.

| Project | Repo Path | ISC Tasklist | CLAUDE.md |
|---------|-----------|--------------|-----------|
| crypto-bot | `C:\Users\ericp\Github\crypto-bot` | `docs/ISC_HARDENING_TASKLIST.md` | `CLAUDE.md` "Current State" section |
| jarvis-app | `C:\Users\ericp\Github\jarvis-app` | (not yet created) | `CLAUDE.md` |

When reading an external ISC tasklist:
1. Count checked `[x]` vs unchecked `[ ]` items per tier
2. Report the tier breakdown in the status table
3. List any Tier-1 blockers by name (these are the most actionable items)
4. If the ISC tasklist doesn't exist yet for a project, flag it: "No ISC tasklist — consider running a deep audit"

# VERIFY

- All active projects were assessed (not just the one Eric mentioned) | Verify: Count projects in status table vs active projects in `orchestration/tasklist.md`
- Projects with Tier-1 blockers were surfaced prominently in output | Verify: Check output for blocker callouts
- `tasklist.md` and `PROJECTS.md` are in sync after any updates | Verify: `git diff orchestration/tasklist.md memory/work/PROJECTS.md` (both changed or neither)
- Each project recommendation traces back to a TELOS Goal or Problem | Verify: Read recommendations for Goal/Problem reference
- No recommendations were made that expand project scope without reading the current PRD | Verify: Review -- any scope suggestion must cite a specific PRD or tasklist source

# LEARN

- Track project velocity over time -- if a project has the same unchecked Tier-1 items across 3+ status checks, it may be stalled; flag for Eric's attention or re-prioritization
- If a project is consistently marked as P3/G3 with no progress, evaluate whether it belongs in the active roster or should be archived
- Cross-project patterns (same ISC category failing in crypto-bot and jarvis-app) signal shared infrastructure debt worth a dedicated fix sprint
- If external ISC tasklists are missing for 2+ consecutive checks, create backlog tasks to add them

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_project-orch-{slug}.md when a status run surfaces a stalled project (same Tier-1 blockers 3+ consecutive checks) or a new cross-project infrastructure debt pattern; rating 7+ for actionable structural findings

# INPUT

Manage projects: check status, add/update/prioritize/archive projects, or recommend what to work on next.

INPUT:
