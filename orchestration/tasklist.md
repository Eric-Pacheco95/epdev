# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-04-07 (Doc-sync: 5C marked complete, skill count 47, vacation-week overnight hardening landed)

## Priority Backlog (ordered by value/effort)

> **Filter applied:** Each item has a demand signal, serves an active goal, and is the highest-value use of the next session. Items that fail the enthusiasm filter go to Parked.

### Tier 1: Validate What's Built (Quick Wins — just confirm live runs)

> These are BUILT and running. Just check that they work. Each takes minutes, not hours. Completing these unlocks the Phase 4->5 gate criteria.

- [x] **Validate morning feed** — Running daily at 9am. Output in `memory/work/jarvis/morning_feed/`. Slack capped by design. (2026-03-29)
- [x] **Validate overnight runner** — Running daily at 4am. Branches created, quality gate + security audit passing. 2 cycles confirmed. (2026-03-29)
- [x] **Validate TELOS introspection runner** — VALIDATED 3/30: 7am run succeeded (5 artifacts, 4 contradictions, 43% coverage, exit 0). Fix from 41f1644 confirmed working. 3 runs: 3/28 pass, 3/29 fail (WinError 206), 3/30 pass post-fix.
- [x] **Validate autonomous value tracking** — VALIDATED 3/30: `acted_on` flip confirmed working. Two 3/29 entries flipped to `true` with session timestamps. Mechanism: `hook_session_start.py` keyword match on morning-feed phrases. (2026-03-30)
- [x] **Human source review ritual** — VALIDATED 3/30: Reviewed all 21 sources. Added 3 new Tier 2 (The AI Automators: YouTube, Blog, GitHub). Retired all 4 Tier 3 candidates (Simon Willison, LangChain, JustinGuitar, Cursor). Total: 24 sources. (2026-03-30)

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
- [x] **5-pre: Evaluate MCPorter for MCP→CLI** — ABSORB-IDEA. No current `claude -p` task is MCP-only; all require LLM reasoning. Slack already uses direct API. Absorbed pattern: JSON-RPC stdio wrapper if batch MCP calls emerge. Decision: `history/decisions/2026-03-31_mcporter-eval-absorb.md`. (2026-03-31)
- [x] **5-pre: Context efficiency audit** — Audit complete. All `claude -p` calls appropriately load CLAUDE.md for steering. MCP tools already deferred, memory on-demand. No changes needed. Audit doc: `memory/work/observability/context_efficiency_audit.md`. (2026-03-31)

### Tier 3: Additive Improvements (Useful but don't compound)

- [x] **3C-5: Tailscale + SSH** — COMPLETE. Terminal working via SSH + Tailscale + Blink Shell. Mobile CLI access live. (2026-03-31)
- [x] **Notion auto-write** — Auto-push to Notion wired into `/telos-report` (Jarvis Reports page) and `/telos-update` (TELOS Mirror page). (2026-03-31)
- [x] **4B: Interleaved thinking** — Already enabled by default on Opus 4.6/Sonnet 4.6 via adaptive thinking. No beta header or config needed. The `interleaved-thinking-2025-05-14` header was for older models. Tuning: `Alt+T`, `/effort`, `CLAUDE_CODE_EFFORT_LEVEL`. (2026-03-31)
- [x] **4B: Tool Search API** — Solved natively by Claude Code's deferred ToolSearch mechanism. 191 tools (41 skills + 150 MCP) load as name-only stubs; schemas fetched on demand. No custom implementation needed. (2026-03-31)
- [x] **4E: Signal retention policy** — Handled by compress_signals.py (180d gzip) + rotate_heartbeat.py (30d raw). Scheduled monthly. (2026-03-30)
- [x] **4E: FTS index validation** — Jarvis-IndexUpdate runs daily 3am. FTS resilience verified in 4E-S1. (2026-03-29)
- [x] **4E: Reporting dashboard data contract** — `tools/schemas/vitals_v1_contract.md` + updated `vitals_collector.v1.json`. (2026-03-30)

### New Skills

