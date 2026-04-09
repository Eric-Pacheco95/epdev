---
type: technical
topic: Prediction Market Platforms and Calibration Mechanics
date: 2026-04-06
depth: default
sub_questions: 7
sources: 5 web searches, ~12 source URLs
---

# Prediction Market Platforms and Calibration Mechanics

> Metaculus | Manifold Markets | Polymarket

## What It Is

Prediction markets are platforms where participants assign probabilities to future events. The
aggregated prices or probability estimates serve as crowd forecasts. Three dominant platforms exist
with fundamentally different incentive structures and mechanics:

- **Metaculus** -- Non-financial, reputation-based forecasting platform. Probability submission
  model (no buying/selling shares). Community aggregation with accuracy-weighted forecaster
  influence. Best public calibration score: Brier 0.111.
- **Manifold Markets** -- Play-money AMM platform. Free to use; real-money (sweepcash) mode
  discontinued March 28, 2025. Lower calibration barrier, accessible for experimentation.
  Brier 0.168 community average.
- **Polymarket** -- Real-money (USDC), on-chain settlement. Migrated from AMM to hybrid CLOB in
  2024. $21B+ lifetime volume. Best on high-liquidity political/financial events.

## How It Works

### Scoring Rules

**Proper scoring rules** -- reward both accuracy AND calibration (not just binary right/wrong):

| Rule | Formula | Behavior |
|------|---------|----------|
| Brier Score | mean((p - o)^2) | Penalizes overconfidence; 0=best, 2=worst |
| Log Score | sum(log(p_i) * o_i) | Stronger penalty for confident wrong answers |
| Resolution | 1 if outcome, 0 if not | Binary ground truth |

Metaculus uses both log score and Brier score. A well-calibrated forecaster at 70% probability
should be correct ~70% of the time across all 70%-rated predictions.

### Metaculus Architecture

- Users submit probability estimates (0-100%) with optional reasoning
- Community Prediction = weighted aggregate, with historically accurate forecasters weighted higher
- Supports question types: Binary, Multiple Choice, Numeric (range), Date
- Calibration curves per user visible in dashboard
- Metaculus Community average Brier Score: **0.111** (best of any public platform as of 2026)

### Manifold Markets Architecture

- AMM (Automated Market Maker) model: Yes/No shares priced by liquidity pool ratios
- Share price = implied probability (a Yes share costs p, pays out M$1 if Yes resolves)
- Play-money Mana (M); users start with M1000 free; earn by correct predictions, referrals, quests
- Daily prediction streaks: M5-M25/day bonus
- Known bias: "Yes bias" -- overestimates long-shots vs. Metaculus or Polymarket
- Public calibration dashboard: manifold.markets/calibration
- 2024 US election Brier: 0.0342 vs Polymarket's 0.0296

### Polymarket Architecture

- Hybrid CLOB: order matching off-chain (speed), settlement on Polygon blockchain (trustless)
- Invariant: 1 YES share + 1 NO share = $1 USDC (split/merge at any time pre-resolution)
- Resolution oracle: UMA Protocol optimistic oracle
  - Outcome proposed on-chain with 2-hour dispute window
  - Anyone can challenge with $750 USDC bond
  - Escalated disputes: UMA token holders vote
- October 2025: 35,500 new markets created (historical high); $3.16B monthly volume

## Ecosystem and APIs

| Platform | API | Python | Notes |
|----------|-----|--------|-------|
| Metaculus | metaculus.com/api/ | forecasting-tools (GitHub), metac-bot-template | REST + Swagger; auth via token; returns questions, forecast distributions, resolution data |
| Manifold | docs.manifold.markets | community libs | REST; free tier; public data for most endpoints |
| Polymarket | docs.polymarket.com | polymarket-apis (PyPI) | REST + WebSocket; requires USDC wallet for trading |

