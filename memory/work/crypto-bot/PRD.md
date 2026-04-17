> **SUPERSEDED by PRD_v4.md on 2026-04-17.** v3.0 preserved for historical reference. See v4.0 for current outcome-shaped ISC and phase ladder.

# PRD: Crypto-Bot Profit Validation Sprint

**Version:** 3.0
**Date:** 2026-04-01
**Author:** Jarvis (deep code audit + research synthesis + architecture review)
**Status:** SUPERSEDED — replaced by PRD_v4.md on 2026-04-17. Activity-shaped ISC (35-bug list) replaced with outcome-shaped ISC (paper 3x, closed-loop learning, 6-phase ladder).

---

## OVERVIEW

The Crypto-Bot Profit Validation Sprint is a phased plan to take the existing crypto-bot from a buggy, untested codebase to a validated, data-driven trading system capable of producing real profit. A deep code audit (2 rounds, 8 parallel agents across 400KB+ of source) revealed 35 distinct issues: 10 critical bugs, 2 dead pipelines, 12 scoring/signal issues, 4 ML tuner defects, 8 infrastructure gaps, and 5 cleanup items. This PRD defines four phases: Phase 0 (fine-tune — fix all bugs, remove Grok P2, revive LP P4, reset drifted params, harden scoring), Phase 1 (paper trading operational 24/7), Phase 2 (data-driven tuning from real results), Phase 3 (go-live decision with conservative capital). Grounded in deep research (social alpha, whale tracking, profitable strategies, exit optimization) and full architecture review.

**Decision: Remove Grok P2 pipeline entirely.** Rationale: scoring zero, $5-10/mo API cost, research shows social alpha decays in minutes (not actionable at 5-min cycle), prediction feed was always blocked by cooldown bug. Bot becomes a 4-pipeline system (P1 LC, P3 Whale, P4 LP, P5 Depth) — honest about what actually works.

---

## PROBLEM AND GOALS

- **35 issues found in deep audit (2 rounds, 8 parallel agents, 400KB+ source).** 10 critical bugs that would corrupt paper trading results. 2 dead pipelines. 12 scoring/signal issues. 4 ML tuner defects. 8 infrastructure gaps. 5 cleanup items.
- **No validated trades exist.** Paper wallet at $5,000 with zero trades.
- **Grok P2 is waste.** $5-10/mo for zero signal. Research says social alpha decays too fast for 5-min cycles.
- **Exit strategy is miscalibrated.** Take-profit at 28.8% never triggers. Hard stop drifted to -27.86% via tuner bug.
- **ML pipeline disabled and undertrained.** 36 features with 50 min samples (need 360+). Online tuner has directional bug.

**Goals:**
- Fix all critical bugs before paper trading produces data (garbage in = garbage out)
- Remove dead weight (Grok P2), revive LP P4
- Reset drifted parameters to sane defaults
- Establish baseline profitability from 50+ validated paper trades
- Make data-grounded go/no-go decision for real capital

---

## NON-GOALS

- Tiered/partial exit strategy (requires Position model refactor — defer post-Phase 3)
- Volume-drop exit signal (no data to calibrate — defer)
- New signal pipelines or data sources
- Solana execution (signing bug), Hyperliquid perps (EIP-712 bug)
- VPS deployment, Dockerization
- Target "5x in 2 months" — replaced with evidence-based 1-3%/month target
- Mobile app / jarvis-app integration

---

## USERS AND PERSONAS

- **Eric (operator):** Wants profit. Needs clear daily P&L visibility, push notifications to Slack. ADHD style — prefers alerts over dashboards.
- **Jarvis (autonomous agent):** Health checks, daily digests, anomaly alerts via scheduled tasks.

---

## USER JOURNEYS OR SCENARIOS

1. **Morning check:** Eric opens Slack, sees overnight digest — positions, P&L, pipeline health. Decides to intervene or not.
2. **Alert scenario:** Pipeline failure detected, alert pushed to Slack. Jarvis offers diagnosis.
3. **Weekly review:** Eric runs `/paper-report` — win rate, hold time, best/worst trades, per-pipeline breakdown.
4. **Go-live decision:** After 50+ paper trades, Eric reviews metrics against ISC gates. Explicit yes/no.

