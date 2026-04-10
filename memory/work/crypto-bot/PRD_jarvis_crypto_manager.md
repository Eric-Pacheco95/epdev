# PRD: Jarvis Crypto-Bot Project Manager

**Version:** 1.0
**Date:** 2026-04-10
**Author:** Jarvis (post /architecture-review with 3 parallel agents)
**Status:** APPROVED
**Architecture Review:** `history/decisions/2026-04-09-arch-review-crypto-loop.md`

---

## OVERVIEW

Jarvis becomes the strategic project manager for crypto-bot, layering on top of health_monitor.py's real-time ops. Jarvis ingests crypto-bot logs, trading data, and API state to identify trends, propose improvements via PRs, accumulate cross-project learnings, and surface crypto-bot status in morning briefings. health_monitor.py continues tactical work (health probes, ML pipeline, process restart, GPT-4o patches). Jarvis handles the strategic layer: multi-day trend analysis, architectural improvements, signal source research, and production readiness tracking — all executed through PRs on the crypto-bot repo, never direct mutation.

## PROBLEM AND GOALS

- Eric has no strategic oversight of crypto-bot without manually checking Telegram and the dashboard — Jarvis should surface this in the daily workflow
- health_monitor.py optimizes tactically (2h cycle GPT-4o patches) but nobody tracks whether the bot is trending toward profitability across days/weeks
- Crypto-bot learnings (signal quality, ML performance, trade patterns) don't feed into Jarvis's synthesis pipeline — knowledge stays siloed
- Improvements requiring code changes (new signal sources, architectural fixes) need PRs with review, not auto-applied patches
- Total system death (all processes including health_monitor) has no external observer

## NON-GOALS

- Replace health_monitor.py's real-time responsibilities (health watchdog, ML pipeline driver, process restart, autonomous agent loop)
- Write directly to crypto-bot's `data/ml_control.json`, `.env`, or any runtime config — all changes via PRs
- Autonomous production mode switching — always requires Eric's explicit approval
- Real-time trade alerting — health_monitor + Telegram already handle this
- API cost optimization — $4.70 variable vs $40 headroom, no pressure

## USERS AND PERSONAS

- **Eric (operator)**: Receives morning briefing with crypto-bot status, reviews PRs for improvements, makes production decisions
- **Jarvis dispatcher (autonomous)**: Schedules analysis tasks, spawns worktree agents for PR creation, routes learnings to synthesis
- **health_monitor.py (peer)**: Continues real-time ops independently; Jarvis reads its outputs but never controls it

## USER JOURNEYS OR SCENARIOS

1. **Morning briefing**: Eric opens Jarvis session → crypto-bot status block shows: processes alive/dead, trade count (open/closed), win rate trend, P&L since last briefing, any alerts fired, health_monitor agent actions taken overnight
2. **Trend detection → PR**: Jarvis overnight runner analyzes 7-day trade data → identifies "signal threshold 70 is too loose, 80% of trades scoring 70-75 lose money" → creates PR on crypto-bot repo raising threshold with evidence
3. **Dead system alert**: All crypto-bot processes die at 3 AM → Jarvis's external poller detects API unreachable after 3 consecutive failures (15 min) → Slack alert to #crypto-bot
4. **Learning capture**: Jarvis reads weekly attribution data from `/api/signal-attribution` → writes signal to `memory/learning/signals/` with source: crypto-bot → feeds into next `/synthesize-signals` run
5. **New signal source research**: Jarvis autoresearch producer identifies a new on-chain data source relevant to crypto → creates backlog item → overnight runner creates PR adding the integration with tests

## FUNCTIONAL REQUIREMENTS

**FR-001: SENSE Collector**
- Polls crypto-bot REST API every 15 min: `GET /api/status`, `GET /api/portfolio`, `GET /api/pipeline-health`, `GET /api/paper-report`, `GET /api/signal-attribution`, `GET /api/costs`
- Reads log files directly: `C:\Users\ericp\Github\crypto-bot\data\logs\{uvicorn,celery_worker,celery_beat,health_monitor}.log` (tail last 200 lines per poll)
- Reads alert audit trail: `C:\Users\ericp\Github\crypto-bot\data\alerts\alerts.jsonl` (new entries since last poll)
- Reads patch audit trail: `C:\Users\ericp\Github\crypto-bot\data\patches.jsonl` (new entries since last poll — surfaces health_monitor GPT-4o auto-applied patches in morning briefing)
- Writes consolidated snapshot to `epdev/data/crypto_bot_state.json` (single file, overwritten each poll)
- API-only reads — never opens `bot.db` directly (per architecture review: avoid WAL contention)