- [x] **`/capture-recording` skill** — Guitar recording analysis via Gemini API. SKILL.md orchestration + Python CLI (`analyze_recording.py`). Solo/band/batch modes, MUSIC.md goal loading, token tracking. 12/12 ISC items passed. PRD: `memory/work/capture-recording/PRD.md`. (2026-03-28)
- [x] **`/absorb` skill** — External content ingestion + dual-lens analysis + TELOS routing. All 5 phases complete: 29/29 ISC PASS. Poller, voice processor, session hook, autonomous enforcement all wired. PRD: `memory/work/absorb/PRD.md`. `/voice-capture` deprecated. (2026-03-30)

### Tier 3: Firecrawl Integration (Research Pipeline Enhancement)

> **Context:** Smoke test passed 2026-04-05 (4/6 PASS). Firecrawl solves JS SPA rendering gap (React apps WebFetch gets empty shells from) and Medium paywalls. Reddit explicitly blocked by Firecrawl. Direct API, not MCP (reduces context bloat). Results: `memory/work/firecrawl_smoke_results.json`

- [x] **Firecrawl API wrapper** — `tools/scripts/lib/firecrawl.py` shipped 2026-04-07. `scrape(url)` returns `ScrapeResult` dataclass (ok, markdown, content_len, elapsed_s, error, injection_hits). Lifts INJECTION_SUBSTRINGS list + ASCII-safe encode from smoke test. Timeout + RequestException + non-200 + JSON decode error paths all covered. CLI smoke: `python -m tools.scripts.lib.firecrawl <url>`. (2026-04-07)
- [x] **Update `/research` waterfall** — `.claude/skills/research/SKILL.md` Step 2.5 added with `from tools.scripts.lib.firecrawl import scrape` snippet. Fallback chain updated: tavily_extract -> Firecrawl -> WebFetch -> WebSearch. Reddit explicitly excluded (Firecrawl blocks). (2026-04-07)
- [x] **Validation** — Smoke-tested wrapper against `https://linear.app/changelog` (JS SPA): 65,570 chars extracted in 1.2s, zero injection false positives. Confirms wrapper solves WebFetch empty-shell gap. (2026-04-07)

### Morning Feed Actions (2026-04-06)

- [x] **Wire Claude Code "defer" into dispatcher (doc)** — autonomous-rules.md updated: `deferred` replaces `manual_required` as the three-state gate pattern using native PreToolUse `{"decision": "defer"}`. Full dispatcher wiring (validate_tool_use.py defer path, dispatcher resume flow, morning briefing surface) requires dedicated Phase 5C session + spike to validate `claude -p --resume` e2e. (2026-04-06)
- [x] **Supply chain audit (Axios/LiteLLM)** — CLEAN. Zero Axios (direct or transitive) in either repo. Zero LiteLLM — crypto-bot uses OpenAI SDK directly. .env files not tracked (gitignore working). No action needed. (2026-04-06)
- [x] **OpenClaw dependency check** — Grep confirmed: 0 references in .claude/, settings.json, or any code/config. Only appears in research/knowledge docs. Clean. (2026-04-06)
- [x] **scan-for-secrets pre-publish** — ABSORB-IDEA. Tool is v0.3 (48h old, pre-1.0, fails maturity gate). Core algo trivial (known-value + escaped variant search). Pattern to lift: build `secret_scanner.py` combining known-value scan + regex key patterns (~5 formats). Wire as pre-publish gate in content pipeline. (2026-04-06)

### ISC Producer (from architecture review 2026-04-06)

- [x] **Build ISC producer** — `tools/scripts/isc_producer.py` built and verified. 21 PRDs scanned in 64s. 8/8 ISC PASS. Cross-model review: 4 High findings fixed (archive exclusion, dedup hash, anti-criterion near-miss, timeout flag). Pending: Task Scheduler entry. (2026-04-06)

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
| 3B | **COMPLETE** | 0 |
| 3C | Layers 1-3 COMPLETE | Layer 4 (voice loop) deferred to Phase 6 |
| 3D | COMPLETE | 0 |
| 3E | COMPLETE | 0 |
| 4A | COMPLETE | 0 |
| 4B | **COMPLETE** | 0 |
| 4C | **COMPLETE** | 0 |
| 4D | **COMPLETE** | 0 |
| 4E | **COMPLETE** | 5/5 steps done |
| 4->5 | **GATE PASSED** | 0 |
| 5A | **COMPLETE** | 0 |
| 5B | **COMPLETE** | 0 |
| 5C | **COMPLETE** | All sub-phases done (5C-1 through 5C-5C); only "ISC template library" deferred |