---

## FUNCTIONAL REQUIREMENTS

### Phase 0: Fine-Tune (Pre-Paper Bug Fix + Strategy Hardening)

> 35 items ordered for build flow: foundations → remove dead code → fix bugs → reset params → harden scoring → harden ML → infrastructure → investigate

#### Step 1: Foundation — Database + Infrastructure (build first, everything depends on these)

- **FR-P0-01:** Add secondary DB indexes — zero indexes on any table means full scans on every query. Add indexes on: `trades(exit_price, created_at)`, `signal_features(trade_id, created_at)`, `portfolio_snapshots(created_at)`, `model_weights(created_at)` | `db.py`
- **FR-P0-02:** Add foreign key constraints — `signal_features.trade_id → trades.id` is conceptual only. Add real FK with CASCADE delete to prevent orphan rows | `db.py`
- **FR-P0-03:** Fix stale startup script — `daily-agent-run.bat` points to old OneDrive path, not current `C:\Users\ericp\Github\crypto-bot`. Update all paths | `daily-agent-run.bat`
- **FR-P0-04:** Fix settings panel threshold disconnect — `config/settings.py` ML pipeline panel has `signal_threshold_base=40` but getter hardcodes env var (70). Ensure `apply_overrides()` propagates correctly or remove dead panel value

#### Step 2: Remove Dead Code (reduce noise before fixing anything)

- **FR-P0-05:** Remove Grok P2 pipeline entirely — delete `ingestion/grok_scraper.py` calls from signal loop, set `grok_mentions` weight to 0, remove Grok query pool logic from `run_full_cycle()`, remove `XAI_API_KEY` dependency. Keep file in repo but disconnect from scoring | `signal_aggregator.py`, `dashboard/app.py`, `config/settings.py`
- **FR-P0-06:** Remove dead Apify/Twitter references — fields like `apify_mention_count`, `apify_followed_mentions` persist in signal_aggregator.py despite Apify removal. Clean up to reduce confusion | `signal_aggregator.py`
- **FR-P0-07:** Update corroboration matrix for 4-pipeline reality — remove all P2 (Grok/Twitter) bonus entries including `tw_score`/`tw_active` references, recalibrate remaining bonuses. Core edge becomes P1+P3 (LC x Whale) and P1+P5 (LC x Depth) | `signal_aggregator.py:1331-1405`
- **FR-P0-08:** Remove dead Grok features from GBT feature set — `weight_tuner.py` FEATURE_COLUMNS includes Grok/Apify features that will always be zero. Remove to reduce dimensionality | `weight_tuner.py:72-110`

#### Step 3: Critical Bugs — Trade Execution (fix P&L accuracy before any trades run)

- **FR-P0-09:** Fix short P&L calculation on close — `paper_wallet.py:315-317` computes `proceeds - size_usd` which gives wrong sign for shorts. Must invert P&L when `is_short=True` | `execution/paper_trader.py`
- **FR-P0-10:** Fix short position restore — `paper_wallet.py:99` `restore_from_db()` only queries `action=="buy"` and never sets `is_short=True`. Shorts restored after restart have wrong P&L direction | `execution/paper_trader.py`
- **FR-P0-11:** Fix production trailing stop peak tracking — `stop_loss.py:115` passes `peak_price=entry_price`, making trailing stop equivalent to second hard stop. Must track actual peak price per position | `risk/stop_loss.py`
- **FR-P0-12:** Fix online adapter exit tuning direction bug — `online_adapter.py:473-477` moves `stop_loss_hard` in same direction (wider) regardless of win or loss. Wins should tighten (add toward zero), losses should widen. One-directional drift explains -20% → -27.86% | `signals/online_adapter.py`
- **FR-P0-13:** Fix liquidation heatmap price reference — `signal_aggregator.py:1670` passes `ta_price_change_1h` (a percentage like -2.5) as `current_price` USD to `fetch_liq_heatmap()`. Must pass actual token price | `signal_aggregator.py`
- **FR-P0-14:** Fix reset-paper data wipe — `dashboard/app.py:2228` deletes ALL signal_features rows regardless of trade mode. Must filter to paper-mode trades only, preserving production ML training data | `dashboard/app.py`
- **FR-P0-15:** Fix agent context query — `_gather_agent_context` (dashboard/app.py:2549-2604) references wrong column names in signal_features queries. Fix column references to match actual schema | `dashboard/app.py`

