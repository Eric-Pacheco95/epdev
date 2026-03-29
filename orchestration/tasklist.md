# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-03-28 (First-principles reorg: priority backlog by value/effort, parked items with enthusiasm filter)

## Priority Backlog (ordered by value/effort)

> **Filter applied:** Each item has a demand signal, serves an active goal, and is the highest-value use of the next session. Items that fail the enthusiasm filter go to Parked.

### Tier 1: Validate What's Built (Quick Wins — just confirm live runs)

> These are BUILT and running. Just check that they work. Each takes minutes, not hours. Completing these unlocks the Phase 4->5 gate criteria.

- [ ] **Validate morning feed** — Check `#epdev` Slack after 9am for vitals + proposals + overnight summary. If present, mark Phase 4B Research runner [x]. If absent, check `data/logs/` and `/self-heal`.
- [ ] **Validate overnight runner** — Check `data/logs/overnight_*.log` + `#epdev` Slack after 4am. Confirm dimension execution, branch creation, Slack summary. If validated, 3 overnight cycles -> Phase 5 gate item checked.
- [ ] **Validate TELOS introspection runner** — Check `data/logs/autoresearch_*.log` + `memory/work/jarvis/autoresearch/run-YYYY-MM-DD/` after 7am. Confirm metrics.json, report.md, proposals.md artifacts. Parent: Phase 4D TELOS introspection runner.
- [ ] **Validate autonomous value tracking** — Reference a morning brief in session, then check `data/autonomous_value.jsonl` for `acted_on` flip.
- [ ] **Human source review ritual** — After first validated morning feed: "What other sources? YouTube channels, blogs, GitHub repos, newsletters?" → update `sources.yaml`

### Tier 2: Complete Autonomous Loop (Multiplicative — compounds daily)

> Each item makes Jarvis smarter without you in a session. Phase 4C + 4E complete the autonomous foundation.