**FR-002: Dead-Man's Switch**
- If `GET /api/status` fails 3 consecutive times (3 × 15 min = 45 min window), emit Slack alert to `#crypto-bot`
- Alert contains: last known state, last successful poll timestamp, which endpoint failed
- Max 3 alerts per incident (per Eric's preference), reset counter on recovery
- On recovery, emit single "crypto-bot back online" message

**FR-003: Morning Briefing Integration**
- Jarvis session-start hook includes crypto-bot status block sourced from `data/crypto_bot_state.json`
- Status block shows: process health (up/down), trade count (open/closed since last briefing), realized P&L, win rate (rolling 50), drawdown %, overnight alerts fired, health_monitor patches applied overnight
- If `crypto_bot_state.json` is stale (>30 min old), show "STALE — last poll {timestamp}" warning

**FR-004: Learning Pipeline Bridge**
- Daily (overnight runner): read `/api/signal-attribution` + `/api/paper-report` + `/api/model-learning-summary`
- Write structured Jarvis signal to `memory/learning/signals/` with `Source: crypto-bot`, `Category: trading-performance`
- Signal content: win rate, avg PnL, top/bottom signal sources by edge, ML model CV accuracy, trade count milestone
- Signal only written when delta from last signal exceeds threshold (avoid noise): win rate change >5pp, trade count milestone (50, 100, 200), CV accuracy change >3pp

**FR-005: Strategic Analysis Producer**
- Daily overnight runner task: analyze crypto-bot trading data for multi-day trends
- Cross-checks against health_monitor's GPT-4o patches (from `patches.jsonl`) to avoid conflicting recommendations
- Inputs: `data/crypto_bot_state.json` history (append-only log in `data/crypto_bot_history.jsonl`), API attribution data, log patterns, patches.jsonl
- Analysis targets:
  - Score threshold effectiveness (win rate by score bucket over 7-day window)
  - Signal source quality trends (which sources are improving/degrading)
  - Hold time vs profitability correlation
  - Stop-loss trigger frequency (too tight? too loose?)
  - Error pattern frequency from logs (recurring issues health_monitor hasn't fixed)
  - Consistency check: are health_monitor's auto-patches improving or degrading performance?
- Output: analysis summary → Slack #crypto-bot + Jarvis learning signal
- Gated: only runs when ≥50 closed trades exist in current paper run

**FR-006: Improvement PRs via Worktree**
- When strategic analysis identifies an actionable improvement with evidence, Jarvis dispatcher spawns a worktree agent on crypto-bot repo
- Agent creates a branch, implements the change, opens a PR with:
  - Evidence from analysis (data, not opinions)
  - Before/after expected impact
  - Test coverage for the change
- PR requires Eric's review and merge — Jarvis never force-pushes or auto-merges
- Worktree agent receives explicit safety context: no RUN_MODE changes, no guardrail weakening, no .env edits, cross-repo edit gate active
- Max 1 PR per overnight run to avoid review fatigue

**FR-007: State History Log**
- Each SENSE poll appends a summary row to `data/crypto_bot_history.jsonl`: timestamp, trade_count_open, trade_count_closed, realized_pnl, win_rate, drawdown_pct, processes_alive, alerts_fired_count
- Used by FR-005 for trend analysis
- Weekly cleanup: compress entries older than 30 days to daily summaries

## NON-FUNCTIONAL REQUIREMENTS

- SENSE collector must complete within 30 seconds per poll (API timeout: 10s per endpoint)
- All crypto-bot data reads are read-only — no POST/PATCH/DELETE calls to any endpoint
- Log file reads use seek-to-end + tail, not full file reads (logs can be 90MB+)
- ASCII-only output for any script that prints to terminal (Windows cp1252 steering rule)
- Worktree agents for PRs must check `git status --short` in crypto-bot before any edit (cross-repo steering rule)

## ACCEPTANCE CRITERIA

- [x] SENSE collector polls 6 API endpoints and writes `crypto_bot_state.json` every 15 min | Verify: `cat data/crypto_bot_state.json` shows timestamp within last 15 min | model: sonnet |
- [x] Dead-man's switch sends Slack alert within 45 min of total crypto-bot API failure | Verify: stop crypto-bot, wait, check #crypto-bot for alert | model: sonnet |
- [x] Dead-man's switch sends max 3 alerts per incident and resets on recovery | Verify: count alerts in #crypto-bot during extended outage | model: sonnet |
- [x] Morning briefing includes crypto-bot status block with trade count, P&L, win rate, process health | Verify: start new Jarvis session, check hook output for crypto-bot section
- [x] Learning signal written to `memory/learning/signals/` with Source: crypto-bot when delta thresholds exceeded | Verify: `grep -l "Source: crypto-bot" memory/learning/signals/` | model: sonnet |
- [x] `crypto_bot_history.jsonl` accumulates one row per 15-min poll with required fields | Verify: `python -c "import json; [json.loads(l) for l in open('data/crypto_bot_history.jsonl')]"` | model: haiku |
- [x] Strategic analysis producer runs only when ≥50 closed trades exist | Verify: with <50 trades, overnight runner skips analysis with logged reason | model: sonnet |
- [x] Improvement PRs created on crypto-bot repo via worktree, never direct push to master | Verify: `git -C /c/Users/ericp/Github/crypto-bot log --oneline -5` shows no Jarvis commits on master without PR
- [x] SENSE collector never calls any POST/PATCH/DELETE endpoint on crypto-bot | Verify: Grep collector source for `requests.post\|requests.patch\|requests.delete\|httpx.post` returns 0 matches
- [x] Collector never opens `bot.db` directly | Verify: Grep collector source for `bot.db\|sqlite` returns 0 matches | model: haiku |

ISC Quality Gate: PASS (6/6) — 10 criteria, all single-sentence, state-not-action, binary-testable, 2 anti-criteria (no POST calls, no direct DB), all have Verify suffix

## SUCCESS METRICS

- Jarvis detects crypto-bot total death within 45 min (vs current: hours until Eric checks manually)
- ≥1 crypto-bot learning signal per week feeds into Jarvis synthesis
- ≥1 evidence-based improvement PR per week once 50+ closed trades exist
- Eric reviews crypto-bot status in morning briefing without opening Telegram or dashboard
- Win rate trend visible in `crypto_bot_history.jsonl` over 30-day rolling window

## OUT OF SCOPE

- Replacing health_monitor.py's real-time health watchdog (120s probes)
- Replacing health_monitor.py's ML pipeline driver (backfill, mini-retrain, drift tracking)
- Replacing health_monitor.py's autonomous agent loop (process restart, error fixes)
- Replacing health_monitor.py's GPT-4o strategy analyst (2h tactical patches)
- Direct config mutation via API or file writes
- Production mode switching or guardrail changes
- API cost optimization (healthy budget, no action needed)
- Real-time trade notifications (Telegram handles this)

## DEPENDENCIES AND INTEGRATIONS

- **crypto-bot REST API** (localhost:8080): 6 GET endpoints for data collection
- **crypto-bot log files**: 4 log files at `data/logs/` + `data/alerts/alerts.jsonl`
- **Jarvis dispatcher**: routes overnight analysis tasks
- **Jarvis overnight runner**: executes strategic analysis + PR creation
- **Jarvis learning pipeline**: receives signals with Source: crypto-bot
- **Jarvis session-start hook**: displays crypto-bot status block
- **Slack #crypto-bot channel**: dead-man's switch alerts + analysis summaries
- **GitHub (crypto-bot repo)**: PR creation via `gh pr create`
- **crypto-bot worktree isolation**: PRs created in isolated worktrees

## RISKS AND ASSUMPTIONS

### Risks
- **Log file size**: celery_worker.log reached 91MB in one day — tail-based reading is essential; full reads will OOM
- **API unavailable during celery restart**: brief windows where API is down during normal restarts could trigger false dead-man alerts — 3-strike rule mitigates this
- **Stale analysis on small samples**: strategic analysis at 50 trades may still be noisy — frame findings as hypotheses, not conclusions, until 200+ trades
- **PR review fatigue**: if Jarvis produces low-quality PRs, Eric stops reviewing them — max 1/day cap + evidence requirement keeps quality high
- **Cross-repo worktree conflicts**: if Eric or another session is editing crypto-bot while Jarvis creates a PR, merge conflicts possible — worktree isolation mitigates

### Assumptions
- crypto-bot REST API remains at localhost:8080 with current endpoint structure
- health_monitor.py continues running independently (Jarvis does not manage its lifecycle)
- Eric reviews PRs within 48 hours (PRs older than 7 days auto-closed with "stale" label via `gh pr close --comment "Auto-closed: stale >7 days"`)
- Slack #crypto-bot channel exists and SLACK_WEBHOOK_URL is configured
- crypto-bot repo remote is accessible for `gh pr create`

## OPEN QUESTIONS

(All resolved during brainstorm — captured in functional requirements above)

1. ~~patches.jsonl reading~~ → YES, added to FR-001 + FR-003
2. ~~Cross-check Jarvis vs GPT-4o~~ → YES, added to FR-005
3. ~~Analysis frequency~~ → DAILY (overnight runner)
4. ~~Stale PR handling~~ → AUTO-CLOSE after 7 days
