# Backtested Geopolitical Predictions

## Overview

Three historical geopolitical events backtested against constrained knowledge cutoffs to measure prediction model calibration. All three resolved 'correct' but all carry HIGH leakage risk and reduced calibration weight of 0.5. The scoring method (keyword-alignment-v1) measures surface keyword overlap between prediction prose and known outcome -- it does not assess reasoning quality, detect leakage, or distinguish a well-reasoned correct call from a lucky one.

## Key Findings

- **Afghanistan collapse (2021)**: Prediction: Afghan government does NOT survive 12 months post-withdrawal. Known outcome: Taliban captured Kabul August 15, 2021 -- 6 weeks after July 8 announcement; government collapsed in days. Outcome label: correct. Primary confidence: 0.65. Alignment: 0.667. Difficulty: high. Weight: 0.5. Leakage risk: HIGH.
- **Brexit (2016)**: Prediction: UK votes Leave. Known outcome: Leave wins 51.9% to 48.1%; turnout 72.2%; Scotland and Northern Ireland voted Remain, England and Wales voted Leave. Outcome label: correct. Primary confidence: 0.75. Alignment: 0.40 -- poor alignment despite correct directional call. Difficulty: high. Weight: 0.5. Leakage risk: HIGH.
- **French election (2022)**: Prediction: Macron wins runoff vs Le Pen. Known outcome: Macron 58.5%, Le Pen 41.5%. Outcome label: correct. Primary confidence: 0.88. Alignment: 1.00. SUSPECT LEAKAGE flagged. Difficulty: low. Weight: 0.5. The combination of high confidence + perfect alignment + low difficulty + leakage flag is the strongest indicator of post-cutoff knowledge bleed in this set.

## Source Articles

- 2026-04-05-geo-afghanistan-collapse-2021.md (resolved 2026-04-06, weight 0.5)
- 2026-04-05-geo-brexit-outcome-2016.md (resolved 2026-04-05, weight 0.5)
- 2026-04-05-geo-french-election-2022.md (resolved 2026-04-05, weight 0.5, SUSPECT LEAKAGE)

## Calibration Summary

| Event              | Confidence | Alignment | Difficulty | Suspect Leakage |
|--------------------|------------|-----------|------------|-----------------|
| Afghanistan 2021   | 0.65       | 0.667     | high       | no              |
| Brexit 2016        | 0.75       | 0.40      | high       | no              |
| French election 22 | 0.88       | 1.00      | low        | YES             |

3/3 correct; N=3 all-correct provides no variance for calibration. Treat as pipeline validation only until leakage audit completes and scoring method is upgraded.

## Caveats

> LLM-flagged, unverified. Review during weekly consolidation.

- [ASSUMPTION] keyword-alignment-v1 assumes surface keyword overlap between prediction prose and outcome text is a valid proxy for prediction quality -- a prediction can match outcome vocabulary through leakage or lucky phrasing, not sound reasoning
- [ASSUMPTION] Uniform weight discount of 0.5 assumes equal leakage severity across all three events -- French election (low difficulty + suspect_leakage=true) arguably warrants a near-zero calibration weight, not 0.5
- [ASSUMPTION] Knowledge cutoff dates (2016-06-20, 2021-07-01, 2022-04-01) assume the model had no information beyond those dates -- this is unverifiable without a controlled leakage audit; the scoring method cannot confirm enforcement
- [FALLACY] Survivorship bias: these three events were selected for backtesting likely because outcomes are high-profile and well-documented; prediction accuracy on lower-salience events may differ significantly
- [FALLACY] Hasty generalization: 3/3 correct with no false negatives cannot establish a base rate; a single-outcome distribution has no calibration signal
- [FALLACY] Appeal to alignment score: perfect alignment (1.0) on a suspect-leakage prediction is evidence of contamination, not forecasting skill -- citing it as a positive signal inverts its meaning
- [FALLACY] False precision: confidence scores (0.65, 0.75, 0.88) imply quantitative rigor that keyword-alignment-v1 on a 3-event all-correct sample cannot support
