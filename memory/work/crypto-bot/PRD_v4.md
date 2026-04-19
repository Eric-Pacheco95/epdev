# PRD: Crypto-Bot — Outcome-Shaped 6-Phase Ladder to Autonomous Profit

**Version:** 4.0
**Date:** 2026-04-17
**Author:** Eric P + Jarvis (backcast + 3-agent architecture review + collaborative ISC design)
**Status:** DRAFT — awaiting Eric approval
**Supersedes:** `PRD.md` (v3.0, 2026-04-01)
**Sources:** `data/predictions/2026-04-17-crypto-bot-backcast.md`, `history/decisions/2026-04-17-arch-review-cryptobot-autonomy.md`

---

## OVERVIEW

Crypto-bot is re-scoped from a 35-bug activity list (v3.0) to an outcome-shaped 6-phase autonomy ladder targeting 3x paper capital by 2027-04-17 under a closed-loop learning architecture (attribution → weight update → forward-trade outcome → next cycle), with Eric's time contribution capped at ≤4h/week steady-state and Jarvis auto-merging improvement PRs behind arch-review-gated guardrails. Current state is Pre-Phase 1 (77/77 consecutive dead polls, broken dead-man's switch, 0 trades since clean-slate reset on 2026-04-09); the revival path begins with Phase 1 ALIVE (2026-05-01 target). PRD orchestration lives in `epdev/memory/work/crypto-bot/`; code lives in the separate `crypto-bot` repo reached via cross-repo worktree invocations from `/implement-prd`.

---

## PROBLEM AND GOALS

- **Problem:** v3.0 PRD measured activity (bug-count resolved, trade-count reached, threshold metrics). This produced a system that, even when functional, had no feedback loop between signals and knowledge and no convergence rule to distinguish good variance from bad drift. The bot is now dead (77 consecutive dead polls), the dead-man's switch didn't fire, and the pre-reset trading window showed 0/17 win rate — three independent failure modes the v3.0 ISC could not detect.
- **Primary outcome goal:** 3x paper capital ($100K → $300K) sustained ≥14 days by 2027-04-17, with 6-month intermediate checkpoint on 2026-10-17 evaluated by a pre-committed 4-of-6 vector gate (not scalar 1.5x).
- **Primary mechanism goal:** Closed-loop learning — bot demonstrably uses signal attribution data to adjust weights, and those adjustments produce forward-trade P&L improvement backed by counterfactual evidence (not correlational).
- **Primary autonomy goal:** Jarvis generates improvement PRs from `/research → /create-prd → /implement-prd → gh pr create`; Eric reviews manually through Phase 4; auto-merge activates in Phase 5 behind 8 guardrails identified in the 2026-04-17 architecture review.
- **Priority order:** Capital cap > API budget > Attention/time > Risk tolerance.

---

## NON-GOALS

- Solana execution, Hyperliquid perps (defer indefinitely — not profit-moving at current maturity)
- Mobile app / jarvis-app integration
- Leveraged products (whitelist-deny until Phase 5 arch-review conditions close)
- VPS / Docker deployment
- New signal pipelines beyond current P1 (LunarCrush), P3 (Whale), P4 (LP events), P5 (DexScreener Depth) until Phase 3 proves closed-loop attribution on existing pipelines
- Target "5x in 2 months" or any scalar return-only goal (replaced by 6-phase ladder + vector-gate checkpoints)
- Real-capital deployment above $500 total before paper-3x milestone confirmed
- Tiered/partial exit strategy (Position model refactor) — defer post-Phase 3
- Volume-drop exit signal — insufficient data to calibrate; defer

---

## USERS AND PERSONAS

- **Eric (operator + strategic reviewer):** ≤4h/week steady-state; attends phase-transition approvals separately; reviews morning briefing for bot status; does not lead diagnosis. Priority anchor: capital cap.
- **Jarvis (strategic manager + improvement-PR author):** Owns SENSE collector, dead-man's switch, morning briefing surfacing, improvement PR pipeline, attribution ledger, shadow-mode auto-merge simulation. Manual merge through Phase 4; auto-merge in Phase 5 behind guardrails.
- **crypto-bot process (tactical trader):** Runs signal→scoring→trade loop, consumes weight updates from `ml_control.json`, writes attribution entries per closed trade. Not trusted to propose its own weight changes to main (Jarvis PR pipeline is the only path).

---

## USER JOURNEYS OR SCENARIOS

