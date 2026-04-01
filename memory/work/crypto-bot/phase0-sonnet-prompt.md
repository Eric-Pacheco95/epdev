# Crypto-Bot Phase 0: Sonnet Execution Prompt

Copy everything below the line into a Sonnet session opened in `C:\Users\ericp\Github\crypto-bot`.

---

You are implementing Phase 0 of the crypto-bot profit validation sprint. This is a pre-existing Python trading bot with 400KB+ of source. A deep audit found 35 issues. You are fixing 27 of them — the well-specified ones. 8 items are marked SKIP (need Opus review for judgment calls).

## Context

- Working directory: `C:\Users\ericp\Github\crypto-bot`
- PRD with full details: `C:\Users\ericp\Github\epdev\memory\work\crypto-bot\PRD.md`
- The bot has 4 active signal pipelines: P1 LunarCrush, P3 Whale, P4 LP Events, P5 DEX Depth
- Grok P2 pipeline is being REMOVED (dead, $5-10/mo, zero signal)
- The bot has NEVER completed a paper trading run — zero validated trades
- Exit params in `data/ml_control.json` drifted via a tuner bug and need reset
- Do NOT change RUN_MODE. Do NOT touch .env secrets. Do NOT modify wallet files.

## Rules

1. Read each file BEFORE modifying it. Understand existing code before changing it.
2. Make minimal, targeted fixes. Do not refactor surrounding code, add docstrings, or "improve" things not listed.
3. After each step (group of related fixes), do a quick `python -c "import <module>"` smoke test to verify no syntax errors.
4. Commit after completing each Step (1 through 8). Use descriptive commit messages like `fix(phase0-step1): add DB indexes and FK constraints`.
5. If you encounter something unexpected that contradicts the spec below, STOP and note it — do not guess.
6. For items marked SKIP — do not implement them, just move on.

## Step 1: Foundation — Database + Infrastructure

### FR-P0-01: Add DB indexes
File: `db.py`
- Find the table creation code (CREATE TABLE statements)
- After each CREATE TABLE, add CREATE INDEX IF NOT EXISTS:
  - `idx_trades_exit_created ON trades(exit_price, created_at)`
  - `idx_signal_features_trade ON signal_features(trade_id, created_at)`
  - `idx_portfolio_snapshots_created ON portfolio_snapshots(created_at)`
  - `idx_model_weights_created ON model_weights(created_at)`
- Add these as part of the init/migration function so they run on startup

### FR-P0-02: Add foreign key constraint
File: `db.py`
- Enable foreign keys: execute `PRAGMA foreign_keys = ON` after each connection open
- If signal_features table creation doesn't have FK, add: `FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE`
- Note: SQLite FK requires PRAGMA per-connection. Add it in the connection function.

### FR-P0-03: Fix stale startup script
File: `daily-agent-run.bat`
- Read the file. Replace any path containing `OneDrive` with the correct path `C:\Users\ericp\Github\crypto-bot`
- Verify all referenced files/scripts actually exist at the new paths

### FR-P0-04: Fix settings panel threshold disconnect
File: `config/settings.py`
- Find `signal_threshold_base` — there's a panel default of 40 and a getter that hardcodes env var (70)
- Make the getter use `apply_overrides()` result or the ml_control.json value, not a hardcoded env default
- The ml_control.json value should win (it has `signal_threshold_base: 70`)

**Commit after Step 1.**

## Step 2: Remove Dead Code

### FR-P0-05: Remove Grok P2 pipeline
Files: `signals/signal_aggregator.py`, `dashboard/app.py`, `config/settings.py`
- In signal_aggregator.py: find `run_full_cycle()` or the signal loop — remove/comment out calls to grok_scraper, grok query pool, Twitter/X scoring
- In signal_aggregator.py: set any `grok_mentions` or `tw_score` weight to 0, or remove the scoring branch
- In dashboard/app.py: remove Grok from the signal loop stages (look in `_signal_loop`)
- In config/settings.py: remove XAI_API_KEY references from required config
- Do NOT delete `ingestion/grok_scraper.py` file — just disconnect it from scoring

