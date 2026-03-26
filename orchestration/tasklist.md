# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-03-26

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
| 4 | **`learning-capture` skill** — Automate LEARN phase, write signals every session | Claude Code | Hooks into Claude Code lifecycle, needs settings.json access |
| 5 | **`telos-update` skill** — Scan session/inputs, propose updates to TELOS files | Claude Code | Needs to read session history + write to telos/ files |

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
| 11 | **`create-prd` skill** — Generate product requirements documents | Cursor | Fabric pattern format |
| 12 | **`review-code` skill** — Code review with security focus | Cursor | Fabric pattern format |
| 13 | **`threat-model` skill** — STRIDE threat modeling | Cursor | Fabric pattern format |
| 14 | **`self-heal` skill** — Auto-diagnose and fix when tests fail | Claude Code | Needs Claude Code lifecycle hooks |
| 15 | **`security-audit` skill** — Scan system for vulnerabilities | Claude Code | Needs file system + security context |

### Phase 2D: Hooks & Infrastructure

> System-level wiring that must be done in Claude Code.

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 16 | **Implicit sentiment analysis hook** — Detect satisfaction/frustration, log as rating signal | Claude Code | Hook into PostToolUse or session-end |
| 17 | **Signal synthesis workflow** — Periodically distill signals into wisdom, update CLAUDE.md steering rules | Claude Code | Reads signals/, writes synthesis/, updates CLAUDE.md |
| 18 | **AI Steering Rules auto-generation** — Failure analysis produces new steering rules | Claude Code | Reads failures/, proposes CLAUDE.md updates |
| 19 | **Skill assembly pipeline** — Auto-build SKILL.md from Fabric pattern components | Claude Code | The meta-system: pattern template + identity + steps + output = skill |
| 20 | **Session-start hook upgrade** — Load TELOS context + active project + recent learnings | Claude Code | The #1 lever for smarter sessions |

### Phase 2E: TELOS Continuous Update System

| # | Task | Build In | Notes |
|---|------|----------|-------|
| 21 | **Voice transcript ingestion** — Process voice recordings into session history | TBD | Depends on voice capture method (ElevenLabs, Whisper, etc.) |
| 22 | **Session transcript → TELOS extraction** — Run extract-wisdom on session transcripts, route to TELOS files | Claude Code | Combines extract-wisdom + telos-update |
| 23 | **TELOS diff reporting** — "What has Jarvis learned about you this week?" summary | Claude Code | Reads LEARNED.md git history, generates report |

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

---

## Build Location Guide

**Cursor** = Fabric-pattern-format skills (structured markdown files that follow IDENTITY/STEPS/OUTPUT template). These are self-contained .md files with no Claude Code lifecycle dependencies.

**Claude Code** = Anything that hooks into Claude Code's lifecycle (hooks, settings.json, session-aware skills, memory system wiring). These need access to the running Claude Code environment.

**TBD** = Depends on external tooling decisions not yet made.