## Active Projects

| Project | Status | Health | Owner | Next Action |
|---------|--------|--------|-------|-------------|
| epdev-jarvis-setup | active | green | epdev | Phase 5C COMPLETE (5C-5C deferred by design), assessing 5D readiness |
| crypto-bot | active | yellow | epdev | Paper trading → production gate — see `memory/work/crypto_trading_bot/project_state.md` |
| jarvis-app | active | green | epdev | Sprint 1+2+3 COMPLETE (app shell, vitals, drill-down, tab restructure) — see `memory/work/jarvis-app/PRD.md` |

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
- [x] **Notion auto-write** — Auto-push to Notion wired into `/telos-report` and `/telos-update` skills. (2026-03-31)
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

- [x] **3C-5: Tailscale + SSH setup** — COMPLETE. Terminal working via SSH + Tailscale + Blink. Mobile CLI access live. (2026-03-31)

#### Layer 4: Conversational Voice Loop (DEFERRED → Phase 6)

- ~~**3C-6: `jarvis_voice_server.py`**~~ **SUPERSEDED** by Slack mobile hub (3C-Slack-2). HTTP voice server no longer needed.
- ~~**3C-7: iOS Shortcut → POST to voice server**~~ **SUPERSEDED** by native Slack dictation.
- [ ] **3C-8: Whisper STT integration** — **DEFERRED to Phase 6** — native iOS dictation sufficient. Voice not current focus.
- [ ] **3C-9: ElevenLabs TTS integration** — **DEFERRED to Phase 6** — read Slack replies aloud on mobile.
- [ ] **3C-10: End-to-end voice session test** — **DEFERRED to Phase 6** — full TTS loop test.

#### Phase 3E-Slack: Slack Bot Socket Mode (PAUSED — crypto-bot rescoping)

> Full slash commands + Block Kit buttons. Paused pending crypto-bot rescope by separate agent.
> PRD to be created: `memory/work/slack_bot/PRD.md`

- [ ] Slack Bot Socket Mode setup — slash commands: `/status`, `/positions`, `/approve`, `/pause`
- [ ] Block Kit trade approval cards — Approve / Reject / Half Size buttons for crypto-bot (replaces Telegram)
- [ ] App mention: `@Jarvis summarize my week`

#### Cross-cutting

- [ ] **Voice signals tracked in heartbeat** — DEFERRED to Phase 6. Add `voice_session_count` metric to heartbeat. Revisit when voice becomes daily habit.
- [x] **Dashboard UI** — Replaced by jarvis-app project (standalone repo). Phase 3.5 vitals route will serve as the dashboard. See `memory/work/jarvis-app/PRD.md`.

### Phase 3D: Visual system of record & ideal-state workflow (COMPLETE)

> **Status:** Replaced by standalone `jarvis-app` project. PRD, research, architecture, and Phase 1 parser all complete. Remaining work tracked in `memory/work/jarvis-app/PRD.md`.
>
> **Dependency note:** Phase 3E can now proceed — the “current vs ideal” vocabulary is defined by the jarvis-app node/edge taxonomy and ISC gap model.

- [x] **Clarify requirements** — Completed via `/project-init` pipeline: `/research` → `/first-principles` → `/red-team` → `/create-prd`. Brain spec defined in `memory/work/jarvis-app/PRD.md` — nodes = TELOS/Goal/Project/Phase/PRD/ISC/Task/Skill/Signal; edges = drives/defines/decomposes-into/gap/etc. Git-markdown is source of truth; jarvis-app is read-only through Phase 3.
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
- [x] **Human source review ritual** — VALIDATED 3/30: Reviewed all 21 sources. Added 3 new Tier 2 (The AI Automators: YouTube, Blog, GitHub). Retired all 4 Tier 3 candidates. Total: 24 sources. (2026-03-30)
- [x] **Research runner** — `tools/scripts/morning_feed.py` running daily at 9am via Task Scheduler. Output validated in `memory/work/jarvis/morning_feed/2026-03-29.md`. Slack posting rate-limited by design. (2026-03-29)
- [x] **Cowork vs scheduler split** — Documented in PRD_autonomous_learning.md: overnight = Task Scheduler + claude -p (separate calls per dimension); morning feed = Task Scheduler + Python (Anthropic API direct); interactive = Claude Code session. (2026-03-28)
- [x] **Interleaved thinking for orchestration skills** — Already enabled by default on Opus 4.6 via adaptive thinking. Beta header approach obsolete. (2026-03-31)
- [x] **Tool Search API** — Solved natively by Claude Code's deferred ToolSearch. 191 tools load as name-only stubs; schemas fetched on demand. All `claude -p` jobs inherit this automatically. (2026-03-31)

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