1. **Morning check:** Eric opens morning briefing; crypto-bot section shows API reachable, process alive, trade count, 24h P&L, any unacknowledged downtime >24h as red flag. If any gate criterion broken, Eric sees it here, not by digging.
2. **Phase 1 revival:** Eric triggers Phase 1 execution; Jarvis runs diagnosis, documents root cause in `history/decisions/`, fixes dead-man's switch, restarts bot under supervised process. Induced failure smoke test verifies alert fires.
3. **Phase 2 trading loop:** Bot places trades, every trade's alert_id links to source pipeline in logs. Pre-trade risk gate enforced via CI; any trade path without gate fails merge. 30-day window shows ≥20 trades with no 7-day zero-trade stretch.
4. **Phase 3 learning:** Attribution ledger writes per closed trade; shuffle-test gates weight updates; regime-change detector freezes updates during transitions. 2026-10-17 vector-gate checkpoint evaluated; pivot or continue per pre-committed rule.
5. **Phase 4 Jarvis PR cycle:** Jarvis runs `/research` on bot underperformance → `/create-prd` on specific fix → `/implement-prd` in crypto-bot worktree → `gh pr create`. Eric reviews and merges manually (≤2h/week review time).
6. **Phase 4.5 Paper-to-Live bridge:** After paper 3x, live execution with $0 P&L target, $500 cap, measured by fill rate / slippage / rejection handling — not P&L.
7. **Phase 5 auto-merge:** Jarvis auto-merges improvement PRs behind guardrail stack; shadow-mode retrospective validated; Eric kill-switch always available.

---

## FUNCTIONAL REQUIREMENTS

Requirements grouped by phase. Phase 3+ carry ⚠️ arch-review gates from `history/decisions/2026-04-17-arch-review-cryptobot-autonomy.md`; do not build gated items until conditions close.

### Phase 1 — ALIVE (target 2026-05-01) `| model: sonnet |`

- **FR-P1-01:** Root-cause 77/77 dead-poll state documented in `history/decisions/YYYY-MM-DD_cryptobot-revival.md` before any restart is attempted.
- **FR-P1-02:** Dead-man's switch alerts_fired_count increments AND emits Slack alert to `#epdev` (not `#jarvis-inbox`) within 60 min of induced 45-min API-down window.
- **FR-P1-03:** Bot process runs continuously ≥7 days under Task Scheduler Python-path supervisor (post-2026-04-10 OOM cascade fix verified, not PowerShell wrapper).
- **FR-P1-04:** Per-pipeline staleness tracking — any active pipeline whose latest successful fetch is >15 min old emits warning in dashboard health endpoint and in scoring logs (derived from v3.0 FR-P0-33).
- **FR-P1-05:** SENSE collector `api_reachable=true` for ≥95% of polls in a 48h rolling window.
- **FR-P1-06:** Morning briefing surfaces crypto-bot status proactively — unacknowledged downtime >24h appears as red-flag section without Eric asking.
- **FR-P1-07:** Verify Grok P2 cleanup status from v3.0 (FR-P0-05/06/07/08) — if scoring pipeline still references Grok/Apify, complete cleanup; if already done, record "cleanup complete, confirmed 2026-04-17" in decisions. No rework if done.
- **FR-P1-08:** Startup path in `daily-agent-run.bat` points to `C:\Users\ericp\Github\crypto-bot` (v3.0 FR-P0-03 verification; fix if drifted).

### Phase 2 — TRADING (target 2026-Q2, complete by 2026-06-30) `| model: sonnet |`

**Correctness (from v3.0 triage):**
- **FR-P2-01:** Short-position P&L computed with inverted sign on close (v3.0 FR-P0-09).
- **FR-P2-02:** Short positions restored correctly from DB after bot restart with `is_short=True` preserved (v3.0 FR-P0-10).
- **FR-P2-03:** Trailing stop tracks actual peak price per position in both paper and production modes (v3.0 FR-P0-11).
- **FR-P2-04:** Online adapter exit tuning tightens on wins (toward zero) and widens on losses; no one-directional drift (v3.0 FR-P0-12).
- **FR-P2-05:** Liquidation heatmap receives actual token USD price, not `ta_price_change_1h` percentage (v3.0 FR-P0-13).
- **FR-P2-06:** `reset-paper` wipes only paper-mode signal_features rows, preserves production ML training data (v3.0 FR-P0-14).

**Signal quality (from v3.0 triage):**
- **FR-P2-07:** ATR computation failures log warnings and return sentinel, never silently zero (v3.0 FR-P0-16).
- **FR-P2-08:** 4h indicator computed from true 4h-boundary bars, not `closes[::4]` stride (v3.0 FR-P0-17).
- **FR-P2-09:** Buy-pressure weighted by USD volume, not transaction count (v3.0 FR-P0-18).
- **FR-P2-10:** Regime detection reads CEX BTC data (Binance/Coinbase), not DexScreener DEX candles (v3.0 FR-P0-19).
- **FR-P2-11:** Regime classifier applies 0.5% hysteresis band to avoid flicker around 3% threshold (v3.0 FR-P0-20).
- **FR-P2-12:** Hard stop uses ATR-adaptive formula `max(-0.25, -3 * atr_pct)` with fixed -20% fallback (v3.0 FR-P0-35; depends on FR-P2-07).

