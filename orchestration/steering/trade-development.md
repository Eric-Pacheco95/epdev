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

## Loaded by

- `.claude/skills/extract-alpha/SKILL.md` (TODO: wire load)
- `.claude/skills/backtest-review/SKILL.md` (TODO: wire load)
- `.claude/skills/analyze-claims/SKILL.md` (TODO: wire load)

Until those skills explicitly reference this file, the rules live here as the canonical source. The wire-up is tracked as a follow-up in `orchestration/tasklist.md`.