#### Steps 1-5: ALL COMPLETE (see summary items above for details)

> Detailed breakdown archived — each step's completion is recorded in the 4E-S1 through 4E-S5 summary lines above with dates, artifact references, and gate status.

**Depends on:** Phase 4D complete (autoresearch is primary producer). Observability audit complete (2026-03-29).

---

> **Open Validations** moved to Priority Backlog Tier 1 (top of file).

## Phase 4 → Phase 5 Gate (verify before starting Phase 5)

- [x] **PAIMM AS2 verified** — Heartbeat every 60min, morning feed at 9am, autoresearch at 7am, overnight at 4am — all via Task Scheduler without human prompt. (2026-03-30)
- [x] **Autoresearch loop has run >=3 cycles** — 3 overnight dirs (2026-03-28/29/30), 2 TELOS introspection runs (2026-03-28/30). Overnight threshold met. (2026-03-30)
- [x] **Steering rules updated from autonomous signals** — Autonomous signals (`absorb-e2e-validated`, `absorbed-geo-strategy-iran-trap`) → synthesis_4 → steering rule (autonomous /absorb verification) added to CLAUDE.md. Full lineage traceable. (2026-03-30)
- [x] **Data layer operational** — 4E complete (5/5 steps): manifest tables queryable (284 signals), lineage populated (44 rows), retention scheduled (3 monthly jobs), producer health monitored, all consumers migrated to manifest queries. (2026-03-30)
- [x] **Phase 5 scoped** — `memory/work/jarvis/PRD_phase5.md` exists with mission, architecture, capability tiers (0-3), SENSE/DECIDE/ACT layers, Phase 5A-5D breakdown. (2026-03-30)

> **Moved to independent Tier 3 tasks (not Phase 5 gate):** Voice capture Layer 1, Remote terminal Layer 3 (Tailscale). These are valuable but orthogonal to autonomous execution.

---

## Phase 5: Autonomous Project Execution

> **Status:** GATE PASSED — ready to begin. PRD at `memory/work/jarvis/PRD_phase5.md`.
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

- [x] **PRD Phase 5** — `memory/work/jarvis/PRD_phase5.md` written with mission, architecture, capability tiers (0-3), SENSE/DECIDE/ACT layers, Phase 5A-5D breakdown. (2026-03-29)
- [x] **Machine-readable task backlog schema** — JSONL format: id, description, project, dependencies, isc, status, complexity, autonomous_safe. File: `orchestration/task_backlog.jsonl` (12 tasks seeded). (2026-03-31)
- [x] **Skill autonomous_safe audit** — 39 skills classified into 4 tiers (0: read-only, 1: local files, 2: gated, 3: human-required). Map at `orchestration/skill_autonomy_map.json`. 13 Tier 0, 6 Tier 1, 7 Tier 2, 13 Tier 3. (2026-03-31)
- [x] **Context profiles per task type** — 6 profiles defined (security-review, synthesis, code-improvement, research-analysis, observability, prd-creation) with always_load/optional_load and token estimates. File: `orchestration/context_profiles.json`. (2026-03-31)
- [x] **Seed initial backlog** — 12 tasks seeded in `task_backlog.jsonl` from tasklist.md, classified by tier and autonomous_safe. (2026-03-31)

### Phase 5B — Single-Repo Dispatcher + Worker (2-3 sessions)