**Config hardening (from v3.0 triage):**
- **FR-P2-13:** Drifted exit params reset in `ml_control.json` — take_profit=0.15, stop_loss_hard=-0.20, stop_loss_trailing=-0.10 (v3.0 FR-P0-21).
- **FR-P2-14:** Drifted size multipliers reset — spot_mult=1.0, prediction_mult=1.0 (v3.0 FR-P0-22).
- **FR-P2-15:** Real-signal gate thresholds reset to round defaults (v3.0 FR-P0-23); tw_corroborated_min removed entirely given Grok P2 removed.
- **FR-P2-16:** Pipeline caps reviewed; if inflated vs code defaults (LC=55 vs 35), reset to conservative unless evidence supports current values (v3.0 FR-P0-24).
- **FR-P2-17:** Sideways-exit params validated against extended hold times or adjusted (v3.0 FR-P0-25).
- **FR-P2-18:** Aggregate modifier cap enforced — total modifier contribution ≤30 pts per token (v3.0 FR-P0-26).
- **FR-P2-19:** Triple-bonus corroboration condition updated to reflect 4-pipeline reality (v3.0 FR-P0-27).
- **FR-P2-20:** Regime confidence wired into scoring as multiplier or threshold gate (v3.0 FR-P0-28).

**New — trading discipline:**
- **FR-P2-21:** Every trade path passes through `risk_gate.py` or equivalent pre-trade risk check; CI pre-merge hook rejects any trade-emitting code path that bypasses the gate.
- **FR-P2-22:** Dry-run simulator replays last 30 days of signals through current config and asserts ≥1 simulated trade; if zero, config is wrong and live start blocked.
- **FR-P2-23:** Every trade log entry carries `alert_id` linked to source pipeline (P1/P3/P4/P5) with timestamp — used as foundation for Phase 3 attribution.

**Investigation:**
- **FR-P2-24:** LP events P4 diagnosed (v3.0 FR-P0-34); either revived with working WSS or explicitly disabled with rationale written to `history/decisions/` and removed from corroboration matrix.

### Phase 3 — LEARNING (target 2026-Q3) ⚠️ GATED on arch-review #2 `| model: opus |`

- **FR-P3-01:** Attribution ledger infrastructure writes `data/attribution/{signal_id}_{trade_id}.jsonl` per closed trade; schema includes signal source, weight at trade time, trade outcome, counterfactual estimate.
- **FR-P3-02:** Weight-update cycle gated by shuffle-test: permute signal-to-trade mapping, recompute attribution; if permuted magnitude ≥50% of real, no weight write that cycle.
- **FR-P3-03:** Attribution normalized by per-signal fire frequency to prevent high-frequency-pipeline dominance.
- **FR-P3-04:** Regime-change detector (realized-vol z-score or HMM state switch) freezes weight updates for 14 days after detected transition.
- **FR-P3-05:** Weight updates require ≥100 trades in attribution window AND samples drawn from ≥2 classified regimes.
- **FR-P3-06:** Weight-update cadence controller (daily / weekly / per-N-trades) driven by config; Jarvis proposes cadence via PR, Eric merges manually this phase.
- **FR-P3-07:** Offline retrain exit reset — offline refits reset exit params + real-signal gates + size multipliers to defaults to prevent online-drift accumulation (v3.0 FR-P0-29).
- **FR-P3-08:** GBT MIN_SAMPLES raised from 50 to 100 AND dead Grok/Apify features removed from FEATURE_COLUMNS (v3.0 FR-P0-30).
- **FR-P3-09:** `MIN_SAMPLES` mutation fixed to be thread-safe — local or class attribute, not global (v3.0 FR-P0-31).
- **FR-P3-10:** EMA tuner bounded by floor/ceiling constraints: take_profit ∈ [0.08, 0.25], stop_loss_hard ∈ [-0.25, -0.10], trailing ∈ [-0.15, -0.05] (v3.0 FR-P0-32).
- **FR-P3-11:** Closed-loop smoke test: inject synthetic attribution delta, observe weight change within ≤24h, observe forward-trade selection change.
- **FR-P3-12:** 2026-10-17 6-month checkpoint evaluated against 4-of-6 vector gate (see ACCEPTANCE CRITERIA below); pivot or continue per pre-committed rule.

### Phase 4 — SELF-IMPROVING (target 2026-Q4) ⚠️ GATED on arch-review #2 `| model: sonnet |`