### FR-P0-06: Remove dead Apify/Twitter references
File: `signals/signal_aggregator.py`
- Search for `apify_mention_count`, `apify_followed_mentions`, and similar Apify fields
- Remove these from scoring calculations, feature dictionaries, and signal breakdowns
- They persist from a previous Apify integration that was already removed

### FR-P0-07: Update corroboration matrix
File: `signals/signal_aggregator.py` (around lines 1331-1405)
- Find the corroboration bonus section
- Remove ALL entries that reference `tw_score`, `tw_active`, or P2/Grok/Twitter
- The remaining valid combinations are: P1+P3 (LC x Whale), P1+P5 (LC x Depth), P3+P5 (Whale x Depth), P1+P3+P5 (triple)
- Update `active_count` logic to only count P1, P3, P4, P5

### FR-P0-08: Remove dead Grok features from GBT
File: `signals/weight_tuner.py` (around lines 72-110)
- Find FEATURE_COLUMNS list
- Remove any features related to Grok, Twitter, Apify (e.g., `tw_score`, `grok_*`, `apify_*`)
- These will always be zero now and waste model capacity

**Commit after Step 2.**

## Step 3: Critical Bugs — Trade Execution

### FR-P0-09: Fix short P&L calculation
File: `execution/paper_trader.py` (around lines 315-317)
- Find the close/exit logic where P&L is calculated as `proceeds - size_usd`
- For short positions (`is_short=True`), P&L should be inverted: `size_usd - proceeds` (you profit when price drops)
- Or equivalently: `pnl = (entry_price - exit_price) / entry_price * size_usd` for shorts

### FR-P0-10: Fix short position restore
File: `execution/paper_trader.py` (around line 99)
- Find `restore_from_db()` — it only queries `action=="buy"` 
- Add logic to also restore short positions (query `action=="sell"` or however shorts are stored)
- Set `is_short=True` on restored short positions

### FR-P0-11: Fix trailing stop peak tracking
File: `risk/stop_loss.py` (around line 115)
- Find where trailing stop is checked in production mode
- Currently passes `peak_price=entry_price` — this makes the trailing stop a second hard stop
- Must track actual peak price per position. The peak should be updated on every price check: `peak = max(peak, current_price)` for longs, `peak = min(peak, current_price)` for shorts
- If Position object doesn't have a `peak_price` field, add one initialized to `entry_price`

### FR-P0-12: SKIP — Exit tuner direction bug (needs Opus review for negative number math)

### FR-P0-13: Fix liquidation heatmap price reference
File: `signals/signal_aggregator.py` (around line 1670)
- Find the call to `fetch_liq_heatmap()` 
- Currently passes `ta_price_change_1h` (a percentage like -2.5) as `current_price`
- Must pass the actual token price in USD instead. Find where the token's current price is available in the scoring context and use that.

### FR-P0-14: Fix reset-paper data wipe
File: `dashboard/app.py` (around line 2228)
- Find the `reset-paper` endpoint/function
- Currently deletes ALL signal_features rows: something like `DELETE FROM signal_features`
- Add a WHERE clause to only delete signal_features linked to paper-mode trades:
  `DELETE FROM signal_features WHERE trade_id IN (SELECT id FROM trades WHERE mode='paper')` or similar
- Check what column distinguishes paper vs production trades and use that

### FR-P0-15: Fix agent context query
File: `dashboard/app.py` (around lines 2549-2604)
- Find `_gather_agent_context` function
- It references wrong column names in signal_features queries
- Read the actual signal_features table schema from `db.py` and fix the column references to match

**Commit after Step 3.**

## Step 4: Critical Bugs — Signal Quality