#### Step 4: Critical Bugs — Signal Quality (fix data feeding into scoring)

- **FR-P0-16:** Fix ATR silent failure — `momentum.py:285-286` catches all exceptions with bare `except Exception: pass`. ATR failures must log warnings and return a sentinel so callers know data is missing, not silently zero | `signals/momentum.py`
- **FR-P0-17:** Fix fake 4h filter — `momentum.py:296` takes every 4th 1h bar (`closes[::4]`) instead of aligning to real 4h boundaries. Misaligned bars produce incorrect 4h indicators | `signals/momentum.py`
- **FR-P0-18:** Fix buy pressure calculation — currently counts transactions, not volume. A single 100 BTC whale buy counts the same as a 0.001 BTC dust tx. Weight by USD volume | `signals/` (identify exact file)
- **FR-P0-19:** Fix regime detection data source — currently uses DexScreener BTC DEX candles (lower fidelity, fragmented liquidity). Should use CEX BTC data (Binance/Coinbase) for more accurate regime classification | `signals/regime.py`
- **FR-P0-20:** Add regime hysteresis — 3% BTC return threshold with no buffer causes flickering (+2.9% = Range, +3.1% = Bull). Add 0.5% hysteresis band: enter bull at +3.0%, exit bull at +2.5% | `signals/regime.py`

#### Step 5: Config Reset (depends on bug fixes — otherwise tuner re-drifts values)

- **FR-P0-21:** Reset drifted exit params in `ml_control.json` — `take_profit`: 0.288 → 0.15, `stop_loss_hard`: -0.278 → -0.20, `stop_loss_trailing`: -0.139 → -0.10. These drifted via the directional bug in FR-P0-12 | `data/ml_control.json`
- **FR-P0-22:** Reset drifted size multipliers — `spot_mult`: 0.69 → 1.0, `prediction_mult`: 0.54 → 1.0. Drifted from tuner on insufficient data (6 trades) | `data/ml_control.json`
- **FR-P0-23:** Reset drifted real-signal gate thresholds to round defaults — `lc_corroborated_min`: 35.15 → 35, `tw_corroborated_min` → remove (P2 gone), `wh_corroborated_min`: 15.10 → 15, etc. | `data/ml_control.json`
- **FR-P0-24:** Review pipeline caps — current caps (LC=55, Depth=45) are much higher than code defaults (LC=35, Depth=30). Assess whether inflated caps cause weak tokens to score above threshold. Consider resetting to code defaults | `data/ml_control.json`
- **FR-P0-25:** Validate sideways exit params — 2.5% band after 24h needs assessment against extended hold times (7-14 days for moderate/swing). May need wider band or longer activation delay | `data/ml_control.json`

#### Step 6: Scoring Engine Hardening (depends on dead code removal + config reset)

- **FR-P0-26:** Add aggregate modifier cap — 134 pts of uncapped additive modifiers can carry a weak best_single (20 pts) over threshold. Add `total_modifier_cap` (e.g., 30 pts) so modifiers cannot exceed ~40% of threshold | `signal_aggregator.py`
- **FR-P0-27:** Fix triple bonus condition — `signal_aggregator.py:1384` checks `active_count >= 3` but should check specific pipeline combinations now that P2 is removed. Update to reflect 4-pipeline reality | `signal_aggregator.py`
- **FR-P0-28:** Wire regime confidence into scoring — regime.py computes confidence but it's never used for gating. Use as a multiplier: low-confidence regime → reduce position sizing or raise threshold | `signals/regime.py`, `signal_aggregator.py`

#### Step 7: ML Tuner Hardening (depends on exit bug fix + config reset)

