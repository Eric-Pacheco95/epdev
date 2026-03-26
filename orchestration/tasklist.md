# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-03-27

## Active Projects

| Project | Status | Health | Owner | Next Action |
|---------|--------|--------|-------|-------------|
| epdev-jarvis-setup | active | green | epdev | Phase 2 skills build — start with Tier 1 foundational |

## Phase 1: Foundation Tasks (COMPLETE)

- [x] Initialize git repo
- [x] Create directory scaffold
- [x] Create CLAUDE.md root context
- [x] Create constitutional security rules
- [x] Create memory system with README
- [x] Create history system with README
- [x] Create orchestration system with README
- [x] Populate TELOS identity
- [x] Configure personality.yaml
- [x] Create lifecycle hooks (session start, security validator, learning capture)
- [x] Create agent definitions (Architect, Engineer, SecurityAnalyst, QATester, Orchestrator)
- [x] Create defensive test baseline (injection + secret scanner — all passing)
- [x] Create Cursor integration (.cursorrules + PRD workflow)
- [x] Create EPDEV Bible (pinned to desktop)
- [x] Wire hooks into .claude/settings.json
- [x] Install Fabric CLI (installed via winget v1.4.441)
- [x] Create self-heal test baseline
- [x] Initial git commit
- [x] Split TELOS into individual identity documents (18 files in memory/work/telos/)

## Phase 2: Skills, Learning Loop & TELOS System

### Phase 2A: Tier 1 Foundational Skills (Build First — These Power Everything)

> These are the engine. Nothing else works well without them.
> Build order matters — each enables the next.

| # | Task | Build In | Why This Order |
|---|------|----------|----------------|
| 1 | ~~**`extract-wisdom` skill**~~ DONE | Cursor | Core extraction engine. Every other skill feeds from this |
| 2 | ~~**`create-summary` skill**~~ DONE | Cursor | Needed for efficient memory writes |
| 3 | ~~**`create-pattern` meta-skill**~~ DONE | Cursor | Once this works, you can prompt "create a new skill for X" and it self-assembles |
| 4 | ~~**`learning-capture` skill**~~ DONE | Claude Code | Hooks into Claude Code lifecycle, needs settings.json access. Also fixed stop hook to stop creating stub signals |
| 5 | ~~**`telos-update` skill**~~ DONE | Claude Code | Needs to read session history + write to telos/ files |

### Phase 2B: Tier 2 Thinking & Analysis Skills

> These make Jarvis smarter at reasoning. Build after Tier 1 is solid.

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 6 | ~~**`analyze-claims` skill**~~ DONE | Cursor | Fabric pattern format |
| 7 | ~~**`first-principles` skill**~~ DONE | Cursor | Based on PAI Thinking Pack |
| 8 | ~~**`red-team` skill**~~ DONE | Cursor | Based on PAI Thinking Pack |
| 9 | ~~**`improve-prompt` skill**~~ DONE | Cursor | Fabric pattern format |
| 10 | ~~**`find-logical-fallacies` skill**~~ DONE | Cursor | Fabric pattern format |

### Phase 2C: Tier 3 Project & Domain Skills

> These handle real work. Build as needed for specific projects.

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 11 | ~~**`create-prd` skill**~~ DONE | Cursor | Fabric pattern format |
| 12 | ~~**`review-code` skill**~~ DONE | Cursor | Fabric pattern format |
| 13 | ~~**`threat-model` skill**~~ DONE | Cursor | Fabric pattern format |
| 14 | ~~**`self-heal` skill**~~ DONE | Claude Code | Needs Claude Code lifecycle hooks |
| 15 | ~~**`security-audit` skill**~~ DONE | Claude Code | Needs file system + security context |

### Phase 2D: Hooks & Infrastructure

> System-level wiring that must be done in Claude Code.

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 16 | ~~**Implicit sentiment analysis**~~ DONE | Claude Code | Built into learning-capture skill (sentiment detection in session analysis) |
| 17 | ~~**Signal synthesis workflow**~~ DONE | Claude Code | New `/synthesize-signals` skill — reads signals, writes synthesis, archives processed |
| 18 | ~~**AI Steering Rules auto-generation**~~ DONE | Claude Code | New `/update-steering-rules` skill — analyzes failures/synthesis, proposes CLAUDE.md updates |
| 19 | ~~**Skill assembly pipeline**~~ DONE | Claude Code | Updated `create-pattern` to auto-save to `.claude/skills/` and confirm registration |
| 20 | ~~**Session-start hook upgrade**~~ DONE | Claude Code | Now loads TELOS status, active projects, learned entries, skill commands |

### Phase 2E: TELOS Continuous Update System

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 21 | **Voice transcript ingestion** — Process voice recordings into session history | TBD | Depends on voice capture method (ElevenLabs, Whisper, etc.) — deferred to Phase 3 |
| 22 | ~~**Session transcript → TELOS extraction**~~ DONE | Claude Code | Workflow: `/extract-wisdom` on input → `/telos-update` with output. No separate skill needed |
| 23 | ~~**TELOS diff reporting**~~ DONE | Claude Code | New `/telos-report` skill — analyzes git history + TELOS changes + signal trends |

