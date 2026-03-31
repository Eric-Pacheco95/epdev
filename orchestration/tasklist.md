# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-03-28 (First-principles reorg: priority backlog by value/effort, parked items with enthusiasm filter)

## Priority Backlog (ordered by value/effort)

> **Filter applied:** Each item has a demand signal, serves an active goal, and is the highest-value use of the next session. Items that fail the enthusiasm filter go to Parked.

### Tier 1: Validate What's Built (Quick Wins — just confirm live runs)

> These are BUILT and running. Just check that they work. Each takes minutes, not hours. Completing these unlocks the Phase 4->5 gate criteria.

- [x] **Validate morning feed** — Running daily at 9am. Output in `memory/work/jarvis/morning_feed/`. Slack capped by design. (2026-03-29)
- [x] **Validate overnight runner** — Running daily at 4am. Branches created, quality gate + security audit passing. 2 cycles confirmed. (2026-03-29)
- [x] **Validate TELOS introspection runner** — VALIDATED 3/30: 7am run succeeded (5 artifacts, 4 contradictions, 43% coverage, exit 0). Fix from 41f1644 confirmed working. 3 runs: 3/28 pass, 3/29 fail (WinError 206), 3/30 pass post-fix.
- [ ] **Validate autonomous value tracking** — Reference a morning brief in session, then check `data/autonomous_value.jsonl` for `acted_on` flip.
- [ ] **Human source review ritual** — After first validated morning feed: "What other sources? YouTube channels, blogs, GitHub repos, newsletters?" → update `sources.yaml`

### Tier 2: Complete Autonomous Loop (Multiplicative — compounds daily)

> Each item makes Jarvis smarter without you in a session. Phase 4C + 4E complete the autonomous foundation.

