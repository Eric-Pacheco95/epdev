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

### Phase 5D — Hardening + Quality (data-gated)

> Prerequisite: 15+ tasks with diverse outcomes before optimizing.

- [ ] **Two-layer verification (data-gated)** — Second `claude -p` review of worker output if ISC quality proves insufficient. Only build after 15+ task outcomes show ISC-pass-but-bad-quality pattern. Aron's CEO-checks-worker pattern, adapted.
- [ ] **Worker prompt optimization (data-gated)** — Analyze run reports: what context did workers actually use vs ignore? Only build after 15+ runs provide calibration data.
  - Hypothesis parked 2026-04-07: test prompt valence (neutral / supportive / urgent) as a worker prompt variable, n≥15 outcomes per arm. Source: dair_ai recap of NeurIPS workshop paper.
- [ ] **Multi-repo support** — Dispatcher handles epdev + crypto-bot + jarvis-app. Per-project config: repo path, context files, ISC sources. Requires pipeline stability first.
- Memory dedup v2 triggers: see `memory/work/jarvis/dedup_v2_triggers.md` — 8 trigger-gated items, do not pre-build.

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

## Phase 6: Daemon-inspired behavioral change (future)

> Status: deferred — requires Phase 5 completion gate.
> Concept: Miessler's "Daemon" — behavioral change targeting guitar practice, health, financial momentum, self-discovery. Runs ON Phase 5 infrastructure.

- [ ] TBD — defined after Phase 5 completion gate passes
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