Metaculus has an official `forecasting-tools` Python framework on GitHub that includes:
- Automated AI forecasting bot scaffold
- Benchmarker that pulls random questions from Metaculus for evaluation
- Support for pydantic question objects (Binary, MC, Numeric, Date)

## Gotchas and Failure Modes

1. **Thin liquidity destroys accuracy** -- calibration advantage only holds in liquid, well-contested
   markets; niche markets have high bid-ask spreads and low forecaster diversity
2. **Novel events uncalibratable** -- no historical base rate = no anchor; markets perform poorly on
   genuinely new event types
3. **Manipulation is real but self-correcting** -- NY Fed research: manipulation typically corrects
   within hours via arbitrageurs; harder in large liquid markets; most dangerous in small markets
4. **Yes bias in play-money markets** -- Manifold systematically overestimates long-shots; financial
   stake sharpens calibration
5. **Resolution oracle risk** -- Polymarket's UMA oracle has been disputed; adversarial bond
   challenges can delay resolution; ambiguous resolution criteria = platform risk
6. **Insider trading** -- contracts tied to regulatory actions or political events are vulnerable to
   information asymmetry; especially for low-volume markets

## Examples and Reference Implementations

- Metaculus `forecasting-tools`: github.com/Metaculus/forecasting-tools
- `polymarket-apis` on PyPI: pip install polymarket-apis
- Manifold calibration dashboard: manifold.markets/calibration (live calibration curves)
- Tetlock's Superforecasting: benchmark for human calibration (~0.15-0.20 Brier for trained forecasters)

## Integration Notes for Jarvis

- **Personal calibration tracking**: Store each `/make-prediction` output with a probability estimate
  and resolution date. Compute running Brier Score. Target: beat Metaculus community average 0.111.
- **Metaculus API as benchmark**: Pull community prediction on same questions Jarvis forecasts;
  compare Jarvis Brier vs. Metaculus 0.111 baseline.
- **Resolution pipeline**: When a prediction's resolution date passes, auto-queue for Brier Score
  update in backtest pipeline. This extends the existing backtest-review skill.
- **Question type mapping**: Jarvis binary predictions map directly to Metaculus Binary question type.
  Numeric range predictions map to Metaculus Numeric type.
- **Avoid Polymarket for personal tracking** -- real-money platform introduces financial risk and
  legal/regulatory friction; use for reading market signals only (liquid markets = high-quality priors).

## Alternatives

| Platform | Differentiator | Use Case |
|----------|---------------|----------|
| Kalshi | US-regulated, real money | Financial hedging; election bets |
| Futuur | Multi-currency, global | Less liquid than Polymarket |
| PredictIt | Small-scale political | Limited to $850/market |
| Good Judgment Open | Professional superforecasters | Benchmarking human accuracy |

## Open Questions

1. Can Metaculus API be queried to pull identical questions to Jarvis's prediction backlog for
   comparison without manual cross-referencing?
2. What is the minimum question volume for Brier Score to be statistically meaningful? (likely 30+)
3. Does Manifold's AMM pricing provide useful calibration signal even after sweepcash removal?

## Sources

- Metaculus FAQ: metaculus.com/faq/
- Metaculus GitHub: github.com/Metaculus/forecasting-tools
- Manifold Markets Wikipedia: en.wikipedia.org/wiki/Manifold_(prediction_market)
- Polymarket CLOB migration: phemex.com/news/article/polymarket-shifts-from-amm-to-clob
- Prediction market failure modes: aashishreddy.substack.com/p/prediction-markets-objections
- KPMG 2025 prediction market state: kpmg.com/kpmg-us/content/dam/kpmg/pdf/2025/current-state-prediction-markets.pdf
- EA Forum calibration data: forum.effectivealtruism.org/posts/hqkyaHLQhzuREcXSX

## Next Steps

- `/make-prediction` -- add Brier Score tracking field to prediction output format
- Consider pulling Metaculus API in backtest-review to compare Jarvis vs. community on same questions
- `/learning-capture` to file calibration patterns as signals