- [x] **4C: Notifier wrapper** — Severity routing (routine→#epdev, critical→#general), dedup (1hr hash window), daily caps (20 routine, 5 critical). All 7 callers migrated. (2026-03-28)
- [x] **4C: Heartbeat + research digests** — Heartbeat CRIT→#general, overnight failures→#general, autoresearch high-contradiction→#general. Routine traffic stays in #epdev. (2026-03-28)
- [x] **4C: Auth health collector + meta-alerting** — `auth_health` collector tests Slack token via auth.test API. Collector-failure meta-alerting injects synthetic WARN/CRIT when any collector returns null. Local fallback log at `data/auth_failures.jsonl`. (2026-03-28)
- [ ] **4E: Signal lineage index** — After `/synthesize-signals`, append to `signal_lineage.jsonl`. Solves signal→synthesis reverse-lookup
- [x] **4E: Event rotation scheduled** — `\Jarvis\JarvisEventRotation` runs 1st of month at 3am. Summarizes + gzips old event JSONL. (2026-03-29)
- [ ] **4E: Autonomous signal volume monitoring** — `autonomous_signal_rate` collector. Prevents runaway research loops
- [ ] **4E: Heartbeat trend detection** — 3-5 run moving average in diff engine to catch slow degradation invisible to single-snapshot thresholds
- [ ] **4E: Heartbeat history rotation** — heartbeat_history.jsonl grows unbounded; wire retention config (raw_days=90) into actual code
- [ ] **4E: jarvis_index.py heartbeat path fix** — FTS expects `data/logs/` but heartbeat writes to `memory/work/isce/`; fix path constant
- [ ] **4E: Delta thresholds in config** — Support `delta_above`/`delta_below` in threshold dict for ramp detection

### Tier 3: Additive Improvements (Useful but don't compound)

- [ ] **3C-5: Tailscale + SSH** — Mobile CLI access. Enables Phase 5 gate item (remote terminal Layer 3)
- [ ] **Notion auto-write** — Auto-push Reports/TELOS Mirror. Nice-to-have, not blocking anything
- [ ] **4B: Interleaved thinking** — Enable on `/delegation`, `/workflow-engine`, `/spawn-agent`. Improves multi-step orchestration
- [ ] **4B: Tool Search API** — Implement when skill/tool count exceeds 50. Not yet at threshold
- [ ] **4E: Signal retention policy** — Only needed after autonomous producers generate 2,000+ processed signals
- [ ] **4E: FTS index validation** — Validate `jarvis_index.py` covers all signal sources
- [ ] **4E: Reporting dashboard data contract** — Define `/vitals` + brain-map Phase 3.5 JSON contract
- [ ] **Voice signals in heartbeat** — `voice_session_count` metric. Low priority until voice is daily habit

### New Skills

- [x] **`/capture-recording` skill** — Guitar recording analysis via Gemini API. SKILL.md orchestration + Python CLI (`analyze_recording.py`). Solo/band/batch modes, MUSIC.md goal loading, token tracking. 12/12 ISC items passed. PRD: `memory/work/capture-recording/PRD.md`. (2026-03-28)

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
| 4E | Not started | 10 |

## Active Projects

| Project | Status | Health | Owner | Next Action |
|---------|--------|--------|-------|-------------|
| epdev-jarvis-setup | active | green | epdev | Phase 3C Layer 2 + 3E ISC engine — see `orchestration/tasklist.md` Phase 3C/3E |
| crypto-bot | active | yellow | epdev | Paper trading → production gate — see `memory/work/crypto_trading_bot/project_state.md` |
| jarvis-brain-map | active | green | epdev | Phase 4: Drill-Down Panel — see `memory/work/jarvis_brain_map/PRD.md` |

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
- [x] **3C-Slack-2: `tools/slack_poller.py`** — Built. Polls `#jarvis-inbox` every 60s; runs `claude -p` from repo root (CLAUDE.md context auto-loads); replies in thread. State in `data/slack_poller_state.json`.
- [x] **3C-Slack-3: `tools/slack_voice_processor.py`** — Built. Polls `#jarvis-voice` every 60s; runs voice-capture prompt headlessly; writes signals to `memory/learning/signals/`; posts confirmation in thread.
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
- [x] **Dashboard UI** — Replaced by jarvis-brain-map project (standalone repo). Phase 3.5 vitals route will serve as the dashboard. See `memory/work/jarvis_brain_map/PRD.md`.

### Phase 3D: Visual system of record & ideal-state workflow (COMPLETE)

> **Status:** Replaced by standalone `jarvis-brain-map` project. PRD, research, architecture, and Phase 1 parser all complete. Remaining work tracked in `memory/work/jarvis_brain_map/PRD.md`.
>
> **Dependency note:** Phase 3E can now proceed — the “current vs ideal” vocabulary is defined by the brain-map node/edge taxonomy and ISC gap model.

- [x] **Clarify requirements** — Completed via `/project-init` pipeline: `/research` → `/first-principles` → `/red-team` → `/create-prd`. Brain spec defined in `memory/work/jarvis_brain_map/PRD.md` — nodes = TELOS/Goal/Project/Phase/PRD/ISC/Task/Skill/Signal; edges = drives/defines/decomposes-into/gap/etc. Git-markdown is source of truth; brain-map is read-only through Phase 3.
- [x] **Survey tooling** — React Flow + Next.js + dagre chosen. Research brief at `memory/work/jarvis_brain_map/research_brief.md`. Compared Obsidian, Mermaid, custom dashboard. Decision: standalone `jarvis-brain-map` repo at `C:\Users\ericp\Github\jarvis-brain-map`.
- [x] **Current vs ideal workflow** — **REOPENED then COMPLETED 2026-03-27**: Original ISC gap model was insufficient. Proper workflow spec now written from Eric's direct input at `memory/work/jarvis/3D_workflow_spec.md`. Covers: actual session patterns, ADHD-driven branching, mobile gap, life coach vision, operator familiarity gap (#1 pain point), measurement vocabulary beyond ISC checkboxes, and downstream requirements for 4D/5.
- [x] **Claude Code analysis session** — Full repo scan + analysis done 2026-03-27. Parser expansion roadmap defined (Phase 2.5). Vitals dashboard scoped (Phase 3.5). Cross-project dependency mapped: brain-map 3.5 depends on epdev 3E.

### Phase 3E: ISC engine & scheduled heartbeat

> **Parallel with 3C:** Layers 2+3 of 3C (Tailscale, voice server, STT/TTS) are independent of 3E. Build whichever has energy — they don't block each other. 3D is now complete (brain-map), so 3E can proceed.
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

**Depends on:** Phase 2 maturity (signals/synthesis patterns), Phase 3D “current vs ideal” spec (shared vocabulary for gaps). **Build in:** mostly **Claude Code/Python** + OS scheduler; Claude Code sessions **review** trends and promote steering rules. **Feeds into:** jarvis-brain-map Phase 3.5 vitals dashboard.

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
- [ ] **Research runner** — `tools/scripts/morning_feed.py` (Anthropic API direct, no claude -p) + `run_morning_feed.bat` wrapper. Task Scheduler `\Jarvis\JarvisMorningFeed` at 9am daily. Dry-run validated. BUILT -- awaiting validation: first live 9am Slack post with rated proposals. (2026-03-28)
- [x] **Cowork vs scheduler split** — Documented in PRD_autonomous_learning.md: overnight = Task Scheduler + claude -p (separate calls per dimension); morning feed = Task Scheduler + Python (Anthropic API direct); interactive = Claude Code session. (2026-03-28)
- [ ] **Interleaved thinking for orchestration skills** — Enable interleaved thinking on `/delegation`, `/workflow-engine`, and `/spawn-agent`: think→tool→think→tool pattern dramatically improves multi-step research and agent composition. Configure via `interleaved-thinking-2025-05-14` header on Claude API calls inside these skills. Do alongside research runner — this is where it pays off most.
- [ ] **Tool Search API** — When skill/tool count exceeds 50, implement Tool Search to prevent token explosion in orchestration loops. Evaluate as part of research runner architecture — autonomous research will eventually need to query 100+ tools by description without loading all schemas upfront.

### Phase 4C — Slack notifications by severity

- [ ] **Notifier wrapper or policy** — Map event types to `#epdev` vs `#general` per `slack-routing.md`; implement daily cap / dedupe
- [ ] **Heartbeat + research digests** — Routine summaries → `#epdev`; regressions and must-see criteria → `#general` only when rules match

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
- [ ] **TELOS introspection live run** — BUILT -- awaiting validation: confirm `run-YYYY-MM-DD/` artifacts appear after first 7am run. Check `data/logs/autoresearch_*.log` + run directory.

**Depends on:** Phase 4A-4C foundations; TELOS and learning layout stable enough to iterate; **Phase 3D "current vs ideal" spec must exist** before writing `autoresearch_program.md`. **Decision:** `history/decisions/2026-03-27_phase4-autonomous-self-improvement.md` (update with 4D)

---

### Phase 4E — Data management & reporting layer

> **Why now:** Phases 4B-4D (auto-research, Slack digests, autoresearch) will produce 200-500+ signals/day, 10K+ event lines/day, and 3-5 synthesis runs/day. Without a data layer, autonomous producers create unbounded growth in directories that 6+ consumers read. This phase builds the plumbing that autonomous Jarvis produces into.
>
> **Corrected by first-principles + quality-gate audit (2026-03-28):** LSM-tree archival was rejected — synthesis aggregates, it doesn't merge-and-discard; moving files from processed/ breaks FTS indexer (absolute paths), heartbeat collectors (false velocity alerts), and brain-map parser. Approach: threshold-triggered retention + lineage indexing, not premature archival.

- [ ] **Signal lineage index** — After each `/synthesize-signals` run, append to `memory/learning/signal_lineage.jsonl`: `{"signal": "filename.md", "synthesis": "YYYY-MM-DD_synthesis.md", "date": "..."}`. Solves reverse-lookup (signal -> synthesis) without moving files.
- [ ] **Signal retention policy** — Add `processed_retention_days` to `heartbeat_config.json`. When processed/ exceeds threshold (2,000 files OR 30+ days since synthesis consumed a signal), delete consumed signals. FTS index retains content; synthesis docs retain references. Gate: only activate after FTS index is verified to contain all processed signal content.
- [ ] **Event rotation scheduled** — Wire `rotate_events.py` into monthly Task Scheduler job. Already built + tested; monthly rollup -> `history/events/rollups/YYYY-MM_summary.json`, gzip after 180d, 90d raw retention.
- [ ] **FTS index as canonical search layer** — Validate `jarvis_index.py` indexes all signal sources (signals/, processed/, synthesis/, failures/). Ensure `update` command runs on heartbeat cadence. This is the layer that survives retention — raw files can be deleted because FTS retains the content.
- [ ] **Reporting dashboard data contract** — Define what `/vitals` and brain-map Phase 3.5 need: signal velocity, synthesis frequency, event volume, FTS index size, retention status. Emit as structured JSON from heartbeat for downstream consumers.
- [ ] **Autonomous signal volume monitoring** — Add `autonomous_signal_rate` collector to heartbeat. Alert if `Source: autonomous` signals exceed daily cap (prevents runaway research loops from flooding the pipeline).

**Depends on:** Phase 4D (autoresearch is the primary producer). Can be built incrementally alongside 4B-4D — lineage index and event rotation are safe to ship immediately.

---

> **Open Validations** moved to Priority Backlog Tier 1 (top of file).

## Phase 4 → Phase 5 Gate (verify before starting Phase 5)

- [ ] **PAIMM AS2 verified** — Jarvis is proactive: heartbeat runs without human prompt, background research produces signals, Slack digests fire on cadence
- [ ] **Autoresearch loop has run >=3 cycles** — `memory/work/jarvis/autoresearch/` contains >=3 `run-YYYY-MM-DD/` directories with `metrics.json`; overnight runner has >=3 `overnight-YYYY-MM-DD/` directories
- [ ] **Steering rules updated from autonomous signals** — at least one CLAUDE.md change promoted from a `Source: autonomous` signal
- [ ] **Voice capture Layer 1 live** — Notion app / Slack `#jarvis-voice` → poller → signal pipeline confirmed working end-to-end; at least one real voice signal exists in `memory/learning/signals/` with `Source: voice`
- [ ] **Remote terminal Layer 3 live** — Tailscale installed on desktop + iPhone; Blink Shell confirmed; full `claude` CLI session reachable from iPhone over Tailscale from outside home network
- [ ] **Data layer operational** — Phase 4E signal lineage index appending after synthesis runs; event rotation scheduled; autonomous signal rate monitoring active
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

**Claude Code (Claude Max)** = All implementation. Skills, hooks, parsers, scripts — everything is built in Claude Code. Cursor is retired (2026-03-27).

**jarvis-brain-map repo** = Standalone project at `C:\Users\ericp\Github\jarvis-brain-map`. React Flow + Next.js + TypeScript. Parser reads epdev markdown. Tracked separately in `memory/work/jarvis_brain_map/PRD.md`.