## Phase 3: Orchestration, Agents & UI (Future)

### Phase 3A: Agent Orchestration (Tier 4 Skills)

- [ ] `delegation` skill — Route tasks to specialized agents (PAI Delegation model)
- [ ] `spawn-agent` skill — Compose agents from traits dynamically (PAI Agents Pack)
- [ ] `workflow-engine` skill — Chain skills into multi-step workflows (Fabric "Stitches")
- [ ] Project-orchestrator skill — Manage multi-project state and priorities

### Phase 3B: External Integrations

- [ ] MCP server integrations (Notion, Slack, email, calendar)
- [ ] ntfy push notifications
- [ ] Add observability (Langfuse or similar)

### Phase 3C: Interface

- [ ] Build dashboard UI
- [ ] Voice system (ElevenLabs)
- [ ] Implement meta/self-update system

### Phase 3D: Visual system of record & ideal-state workflow

> **Defer deep design:** Run a focused **Claude Code** analysis pass on this subsection **after Phase 2** (skills, learning loop, TELOS wiring) is further along—more of the system will exist to anchor decisions (ISC, `STATE.md`, hooks, tasklist).

- [ ] **Clarify requirements** — Short written spec: what “brain” means (nodes = PRDs, ISCs, TELOS pillars, projects; edges = deps / order), and what “mould ideal state” must preserve (git-markdown as source of truth vs visual-only layer)
- [ ] **Survey tooling** — Compare low-friction options (e.g. Obsidian vault on `docs/`, Mermaid diagrams in-repo, Canvas/mind-map) vs custom `ui/` dashboard; record pros/cons in `memory/work/` or `docs/`
- [ ] **Current vs ideal workflow** — Define how observed state (tests, hooks, `STATE.md`, signal counts) maps to **gaps vs ISC** and how those gaps become **tasklist** items (manual ritual first; optional automation later)
- [ ] **Claude Code analysis session** — One dedicated session: read spec + survey, recommend implementation order and Phase 3C/3D dependencies; optionally spawn follow-up PRDs

### Phase 3E: ISC engine & scheduled heartbeat

> **Intent:** A **time-driven VERIFY** loop—Miessler-style **current state** as measurable data points, compared to **PRD ISC**, with **gaps** flowing into **learning** (signals/failures), not only when you are in a chat session.
>
> **Example:** Every 30 minutes (configurable) a **heartbeat** job runs collectors (tests passing, defensive suite, file counts, hook self-check, optional health probes), scores each mapped **ISC** or “slowly improve” feature dimension, and **emits** structured notes when gaps or regressions cross thresholds.

- [ ] **ISC engine PRD** — Spec in `memory/work/`: map each PRD ISC line (or feature dimension) to **metric keys**, **thresholds**, **severity**, and **when to write a learning signal** vs suppress noise
- [ ] **Metric collectors** — Small, pluggable modules (stdlib-first): e.g. run `tests/defensive/`, parse results, repo counters, optional lint; output a single **snapshot JSON** per run
- [ ] **`heartbeat` runner** — One CLI entrypoint (e.g. `tools/scripts/jarvis_heartbeat.py`) that loads config, runs collectors, diffs vs last snapshot, updates `memory/work/{project}/STATE.md` or a dedicated **heartbeat log** under `memory/work/` or `history/changes/`
- [ ] **Scheduler** — **Windows Task Scheduler** (primary on your machine) or cron/WSL; document interval (e.g. 30 min), failure alerts, and log rotation in `docs/EPDEV_JARVIS_BIBLE.md`
- [ ] **Gap → learning pipeline** — On regression or sustained gap: append **`memory/learning/signals/`** (and **`failures/`** if user-defined) with template: ISC ref, observed metrics, delta, suggested next action; optional link to `orchestration/tasklist.md` bullets
- [ ] **Security & safety** — Heartbeat reads repo only; no secrets in logs; validate outputs against `security/constitutional-rules.md`; cap signal volume (dedupe, cooldown) to avoid spam
- [ ] **Optional integrations** — Phase 3B: **ntfy** on regression; Phase 3C: dashboard reads last heartbeat JSON

**Depends on:** Phase 2 maturity (signals/synthesis patterns), Phase 3D “current vs ideal” spec (shared vocabulary for gaps). **Build in:** mostly **Cursor/Python** + OS scheduler; Claude Code sessions **review** trends and promote steering rules.

---

## Build Location Guide

**Cursor** = Fabric-pattern-format skills (structured markdown files that follow IDENTITY/STEPS/OUTPUT template). These are self-contained .md files with no Claude Code lifecycle dependencies.

**Claude Code** = Anything that hooks into Claude Code's lifecycle (hooks, settings.json, session-aware skills, memory system wiring). These need access to the running Claude Code environment.

**TBD** = Depends on external tooling decisions not yet made.
