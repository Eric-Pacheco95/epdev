---
domain: ai-infra
source: /research
date: 2026-04-06
topic: Prediction Market Platforms and Calibration Mechanics
confidence: 8
source_files:
  - memory/work/prediction-market-mechanics/research_brief.md
tags: [prediction, calibration, brier-score, metaculus, manifold, polymarket, forecasting, make-prediction]
---

## Key Findings
- Metaculus is the best platform for personal calibration tracking: Brier Score 0.111 (industry best),
  proper scoring rules (log + Brier), accuracy-weighted community aggregation, and a REST API with
  official Python SDK (forecasting-tools on GitHub)
- Proper scoring rules reward calibration, not just accuracy: a forecaster at 70% must be right ~70%
  of the time; Brier Score = mean((p - outcome)^2), 0=perfect, 2=worst; target for Jarvis: beat 0.111
- Calibration fails in thin markets (no liquidity), novel events (no base rate), and play-money
  platforms (Manifold yes-bias); real-money markets (Polymarket) are better calibrated but introduce
  financial/regulatory risk
- Polymarket runs a hybrid CLOB on Polygon (off-chain matching, on-chain settlement), uses UMA
  optimistic oracle for resolution (2h dispute window, $750 bond challenge), and has processed $21B+
  lifetime volume
- Manifold's real-money (sweepcash) mode was sunset March 28, 2025; platform reverted to play-money
  only; Brier 0.168 community average vs. Metaculus 0.111

## Context
This directly extends the prediction-framework article (2026-04-02). The platform mechanics fill the
gap identified in that article's open questions: how to store predictions for future Brier Score
calculation. Answer: Metaculus API + forecasting-tools Python SDK provides the comparison baseline;
Jarvis should track Brier Score internally against every /make-prediction output using the same
formula and target beating 0.111.

## Open Questions
- Minimum prediction volume for statistically meaningful Brier Score? (likely 30+ questions)
- Can Metaculus API be queried to find questions identical to Jarvis's backlog for automatic
  community comparison?
- Does Manifold's AMM pricing still provide useful calibration signal in play-money-only mode?