- **FR-P0-29:** Add offline retrain exit reset — offline retrain never resets exit params, real-signal gates, or size multipliers. Add reset-to-defaults when offline retrain runs so online drift doesn't accumulate indefinitely | `signals/weight_tuner.py`
- **FR-P0-30:** Raise GBT MIN_SAMPLES from 50 to 100 — with 36 features (fewer after Grok removal), 50 is overfitting territory. Also remove dead Grok/Apify features from FEATURE_COLUMNS | `signals/weight_tuner.py`
- **FR-P0-31:** Fix global MIN_SAMPLES mutation — `weight_tuner.py:670-673` mutates global variable, not thread-safe. Use local variable or class attribute | `signals/weight_tuner.py`
- **FR-P0-32:** Add EMA tuner floor/ceiling constraints — prevent extreme drift: take_profit [0.08, 0.25], stop_loss_hard [-0.25, -0.10], trailing [-0.15, -0.05]. Tighter than current bounds | `signals/online_adapter.py`
- **FR-P0-33:** Add per-pipeline staleness tracking — if LunarCrush fails, bot scores with stale cache silently. Flag stale data in pipeline health endpoint and log warnings when scoring with data older than 15 minutes | `signal_aggregator.py`, `dashboard/app.py`

#### Step 8: Pipeline Investigation (last — depends on everything else being clean)

- **FR-P0-34:** Diagnose and fix LP events P4 — check `QUICKNODE_*_WSS` env vars, verify WebSocket listeners start, verify events flow into `_event_queue`. If WSS unavailable on Eric's tier, explicitly disable P4 and remove from corroboration matrix | `ingestion/onchain_indexer.py`, `.env`
- **FR-P0-35:** Wire ATR into hard stop — add ATR-adaptive logic to `check_hard_stop()` with -25% absolute floor: `max(-0.25, -3 * atr_pct)`, falling back to fixed -20% when ATR unavailable. Depends on ATR silent failure fix (FR-P0-16) | `risk/stop_loss.py`

### Phase 1: Paper Trading Operational (Weeks 1-2 after Phase 0)

- **FR-001:** Bot runs signal loop continuously (24/7) via uvicorn, completing full scoring cycles every 5 minutes
- **FR-002:** Paper trades execute automatically when composite score exceeds threshold (70 for spot)
- **FR-003:** Daily digest pushed to Slack `#jarvis-inbox` — positions open/closed, daily P&L, pipeline health, trade count
- **FR-004:** Dashboard accessible at localhost:8080 with live position table, P&L chart, pipeline status

### Phase 2: Data-Driven Tuning (Weeks 3-4)

- **FR-005:** After 50+ closed paper trades, verify online EMA tuner is running and producing weight updates
- **FR-006:** After 100+ labeled trades, enable GBT mini-retrain (`use_ml_pipeline: true`)
- **FR-007:** Generate paper trading report: win rate, profit factor, Sharpe ratio, max drawdown, avg hold time, per-pipeline contribution
- **FR-008:** Based on data: adjust threshold, disable underperforming pipelines, tune exits from actual trade outcome distribution
- **FR-009:** If win rate < 45% after 50+ trades, trigger strategy review — entries vs exits analysis

### Phase 3: Go-Live Decision (Weeks 5-6)

- **FR-010:** Go-live ISC gate: win rate >= 50%, profit factor >= 1.2, max drawdown <= 20%, 50+ closed trades
- **FR-011:** If gate passes: $500 max real capital on Base chain, MAX_TRADE_SIZE=0.05, SIGNAL_THRESHOLD=65+
- **FR-012:** If gate fails: document failure, propose changes, return to Phase 2
- **FR-013:** First 7 days live: all trades require Telegram approval
- **FR-014:** After 30+ live trades: review real vs paper delta. Pause if live win rate >10% worse

---

## NON-FUNCTIONAL REQUIREMENTS

- **Uptime:** Signal loop 24/7 with auto-restart on crash
- **Latency:** Scoring cycle < 5 minutes (expect faster with Grok removed — saves ~30s/cycle)
- **Cost:** Monthly API spend under $100 (reduced by removing Grok $5-10/mo)
- **Data integrity:** All paper trades persisted to SQLite with signal breakdown for ML
- **Monitoring:** Pipeline health endpoint reports accurate status for all 4 active pipelines
- **Security:** RUN_MODE=paper until explicit Phase 3 approval. No .env or wallet changes