- [x] **Shared worktree library** — `tools/scripts/lib/worktree.py` extracted from overnight_runner. Worktree create/cleanup/branch/lock logic. Used by dispatcher + overnight runner. (2026-03-31)
- [x] **Dispatcher script** — `tools/scripts/jarvis_dispatcher.py`: reads backlog, selects next task, creates worktree, invokes worker via `claude -p`, verifies ISC, notifies Slack. Lockfile mutex, task lifecycle state machine, Git Bash resolution, ISC sanitization, self-test suite (12 tests). (2026-03-31)
- [x] **Worker prompt template** — Tiered context assembly (Tier 0: ~2K tokens, Tier 1: ~4K). Skill instructions from `skill_autonomy_map.json`, context profile matching from `context_profiles.json`, goal_context injection, context file loading with truncation. 12/12 self-tests pass. (2026-03-31)
- [x] **Task Scheduler wiring** — `\Jarvis\JarvisDispatcher` via `run_dispatcher.bat`. Scheduled alongside overnight runner (staggered). 1 task/night. (2026-03-31)
- [x] **Validation** — 3 tasks from backlog executed: branches created, ISC verified, Slack notifications sent, human merges successfully (2026-04-02, gate report: history/validations/2026-04-02_5B-dispatcher-gate.md)

### Phase 5C — Unified Pipeline + Intake Convergence (3-4 sessions)

> **Vision:** All work from any source flows through one system: `source -> backlog_append() -> task_backlog.jsonl -> dispatch gate -> dispatcher -> execution -> learning`. No silos. Two gates catch bad tasks at write-time and dispatch-time. Architecture review: `memory/work/_arch-review-20260402c/`.

**Previously completed (5C Sprint 1):**
- [x] **Task gate** — `tools/scripts/task_gate.py`: routing gate for task producers. 3 deterministic checks (has ISC? Tier 0-2 skill? no arch keywords?). Pass -> backlog. Fail -> `#jarvis-decisions`. (2026-04-01)
- [x] **Heartbeat -> task generation** — Heartbeat WARN/CRIT threshold crossings auto-propose remediation tasks via `remediation_map` in `heartbeat_config.json`. Routes through task gate. (2026-04-01)
- [x] **#jarvis-decisions Slack channel** — `C0APQ4X9EAK`. Severity="decision" in `slack_notify.py`. For task gate escalations requiring Eric's input. (2026-04-01)
- [x] **Dispatcher Tier 2** — `MAX_TIER` raised to 2. Tier 2 skills (synthesize-signals, security-audit, learning-capture, self-heal, absorb) eligible for autonomous execution. (2026-04-01)
- [x] **backlog_append() library** — `tools/scripts/lib/backlog.py`: single write path for all task sources. 10 structural checks (Stage 1 gate), auto-fill 14 defaults, routine dedup, atomic write. 34 tests. (2026-04-02)
- [x] **Lightweight validation tier** — `isc_validator.py --task/--task-inline` mode: 10 structural checks for backlog tasks (vs `--prd` heavyweight 6-check ISC quality gate). (2026-04-02)

**5C-1: Two-stage quality gate convergence**
- [x] **Converge task_gate.py + backlog_append()** — Done in 5C-3: task_gate keeps routing logic, delegates writes to backlog_append(). Stale ISC allowlist removed.
- [x] **Stage 2 dispatch gate hardening** — All 3 items implemented: `_scan_task_metadata_injection()` in select_next_task (line 328), JARVIS_SESSION_TYPE assertion (line 966), settings.json + CLAUDE.md write protection in validate_tool_use.py. PreToolUse hook matcher broadened from Bash-only to all tools (2026-04-05). (2026-04-05)

**5C-2: Routines engine (first new intake source)**
- [x] **Routines config** — `orchestration/routines.json`: schedule, task template, dedup key. Day-one routines: weekly security audit, weekly synthesis, monthly steering audit
- [x] **inject_routines() dispatcher pre-step** — Before task selection, check routines for due items, inject via backlog_append() with routine_id dedup. Cron-like schedule evaluation
- [x] **Routine state tracking** — `data/routine_state.json`: last_run timestamps per routine. Prevents re-injection on every dispatch cycle

**5C-3: Heartbeat intake convergence (refactor existing source)**
- [x] **Wire heartbeat auto-propose through backlog_append()** — Refactored task_gate.py to use backlog_append() as write backend; heartbeat -> task_gate -> backlog_append chain validated (8/8 gate tests + 17/17 dispatcher tests pass)

**5C-4: Session task capture (interactive intake)**
- [x] **Session -> backlog pathway** — /backlog skill: pending_review status + Review ISC + description injection hardening. Arch-reviewed by 3 agents.