- **FR-P4-01:** Jarvis improvement-PR pipeline operational: `/research` → `/create-prd` → `/implement-prd` (cross-repo worktree into crypto-bot) → `gh pr create`.
- **FR-P4-02:** Each Jarvis-authored PR carries pre-registered expected P&L delta AND forward window length in PR template.
- **FR-P4-03:** Worktree-isolation guarantee: cross-repo PR creation never touches crypto-bot main directory mid-trading; PR activation gated to scheduled restart window.
- **FR-P4-04:** PR quality baseline tracked: last-10-PR merge rate, expected-vs-actual P&L delta distribution, Eric review-time per PR (target ≤2h/week).
- **FR-P4-05:** Shadow-mode simulation infrastructure — simulates what Jarvis WOULD auto-merge, logs retrospective outcomes, does NOT execute.
- **FR-P4-06:** Cumulative drift meter: rolling sum of (actual − expected) P&L deltas over last 30 shadow merges; negative cumulative triggers halt.
- **FR-P4-07:** Phase regression criteria defined in `history/decisions/`: Phase 3→2 if weight-adjusted model underperforms frozen baseline over 30-day window; regime-change detector triggers phase hold.

### Phase 4.5 — PAPER-TO-LIVE BRIDGE (target 2027-Q1) ⚠️ GATED on arch-review #6

- **FR-P4.5-01:** Live execution runs with $500 hard cap at exchange sub-account level AND $0 P&L target — measure execution quality only.
- **FR-P4.5-02:** Execution-quality metrics logged per trade: fill rate vs backtest, slippage vs expected, rejection count by reason, API latency distribution.
- **FR-P4.5-03:** Fill-rate parity check — live 30-day fill rate within ±10% of backtest fill rate; deviation outside band triggers bridge-phase extension.
- **FR-P4.5-04:** Precondition check: paper balance ≥$300K sustained ≥14 days before bridge phase entry.

### Phase 5 — AUTONOMOUS (target 2027-Q1/Q2) ⚠️ GATED on arch-review #1, #3, #4, #5 `| model: opus |`

- **FR-P5-01:** Guardrail stack deployed: (a) forward-P&L gate vs pre-registered delta, (b) cumulative drift meter, (c) cost ceiling (API $/day), (d) security scrub (no secrets / PII / .env in PR), (e) profit delta floor, (f) fill-rate parity, (g) walk-forward CI harness with strict t-1 gap, (h) drain-to-zero gate — no auto-merge while positions open.
- **FR-P5-02:** $500 real-capital cap enforced at exchange sub-account funding level with scoped API key (no-transfer, no-withdraw permissions). Repo-level cap file is advisory only; hardware-level cap is the enforcement.
- **FR-P5-03:** Auto-merge counter resets to 0 on every Eric review; merges beyond 100 without human review auto-refused.
- **FR-P5-04:** Rollback protocol atomic three-step: freeze new entries → flatten open positions via TWAP over 2h → activate prior version.
- **FR-P5-05:** Shadow-mode proof: ≥48 of last 60 non-overlapping auto-merge events met or exceeded pre-registered expected delta on forward window; window spans ≥1 vol-regime transition.
- **FR-P5-06:** Eric kill-switch is API-key revocation (out-of-band), not a config flag the bot respects.
- **FR-P5-07:** No position-sizing PR ever auto-merges — Eric-only domain.
- **FR-P5-08:** Signal content NEVER passed to tool-enabled LLMs; content fence enforced on all summarization; PR-body whitelist check before `gh pr create`.
- **FR-P5-09:** Signal-source diversity floor — no single producer contributes >15% of attributed weight.

### Cross-phase (not gated)

- **FR-X-01:** `TELOS.md` crypto-bot entry updated from "Paper trading live" to "Pre-Phase 1 revival; 2026-07-16 vector-gate checkpoint; 2026-10-17 6-month vector-gate checkpoint."
- **FR-X-02:** Signal pipeline instrumentation: `data/signal_trace/` writes reason-fired / reason-not-fired per alert, committed (not gitignored) for visibility.

---

## NON-FUNCTIONAL REQUIREMENTS

- **Uptime:** Signal loop 24/7 with auto-restart; supervisor on Python path (post-2026-04-10 fix).
- **Latency:** Scoring cycle < 5 min.
- **Cost:** Monthly API spend under $100 across all active pipelines + Jarvis LLM calls.
- **Data integrity:** Paper trades persisted to SQLite with full signal breakdown for ML.
- **Observability:** Morning briefing surfaces bot state daily; dashboard health endpoint accurate for all 4 pipelines.
- **Security:** `RUN_MODE=paper` until Phase 4.5 bridge + arch-review #4 closure; no .env or wallet changes without explicit phase transition.
- **Cross-repo discipline:** All changes to crypto-bot code originate via `gh pr create` from a worktree; no direct pushes to crypto-bot `main`.

---

## ACCEPTANCE CRITERIA

### Phase 1 ISC — ALIVE

