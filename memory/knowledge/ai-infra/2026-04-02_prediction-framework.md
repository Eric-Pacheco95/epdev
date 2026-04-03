---
domain: ai-infra
source: /research (backfill)
date: 2026-04-02
topic: General-Purpose Prediction Framework — Bayesian + Game Theory + Scenario Planning
confidence: 9
source_files:
  - memory/work/make-prediction/research_brief.md
tags: [prediction, bayesian, game-theory, superforecasting, scenario-planning, brier-score, make-prediction]
---

## Key Findings
- A domain-agnostic prediction framework uses three engines: **Bayesian reasoning** (probability spine — set base rate, identify evidence streams, update iteratively, output probability estimate), **Game Theory / BDM model** (actor/incentive modeling — position, capability, salience, risk tolerance per actor; claimed 90%+ CIA accuracy), **Scenario Planning** (Shell/GBN 2x2 matrix — identify two critical uncertainties, build four internally consistent narratives, assign Bayesian probability weights, define signposts)
- Superforecasting discipline (Tetlock): update in small increments, not big swings; resist anchoring on initial estimate; resist overcorrecting on new evidence; **Brier Score** (mean squared error of probabilistic forecasts, 0=best, 2=worst) is the calibration metric to build into `/make-prediction`; Metaculus community averages ~0.15
- Base rate is the foundation — reference class forecasting ("of all situations like this historically, what % led to outcome X?") is more predictive than domain-specific expertise alone
- Domain-specific lenses layer on top of the universal chassis: geopolitics uses actor incentive mapping + historical pattern matching (Prof Jiang's approach); markets use sentiment + flow data + regime detection; technology uses S-curve adoption models
- The prediction's value is not in being right once but in **calibration over time** — a forecaster who says "70%" should be right roughly 70% of the time on those predictions

## Context
This brief underpins the `/make-prediction` skill design. The universal chassis (Bayesian + Game Theory + Scenario Planning) is domain-agnostic — the math doesn't care about the subject matter; base rates come from reference classes, evidence comes from domain signals. The BDM model is the most operationalized game-theory prediction system — used by CIA and defense agencies and documented in Bueno de Mesquita's "The Predictioneer's Game" (2009). The Brier Score tracking is the bridge between prediction making and the backtesting vision in Eric's prediction philosophy.

## Open Questions
- How should the `/make-prediction` skill store predictions for future Brier Score calculation?
- What reference class databases are best for base rate lookup across geopolitics, markets, and technology?
- Is the BDM model's "position + capability + salience + risk tolerance" input format practical for rapid prediction generation?