**5C-5A: Fix overnight runner (prerequisite)**
- [x] **Rate limit detection** — Detect "hit your limit" in claude -p output, abort remaining dimensions, log clearly
- [x] **Self-test state isolation** — Self-test no longer overwrites production overnight_state.json
- [x] **Validate real production run** — VALIDATED: 7 runs completed, all 6 dimensions active, 159 total kept changes (scaffolding:28, codebase_health:53, knowledge_synthesis:19, external_monitoring:26, prompt_quality:30, cross_project:3). Last run: 2026-04-05. (2026-04-05)

**5C-5B: Dispatcher budget controls (independent)**
- [x] **max_tasks_per_source_per_day** — 3 per source per day; checked via run report history before execution
- [x] **max_wall_time_per_task_s** — 900s (15 min) hard cap; replaces hardcoded 30 min timeout
- [x] **daily_aggregate_cap_s** — 2700s (45 min) total dispatcher time; checked before task selection
- [x] **Rate limit detection** — Detect "hit your limit" in claude -p output; return task to pending, don't count as failure

**5C-5C: Overnight producer interface (deferred until 3+ real production runs)**
- [x] **Overnight runner emits backlog task** — `inject_review_task()` at line 544: creates `pending_review` task via `backlog_append()` after each run with kept changes. Deduplicates by `routine_id`. 3 review tasks created (Apr 3-5). (2026-04-05, discovered already built)
- [ ] **ISC template library** — Deterministic ISC generation from structured gap output (add_tests, fix_lint, remove_dead_code, update_docs). Current: ISC generated inline per-branch, functional but not templated
- [x] **Human review gate** — Tasks created with `autonomous_safe: false` + `status: pending_review`. Security failures skip task injection entirely. (2026-04-05, discovered already built)

### Phase 5D — Hardening + Quality (2-3 sessions, data-dependent)

> **Prerequisite:** Let pipeline run organically. Collect 15+ tasks with diverse outcomes before optimizing.

- [x] **Branch lifecycle tracker** — `tools/scripts/branch_lifecycle.py`: scans `jarvis/auto-*` and `jarvis/overnight-*` branches, flags stale (>7d, not merged), reports merged (safe to delete). Heartbeat collector `stale_branches` wired with warn>0, crit>3. CLI: `--json`, `--notify` (Slack), `--self-test` (5 tests pass). (2026-04-05)
- [x] **Autonomous signal rate monitoring** — Enhanced `manifest_autonomous_signal_rate` collector with per-category and per-producer breakdown (prediction, backtest, heartbeat, overnight, dispatcher). Remediation_map entries added for both `autonomous_signal_rate` and `stale_branches`. Thresholds: warn>10/day, crit>20/day. (2026-04-05)
- [ ] **Two-layer verification (data-gated)** — Second `claude -p` review of worker output if ISC quality proves insufficient. Only build after 15+ task outcomes show ISC-pass-but-bad-quality pattern. Aron's CEO-checks-worker pattern, adapted
- [ ] **Worker prompt optimization (data-gated)** — Analyze run reports: what context did workers actually use vs ignore? Only build after 15+ runs provide calibration data
- [ ] **Multi-repo support** — Dispatcher handles epdev + crypto-bot + jarvis-app. Per-project config: repo path, context files, ISC sources (moved from 5C -- requires pipeline stability first)

### Phase 5E — Self-Correcting Pipeline (after 5D + 15 diverse task outcomes including 3+ manual_review)

> **Prerequisite:** 15+ dispatcher tasks with diverse outcomes (done, failed, manual_review, retried). Architecture review: `memory/work/_arch-review-20260403/` (3-agent convergence on design constraints).

**5E-1: Deterministic follow-on (partial-ISC retry)**
- [ ] **`generation` field in task schema** — Hard cap at 2 (parent -> G1 -> G2 -> terminal). Prevents runaway loops, scope drift, quality degradation simultaneously
- [ ] **`_emit_followon()` in dispatcher** — DECIDE function after write_backlog(), before notify_completion(). Extracts failing ISC criteria from verify_isc() results. Never derives from worker output
- [ ] **Root-source attribution** — Follow-on tasks trace budget to original producer source, not "dispatcher". Prevents budget circumvention
- [ ] **Always `pending_review`** — Follow-on tasks never enter `pending` autonomously. Max 1 follow-on per dispatch run
- [ ] **Slack notification includes follow-on task ID** — Eric knows what to review