- [ ] `data/crypto_bot_state.json` shows `api_reachable=true` for ≥95% of polls in a 48h window | Verify: `python tools/scripts/verify_phase1_api.py --window 48h` exits 0 on pass, nonzero on fail
- [ ] Dead-man's-switch alert fires within 60 min of an induced 45-min API-down window | Verify: `python tools/scripts/induce_failure_smoke_test.py` exits 0 only if Slack alert recorded
- [ ] `data/crypto_bot_history.jsonl` shows `alerts_fired_count > 0` after induced failure | Verify: `python tools/scripts/verify_alert_counter.py` exits nonzero if counter still 0
- [ ] Root-cause file `history/decisions/{YYYY-MM-DD}_cryptobot-revival.md` exists with non-empty body before any restart | Verify: `test -s history/decisions/*_cryptobot-revival.md`
- [ ] Morning briefing crypto-bot section shows `red_flag: true` when `downtime_hours > 24` | Verify: `python tools/scripts/verify_briefing_redflag.py --downtime 25` exits 0 only if red flag present
- [ ] **Anti:** No bot restart attempted without root-cause file on disk | Verify: `python tools/scripts/verify_no_restart_without_rca.py` exits nonzero if any restart log entry lacks matching decision file
- [ ] Per-pipeline staleness warning emitted in dashboard for any pipeline with `last_success > 15min` | Verify: `python tools/scripts/verify_staleness_warning.py` exits 0 only if warning present under induced staleness

**ISC Quality Gate: PASS (6/6)** — 7 criteria (in-bounds), single-sentence, state-based, binary, anti-criterion present, every `| Verify:` uses an exit-nonzero script (no bare find/ls, no gitignored paths for verify data).

### Phase 2 ISC — TRADING

- [ ] Bot places ≥5 trades/week for 30 consecutive days | Verify: `python tools/scripts/verify_trade_cadence.py --days 30 --min-per-week 5` exits nonzero on shortfall
- [ ] No 7-day window in the 30-day observation shows zero trades | Verify: same verify script checks for 7-day zero-stretch, exits nonzero
- [ ] Every trade's `alert_id` resolves to one of {P1, P3, P4, P5} in trade log | Verify: `python tools/scripts/verify_trade_provenance.py` exits nonzero if any trade lacks valid alert_id
- [ ] Every code path that emits a trade passes through `risk_gate.py` | Verify: `python tools/scripts/verify_risk_gate_coverage.py` exits nonzero on uncovered path
- [ ] Trailing-50-trade profit factor > 1.1 AND win rate > 45% | Verify: `python tools/scripts/verify_phase2_pf_wr.py` exits nonzero if either threshold missed
- [ ] **Anti:** No trade bypasses the pre-trade risk gate | Verify: same `verify_risk_gate_coverage.py` (covers both directional and anti-criterion state)
- [ ] Dry-run simulator over last 30 days of signals produces ≥1 simulated trade under current config | Verify: `python tools/scripts/verify_dryrun_nonzero.py` exits nonzero if 0 trades simulated

**ISC Quality Gate: PASS (6/6)** — 7 criteria, single-sentence, state-based, binary, anti-criterion present, verify scripts return nonzero on forbidden state.

### Phase 3 ISC — LEARNING ⚠️ Preconditions: arch-review #2 closed

- [ ] Attribution ledger `data/attribution/` contains ≥1 entry per closed trade in last 30 days | Verify: `python tools/scripts/verify_attribution_coverage.py` exits nonzero on gap
- [ ] Every weight-update cycle in last 30 days passed shuffle-test OR was skipped | Verify: `python tools/scripts/verify_shuffle_test_gate.py` exits nonzero if any unshuffled update
- [ ] 30-day forward test shows weight-adjusted model beats frozen baseline by ≥2% absolute win rate | Verify: `python tools/scripts/verify_forward_beats_baseline.py` exits nonzero on miss
- [ ] Closed-loop smoke test: synthetic attribution delta produces observable weight change within 24h AND forward-trade selection change | Verify: `python tools/scripts/verify_closed_loop_smoke.py` exits nonzero on fail
- [ ] Regime-change detector freezes weight updates for 14 days after transition | Verify: `python tools/scripts/verify_regime_freeze.py` exits nonzero if updates leaked during freeze window
- [ ] **Anti:** No weight update written with fewer than 100 trades in attribution window | Verify: `python tools/scripts/verify_min_samples.py` exits nonzero if any write below threshold
- [ ] **Anti:** No weight update written with samples from a single regime | Verify: `python tools/scripts/verify_regime_diversity.py` exits nonzero if single-regime update found

**ISC Quality Gate: PASS (6/6)** — 7 criteria, state-based, binary, two anti-criteria (correlation-to-causation defense requires both), each anti-criterion has an exit-nonzero detector. ISC wording rewritten from v3.0's correlational framing per arch-review corrected-assumption #2.

### 2026-10-17 6-Month Vector Gate (checkpoint — pre-committed rule)

Evaluated on 2026-10-17 using data through that date. Continue to Phase 4 only if ≥4 of 6 pass:

