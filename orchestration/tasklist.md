# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-03-26 (Phase 3C Voice/Mobile PRD: `memory/work/jarvis/PRD_voice_mobile.md`)

## Active Projects

| Project | Status | Health | Owner | Next Action |
|---------|--------|--------|-------|-------------|
| epdev-jarvis-setup | active | green | epdev | Phase 4: autonomous self-improvement — see `memory/work/jarvis/PRD.md` |

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
| 21 | **Voice transcript ingestion** — Process voice recordings into session history | Claude Code | Moved to Phase 3C — see `memory/work/jarvis/PRD_voice_mobile.md` for full architecture |
| 22 | ~~**Session transcript → TELOS extraction**~~ DONE | Claude Code | Workflow: `/extract-wisdom` on input → `/telos-update` with output. No separate skill needed |
| 23 | ~~**TELOS diff reporting**~~ DONE | Claude Code | New `/telos-report` skill — analyzes git history + TELOS changes + signal trends |

## Phase 3: Orchestration, Agents & UI (Future)

### Phase 3A: Agent Orchestration (Tier 4 Skills)

- [x] `delegation` skill — Route tasks to specialized agents (PAI Delegation model)
- [x] `spawn-agent` skill — Compose agents from traits dynamically (PAI Agents Pack)
- [x] `workflow-engine` skill — Chain skills into multi-step workflows (Fabric "Stitches")
- [x] `project-orchestrator` skill — Manage multi-project state and priorities

### Phase 3B: External Integrations