**5E-2: Pipeline lifecycle + observability**
- [ ] **`pending_review` TTL** — 7-day TTL in archive sweep. Stale pending_review tasks escalate to Slack alert, then auto-fail
- [ ] **Branch existence validation at selection time** — If task references parent_branch, verify it exists before claiming. Expired branch -> manual_review
- [ ] **Follow-on ISC count must decrease per generation** — If G1 fails more ISC than parent, route to manual_review (evidence of scope expansion)

**5E-3: LLM-assisted follow-on (deferred within 5E)**
- [ ] **FOLLOW_UP staging gate** — Worker FOLLOW_UP lines go to `data/followon_pending/` staging file, not directly to backlog. Requires human review before promotion (CLAUDE.md data-source checklist)
- [ ] **Description injection hardening** — Unicode normalization, protected-path scan on description field, not just ISC
- [ ] **Overnight producer interface** — Moved from 5C-5C. Requires 3+ real overnight production runs + staging gate

**Phase 5 Completion Gate**
- [ ] **>=90% success rate over 14 days** — Dispatcher autonomously executes Tier 0-1 tasks. Measured after 5D is stable. 5E is not required for this gate but extends the pipeline beyond it

---

## Capability Tracks (dependency-triggered, not phase-sequenced)

> Items below activate when their dependency triggers are met, not at a specific phase. They live in `task_backlog.jsonl` as `pending_review`. This section ensures visibility so they resurface at the right time.

### Prediction Engine

> **Skill:** `/make-prediction` (v1 live, 2026-04-03). **Goal:** 50+ tracked predictions for calibration learning, then autonomous backtesting.

- [x] **Prediction review scheduled task** — `prediction_review_task.py` posts weekly Slack digest of predictions due within 30 days. Routine `prediction-weekly-review` in routines.json. Haiku model for cost efficiency. (2026-04-05)
- [x] **Prediction backtesting pipeline** — `prediction_backtest_producer.py` + `prediction_resolver.py`. 35 backtest predictions across 3 domains (10 geo, 10 market, 10 tech, 5 planning). 59 resolutions scored. Events sourced from `data/backtest_events.yaml` (35 events). Routine `prediction-backtest` in routines.json. (2026-04-05)
- [x] **Prediction calibration feedback loop** — `prediction_calibration.py` computes per-domain accuracy and overconfidence adjustments. `data/calibration.json` active with 3 domains: geo (adj +0.058, n=7), market (adj +0.061, n=9), tech (adj +0.15 clamped, n=9). 25 resolved predictions (above 20 threshold). Routine `prediction-calibration-check` in routines.json. (2026-04-05)

---

## Phase 6: Daemon-inspired behavioral change (future)

> **Status:** deferred — requires Phase 5 completion gate.
> **Concept:** Miessler's "Daemon" project targets behavioral change — not system improvement but *human behavior*. Phase 6 closes the loop from AI-augmented capability to actual life change: guitar practice, health systems, financial momentum, self-discovery. Runs ON the Phase 5 autonomous execution infrastructure.

- [ ] TBD — defined after Phase 5 completion gate passes
- [ ] **Local embedding + vector search for memory** — DEFERRED from Phase 5. Add semantic retrieval layer (nomic-embed-text + numpy/cosine, no ChromaDB) alongside grep. Triggers: file count > 400 OR 5+ documented grep retrieval failures. Research: `memory/work/local-embeddings/research_brief.md`. Architecture review: `memory/work/_arch-review-20260402b/`. Decision: premature at 126 files; grep + Claude's native semantic reasoning is sufficient at current scale

---

## Build Location Guide

**Claude Code (Claude Max)** = All implementation. Skills, hooks, parsers, scripts — everything is built in Claude Code. Cursor is retired (2026-03-27).

**jarvis-app repo** = Standalone project at `C:\Users\ericp\Github\jarvis-app`. React Flow + Next.js + TypeScript. Parser reads epdev markdown. Tracked separately in `memory/work/jarvis-app/PRD.md`.