---

## ACCEPTANCE CRITERIA (ISC)

### Phase 0 ISC: Fine-Tune Complete

- [ ] All 35 Phase 0 items resolved — each FR has a passing test, verified fix, or documented "deferred with rationale" [E][A] | Verify: Checklist walkthrough of FR-P0-01 through FR-P0-35 with evidence per item
- [ ] Short position P&L is correct on close for both profit and loss scenarios [E][M] | Verify: Unit test — short entry at $100, close at $80 shows +20% profit, close at $120 shows -20% loss
- [ ] Trailing stop tracks actual peak price in both paper and production modes [E][M] | Verify: Unit test — position peaks at $150, current $130, trailing stop fires at 10% from peak ($135)
- [ ] Online adapter tightens stops on wins and widens on losses [E][M] | Verify: Unit test — simulate win, assert stop_loss_hard moved toward zero; simulate loss, assert moved away
- [ ] Grok P2 pipeline produces no API calls and no tw_score appears in scoring [E][M] | Verify: Run one cycle, `grep xai logs/` returns zero hits, `last_cycle_scores.json` has no tw_score field
- [ ] Take-profit reads 0.15 and hard stop reads -0.20 in ml_control.json [E][M] | Verify: `python -c "import json; d=json.load(open('data/ml_control.json')); print(d['exits']['take_profit'], d['exits']['stop_loss_hard'])"`
- [ ] Aggregate modifier contribution does not exceed thirty points for any token [I][M] | Verify: Add assertion in score() that total_modifiers <= 30, run full cycle with no assertion failures
- [ ] DB tables have secondary indexes and no query requires a full table scan [I][M] | Verify: `sqlite3 bot.db ".indexes"` shows indexes on trades, signal_features, portfolio_snapshots