> **Ideal state — agreed:** **TELOS + Notion:** read-heavy (pull context for grounding), **selective write** to Notion only when a workflow explicitly allows it. **Canonical identity** stays in-repo: `memory/work/telos/*.md` is updated from **merged** context (Notion + sessions + chat), not replaced blindly by Notion.
>
> **Slack:** Enforced routing in **`memory/work/slack-routing.md`** — **`#epdev`** [`C0ANZKK12CD`](https://ericpdev.slack.com/archives/C0ANZKK12CD) = routine (default); **`#general`** [`C0AKR43PDA4`](https://ericpdev.slack.com/archives/C0AKR43PDA4) = must-see only. **ClaudeActivities** app reused; **MCP route A**.
>
> **Miessler / PAI alignment:** Prefer **PAI-shaped** wiring: MCP for external tools, **hooks** as nervous system, **Fabric** patterns, **structured events** — see PAI’s observability direction (e.g. `pai-observability-server` / event capture in the PAI repo). Use **Langfuse or similar** only if you want hosted LLM tracing and it fits deployment better than PAI-style telemetry.

- [x] **Notion (MCP)** — 🧠 Jarvis Brain structure created (Inbox, Journal, Goals & Growth, Ideas, Music, Jarvis Reports, TELOS Mirror). Page registry at `memory/work/notion_brain.md`. Session-start hook Notion read + auto-write to Reports/Mirror pending (Phase 3E era).
- [x] **Slack (MCP)** — `#epdev` routine traffic via ClaudeActivities app confirmed working; stop hook posts session-end summaries. Full MCP read/write integration deferred — current posting flow meets needs.
- [ ] **Email & calendar (MCP)** — Triage and scheduling context
- [ ] **ntfy** — Push notifications to **iPhone** (ntfy iOS app); topic URL secret; regression/heartbeat alerts (see Phase 3E)
- [ ] **Observability** — PAI-aligned hooks/events first; optional Langfuse (or similar) for LLM trace dashboards

### Phase 3C: Voice & Mobile Interface

> **PRD / ISC:** `memory/work/jarvis/PRD_voice_mobile.md`
> **Ideal state:** Eric can speak an idea on his iPhone and it lands in Jarvis's memory pipeline within minutes. He can also reach a full Jarvis terminal session from mobile. Voice sessions produce signals identical in quality to chat sessions.
>
> **Three layers — build in order:**
> - **Layer 1 (capture):** iPhone voice → transcript → inbox → `/voice-capture` → signals
> - **Layer 2 (remote invocation):** Mobile → SSH or HTTP → full Claude Code session
> - **Layer 3 (conversational loop):** STT → Jarvis response → ElevenLabs TTS → spoken reply

#### Layer 1: Voice Capture (quick-win — buildable in one session)

- [x] **3C-1: Inbox structure** — Create `memory/work/inbox/voice/` and `memory/work/inbox/voice/processed/`; document format in PRD
- [x] **3C-2: `/voice-capture` skill** — New Claude Code skill: reads Notion Inbox via MCP, extracts signals with `Source: voice`, queues TELOS-relevant content for `/telos-update`
- [x] **3C-3: Voice capture transport** — **Architecture change**: Notion app (iPhone) → built-in voice transcription → Jarvis Brain Inbox page → Jarvis reads via Notion MCP. iCloud and OneDrive no longer required. `voice_inbox_sync.py` archived (no longer needed for Layer 1). Notion Inbox page ID: `32fbf5ae-a9e3-8198-9975-cbc6293c8690`.
- [x] **3C-4: Register skill + session hook** — Add `/voice-capture` to session-start banner; `/voice-capture` now reads from Notion Inbox via MCP

#### Layer 2: Remote Jarvis Invocation

- [ ] **3C-5: Tailscale + SSH setup** — Install Tailscale on desktop + iPhone; install Blink Shell (iOS); confirm full `claude` CLI session from iPhone over Tailscale. Document in `docs/EPDEV_JARVIS_BIBLE.md`.
- [ ] **3C-6: `jarvis_voice_server.py`** — Lightweight HTTP endpoint on desktop: accepts POST with transcript text + auth token → writes to voice inbox OR runs `claude --print` batch session → returns/Slacks response. Requires auth token (even on local network — see `security/constitutional-rules.md`).
- [ ] **3C-7: iOS Shortcut for remote invocation** — "Hey Siri, ask Jarvis [command]" → STT → POST to `jarvis_voice_server` → response spoken back via Shortcut

#### Layer 3: Conversational Voice Loop (build after Layer 1 + 2 stable)

- [ ] **3C-8: Whisper STT integration** — Evaluate Whisper API vs local `whisper.cpp`; document privacy tradeoff; integrate into `jarvis_voice_server.py` as optional higher-accuracy STT path
- [ ] **3C-9: ElevenLabs TTS integration** — Add TTS step to voice server: Jarvis response → ElevenLabs API → audio file or stream → iOS Shortcut plays it back. API key in env, never logged.
- [ ] **3C-10: End-to-end voice session test** — Full loop: speak → STT → Jarvis session → TTS response → plays on iPhone. Log test result in `history/changes/`.

#### Cross-cutting

- [ ] **Voice signals tracked in heartbeat** — Add `voice_session_count` metric to heartbeat; alert in `#epdev` when no voice sessions in 7 days (behavioral gap signal for Phase 5)
- [ ] **ntfy on capture complete** — Optional: ntfy push to iPhone confirming voice capture was processed (Phase 3B/3E integration point)
- [ ] **Dashboard UI** — Deferred to Phase 3C later (depends on Phase 3D visual system spec)

### Phase 3D: Visual system of record & ideal-state workflow

> **Dependency:** Phase 3D must be substantially complete **before Phase 3E** (the “current vs ideal” vocabulary it produces is the input to heartbeat thresholds and gap→learning logic) and **before Phase 4D** (the autoresearch `autoresearch_program.md` cannot be written without this spec). Do Phase 3D first within Phase 3.

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
- [ ] **AI Steering Rules cadence** — Define ritual: after each `/synthesize-signals` pass (or monthly minimum), run `/update-steering-rules` to promote synthesis findings into `CLAUDE.md` behavioral corrections; log cadence in `docs/EPDEV_JARVIS_BIBLE.md`

**Depends on:** Phase 2 maturity (signals/synthesis patterns), Phase 3D “current vs ideal” spec (shared vocabulary for gaps). **Build in:** mostly **Cursor/Python** + OS scheduler; Claude Code sessions **review** trends and promote steering rules.

---

---

## Phase 3E → Phase 4 Gate (must pass before starting Phase 4A)

> **This gate protects Phase 4 from building on an empty foundation.** Phase 4 autoresearch iterates over accumulated signals and session history — if neither exists, the loop has nothing to improve on.

- [ ] **Heartbeat running** — `jarvis_heartbeat.py` is scheduled and has produced at least one successful snapshot JSON
- [ ] **Learning loop active** — `memory/learning/signals/` contains ≥5 signals captured via `/learning-capture` (not stubs)
- [ ] **At least one synthesis run** — `/synthesize-signals` has produced a dated synthesis doc in `memory/learning/synthesis/`
- [ ] **AI Steering Rules updated once** — `/update-steering-rules` has been run and produced at least one proposed or merged CLAUDE.md change
- [ ] **PAIMM AS1 verified** — Jarvis persistently loads who Eric is across sessions (TELOS + signals + projects in session hook); confirm with: "Does the session start banner reflect current project state and recent learnings?" → yes

---

## Phase 4: Autonomous self-improvement (background Jarvis)

> **PRD / ISC:** `memory/work/jarvis/PRD.md` — **state:** `memory/work/jarvis/STATE.md`  
> **Intent:** Jarvis **self-improves** via automation that does **not** depend on human chat sessions: measure progress toward ideal state, harvest **curated** external patterns (web, GitHub, YouTube, Claude docs), run **[Karpathy-style bounded autoresearch](https://github.com/karpathy/autoresearch)** over **TELOS + learning signals + session history** (writes proposals only — see PRD §4D), and **notify Slack** by importance (`memory/work/slack-routing.md`). Human sessions approve merges, secrets, and TELOS changes.

### Phase 4A — Ideal-state loop & heartbeat (extends 3E)

- [ ] **ISC mapping** — Wire `jarvis_heartbeat` (and collectors) to explicit thresholds from `memory/work/jarvis/PRD.md` ISC lines
- [ ] **Gap → learning** — When metrics cross thresholds, append structured signals (template references ISC); dedupe and cooldown
- [ ] **Windows Task Scheduler** — Document tasks for heartbeat interval; env inheritance (`SLACK_BOT_TOKEN`); log rotation pointer in `docs/EPDEV_JARVIS_BIBLE.md`

### Phase 4B — Autonomous research & pattern harvesting

- [ ] **Source allow-list** — Create `memory/work/jarvis/sources.yaml`; seed with Miessler's own repos first: PAI GitHub, TheAlgorithm, Fabric patterns, PAIMM posts, Unsupervised Learning newsletter — these are the highest-signal sources for Jarvis's current development
- [ ] **Human source review ritual** — After first research run, ask Eric: "What other sources should be added? (YouTube channels, blogs, GitHub repos, newsletters)" — capture answers in sources.yaml and `history/decisions/`
- [ ] **Research runner** — Scheduled job: fetch/summarize → draft digest → optional `memory/learning/signals/` with `Source: autonomous` or inbox folder for review
- [ ] **Cowork vs scheduler split** — Document which steps run as OS jobs vs sandbox agent prompts (per PRD architecture table)

### Phase 4C — Slack notifications by severity

- [ ] **Notifier wrapper or policy** — Map event types to `#epdev` vs `#general` per `slack-routing.md`; implement daily cap / dedupe
- [ ] **Heartbeat + research digests** — Routine summaries → `#epdev`; regressions and must-see criteria → `#general` only when rules match

### Phase 4D — Capstone: internal autoresearch (Karpathy-inspired)

> Pattern from [karpathy/autoresearch](https://github.com/karpathy/autoresearch): human-steered **program**, bounded runs, **one writable surface** for the agent (here: review tree only — not live TELOS). Full spec: `memory/work/jarvis/PRD.md` §4D.

- [ ] **`autoresearch_program.md`** — Create `memory/work/jarvis/autoresearch_program.md` (mission, metrics, step limits, what “better understanding” means)
- [ ] **Review tree** — `memory/work/jarvis/autoresearch/` for runs, proposals, logs; canonical TELOS remains merge-only after human review
- [ ] **Read scope** — Documented inputs: `memory/work/telos/`, `memory/learning/signals/` (+ synthesis/failures as needed), `memory/session/` (time-bounded)
- [ ] **Runner** — `tools/scripts/jarvis_autoresearch.py` and/or documented Cowork/Claude Code batch prompt that enforces read/write boundaries
- [ ] **Metrics per run** — Persist snapshot in run artifact (e.g. contradiction list, open questions, checklist score — per program file)
- [ ] **Integration** — Optional signals with `Source: autonomous`; optional `#epdev` Slack when impact or delta crosses threshold
- [ ] **Human merge path** — Document workflow: review queue → `/telos-update` or manual edit → delete or archive run

**Depends on:** Phase 4A–4C foundations; TELOS and learning layout stable enough to iterate; **Phase 3D "current vs ideal" spec must exist** before writing `autoresearch_program.md`. **Decision:** `history/decisions/2026-03-27_phase4-autonomous-self-improvement.md` (update with 4D)

---

## Phase 4 → Phase 5 Gate (verify before starting Phase 5)

- [ ] **PAIMM AS2 verified** — Jarvis is proactive: heartbeat runs without human prompt, background research produces signals, Slack digests fire on cadence
- [ ] **Autoresearch loop has run ≥3 cycles** — `memory/work/jarvis/autoresearch/` contains ≥3 dated run artifacts with metrics
- [ ] **Steering rules updated from autonomous signals** — at least one CLAUDE.md change promoted from a `Source: autonomous` signal
- [ ] **Voice capture Layer 1 live** — iOS Shortcut → iCloud → `voice_inbox_sync.py` → inbox pipeline confirmed working end-to-end; at least one real voice signal exists in `memory/learning/signals/` with `Source: voice`
- [ ] **Remote terminal Layer 2 live** — Tailscale installed on desktop + iPhone; Blink Shell confirmed; full `claude` CLI session reachable from iPhone over Tailscale from outside home network
- [ ] **Phase 5 scoped** — `memory/work/jarvis/PRD_phase5.md` stub exists with initial behavioral-change goals defined

---

## Phase 5: Daemon-inspired behavioral change (exploration)

> **Status:** planning stub — requires Phase 4 completion and focused design session.
> **Concept:** Miessler's forthcoming "Daemon" project targets behavioral change — not system improvement but *human behavior*. Phase 5 closes the loop from AI-augmented capability to actual life change: guitar practice, health systems, financial momentum, self-discovery.
> **Key principle:** Jarvis observes patterns in TELOS goals vs. actual session/signal evidence, surfaces behavioral gaps, and proposes concrete habit/action suggestions — without being a nag or replacing human agency.

### Phase 5A — Exploration & design (do this first)

- [ ] **Define what "behavioral change" means for Jarvis** — Study Miessler's Daemon concept; write a short spec: what signals indicate behavioral gap vs. system gap? (e.g. "no guitar session logged in 14 days" vs "heartbeat threshold crossed")
- [ ] **Map TELOS goals to observable signals** — For each TELOS goal (guitar, health, financial, self-discovery), define: what does evidence of progress look like in session/signal data?
- [ ] **Design review ritual** — How does Jarvis surface behavioral proposals? (Slack digest? Session-start banner item? Weekly Telos report?) — must not be spam; must be actionable
- [ ] **PRD Phase 5** — Write `memory/work/jarvis/PRD_phase5.md` with ISC, non-goals, and architecture before building anything

### Phase 5B — Implementation (after 5A spec is solid)

- [ ] TBD — defined during Phase 5A design session

---

## Build Location Guide

**Cursor** = Fabric-pattern-format skills (structured markdown files that follow IDENTITY/STEPS/OUTPUT template). These are self-contained .md files with no Claude Code lifecycle dependencies.

**Claude Code** = Anything that hooks into Claude Code's lifecycle (hooks, settings.json, session-aware skills, memory system wiring). These need access to the running Claude Code environment.

**TBD** = Depends on external tooling decisions not yet made.