### FR-P0-16: Fix ATR silent failure
File: `signals/momentum.py` (around lines 285-286)
- Find the bare `except Exception: pass` around ATR calculation
- Replace with: log a warning (use the existing logger), and return `None` or a clear sentinel value
- Callers should check for None and handle missing ATR gracefully (fall back to fixed stops)

### FR-P0-17: Fix fake 4h filter
File: `signals/momentum.py` (around line 296)
- Find where 4h bars are constructed from 1h bars using `closes[::4]` (every 4th bar)
- This doesn't align to real 4h boundaries. Fix by grouping 1h bars into 4h buckets based on actual timestamps:
  - Group by `timestamp // (4 * 3600)` or similar
  - Use OHLC aggregation within each group: open=first, high=max, low=min, close=last
- If the 4h data is only used for a simple filter, at minimum align the slicing to start from a 4h boundary

### FR-P0-18: SKIP — Buy pressure calculation (needs to identify exact file first)

### FR-P0-19: SKIP — Regime data source CEX vs DEX (design decision)

### FR-P0-20: Add regime hysteresis
File: `signals/regime.py` (around lines 223-236)
- Find the BTC return threshold that determines bull/bear/range regime
- Currently: +3% = Bull, below = Range (or similar hard cutoff)
- Add hysteresis: use two thresholds per boundary
  - Enter bull: BTC 24h return >= +3.0%
  - Exit bull (back to range): BTC 24h return < +2.5%
  - Enter bear: BTC 24h return <= -3.0%
  - Exit bear (back to range): BTC 24h return > -2.5%
- This requires knowing the PREVIOUS regime state. If the function is stateless, add a module-level or class-level cache for `_last_regime`

**Commit after Step 4.**

## Step 5: Config Reset

### FR-P0-21: Reset exit params
File: `data/ml_control.json`
- Change `take_profit` from 0.2888... to `0.15`
- Change `stop_loss_hard` from -0.2786... to `-0.20`
- Change `stop_loss_trailing` from -0.1393... to `-0.10`

### FR-P0-22: Reset size multipliers
File: `data/ml_control.json`
- Change `spot_mult` from 0.692... to `1.0`
- Change `prediction_mult` from 0.536... to `1.0`

### FR-P0-23: Reset real-signal gates
File: `data/ml_control.json`
- Round all `*_corroborated_min` values to clean integers: 35.15 → 35, 15.10 → 15, etc.
- Remove `tw_corroborated_min` entirely (P2 gone)
- Remove any other Grok/Twitter-specific thresholds

### FR-P0-24: SKIP — Pipeline caps review (judgment call on whether to reset)

### FR-P0-25: SKIP — Sideways exit validation (judgment call on extended holds)

**Commit after Step 5.**

## Step 6: Scoring Engine Hardening

### FR-P0-26: Add aggregate modifier cap
File: `signals/signal_aggregator.py`
- Find where the composite score is assembled (around lines 1770-1792)
- After all modifiers are summed, add: `total_modifiers = min(total_modifiers, 30.0)`
- This caps the sum of ALL additive modifiers (corroboration bonus, momentum bonus, regime bonus, etc.) at 30 points
- The `best_single` score should NOT be capped by this — only the modifiers on top of it

### FR-P0-27: Fix triple bonus condition
File: `signals/signal_aggregator.py` (around line 1384)
- Find the triple corroboration bonus check: `active_count >= 3`
- Replace with explicit pipeline check: something like `sum([lc_active, wh_active, lp_active, depth_active]) >= 3`
- Remove any reference to `tw_active` in the active count

### FR-P0-28: SKIP — Regime confidence wiring (design decision for Opus)

**Commit after Step 6.**

## Step 7: ML Tuner Hardening

### FR-P0-29: Add offline retrain exit reset
File: `signals/weight_tuner.py`
- Find the offline retrain function (the one that runs GBT)
- At the START of the retrain function, add a reset of exit params to defaults:
  ```python
  # Reset exit params to prevent online drift accumulation
  defaults = {
      "take_profit": 0.15,
      "stop_loss_hard": -0.20,
      "stop_loss_trailing": -0.10,
  }
  ```