- [ ] Gate-A: Phase 2 cleared — ≥5 trades/week for 30-day window, no 7-day zero stretch | Verify: `python tools/scripts/verify_phase2_cleared.py` exits 0/1
- [ ] Gate-B: Trailing-50-trade Sharpe > 1.0 | Verify: `python tools/scripts/verify_sharpe.py --min 1.0`
- [ ] Gate-C: Max drawdown < 15% over 90-day rolling window | Verify: `python tools/scripts/verify_max_dd.py --max 0.15`
- [ ] Gate-D: Top single trade < 25% of cumulative P&L | Verify: `python tools/scripts/verify_topshare.py --max 0.25`
- [ ] Gate-E: Attribution-to-forward-P&L Pearson correlation > 0.2 (Phase 3 only) | Verify: `python tools/scripts/verify_attrib_corr.py --min 0.2`
- [ ] Gate-F: Paper balance ≥ $115,000 | Verify: `python tools/scripts/verify_paper_balance.py --min 115000`

**Pivot action on fail (<4 of 6):** freeze ML/closed-loop work; Eric writes decision memo (continue-with-scope-cut vs retire); if continue, drop autonomy + 3x targets from 12mo scope. This rule is **signed 2026-04-17** — prior to any 6-month data existing, per CLAUDE.md loop-closure motivated-reasoning mitigation.

### Phase 4 ISC — SELF-IMPROVING ⚠️ Preconditions: arch-review #2 closed

- [ ] `gh pr list --author jarvis` shows ≥4 merged improvement PRs per month over 3 months | Verify: `python tools/scripts/verify_jarvis_pr_cadence.py` exits nonzero on shortfall
- [ ] Every Jarvis PR body contains a pre-registered expected P&L delta and forward window | Verify: `python tools/scripts/verify_pr_registration.py` exits nonzero on any PR missing both fields
- [ ] Eric's PR review time ≤2h/week over rolling 4-week window | Verify: `python tools/scripts/verify_review_time.py --max-hours-week 2` exits nonzero on exceed
- [ ] Last-10-PR merge rate ≥70% | Verify: `python tools/scripts/verify_pr_merge_rate.py --min 0.7` exits nonzero on miss
- [ ] Shadow-mode simulation has logged ≥30 events with retrospective outcomes | Verify: `python tools/scripts/verify_shadow_event_count.py --min 30` exits nonzero on miss
- [ ] **Anti:** No PR merged without the expected-delta field populated | Verify: `python tools/scripts/verify_pr_registration.py --strict` returns nonzero if any merged PR lacked the field
- [ ] Phase regression criteria documented in `history/decisions/phase-regression-rules.md` | Verify: `test -s history/decisions/phase-regression-rules.md`

**ISC Quality Gate: PASS (6/6)**

### Phase 4.5 ISC — PAPER-TO-LIVE BRIDGE ⚠️ Preconditions: arch-review #6 closed, paper 3x sustained ≥14 days

- [ ] Live account funded to exactly $500 at exchange sub-account level with scoped API key (no transfer/withdraw perms) | Verify: `python tools/scripts/verify_subaccount_cap.py` exits nonzero if balance > $500 OR permissions broader than trading-only
- [ ] Live-30d fill rate within ±10% of backtest-30d fill rate | Verify: `python tools/scripts/verify_fill_parity.py --band 0.10` exits nonzero on deviation
- [ ] Slippage-per-trade distribution median within ±20% of expected | Verify: `python tools/scripts/verify_slippage.py --band 0.20` exits nonzero on miss
- [ ] API latency p99 < 2 seconds over 30-day window | Verify: `python tools/scripts/verify_api_latency.py --p99-max 2000ms`
- [ ] **Anti:** No live trade P&L target set (explicitly disabled) | Verify: `python tools/scripts/verify_no_pnl_target.py` exits nonzero if any config sets nonzero P&L target during bridge
- [ ] **Anti:** Live account balance never exceeds $500 during entire bridge phase | Verify: `python tools/scripts/verify_subaccount_cap.py --historical` reads exchange statements, exits nonzero on any > $500 observation

**ISC Quality Gate: PASS (6/6)**

### Phase 5 ISC — AUTONOMOUS ⚠️ Preconditions: arch-review #1, #3, #4, #5 closed

- [ ] 8-guardrail stack deployed and passing: forward-P&L gate, drift meter, cost ceiling, security scrub, profit delta floor, fill-rate parity, walk-forward CI, drain-to-zero gate | Verify: `python tools/scripts/verify_guardrail_stack.py` exits nonzero on any missing/disabled guardrail
- [ ] ≥48 of last 60 non-overlapping auto-merges met/exceeded pre-registered expected delta | Verify: `python tools/scripts/verify_automerge_pass_rate.py --min 48 --window 60`
- [ ] Last 60-merge window spans ≥1 regime-classifier transition | Verify: `python tools/scripts/verify_regime_coverage.py` exits nonzero on single-regime window
- [ ] ≥1 successful auto-rollback of profit-regressing merge logged in last 90 days | Verify: `python tools/scripts/verify_rollback_event.py --days 90 --min 1`
- [ ] Zero secrets, .env values, or PII appear in any auto-merged PR description in last 90 days | Verify: `python tools/scripts/verify_pr_security_scrub.py --days 90` exits nonzero on any leak
- [ ] **Anti:** No auto-merge occurs while any position is open | Verify: `python tools/scripts/verify_drain_to_zero.py` exits nonzero on violation
- [ ] **Anti:** No auto-merge raises or modifies `$500` cap in any config path | Verify: `python tools/scripts/verify_cap_immutable.py` exits nonzero if any PR diff touches cap value
- [ ] **Anti:** No position-sizing change auto-merges (Eric-only) | Verify: `python tools/scripts/verify_no_automerge_sizing.py` exits nonzero on violation