**ISC Quality Gate: PASS (6/6)** — 8 criteria, single-sentence, state-based, binary, anti-criterion (#1 prevents regressions), all verified.

### Phase 1 ISC: Paper Trading Operational

- [ ] Signal loop completes full cycles every five minutes continuously [E][M] | Verify: `curl localhost:8080/api/pipeline-health` returns all pipelines ok for 24h+
- [ ] Paper wallet has fifty or more closed trades after two weeks [E][M] | Verify: `SELECT COUNT(*) FROM trades WHERE exit_price IS NOT NULL` >= 50
- [ ] Hard stop uses ATR with negative-twenty-five percent absolute floor [I][M] | Verify: Unit test — 15% ATR token gets -25% stop (floor), 5% ATR token gets -15% stop (3x ATR)
- [ ] No active pipeline reports zero contribution across above-threshold tokens [I][M] | Verify: `last_cycle_scores.json` breakdown shows no active pipeline at 0.0
- [ ] Daily Slack digest arrives in jarvis-inbox before 9 AM ET [E][M] | Verify: 3+ consecutive daily digests in Slack history
- [ ] Bot does not execute real on-chain transactions [E][A] | Verify: `grep RUN_MODE .env` returns "paper"

**ISC Quality Gate: PASS (6/6)**

### Phase 2 ISC: Data-Driven Tuning

- [ ] Online EMA tuner has updated weights at least three times [I][M] | Verify: Log grep shows 3+ weight update events
- [ ] Paper trading report generated with win rate and profit factor [E][M] | Verify: Report file exists with numeric metrics
- [ ] Per-pipeline contribution analysis identifies top and bottom performers [I][M] | Verify: Report contains per-pipeline win-rate breakdown (P1/P3/P4/P5)
- [ ] Signal threshold adjusted based on data not assumptions [E][A] | Verify: Decision log entry cites trade data
- [ ] No parameter change made without supporting evidence [E][A] | Verify: Each ml_control.json change logged

**ISC Quality Gate: PASS (6/6)**

### Phase 3 ISC: Go-Live Decision

- [ ] Win rate exceeds fifty percent across fifty-plus closed paper trades [E][M] | Verify: `/paper-report` win_rate >= 0.50
- [ ] Profit factor exceeds one-point-two [E][M] | Verify: `/paper-report` profit_factor >= 1.2
- [ ] Maximum drawdown stayed below twenty percent [E][M] | Verify: Portfolio snapshots show no 20%+ drop from peak
- [ ] Eric has explicitly approved go-live [E][A] | Verify: Decision log entry exists
- [ ] Live trading uses five hundred dollars maximum [E][M] | Verify: Wallet balance <= $500
- [ ] No live trade executes without approval in first seven days [E][A] | Verify: All week-1 trades have approval_status=approved

**ISC Quality Gate: PASS (6/6)**

---

## SUCCESS METRICS

- **Phase 0:** All 35 issues resolved, zero critical bugs remaining, bot produces clean scoring cycles with 4 pipelines
- **Phase 1:** 50+ paper trades, all pipelines contributing
- **Phase 2:** Win rate >= 50%, profit factor >= 1.2, max drawdown < 20%
- **Phase 3:** Positive returns in first 30 live days (1-3% monthly target)
- **Honest baseline:** If paper shows win rate < 45%, the signal architecture needs fundamental changes — valid outcome

---

## OUT OF SCOPE

- Tiered/partial exit strategy (Position model refactor)
- Volume-drop exit signal
- Grok P2 pipeline (removed — decision documented)
- Solana execution, Hyperliquid perps
- VPS deployment
- New signal sources

---

## DEPENDENCIES AND INTEGRATIONS

- **LunarCrush API:** P1 pipeline — free tier, valid key required
- **Moralis Streams:** P3 whale pipeline — webhook via ngrok, MORALIS_WEBHOOK_SECRET + active stream
- **QuickNode:** P4 LP events — WSS endpoints needed (check/configure in .env)
- **DexScreener:** P5 depth + price — free, rate limits managed by semaphore
- **Slack MCP:** Daily digest delivery to `#jarvis-inbox`
- **Telegram Bot:** Trade notifications, Phase 3 approval workflow
- **SQLite:** bot.db — trade persistence, ML training data, WAL mode

---

## RISKS AND ASSUMPTIONS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phase 0 fixes introduce new bugs | Medium | High | Unit tests for each fix, run full scoring cycle after each change |
| Removing Grok reduces signal diversity below useful threshold | Low | Medium | 3 remaining pipelines (LC, Whale, Depth) + LP still provide corroboration. Monitor diversity in Phase 1 |
| Paper trading shows strategy doesn't work | Medium | High | Valid outcome — better to learn on paper. Triggers strategy review |
| ML tuner drifts again after reset | Medium | Medium | Tighter bounds (FR-P0-17) + offline retrain exit reset (FR-P0-15) |
| QuickNode WSS not available on free tier | Medium | Medium | If P4 can't be revived, bot runs on 3 pipelines — still viable |
| Bot runs but Eric doesn't monitor | Medium | Medium | Daily Slack digest forces visibility |

### Assumptions

- 4-pipeline corroboration (LC + Whale + LP + Depth) provides sufficient signal diversity
- Removing Grok saves $5-10/mo and reduces cycle time without losing alpha (research supports this)
- Current codebase bugs are fixable without major architectural changes
- $5,000 paper balance at $100/trade generates enough data in 2 weeks

---

## OPEN QUESTIONS

1. **Can QuickNode WSS be configured?** Check Eric's QuickNode tier — Build tier should include WSS. If not, P4 stays disabled.
2. **Should pipeline caps reset to code defaults?** ml_control.json caps (LC=55) are much higher than code defaults (LC=35). Need to decide: trust the tuner's inflation or reset to conservative values.
3. **What modifier cap is right?** Proposed 30 pts total — but need to check what the current average modifier contribution is in a real cycle to avoid cutting too aggressively.
4. **uvicorn vs Celery for 24/7?** uvicorn is simpler (no Redis). Which is more stable on Windows?
5. **Should the online EMA tuner be disabled during Phase 1?** Run with static params first to establish a clean baseline, then enable tuner in Phase 2? Or let it tune from the start?
6. **Base vs Arbitrum for go-live?** Lowest gas vs better liquidity depth for scored tokens.