- Also reset size multipliers to 1.0 and real-signal gates to round defaults
- Write these resets to ml_control.json before the retrain runs

### FR-P0-30: Raise MIN_SAMPLES and remove dead features
File: `signals/weight_tuner.py`
- Change `MIN_SAMPLES = 50` to `MIN_SAMPLES = 100` (around line 51)
- Change `MIN_CV_SAMPLES = 80` to `MIN_CV_SAMPLES = 150` (around line 52)
- In FEATURE_COLUMNS (lines 72-110): remove any Grok/Twitter/Apify features (same ones removed in FR-P0-08)

### FR-P0-31: Fix global MIN_SAMPLES mutation
File: `signals/weight_tuner.py` (around lines 670-673)
- Find where `global MIN_SAMPLES` is mutated
- Replace with a local variable: `local_min_samples = ...` and use that in the function
- Do not mutate the module-level constant

### FR-P0-32: Add EMA tuner bounds
File: `signals/online_adapter.py`
- Find where exit params are updated by the EMA tuner (around lines 456-478)
- After each update, clamp to bounds:
  ```python
  take_profit = max(0.08, min(0.25, take_profit))
  stop_loss_hard = max(-0.25, min(-0.10, stop_loss_hard))
  stop_loss_trailing = max(-0.15, min(-0.05, stop_loss_trailing))
  ```
- Add these clamps AFTER the EMA update math, before writing to ml_control.json

### FR-P0-33: Add per-pipeline staleness tracking
Files: `signals/signal_aggregator.py`, `dashboard/app.py`
- In signal_aggregator.py: after each pipeline's data fetch, record the timestamp of the last successful fetch
- Add a `pipeline_health` dict or similar: `{"lc": {"last_fetch": timestamp, "stale": bool}, ...}`
- Mark stale if last_fetch > 15 minutes ago
- Log a warning when scoring with stale data: `logger.warning(f"Pipeline {name} data is {age}s old — scoring with stale cache")`
- In dashboard/app.py: expose staleness info in the pipeline health endpoint

**Commit after Step 7.**

## Step 8: Pipeline Investigation + ATR Wiring

### FR-P0-34: SKIP — LP P4 investigation (needs diagnosis, not a known fix)

### FR-P0-35: Wire ATR into hard stop
File: `risk/stop_loss.py`
- Find `check_hard_stop()` or equivalent function
- Currently uses a fixed hard stop from ml_control.json
- Add ATR-adaptive logic:
  ```python
  def get_adaptive_hard_stop(atr_pct, fixed_stop=-0.20, floor=-0.25):
      if atr_pct is None or atr_pct <= 0:
          return fixed_stop  # fallback when ATR unavailable
      atr_stop = -3.0 * atr_pct
      return max(floor, atr_stop)  # floor prevents stops wider than -25%
  ```
- Integrate this into the stop check: use ATR-adaptive when ATR is available, fall back to fixed when not
- The ATR value should come from `signals/momentum.py` which already computes `atr_pct`

**Commit after Step 8.**

## Final Verification

After all steps, run:
1. `python -c "from signals.signal_aggregator import SignalAggregator; print('aggregator OK')"` 
2. `python -c "from execution.paper_trader import PaperTrader; print('paper_trader OK')"` 
3. `python -c "from signals.weight_tuner import WeightTuner; print('weight_tuner OK')"` 
4. `python -c "from signals.online_adapter import OnlineAdapter; print('online_adapter OK')"` 
5. `python -c "from risk.stop_loss import *; print('stop_loss OK')"` 
6. `python -c "import json; d=json.load(open('data/ml_control.json')); print('TP:', d['exits']['take_profit'], 'HS:', d['exits']['stop_loss_hard'])"` — should show 0.15 and -0.20

Report: which items were completed, which had unexpected issues, and which were skipped.
