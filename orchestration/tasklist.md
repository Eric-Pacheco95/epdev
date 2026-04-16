# Task Console

> Unified view of all active work across the epdev system.
> Last updated: 2026-04-15 (pruned: phases 1-4 + 5A/5B/5C detail removed; git history is the archive)

## Completion Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 1–2 | COMPLETE | Foundation, skills, learning loop, TELOS system |
| 3A–3E | COMPLETE | Agent orchestration, Slack/Notion/calendar integrations, heartbeat ISC engine |
| 4A–4E | COMPLETE | Autonomous self-improvement, autoresearch, data hybrid layer |
| 4→5 gate | PASSED | |
| 5A | COMPLETE | PRD, backlog schema, skill audit, context profiles |
| 5B | COMPLETE | Dispatcher + worker, worktree lib, Task Scheduler wiring, 3-task validation |
| 5C | COMPLETE (one deferred) | Unified pipeline, task gate, backlog_append(), routines engine, session capture, Dispatcher Tier 2; ISC template library deferred |
| 5D | IN PROGRESS | Branch lifecycle tracker + signal rate monitoring shipped; data-gated items pending |
| 5E | BUILT — falsification in progress | 5E-2 VALIDATED; 5E-1 window 2026-04-21 |

## Active Projects

| Project | Status | Health | Next Action |
|---------|--------|--------|-------------|
| epdev-jarvis | active | green | Phase 5D data-gated items; 5E-1 falsification 2026-04-21 |
| crypto-bot | active | yellow | Paper trading → production gate — `memory/work/crypto_trading_bot/project_state.md` |
| jarvis-app | active | green | Sprint 1+2+3 COMPLETE — `memory/work/jarvis-app/PRD.md` |

---

## Open Tasks

### Priority: Active

- [ ] **Wire Claude Code "defer" into dispatcher (code)** — validate_tool_use.py defer path, dispatcher resume flow, morning briefing surface. Requires `claude -p --resume` e2e spike first. (split from doc task 2026-04-08)
- [ ] **5C-5C: ISC template library** — Deterministic ISC generation from structured gap output (add_tests, fix_lint, remove_dead_code, update_docs). Current: ISC generated inline per-branch, functional but not templated.

### Phase 4→5 Capability Bridge (backcasted from Phase 7 DA ideal state)

> Gate condition: 5E-1 falsification passes (2026-04-21) + 15+ dispatcher task outcomes before building.
> Architecture-review 2026-04-15: corrected 3 items; see `history/decisions/2026-04-15-arch-review-phase47-roadmap.md`