**ISC Quality Gate: PASS (6/6)** — 8 criteria (at ceiling), 3 anti-criteria covering highest blast-radius violations.

### Ideal-State Gate (2027-04-17)

- [ ] Paper balance ≥ $300,000 sustained ≥14 days | Verify: `python tools/scripts/verify_paper_3x_sustained.py`
- [ ] ≥180 closed trades, trailing 90-day Sharpe > 1.5 | Verify: `python tools/scripts/verify_ideal_sharpe.py`
- [ ] ≥90% of recent weight updates traceable to attribution P&L delta | Verify: `python tools/scripts/verify_weight_provenance.py --min 0.9`
- [ ] ≥12 Jarvis auto-merged PRs in `history/pull_requests/` with zero security leaks | Verify: `python tools/scripts/verify_pr_security_scrub.py --days 365 --min-count 12`
- [ ] Eric's monthly git-commit count to crypto-bot ≤16 AND none are diagnostic fixes to producer health | Verify: `python tools/scripts/verify_eric_commit_budget.py`
- [ ] **Anti:** No 30-day zero-trade gap occurred in prior 365 days | Verify: `python tools/scripts/verify_no_zero_trade_gap.py --max-gap-days 30`
- [ ] **Anti:** Real-capital balance never exceeded $500 pre-3x milestone | Verify: `python tools/scripts/verify_subaccount_cap.py --historical --until-3x`

**ISC Quality Gate: PASS (6/6)**

---

## SUCCESS METRICS

- **Phase 1:** 7-day continuous uptime; dead-man's switch proven via induced failure; morning briefing surfaces status proactively
- **Phase 2:** ≥20 trades in 30-day window, no 7-day zero stretch, trailing-50 profit factor >1.1, win rate >45%
- **Phase 3:** Closed-loop smoke test passes; 2026-10-17 vector gate passes 4 of 6
- **Phase 4:** ≥4 Jarvis PRs/month, ≥70% merge rate, ≤2h/week Eric review time
- **Phase 4.5:** Live fill parity within ±10% over 30 days, p99 latency <2s
- **Phase 5:** ≥48/60 auto-merge pass rate, ≥1 rollback-with-drain-to-zero event, zero security leaks in 90-day window
- **Ideal state:** Paper 3x sustained, Sharpe >1.5, Eric ≤16 commits/month, zero diagnostic-fix commits by Eric

---

## OUT OF SCOPE

- Solana execution, Hyperliquid perps (defer indefinitely)
- Mobile app / jarvis-app integration
- Leveraged products (whitelist-deny until Phase 5 arch-review closure)
- VPS / Docker
- New signal pipelines beyond P1/P3/P4/P5 until Phase 3 proves closed-loop
- Tiered/partial exit (Position model refactor)
- Volume-drop exit signal
- Scalar-return gates ("1.5x at 6mo" replaced by vector gate)
- Real capital > $500 before paper-3x

---

## DEPENDENCIES AND INTEGRATIONS

- **LunarCrush API:** P1 pipeline — free tier, valid key
- **Moralis Streams:** P3 whale pipeline — webhook via ngrok, `MORALIS_WEBHOOK_SECRET`, active stream
- **QuickNode:** P4 LP events — WSS endpoints required (tier status pending — see Open Questions)
- **DexScreener:** P5 depth + price — free, rate-limited by semaphore
- **Slack MCP:** dead-man's switch alerts to `#epdev`, improvement-PR notifications to same
- **GitHub CLI (`gh`):** Jarvis improvement-PR pipeline via cross-repo worktree
- **Exchange sub-account provider (TBD):** Phase 5 real-capital cap enforcement — see Open Questions
- **SQLite:** `bot.db` — trade persistence, ML training, WAL mode
- **epdev orchestration:** SENSE collector (`tools/scripts/crypto_bot_sense.py` or equivalent), morning briefing (`tools/scripts/hook_session_start.py`), worktree helpers (`tools/scripts/lib/worktree.py`)

---

