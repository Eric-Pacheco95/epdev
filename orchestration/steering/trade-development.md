# Trade Development — Steering Rules

> Domain-specific behavioral constraints for trade research, thesis-building, and prediction work. Loaded contextually by trade-related skills (`/extract-alpha`, `/backtest-review`, `/analyze-claims`, etc.) rather than universally via `CLAUDE.md`. Moved out of `CLAUDE.md` 2026-04-07 during steering audit to free root context budget.

## Rules

### Persist every thesis, even when no trade is taken

Trade development sessions must persist the final thesis to `data/predictions/` as a structured prediction record — even when no trade is ultimately taken. Lost theses cannot be backtested, and prior analysis becomes wasted re-research the next time the same setup appears.

**How to apply:** at the end of any `/extract-alpha`, `/research`, or trade-debrief session, write a prediction record (ticker, direction, thesis summary, key catalysts, invalidation conditions, decision: TAKEN / PASSED / WATCHLIST). PASSED and WATCHLIST records are equally valuable for backtesting.

### Check extension history on political-deadline trades

For trades involving political deadlines, ultimatums, or "by date X" announcements, always run `/analyze-claims` with `/research` to check the announcer's extension history before sizing the position. Serial extenders invalidate short-dated trade structures.

**Reference incident:** Trump Iran ultimatums extended 4 times in 16 days. Anyone holding short-dated puts on the original deadline got chopped on each extension.

**How to apply:** during thesis construction for any deadline-driven trade, the ISC must include "extension history checked, base rate computed" as a verifiable criterion before position sizing.

### No auto-apply config patches in live trading + ML control consistency validator

No live-trading code path may auto-apply config patches classified by an LLM as "low-risk" without per-change explicit approval (Telegram button or equivalent). The ML control panel must run a startup consistency validator that asserts `gate_threshold[X] ≤ pipeline_max_contribution[X]` for every pipeline, AND must detect "structurally dormant pipelines" (score=0 for N consecutive cycles with non-zero cap allocation) and log them in the weekly health snapshot.

**Reference incident:** 2026-04-19 crypto-bot Session 2 surfaced three latent capital-risk bugs in one session — (1) `_weekly_retrain()` auto-applying LLM-classified "low-risk" patches autonomously; (2) `lc_corroborated_min=35` > `pipeline_max_contribution["lc"]=31.5`, Path 1 structurally unreachable; (3) LP pipeline fires only on Uniswap V2/V3 PairCreated events, but the universe is CEX-listed tokens that never emit them — `lp_score=0` structurally while weighted at 35. Each would have been caught by a 10-line startup validator.

**How to apply:** (a) remove all `propose_and_apply()` / auto-patch blocks from any path touching live config; (b) add `verify_ml_control_consistency.py` to bot boot sequence, exit 1 on threshold>cap; (c) add dormant-pipeline detector to weekly health snapshot.

## Loaded by

- `.claude/skills/extract-alpha/SKILL.md` — top-of-STEPS directive added 2026-04-07
- `.claude/skills/backtest-review/SKILL.md` — top-of-STEPS directive added 2026-04-07
- `.claude/skills/analyze-claims/SKILL.md` — inlined into Step 0 INPUT VALIDATION (trade-deadline detection) 2026-04-07