- [ ] **Health schema + log command (4A)** — Define `data/health.jsonl` schema (date, gym_sessions, sleep_avg_hours, subjective_energy, notes) + one-command log entry skill. Zero dependencies. Ships now — not Phase 6. | Gate: none.
- [ ] **Financial feed snapshot (Phase 5 routine)** — Tier 0 read-only: aggregate crypto-bot P&L + Substack revenue into `data/financial/snapshot.jsonl` (gitignored, blocked from autonomous agent reads). Feeds morning briefing + TELOS G1 tracking. | Gate: crypto-bot paper trading stable.
- [ ] **Goal-drift detection** — Slack alert when G1/G2 go N days without active capture. Scope: G1/G2 ONLY until G3/G4 have signal pipelines (Item 4A is G4's prerequisite). Per-goal threshold; alert names goal + last signal date. | Gate: 5E-1 passes.
- [ ] **Morning briefing: proactive daily priority** — Cron-triggered Tier 0 task: reads TELOS goals + signal queue + backlog pending count → Slack DM before Eric's first session. Input must include `task_backlog.jsonl` pending count and any `manual_review` items. Can ship before 5E-1 falsification — zero risk. | Gate: none (accelerated).
- [ ] **Autonomous task proposals (NOT direct backlog writes)** — Jarvis writes signal-derived proposals to `orchestration/task_proposals.jsonl`; Eric batch-approves in morning review. Live backlog remains human-approved-only per PRD_phase5.md safety invariant. Replaces "autonomous backlog generation" which was blocked. | Gate: Phase 5 completion (90% over 14 days) + loop-health metric live.

### Phase 5D — Hardening + Quality (data-gated)

> Prerequisite: 15+ tasks with diverse outcomes before optimizing.

- [ ] **Two-layer verification (data-gated)** — Second `claude -p` review of worker output if ISC quality proves insufficient. Only build after 15+ task outcomes show ISC-pass-but-bad-quality pattern. Aron's CEO-checks-worker pattern, adapted.
- [ ] **Worker prompt optimization (data-gated)** — Analyze run reports: what context did workers actually use vs ignore? Only build after 15+ runs provide calibration data.
  - Hypothesis parked 2026-04-07: test prompt valence (neutral / supportive / urgent) as a worker prompt variable, n≥15 outcomes per arm. Source: dair_ai recap of NeurIPS workshop paper.
- [ ] **Multi-repo support** — Dispatcher handles epdev + crypto-bot + jarvis-app. Per-project config: repo path, context files, ISC sources. Requires pipeline stability first.
- Memory dedup v2 triggers: see `orchestration/dedup_v2_triggers.md` — 8 trigger-gated items, do not pre-build.

### Phase 5E — Self-Correcting Pipeline

> Prerequisite: 15+ dispatcher tasks with diverse outcomes (done, failed, manual_review, retried).

**5E-1: Deterministic follow-on (partial-ISC retry)**
- STATUS: BUILT 2026-04-07 (commit `26e90d0`, 26/26 self-tests) — falsification window 2026-04-21. PRD: `memory/work/jarvis/PRD_phase5e1.md`.
- [x] `generation` field in task schema — hard cap at 2, enforced in `backlog.validate_task` AND `_emit_followon()` Gate 3
- [x] `_emit_followon()` in dispatcher — 9 sequential gates
- [x] Root-source attribution — child inherits `parent.source`, never set to "dispatcher"
- [x] Always `pending_review` — anti-criterion enforced; throttle=1/day via `data/followon_state.json`
- [x] Slack notification includes follow-on task ID — `parent_id → followon_id` lineage in notify

**5E-2: Pipeline lifecycle + observability**
- STATUS: BUILT 2026-04-07 — **VALIDATED 2026-04-15** (dispatcher ran 8 production cycles, both `sweep_pending_review` + `validate_parent_branch` live with no errors; no TTL expiries yet, expected). PRD: `memory/work/jarvis/PRD_phase5e2.md`.
- [x] `pending_review` TTL — `sweep_pending_review()` + `apply_pending_review_sweep()`: 7d Slack alert, 14d auto-fail with archive to `data/pending_review_expired/`
- [x] Branch existence validation at selection time — `validate_parent_branch()` invoked in `select_next_task()`
- [x] Follow-on ISC count must decrease per generation — `validate_followon_isc_shrinks()` wired into 5E-1 Gate 9

**5E-3: LLM-assisted follow-on (deferred within 5E)**
- [ ] FOLLOW_UP staging gate — Worker FOLLOW_UP lines go to `data/followon_pending/` staging file, not directly to backlog. Requires human review before promotion.
- [ ] Description injection hardening — Unicode normalization, protected-path scan on description field.
- [ ] Overnight producer interface — Moved from 5C-5C. Requires 3+ real overnight production runs + staging gate.

### Phase 5 Completion Gate

- [ ] **≥90% success rate over 14 days** — Dispatcher autonomously executes Tier 0-1 tasks. Measured after 5D is stable.

---

## Capability Tracks (trigger-gated)

### Prediction Engine

> Skill: `/make-prediction` (v1 live, 2026-04-03). Goal: 50+ tracked predictions for calibration learning, then autonomous backtesting.

- [x] Prediction review scheduled task — `prediction_review_task.py` posts weekly Slack digest. (2026-04-05)
- [x] Prediction backtesting pipeline — 35 backtest predictions, 59 resolutions scored. (2026-04-05)
- [x] Prediction calibration feedback loop — `prediction_calibration.py`, 3 domains active. (2026-04-05)

---

## Parked (no demand signal within 60 days)

- **App development skills (iOS/Windows/.exe)** — Research brief at `memory/work/frontend-research/research_brief.md`. Revisit when a concrete app needs App Store/Windows distribution.
- **Slack Bot Socket Mode** — Slash commands + Block Kit. No active use case beyond current poller.
- **3C-8/9/10: Whisper STT, ElevenLabs TTS, voice loop** — Deferred to Phase 6. Native iOS dictation sufficient.

---

## Strategic Horizon — Where AI Is Going and What Jarvis Will Face

> Source: Miessler DA thesis analysis + architecture-review 2026-04-15. Read before planning Phase 6+.
> Full analysis: `history/decisions/2026-04-15-arch-review-phase47-roadmap.md`
> Prediction: `data/predictions/2026-04-15-jarvis-phase7-da-backcast.md`

### The Convergence Thesis (working hypothesis, not law)
PAI, Claude Code, OpenCode, MoltBot all independently arrived at the same 5 primitives: Skills, Hooks, Memory, Agent orchestration, Context priming. Independent convergence is the strongest architectural signal available — but the sample is small (4 projects, proximate ecosystem) and remains a hypothesis to validate, not a law to cite. Before treating this as architectural law, validate against AutoGen/CrewAI/Semantic Kernel (non-Anthropic-adjacent projects).

### The DA Absorption Rule
Any standalone AI product feature in the eventual DA scope is a dead-end. The DA will absorb it the way smartphones absorbed cameras, maps, and alarm clocks. Apply this test before adopting any new tool: *"Will a Phase 7 DA do this automatically?"* If yes, don't build a standalone version — build toward the DA integration instead.

### Phase-by-Phase Headwinds Jarvis Will Hit

| Phase | Problem to anticipate |
|---|---|
| 4 (Presence) | Without mobile access, Jarvis stays terminal-only and engagement drops outside work hours — Phase 5 has no delivery surface |
| 5 (Proactive) | Autonomous task generation without loop-health monitoring creates silent self-reinforcing bad patterns |
| 5→6 | Anthropic pricing/capability shift hits hardest here — 47 skills fully locked in, substrate abstraction not yet built |
| 6 (Senses) | Every new input stream (calendar, email, health API) adds to the MCP attack surface; 43% of MCP servers vulnerable per 2026-04-06 security research |
| 6→7 | Hallucination under autonomy gets irreversible — proactive actions at Phase 5+ cannot be rolled back the way interactive actions can |
| 7 (Advocates) | DA layer consolidates at 2-3 companies (Anthropic, Google, OpenAI); Jarvis risks becoming a config layer on a vendor-controlled substrate with no leverage |

### Known Structural Risks (don't re-discover these)
- **Vendor lock-in (HIGH):** Claude Code controls both model and harness substrate simultaneously. Substrate abstraction (`claude_runner.py`) must ship before Phase 6 deepens lock-in further.
- **Read-only is policy, not sandbox:** Calendar, email, financial integrations enforced by system prompt text + settings.json allow-lists — not a hard technical boundary. Until Claude Code supports per-subagent hard permission profiles, all "read-only" constraints are advisory.
- **Spear-phishing escalation:** As Jarvis gains access to calendar, email, and financial data, it becomes a higher-value injection target. Every new sense is a new attack surface. Treat ambient data feeds as untrusted external input even when they come from "trusted" sources (Eric's own calendar can be poisoned via invite).
- **The "Her" OS is over-specified:** Voice-first, always-on is ONE possible interface end-state. The correct north star is orchestration capability + advocacy for Eric's goals — not the interface modality. Build the orchestration; let the interface emerge.
- **MCP is vendor-controlled:** Model Context Protocol is Anthropic's protocol. Watch for OpenAPI-native alternatives. MCP is the right bet today; it may not be in 2027.

---

## Phase 6: Senses — Persistent ambient awareness (future)

> Status: deferred — requires Phase 5 completion gate.
> Concept: Miessler's Phase 6 (Senses) + Daemon behavioral change — persistent input streams + goal advocacy. Runs ON Phase 5 infrastructure.
> Gate: Phase 5 completion gate (≥90% success rate over 14 days)

- [ ] **Health sensor integration (4B)** — Automated gym/sleep capture from wearable API (Garmin Connect, Apple Health export). Optional — manual log (4A) is defensible indefinitely for solo operator. Only pursue if 4A proves insufficient. | Gate: Phase 5 completion + 4A live 60+ days.
- [ ] **Substack human-gated draft pipeline** — `/extract-wisdom` → draft → Slack DM with draft link → Eric reviews → Eric triggers publish. Autonomous publish is BLOCKED permanently under Tier 3 classification until Eric explicitly upgrades Substack to an approved external write surface (policy decision, not tech work). | Gate: explicit policy decision by Eric.
- [ ] **Thin claude_runner.py wrapper** — Centralize `subprocess.run(["claude", "-p", ...])` call in `tools/scripts/lib/claude_runner.py`. All 47 skill call sites stay unchanged; only the internal implementation consolidates. This is cleanup, not full provider abstraction. Full abstraction only when a second provider is named. | Gate: none (low priority, any Phase 5 sprint).
- [ ] **Loop-health metric** — Track human-to-autonomous task ratio over 30-day rolling window. Alert when autonomous > 70%. Required before autonomous task proposals (Phase 4→5) or autonomous PRD generation (Phase 7) go live. Prevents silent self-reinforcing feedback loops. | Gate: before task proposals ship.
- [ ] TBD — Daemon targets (guitar practice, financial momentum, self-discovery) defined after Phase 5 gate
---

## Phase 7: Advocates — Jarvis represents Eric's interests autonomously (future)

> Status: north star only — defined by backcasting from ideal DA end-state (2026-04-15 prediction: `data/predictions/2026-04-15-jarvis-phase7-da-backcast.md`)
> Gate: Phase 6 Senses operational + substrate abstraction layer complete

- [ ] **Autonomous PRD generation (staged)** — Jarvis generates PRD proposals from signal patterns into a staging directory; human `git mv` required to promote to `memory/work/`. Generated PRDs must pass ISC Quality Gate (6 checks) before entering review queue. Anti-criterion: no generated PRD may modify TELOS goals or security rules. Loop-health metric must be live before this ships. | Gate: Phase 6 complete + loop-health metric + 3+ manual signal→gap→task cycles proven.
- [ ] **Calendar + email integration (read-only)** — Jarvis reads calendar/email; injects "N items today, next free block at X" into morning briefing. Hard requirements: OAuth scopes read-only at API level (not prompt level); email content treated as untrusted (length cap + injection strip before synthesis); provenance marker `[email-sourced]` on all derived content; feature-flagged OFF by default (`JARVIS_EMAIL_READER_ENABLED=false`). | Gate: Phase 6 complete + explicit security review.
- [ ] **Multi-domain parallel orchestration** — 3+ simultaneous overnight jobs with per-project file locking, TOCTOU fix on `task_backlog.jsonl`, per-job Claude budget allocation, and circuit breaker (2/3 failures → halt all + alert). This is a safety architecture redesign, not a scaling operation. | Gate: Phase 5 gate (90% over 14 days) + single-task reliability proven + per-project lock design reviewed.

---

- [ ] **Local embedding + vector search for memory** — Deferred from Phase 5. Triggers: file count > 400 OR 5+ documented grep retrieval failures. Research: `memory/work/local-embeddings/research_brief.md`. Decision: premature at current scale.
- [ ] **Harness hill-climbing eval loop (Trace Grader)** — Phase 1: wire report.md TSV delta into Slack review message. Phase 2 (gated on ~30 merged runs): `grade_overnight.py`. Architecture review: `history/decisions/2026-04-08-arch-review-trace-grader.md`. Trigger: Phase 5 gate + merge volume evidence.
- [ ] **Evaluate ACP/acpx for overnight runner + dispatcher** — Deferred. Source: openclaw/acpx. Trigger: (a) `claude -p` rate-limit handling fragile after 15+ outcomes, OR (b) need stateful multi-turn workers, OR (c) need non-Claude agents. Acceptance: must not add auth surface, must work with `JARVIS_SESSION_TYPE=autonomous`. Per "absorb over adopt" rule — do not adopt until existing `claude -p` proves insufficient.
- [ ] **Learning Pipeline Phase 2: Wisdom Tier** — Deferred from Phase 1. 30-day evaluation gate: by 2026-05-10, assess whether existing tiers absorb domain/system knowledge adequately. Scope: wisdom doc format, promotion logic, human approval gate. Trigger: 30 days of synthesis under Phase 1 warehouse model.

---

## Closed Decisions

> Paths evaluated and deliberately closed. Preserved to prevent re-proposals by agents or future sessions.

- **ntfy RETIRED** — All notifications routed to Slack (ClaudeActivities app). Scripts remain but inactive. Decision: 2026-03-27.
- **4B: Interleaved thinking** — Already enabled by default on Opus/Sonnet 4.6 via adaptive thinking. The `interleaved-thinking-2025-05-14` beta header was for older models. Tuning via `Alt+T`, `/effort`, `CLAUDE_CODE_EFFORT_LEVEL`. No implementation needed.
- **4B: Tool Search API** — Solved natively by Claude Code's deferred ToolSearch mechanism (191 tools as name-only stubs, schemas fetched on demand). No custom implementation needed.
- **5-pre: MCPorter eval** — ABSORB-IDEA. No current `claude -p` task is MCP-only; all require LLM reasoning. Slack uses direct API. Pattern absorbed: JSON-RPC stdio wrapper if batch MCP calls emerge. Decision: `history/decisions/2026-03-31_mcporter-eval-absorb.md`.
- **Dispatcher MAX_TIER=2** — Deliberate permission decision: Tier 2 skills (synthesize-signals, security-audit, learning-capture, self-heal, absorb) are eligible for autonomous execution. Do not lower without explicit approval.

---

## Build Location Guide

**Claude Code (Claude Max)** = All implementation. Cursor retired 2026-03-27.  
**jarvis-app repo** = `C:\Users\ericp\Github\jarvis-app` — React Flow + Next.js + TypeScript. Tracked in `memory/work/jarvis-app/PRD.md`.