## RISKS AND ASSUMPTIONS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phase 1 revival restarts bot without root-causing 77/77 dead state | HIGH | HIGH | FR-P1-01 + Phase 1 anti-criterion enforcement via `verify_no_restart_without_rca.py` |
| Phase 2 trade-count met by relaxing thresholds (junk trades) | MED | HIGH | FR-P2-05 profit factor + win-rate gates rule out low-quality churn |
| Attribution correlation-to-causation fallacy not actually caught by shuffle-test | MED | HIGH | Multi-layered: shuffle-test + fire-frequency normalization + N≥100 + regime detector; any single layer failing still leaves others |
| 6-month vector gate bent by motivated reasoning on 2026-10-17 | MED | HIGH | Rule signed 2026-04-17 in `history/decisions/`; pivot action pre-committed |
| Exchange sub-account provider doesn't support scoped API keys or hard funding caps in Canada | MED | HIGH | Open Question Q3; must be resolved before Phase 5 entry |
| Jarvis PR pipeline ships cosmetic refactors instead of profit-moving changes | MED | MED | FR-P4-02 expected-delta registration + FR-P4-04 outcome tracking |
| Crypto-regime shift (LUNA/FTX/halving analogue) invalidates shadow-mode window | MED | HIGH | FR-P5-05 requires ≥1 regime transition in window; Mahalanobis distance re-qualification |
| Rollback orphans open positions at worse prices than regression | MED | HIGH | FR-P5-04 drain-to-zero gate + atomic 3-step protocol |
| Supply-chain signal poisoning (adversary-owned sentiment source) | LOW | HIGH | FR-P5-09 source-diversity floor (no single producer >15% weight) |
| Prompt injection via signal content into Jarvis planning LLM | LOW | HIGH | FR-P5-08 content fence + no-tool LLM for signal summarization |
| Closed-loop bot diverges and Eric doesn't notice (4h/week too thin) | MED | MED | Phase-transition approvals separate budget; morning briefing red-flag surfacing |

### Assumptions

- Current 4-pipeline set (P1/P3/P4/P5) contains enough signal diversity for closed-loop attribution to identify marginal contributions once shuffle-test gates applied
- Post-reset $100K paper wallet provides adequate base for 12-month 3x trajectory test
- Jarvis improvement-PR pipeline quality improves with PR quantity (learning curve) rather than plateaus
- Eric's 4h/week steady-state is achievable once phase-transition approvals and arch-review gates are resolved
- Cross-repo worktree model works for `crypto-bot` repo (verified for `epdev` already)
- Market regime shifts during 12-month window will occur at least twice (bull/bear/chop) — required for regime-diversity ISC to be achievable, not just testable

---

## OPEN QUESTIONS

1. **Dead-man's-switch failure mode (Phase 1 blocker):** Is the `alerts_fired_count=0` across 77 dead polls caused by (a) counter-increment logic not reached, (b) alerting path broken, or (c) Slack integration silent failure? Needs Phase 1 diagnosis before fix design.
2. **QuickNode tier (Phase 2 FR-P2-24):** Does Eric's current QuickNode tier include WSS for Base/Arbitrum? If not, P4 is permanently disabled — affects corroboration matrix and Phase 3 attribution surface.
3. **Exchange sub-account provider (Phase 5 blocker):** Which exchanges serving Canadian residents support API-key-scoped sub-accounts with hard funding caps? Coinbase? Kraken? Bitbuy? Without this, FR-P5-02 cannot be implemented.
4. **Regime classifier choice (Phase 3 blocker):** HMM state switch, realized-vol z-score, volatility-ratio classifier, or ensemble? Each has different false-positive/negative tradeoffs for FR-P3-04.
5. **Attribution method (Phase 3 blocker):** SHAP, Shapley values, causal counterfactual ablation, or double/debiased ML? Each carries different identifiability guarantees; choice affects FR-P3-02 shuffle-test design.
6. **Model routing annotations for ISC criteria:** This PRD ships with no `| model: X |` annotations (safe default per `/create-prd` rule 4). Before `/implement-prd` invocation, review each FR group and annotate — candidate mapping: Phase 1 verification scripts → `sonnet` (code generation); Phase 2 correctness fixes → `sonnet`; Phase 3 attribution architecture + Phase 5 guardrails → Opus (no annotation, judgment/security); Phase 4 PR pipeline scaffolding → `sonnet`.
7. **Morning-briefing red-flag threshold:** FR-P1-06 uses >24h downtime — is 24h the right threshold or should it be shorter for an active trading system? Trade-off: alert fatigue vs missed revenue window.
8. **Pivot-action memo template (2026-10-17):** Should the decision memo template be drafted now (pre-data) per the motivated-reasoning mitigation, or left to emerge at the checkpoint? Recommend drafting now; tracked as Phase 3 sub-task.

---

**Next step:** `/implement-prd memory/work/crypto-bot/PRD_v4.md` — OQ1 RESOLVED 2026-04-19 (`history/decisions/2026-04-19_cryptobot-revival.md`); OQ6 RESOLVED 2026-04-19 (model pins applied above). Questions 3, 4, 5 deferred to their phase's pre-build sprint. UNBLOCKED.