- [x] **4C: Notifier wrapper** — Severity routing (routine→#epdev, critical→#general), dedup (1hr hash window), daily caps (20 routine, 5 critical). All 7 callers migrated. (2026-03-28)
- [x] **4C: Heartbeat + research digests** — Heartbeat CRIT→#general, overnight failures→#general, autoresearch high-contradiction→#general. Routine traffic stays in #epdev. (2026-03-28)
- [x] **4C: Auth health collector + meta-alerting** — `auth_health` collector tests Slack token via auth.test API. Collector-failure meta-alerting injects synthetic WARN/CRIT when any collector returns null. Local fallback log at `data/auth_failures.jsonl`. (2026-03-28)
- [x] **5-pre: Observability audit** — Data flow audit complete. All producers/consumers mapped with empirical volumes. Hybrid architecture decided (files=truth, SQLite=query accelerator). Audit doc: `memory/work/observability/data_flow_audit.md`. Decision: `history/decisions/2026-03-29_data-layer-hybrid-architecture.md`. (2026-03-29)
- [x] **4E: Event rotation scheduled** — `\Jarvis\JarvisEventRotation` runs 1st of month at 3am. Summarizes + gzips old event JSONL. (2026-03-29)
- **--- 4E Revised Plan (Hybrid Architecture, sequential with gates) ---**
- [x] **4E-S1: Foundation** — Orphaned DB deleted, WAL checkpoint added to build/update, FTS index scheduled daily 3am, FTS resilience verified (content persists after file deletion), memory/session/ removed (FTS indexes native JSONL), all consumers confirmed directory-scan based. Gate: PASSED. (2026-03-29)
- [x] **4E-S2: Manifest tables** — 6 tables created (signals, lineage, producer_runs, session_costs, skill_usage, schema_version). Backfill: 284 signals, 17 lineage edges, 14 producer runs (8 producers). Build regression + schema version check passing. (2026-03-29)
- [x] **4E-S3: Wire producers** — `manifest_db.py` shared writer. `self_diagnose_wrapper.py` writes `producer_runs` for all 4 producers. `hook_stop.py` writes `session_costs` (token counts N/A — Claude Code doesn't expose in hook payload). `hook_events.py` writes `skill_usage` (sys.path bug fixed 2026-03-30). `producer_health` heartbeat collector wired. `/synthesize-signals` uses `sync_lineage.py` for JSONL→SQLite mirror. (2026-03-29, patched 2026-03-30)
- [x] **4E-S4: Retention layer** — `compress_signals.py` scheduled monthly (gzip processed signals >180d). `rotate_heartbeat.py` scheduled monthly (30d raw, monthly summary). `autonomous_signal_rate` collector live (0.29/day). `signal_volume` collector reads manifest (284 signals). `producer_health` collector wired. Gate: PASSED — all growing datasets have rotation. (2026-03-30)
- [x] **4E-S5: Consumer migration** — 3 collectors migrated to manifest DB (signal_count, signal_velocity, autonomous_signal_rate). Trend averages computed from heartbeat_history (5 metrics: isc_ratio, signal_velocity, signal_count, autonomous_signal_rate, tool_failure_rate). JSON contract documented at `tools/schemas/vitals_v1_contract.md`. Schema updated. Gate: PASSED — no consumer scans directories for data available in manifest. (2026-03-30)
- [ ] **5-pre: Evaluate MCPorter for MCP→CLI** — `steipete/mcporter` wraps MCP servers as standalone CLIs. Evaluate for: (1) moving deterministic tool calls off the LLM path (cost reduction), (2) enabling Task Scheduler jobs to call MCP tools without `claude -p`. Blocked by: 4E-S2 (need manifest data). Target: after 4E-S2.
- [ ] **5-pre: Context efficiency audit** — Review sub-agent, fresh-agent, and `claude -p` session context loading. Map what each agent type actually needs vs what it loads. Goal: minimal required context per invocation type. Blocked by: 4E-S5 + MCPorter eval. Target: after 4E complete.

### Tier 3: Additive Improvements (Useful but don't compound)

- [ ] **3C-5: Tailscale + SSH** — Mobile CLI access. Enables Phase 5 gate item (remote terminal Layer 3)
- [ ] **Notion auto-write** — Auto-push Reports/TELOS Mirror. Nice-to-have, not blocking anything
- [ ] **4B: Interleaved thinking** — Enable on `/delegation`, `/workflow-engine`, `/spawn-agent`. Improves multi-step orchestration
- [ ] **4B: Tool Search API** — Implement when skill/tool count exceeds 50. Not yet at threshold
- [ ] **4E: Signal retention policy** — Only needed after autonomous producers generate 2,000+ processed signals
- [ ] **4E: FTS index validation** — Validate `jarvis_index.py` covers all signal sources
- [ ] **4E: Reporting dashboard data contract** — Define `/vitals` + jarvis-app Phase 3.5 JSON contract
- [ ] **Voice signals in heartbeat** — `voice_session_count` metric. Low priority until voice is daily habit

### New Skills

- [x] **`/capture-recording` skill** — Guitar recording analysis via Gemini API. SKILL.md orchestration + Python CLI (`analyze_recording.py`). Solo/band/batch modes, MUSIC.md goal loading, token tracking. 12/12 ISC items passed. PRD: `memory/work/capture-recording/PRD.md`. (2026-03-28)
- [x] **`/absorb` skill** — External content ingestion + dual-lens analysis + TELOS routing. All 5 phases complete: 29/29 ISC PASS. Poller, voice processor, session hook, autonomous enforcement all wired. PRD: `memory/work/absorb/PRD.md`. `/voice-capture` deprecated. (2026-03-30)

### Parked (No demand signal within 60 days — research saved)

> Items below failed the enthusiasm filter: no specific project, no specific user, no specific ship date. Research is preserved. Revisit when a real project creates demand.

- **App development skills (iOS/Windows/.exe)** — Full research brief at `memory/work/frontend-research/research_brief.md` (35+ sources, framework comparison, deployment pipelines, UI/UX patterns). Lesson: ship first, extract skill second. Revisit when a concrete app needs App Store/Windows distribution.
- **Slack Bot Socket Mode** — Slash commands + Block Kit. No active use case beyond what current poller handles.
- **3C-8/9/10: Whisper STT, ElevenLabs TTS, voice loop** — Deferred to Phase 3F. Native iOS dictation sufficient.

## Completion Summary

| Phase | Status | Remaining |
|-------|--------|-----------|
| 1-2 | COMPLETE | 0 |
| 3A | COMPLETE | 0 |
| 3B | Near-complete | 1 (Notion auto-write) |
| 3C | Layers 1-2 complete | Layer 3 (Tailscale), Layer 4 (deferred) |
| 3D | COMPLETE | 0 |
| 3E | COMPLETE | 0 |
| 4A | COMPLETE | 0 |
| 4B | Near-complete | 3 (source review, interleaved thinking, tool search) |
| 4C | **COMPLETE** | 0 |
| 4D | **COMPLETE** | 0 |
| 4E | **COMPLETE** | 5/5 steps done |

## Active Projects

| Project | Status | Health | Owner | Next Action |
|---------|--------|--------|-------|-------------|
| epdev-jarvis-setup | active | green | epdev | Phase 3C Layer 2 + 3E ISC engine — see `orchestration/tasklist.md` Phase 3C/3E |
| crypto-bot | active | yellow | epdev | Paper trading → production gate — see `memory/work/crypto_trading_bot/project_state.md` |
| jarvis-app | active | green | epdev | Phase 4: Drill-Down Panel — see `memory/work/jarvis_brain_map/PRD.md` |

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
- [x] Create lifecycle hooks (session start, security validator, learning capture) — scripts in `tools/scripts/`, wired via `.claude/settings.json`
- [x] Create agent definitions (Architect, Engineer, SecurityAnalyst, QATester, Orchestrator)
- [x] Create defensive test baseline (injection + secret scanner — all passing)
- [x] Create Cursor integration (.cursorrules + PRD workflow)
- [x] Create EPDEV Bible (pinned to desktop)
- [x] Wire hooks into .claude/settings.json
- [x] Install Fabric CLI (installed via winget v1.4.441)
- [x] Create self-heal test baseline
- [x] Initial git commit
- [x] Split TELOS into individual identity documents (19 files in memory/work/telos/)

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

- [x] **Notion (MCP)** — Jarvis Brain structure created (Inbox, Journal, Goals & Growth, Ideas, Music, Jarvis Reports, TELOS Mirror). Page registry at `memory/work/notion_brain.md`. Session-start hook reads Notion on load.
- [ ] **Notion auto-write** — Auto-push Reports/TELOS Mirror to Notion (split from MCP setup; was "pending" inside checked item since Phase 3E)
- [x] **Slack (MCP)** — `#epdev` routine traffic via ClaudeActivities app confirmed working; stop hook posts session-end summaries. Full MCP read/write integration deferred — current posting flow meets needs.
- [x] **Calendar (MCP)** — `@cocal/google-calendar-mcp` working. OAuth via `gcp-oauth.keys.json`. 3 calendars loading (primary, Family, Holidays). Validated 2026-03-27.
- [x] **Gmail (MCP)** — `@gongrzhe/server-gmail-autoauth-mcp` working. Web app OAuth client (separate from calendar Desktop client). Credentials at `~/.gmail-mcp/credentials.json`. Scopes: `gmail.modify` + `gmail.settings.basic`. Validated 2026-03-27. **Note**: requires new session to load tools.
- ~~**ntfy**~~ **RETIRED** — All notifications routed to Slack. Scripts (`ntfy_notify.py`, `hook_notification.py`) remain but are inactive. Decision: 2026-03-27.
- [x] **Observability Phase 1** — `hook_events.py` captures all PostToolUse events to `history/events/YYYY-MM-DD.jsonl`. Research brief at `memory/work/observability/research_brief.md`. Phase 2 (Langfuse) deferred to Phase 4+.

### Phase 3C: Voice & Mobile Interface

> **PRD / ISC:** `memory/work/jarvis/PRD_voice_mobile.md`
> **Ideal state:** Eric can speak an idea on his iPhone and it lands in Jarvis's memory pipeline within minutes. He can also reach a full Jarvis terminal session from mobile. Voice sessions produce signals identical in quality to chat sessions.
>
> **Architecture updated 2026-03-27:** Slack replaces custom voice server as the mobile hub.
> New layers:
> - **Layer 1 (capture):** iPhone voice → transcript → inbox → `/voice-capture` → signals ✅
> - **Layer 2 (Slack mobile hub):** Dictate/type to `#jarvis-inbox` → Slack poller → `claude -p` → reply in thread
> - **Layer 3 (remote CLI fallback):** Tailscale + SSH → full Claude Code session on desktop
> - **Layer 4 (conversational loop):** ElevenLabs TTS — deferred to Phase 3F
>
> **PRD:** `memory/work/slack_mobile_hub/PRD.md`

#### Layer 1: Voice Capture (COMPLETE)

- [x] **3C-1: Inbox structure** — Create `memory/work/inbox/voice/` and `memory/work/inbox/voice/processed/`; document format in PRD
- [x] **3C-2: `/voice-capture` skill** — New Claude Code skill: reads Notion Inbox via MCP, extracts signals with `Source: voice`, queues TELOS-relevant content for `/telos-update`
- [x] **3C-3: Voice capture transport** — **Architecture change**: Notion app (iPhone) → built-in voice transcription → Jarvis Brain Inbox page → Jarvis reads via Notion MCP. iCloud and OneDrive no longer required. `voice_inbox_sync.py` archived (no longer needed for Layer 1). Notion Inbox page ID: `32fbf5ae-a9e3-8198-9975-cbc6293c8690`.
- [x] **3C-4: Register skill + session hook** — Add `/voice-capture` to session-start banner; `/voice-capture` now reads from Notion Inbox via MCP

#### Layer 2: Slack Mobile Hub (ACTIVE — supersedes 3C-6/3C-7)

- [x] **3C-Slack-1: Channel setup** — Channels created, bot invited, all 4 channel IDs + SLACK_BOT_TOKEN added to epdev `.env`. Scope fix applied (channels:history + reinstall).
- [x] **3C-Slack-2: `tools/scripts/slack_poller.py`** — Built. Polls `#jarvis-inbox` every 60s; runs `claude -p` from repo root (CLAUDE.md context auto-loads); replies in thread. State in `data/slack_poller_state.json`.
- [x] **3C-Slack-3: `tools/scripts/slack_voice_processor.py`** — Built. Polls `#jarvis-voice` every 60s; runs voice-capture prompt headlessly; writes signals to `memory/learning/signals/`; posts confirmation in thread.
- [x] **3C-Slack-4: Heartbeat → `#epdev`** — Already operational (`jarvis_heartbeat.py` posts to #epdev via SLACK_BOT_TOKEN).
- [x] **3C-Slack-5: `tools/start_jarvis.bat`** — Built. Launches poller + voice processor in separate CMD windows; runs heartbeat once on startup.
- [x] **3C-Slack-6: End-to-end test** — Validated 2026-03-27: iPhone dictation → `#jarvis-voice` → poller detected → Jarvis replied in thread. Gap found: `claude -p` sessions are stateless per message (steering rule added). Voice signal produced.

#### Layer 3: Remote CLI Fallback

- [ ] **3C-5: Tailscale + SSH setup** — Install Tailscale on desktop + iPhone; install Blink Shell (iOS); confirm full `claude` CLI session from iPhone over Tailscale. Document in `docs/EPDEV_JARVIS_BIBLE.md`.

#### Layer 4: Conversational Voice Loop (DEFERRED → Phase 3F)

- ~~**3C-6: `jarvis_voice_server.py`**~~ **SUPERSEDED** by Slack mobile hub (3C-Slack-2). HTTP voice server no longer needed.
- ~~**3C-7: iOS Shortcut → POST to voice server**~~ **SUPERSEDED** by native Slack dictation.
- [ ] **3C-8: Whisper STT integration** — **DEFERRED to Phase 3F** — native iOS dictation sufficient for Phase 1.
- [ ] **3C-9: ElevenLabs TTS integration** — **DEFERRED to Phase 3F** — read Slack replies on mobile.
- [ ] **3C-10: End-to-end voice session test** — **DEFERRED to Phase 3F** — reframed as full TTS loop test.

#### Phase 3E-Slack: Slack Bot Socket Mode (FUTURE)

> Full slash commands + Block Kit buttons. Specced after Phase 3D session.
> PRD to be created: `memory/work/slack_bot/PRD.md`

- [ ] Slack Bot Socket Mode setup — slash commands: `/status`, `/positions`, `/approve`, `/pause`
- [ ] Block Kit trade approval cards — Approve / Reject / Half Size buttons for crypto-bot (replaces Telegram)
- [ ] App mention: `@Jarvis summarize my week`

#### Cross-cutting

- [ ] **Voice signals tracked in heartbeat** — Add `voice_session_count` metric to heartbeat; alert in `#epdev` when no voice sessions in 7 days (behavioral gap signal for Phase 5)
- [x] **Dashboard UI** — Replaced by jarvis-app project (standalone repo). Phase 3.5 vitals route will serve as the dashboard. See `memory/work/jarvis_brain_map/PRD.md`.

### Phase 3D: Visual system of record & ideal-state workflow (COMPLETE)

> **Status:** Replaced by standalone `jarvis-app` project. PRD, research, architecture, and Phase 1 parser all complete. Remaining work tracked in `memory/work/jarvis_brain_map/PRD.md`.
>
> **Dependency note:** Phase 3E can now proceed — the “current vs ideal” vocabulary is defined by the jarvis-app node/edge taxonomy and ISC gap model.

- [x] **Clarify requirements** — Completed via `/project-init` pipeline: `/research` → `/first-principles` → `/red-team` → `/create-prd`. Brain spec defined in `memory/work/jarvis_brain_map/PRD.md` — nodes = TELOS/Goal/Project/Phase/PRD/ISC/Task/Skill/Signal; edges = drives/defines/decomposes-into/gap/etc. Git-markdown is source of truth; jarvis-app is read-only through Phase 3.
- [x] **Survey tooling** — React Flow + Next.js + dagre chosen. Research brief at `memory/work/jarvis_brain_map/research_brief.md`. Compared Obsidian, Mermaid, custom dashboard. Decision: standalone `jarvis-app` repo at `C:\Users\ericp\Github\jarvis-app`.
- [x] **Current vs ideal workflow** — **REOPENED then COMPLETED 2026-03-27**: Original ISC gap model was insufficient. Proper workflow spec now written from Eric's direct input at `memory/work/jarvis/3D_workflow_spec.md`. Covers: actual session patterns, ADHD-driven branching, mobile gap, life coach vision, operator familiarity gap (#1 pain point), measurement vocabulary beyond ISC checkboxes, and downstream requirements for 4D/5.
- [x] **Claude Code analysis session** — Full repo scan + analysis done 2026-03-27. Parser expansion roadmap defined (Phase 2.5). Vitals dashboard scoped (Phase 3.5). Cross-project dependency mapped: jarvis-app 3.5 depends on epdev 3E.

### Phase 3E: ISC engine & scheduled heartbeat

> **Parallel with 3C:** Layers 2+3 of 3C (Tailscale, voice server, STT/TTS) are independent of 3E. Build whichever has energy — they don't block each other. 3D is now complete (jarvis-app), so 3E can proceed.
>
> **Intent:** A **time-driven VERIFY** loop—Miessler-style **current state** as measurable data points, compared to **PRD ISC**, with **gaps** flowing into **learning** (signals/failures), not only when you are in a chat session.
>
> **Example:** Every 30 minutes (configurable) a **heartbeat** job runs collectors (tests passing, defensive suite, file counts, hook self-check, optional health probes), scores each mapped **ISC** or “slowly improve” feature dimension, and **emits** structured notes when gaps or regressions cross thresholds.

- [x] **ISC engine PRD** — `memory/work/isce/PRD.md` — 25 ISCs across 5 phases, 6 resolved decisions, config-driven architecture. Completed 2026-03-27.
- [x] **Metric collectors** — `tools/scripts/collectors/core.py` — 19 collectors: file_count, velocity, checkbox, PRD ISC, query_events, recency, dir_count, disk_usage, hook_output_size, derived. All passing on live epdev. Completed 2026-03-27.
- [x] **`heartbeat` runner** — `tools/scripts/jarvis_heartbeat.py` — Config-driven, 19 collectors, diff engine, auto-signal writing, modular alert routing, backward-compatible snapshot. Completed 2026-03-27.
- [x] **Scheduler** — JarvisHeartbeat in Task Scheduler every 60 min. `rotate_events.py` wired into `run_heartbeat.bat`. Troubleshooting section added to BIBLE. Completed 2026-03-28.
- [x] **Gap → learning pipeline** — Auto-signal writing on WARN/CRIT threshold crossings. Severity-scaled ratings (INFO=4, WARN=6, CRIT=8). Cooldown (60 min per metric). 3 auto-signals produced on first run. Completed 2026-03-27.
- [x] **Security & safety** — Path traversal prevention via `_resolve_path` validation. Metric name sanitization for filenames. No secrets in output (verified). Alert daily caps. `/review-code` passed. Completed 2026-03-27.
- [x] **Optional integrations** — Slack + ntfy alert routing built and config-driven. `rotate_events.py` for storage rotation. Completed 2026-03-27.
- [x] **AI Steering Rules cadence** — Ritual established: run `/update-steering-rules` after each `/synthesize-signals` pass. Dynamic synthesis threshold replaces static count (15 hard ceiling, 8+24h, 5+72h tiers). 5 synthesis runs + 5 steering rule updates completed 2026-03-27. Decision logged.
- [x] **Agent-based hooks** — Validators already Python (`validate_tool_use.py` with 26 rules, `secret_scanner.py`). No shell scripts remain. Full coverage confirmed 2026-03-28.
- [x] **`/vitals` skill (3E capstone)** — `.claude/skills/vitals/SKILL.md` — Runs heartbeat, reads snapshot, presents ASCII-safe dashboard with ISC ratio, signal velocity, sessions/day, storage budget, missing skill detection. Completed 2026-03-27.
- [x] **[ISC 8/10] Context budget as vitals metric** — `context_budget_proxy` collector measures hook output char count (1,692 chars current). Threshold: warn_above 3,000, crit_above 5,000. Tracked in heartbeat snapshot. Completed 2026-03-27. Remaining: MCP schema overhead estimate, per-session burn rate (needs API usage headers).

**Depends on:** Phase 2 maturity (signals/synthesis patterns), Phase 3D “current vs ideal” spec (shared vocabulary for gaps). **Build in:** mostly **Claude Code/Python** + OS scheduler; Claude Code sessions **review** trends and promote steering rules. **Feeds into:** jarvis-app Phase 3.5 vitals dashboard.

---

---

## Phase 3E → Phase 4 Gate (must pass before starting Phase 4A)

> **This gate protects Phase 4 from building on an empty foundation.** Phase 4 autoresearch iterates over accumulated signals and session history — if neither exists, the loop has nothing to improve on.

- [x] **Heartbeat running** — ISC engine heartbeat fully operational: 19 collectors, diff engine, auto-signal writing, alert routing. 4+ snapshots produced. Task Scheduler wired (Phase 4A). Validated 2026-03-27.
- [x] **Learning loop active** — 97+ signals captured (10 raw + 87 processed), well past >=5 threshold. Validated 2026-03-27.
- [x] **At least one synthesis run** — 5 synthesis docs in `memory/learning/synthesis/`. Last: `2026-03-27_synthesis.md`.
- [x] **AI Steering Rules updated once** — Multiple steering rule updates merged into CLAUDE.md (MCP transport, hook paths, crypto-bot rules, etc.). Validated 2026-03-27.
- [x] **PAIMM AS1 verified** — Session-start hook loads TELOS status, active projects, signal counts, skill registry, recent security events. Confirmed across 4+ sessions 2026-03-27.

---

## Phase 4: Autonomous self-improvement (background Jarvis)

> **PRD / ISC:** `memory/work/jarvis/PRD.md` — **state:** `memory/work/jarvis/STATE.md`  
> **Intent:** Jarvis **self-improves** via automation that does **not** depend on human chat sessions: measure progress toward ideal state, harvest **curated** external patterns (web, GitHub, YouTube, Claude docs), run **[Karpathy-style bounded autoresearch](https://github.com/karpathy/autoresearch)** over **TELOS + learning signals + session history** (writes proposals only — see PRD §4D), and **notify Slack** by importance (`memory/work/slack-routing.md`). Human sessions approve merges, secrets, and TELOS changes.

### Phase 4A — Ideal-state loop & heartbeat (extends 3E)

- [x] **ISC mapping** — `isc_ref` field added to collector config + auto-signal frontmatter. PRD ISC lines mapped: 4 measurable (collectors), 4 architectural (code-enforced). Completed 2026-03-27.
- [x] **Gap → learning** — Auto-signals now include `isc_ref` in frontmatter + body linking to PRD ISC. Dedup/cooldown verified (60 min per metric). Dry-run test passed. Completed 2026-03-27.
- [x] **Windows Task Scheduler** — `JarvisHeartbeat` task runs every 60 min via `run_heartbeat.bat`. Absolute Python path, PowerShell date for logs, env vars inherited. Documented in bible. Completed 2026-03-27.
- [x] **Subagent tool scoping** — Layer 5 policy added to `security/constitutional-rules.md`: 7 roles with explicit MCP tool + file access boundaries. Non-negotiable rules: no TELOS writes, no git push, no #general without severity check. Completed 2026-03-27.

### Phase 4B — Autonomous research & pattern harvesting

- [x] **Source allow-list** — `memory/work/jarvis/sources.yaml` created with 6 Tier 1, 6 Tier 2, 12 Tier 3 sources. Companion rationale doc at `sources_rationale.md`. (2026-03-28)
- [ ] **Human source review ritual** — After first research run, ask Eric: "What other sources should be added? (YouTube channels, blogs, GitHub repos, newsletters)" — capture answers in sources.yaml and `history/decisions/`
- [x] **Research runner** — `tools/scripts/morning_feed.py` running daily at 9am via Task Scheduler. Output validated in `memory/work/jarvis/morning_feed/2026-03-29.md`. Slack posting rate-limited by design. (2026-03-29)
- [x] **Cowork vs scheduler split** — Documented in PRD_autonomous_learning.md: overnight = Task Scheduler + claude -p (separate calls per dimension); morning feed = Task Scheduler + Python (Anthropic API direct); interactive = Claude Code session. (2026-03-28)
- [ ] **Interleaved thinking for orchestration skills** — Enable interleaved thinking on `/delegation`, `/workflow-engine`, and `/spawn-agent`: think→tool→think→tool pattern dramatically improves multi-step research and agent composition. Configure via `interleaved-thinking-2025-05-14` header on Claude API calls inside these skills. Do alongside research runner — this is where it pays off most.
- [ ] **Tool Search API** — When skill/tool count exceeds 50, implement Tool Search to prevent token explosion in orchestration loops. Evaluate as part of research runner architecture — autonomous research will eventually need to query 100+ tools by description without loading all schemas upfront.

### Phase 4C — Slack notifications by severity (COMPLETE)

- [x] **Notifier wrapper** — `tools/scripts/slack_notify.py`: severity routing (routine→#epdev, critical→#general), dedup (1hr hash window), daily caps (20 routine, 5 critical). All 7 callers migrated. (2026-03-28)
- [x] **Heartbeat + research digests** — Heartbeat CRIT→#general, overnight failures→#general, autoresearch high-contradiction→#general. Routine traffic stays in #epdev. (2026-03-28)
- [x] **Auth health collector + meta-alerting** — `auth_health` collector tests Slack token via auth.test API. Collector-failure meta-alerting injects synthetic WARN/CRIT when any collector returns null. Local fallback log at `data/auth_failures.jsonl` (created on-demand when auth fails, not pre-existing). (2026-03-28)

### Phase 4D — Capstone: internal autoresearch (Karpathy-inspired)

> Pattern from [karpathy/autoresearch](https://github.com/karpathy/autoresearch): human-steered **program**, bounded runs, **one writable surface** for the agent (here: review tree only — not live TELOS). Full spec: `memory/work/jarvis/PRD.md` §4D.
>
> **Two runners:** `overnight_runner.py` iterates on code quality (6 dimensions). `jarvis_autoresearch.py` iterates on TELOS/signal alignment (the actual PRD 4D capstone).

#### Code improvement runner (overnight_runner.py)

- [x] **`autoresearch_program.md`** — 6 code-improvement dimensions (scaffolding, codebase_health, knowledge_synthesis, external_monitoring, prompt_quality, cross_project) with metric/guard/scope/iterations. (2026-03-28)
- [x] **Overnight runner** — `tools/scripts/overnight_runner.py` + `run_overnight_jarvis.bat`. Task Scheduler `\Jarvis\JarvisOvernight` at 4am daily, 2hr timeout. claude -p per dimension, Slack posting, state tracking. Self-test 9/9. (2026-03-28)
- [x] **Overnight merge path** — All work on `jarvis/overnight-YYYY-MM-DD` branches. Eric merges in morning session. `/vitals` flags unmerged branches > 7 days. (2026-03-28)

#### TELOS introspection runner (jarvis_autoresearch.py) -- PRD 4D capstone

- [x] **`autoresearch_program.md` TELOS section** — Updated with introspection mission, "better understanding" definition, read scope table, 6 metrics, constraints, human merge path. (2026-03-28)
- [x] **Review tree** — `memory/work/jarvis/autoresearch/` with README documenting both runners' output formats (`overnight-*/` and `run-*/`). (2026-03-28)
- [x] **Read scope** — Documented in program.md: TELOS (all 19), synthesis (5 recent), signals (14d), raw (7d), failures (14d), sessions (7d). All read-only, time-bounded. (2026-03-28)
- [x] **TELOS introspection runner** — `tools/scripts/jarvis_autoresearch.py` (Anthropic API direct). Reads TELOS + signals + synthesis, produces metrics.json + report.md + proposals.md + contradictions.md + coverage.md. 19/19 self-tests + 27/27 defensive tests passing. `/review-code` passed. (2026-03-28)
- [x] **Metrics per run** — JSON: contradiction_count, open_questions, coverage_score, staleness_flags, insight_count, proposal_count. Written to `run-YYYY-MM-DD/metrics.json`. (2026-03-28)
- [x] **Integration** — Autonomous signals with `Source: autonomous, Category: introspection` when thresholds crossed (>=3 contradictions OR <50% coverage). Slack to `#epdev`. Dedup counter for signals. (2026-03-28)
- [x] **Human merge path** — Proposals to `run-YYYY-MM-DD/proposals.md`. Eric reviews via `/telos-update` or manual edit. `/vitals` updated to track unreviewed runs > 7 days. (2026-03-28)
- [x] **Scheduler** — `\Jarvis\JarvisAutoresearch` Task Scheduler at 7am daily via `run_autoresearch.bat`. Runs after overnight (4am), before morning feed (9am). (2026-03-28)
- [x] **TELOS introspection live run** — `run-2026-03-28/` has all 5 artifacts (metrics.json, report.md, proposals.md, contradictions.md, coverage.md). 3/29 run failed due to PATH bug (separate fix). (2026-03-29)

**Depends on:** Phase 4A-4C foundations; TELOS and learning layout stable enough to iterate; **Phase 3D "current vs ideal" spec must exist** before writing `autoresearch_program.md`. **Decision:** `history/decisions/2026-03-27_phase4-autonomous-self-improvement.md` (update with 4D)

---

### Phase 4E — Data management & reporting layer (Hybrid Architecture)

> **Architecture decision (2026-03-29):** Hybrid — files remain source of truth, extend existing `jarvis_index.db` (SQLite FTS5) as read-optimized query/lineage/manifest layer. Rebuildable from files at any time. See `history/decisions/2026-03-29_data-layer-hybrid-architecture.md`.
>
> **Informed by:** `/first-principles` analysis (9 core assumptions challenged), `/find-logical-fallacies` audit (9 issues in original plan), empirical data exploration (92 signals/day, 1 MB/day events, 1 MB/day heartbeat history). Full audit: `memory/work/observability/data_flow_audit.md`.
>
> **Build order is sequential with gates.** Original plan assumed independent items — fallacy analysis proved they have forced dependencies: FTS verification > lineage > retention > monitoring.

#### Step 1: Foundation (gate: FTS resilience test passes)
- [ ] Delete orphaned `data/jarvis_events.db` (0 bytes, created 2026-03-28)
- [ ] Enable WAL mode on `jarvis_index.db` (`PRAGMA journal_mode=WAL`) — prevents lock contention
- [ ] Schedule `jarvis_index.py update` as daily Task Scheduler job (3am)
- [ ] FTS resilience test: delete one processed signal, query index for its content, confirm retention
- [x] Event rotation scheduled — `\Jarvis\JarvisEventRotation` runs 1st of month at 3am (2026-03-29)

#### Step 2: Manifest tables (gate: manifest queryable with backfilled data)
- [ ] Add `signals` metadata table: `(id, filename, source, category, date, processed, synthesis_id, compressed)`
- [ ] Add `lineage` table: `(signal_id, synthesis_id, date)`
- [ ] Add `producer_runs` table: `(producer, run_date, status, artifact_count, log_path)`
- [ ] Backfill signal metadata from existing 276+ signal files (one-time migration)

#### Step 3: Wire producers (gate: lineage populated after next synthesis run)
- [ ] `/synthesize-signals` writes lineage rows after processing
- [ ] Heartbeat, overnight, autoresearch, morning_feed write `producer_runs` row on completion
- [ ] Add `producer_health` heartbeat collector (queries producer_runs for stale/failed runs)

#### Step 4: Retention layer (gate: no unbounded datasets remain)
- [ ] Compress-in-place for processed signals (gzip after synthesis, retain 180 days for Phase 5)
- [ ] Heartbeat history rotation (30 days raw, monthly summary JSON, delete >180 days)
- [ ] `autonomous_signal_rate` collector — alert if Source:autonomous signals exceed daily cap
- [ ] `signal_volume` collector reads manifest table instead of directory scan

#### Step 5: Consumer migration (gate: no consumer scans directories for manifest-available data)
- [ ] Migrate heartbeat file_count/velocity collectors to manifest table queries
- [ ] Pre-aggregate event metrics (move query_events.py patterns into manifest or summary table)
- [ ] Heartbeat trend detection — 3-5 run moving average from heartbeat_history
- [ ] Define `/vitals` + jarvis-app JSON data contract against manifest tables

**Depends on:** Phase 4D complete (autoresearch is primary producer). Observability audit complete (2026-03-29).

---

> **Open Validations** moved to Priority Backlog Tier 1 (top of file).

## Phase 4 → Phase 5 Gate (verify before starting Phase 5)

- [ ] **PAIMM AS2 verified** — Jarvis is proactive: heartbeat runs without human prompt, background research produces signals, Slack digests fire on cadence
- [ ] **Autoresearch loop has run >=3 cycles** — `memory/work/jarvis/autoresearch/` contains >=3 `run-YYYY-MM-DD/` directories with `metrics.json`; overnight runner has >=3 `overnight-YYYY-MM-DD/` directories
- [ ] **Steering rules updated from autonomous signals** — at least one CLAUDE.md change promoted from a `Source: autonomous` signal
- [ ] **Data layer operational** — 4E hybrid architecture complete: manifest tables in jarvis_index.db queryable, lineage populated after synthesis, retention compressing (not deleting), producer health monitored, no unbounded datasets
- [ ] **Phase 5 scoped** — `memory/work/jarvis/PRD_phase5.md` exists with autonomous execution ISC, capability tiers, and architecture defined

> **Moved to independent Tier 3 tasks (not Phase 5 gate):** Voice capture Layer 1, Remote terminal Layer 3 (Tailscale). These are valuable but orthogonal to autonomous execution.

---

## Phase 5: Autonomous Project Execution

> **Status:** design phase — PRD in progress.
> **Concept:** Jarvis autonomously picks tasks from a structured backlog, executes them in isolated git worktrees via `claude -p`, verifies against ISC, and presents ready-to-merge branches. Cross-project awareness (epdev, crypto-bot, jarvis-app). No new external dependencies — skill-first single-brain architecture using Task Scheduler + worktrees + existing skills.
> **Inspiration:** Aron Prins / Paperclip AI playbook patterns, translated for single-operator skill-first architecture. Research brief: `memory/work/aron-prins-research/research_brief.md`
> **Key principle:** Three-layer SENSE/DECIDE/ACT. Dispatcher (DECIDE) is the hard part — 60% of implementation effort. Workers run in worktrees, never touch main tree, never push.

### Capability Tiers (ship incrementally)

| Tier | Scope | Risk | Target Phase |
|------|-------|------|-------------|
| Tier 0 | Read-only analysis (synthesize, audit, review) | None | 5A |
| Tier 1 | Reversible code changes (ISC-verifiable, single-scope) | Low — git revert | 5B |
| Tier 2 | Multi-skill chains (research -> PRD -> implement) | Medium — intermediate state | 5C |
| Tier 3 | External side effects (Slack, Notion, APIs) | High — not reversible | Phase 6+ or manual-only |

### Phase 5A — Design + Task Source (1-2 sessions)

- [ ] **PRD Phase 5** — Write `memory/work/jarvis/PRD_phase5.md` with ISC, non-goals, capability tiers, architecture
- [ ] **Machine-readable task backlog schema** — JSONL format: id, description, project, dependencies, isc, status, complexity, autonomous_safe. File: `orchestration/task_backlog.jsonl`
- [ ] **Skill autonomous_safe audit** — Classify every skill: safe for unattended `claude -p` execution vs. requires human-in-loop. Add `autonomous_safe` field to skill metadata
- [ ] **Context profiles per task type** — Define minimal context each worker invocation needs (vs. loading full CLAUDE.md). Measure current `claude -p` context costs
- [ ] **Seed initial backlog** — Curate 10-15 tasks from tasklist.md that are safe for Tier 0-1 autonomous execution

### Phase 5B — Single-Repo Dispatcher + Worker (2-3 sessions)

- [ ] **Shared worktree library** — Extract worktree create/cleanup/branch logic from `overnight_runner.py` into `tools/scripts/lib/worktree.py`
- [ ] **Dispatcher script** — `tools/scripts/jarvis_dispatcher.py`: reads backlog, selects next task (priority + dependencies + safety), creates worktree, invokes worker, verifies, notifies. Includes: lockfile mutex, task lifecycle state machine (pending -> claimed -> executing -> verifying -> done/failed), cleanup for partial failures
- [ ] **Worker prompt template** — Task-specific prompt generation: loads minimal context profile, task description, ISC criteria, relevant project files. Uses stdin pattern (no WinError 206)
- [ ] **Task Scheduler wiring** — `\Jarvis\JarvisDispatcher` scheduled alongside overnight runner (staggered). Initially 1 task/night
- [ ] **Validation** — 3 tasks from backlog executed: branches created, ISC verified, Slack notifications sent, human merges successfully

### Phase 5C — Cross-Project + Routines (2-3 sessions)

- [ ] **Multi-repo support** — Dispatcher handles epdev + crypto-bot + jarvis-app. Per-project config: repo path, context files, ISC sources
- [ ] **Routines engine** — Recurring tasks that re-enter backlog on schedule (weekly security audit, monthly steering review). Config-driven, not hardcoded
- [ ] **Heartbeat -> task generation** — When ISC gaps detected by heartbeat, dispatcher can propose new tasks for human approval before execution
- [ ] **Budget controls** — Max tasks/day, max `claude -p` time per task, daily aggregate time cap

### Phase 5D — Hardening + Quality (1-2 sessions)

- [ ] **Two-layer verification (optional)** — Second `claude -p` review of worker output if Tier 1 self-verification quality is insufficient. Aron's CEO-checks-worker pattern, adapted
- [ ] **Worker prompt optimization** — Based on observed context efficiency and quality data
- [ ] **Autonomous signal rate monitoring** — 4E item, now critical for Phase 5 safety
- [ ] **Phase 5 completion gate** — Dispatcher autonomously executes Tier 0-1 tasks with >=90% success rate over 14 days

---

## Phase 6: Daemon-inspired behavioral change (future)

> **Status:** deferred — requires Phase 5 autonomous execution as foundation.
> **Concept:** Miessler's "Daemon" project targets behavioral change — not system improvement but *human behavior*. Phase 6 closes the loop from AI-augmented capability to actual life change: guitar practice, health systems, financial momentum, self-discovery. Runs ON the Phase 5 autonomous execution infrastructure.

- [ ] TBD — defined after Phase 5 completion gate passes

---

## Build Location Guide

**Claude Code (Claude Max)** = All implementation. Skills, hooks, parsers, scripts — everything is built in Claude Code. Cursor is retired (2026-03-27).

**jarvis-app repo** = Standalone project at `C:\Users\ericp\Github\jarvis-app`. React Flow + Next.js + TypeScript. Parser reads epdev markdown. Tracked separately in `memory/work/jarvis_brain_map/PRD.md`.
