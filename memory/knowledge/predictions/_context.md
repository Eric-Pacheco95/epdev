# Predictions Domain Knowledge



## Overview

This domain captures forward-looking predictions and backtested calibration exercises. Articles span three sub-topics: backtested historical geopolitical events (sub-domain, 3 articles), active near-term geopolitical forecasts (2 articles, below threshold), and market/trade plans tied to live events (1 article, below threshold). As of 2026-04-15, all backtested predictions resolved 'correct' but carry HIGH leakage risk and reduced calibration weight (0.5).

## Sub-Domain: Backtested Geopolitics

- Three historical events backtested against constrained knowledge cutoffs (2016, 2021, 2022)
- All resolved 'correct'; alignment scores range 0.40-1.00 with one suspect-leakage flag on the highest-confidence case
- Calibration value is limited until keyword-alignment-v1 is replaced with a stronger scoring method and leakage is formally audited
- N=3 all-correct provides no variance; treat as pipeline validation, not calibration data

## Direct Entries

### Active Geopolitics Predictions

**2026-04-03: US-China Balance of Power by 2035**
- Thesis: US-led unipolarity transitions to contested bipolarity by 2035; US remains most powerful state but cannot dictate outcomes unilaterally (45% primary outcome)
- Watch-for triggers: China semiconductor self-sufficiency >50% by 2028; USD excluded from major trade settlement agreement by 2031
- Status: open; horizon 2035; no resolution data available

**2026-04-06: Trump Iran Power Plant Strikes by April 8**
- Thesis: 55% probability Trump orders strikes on Iranian civilian infrastructure if no deal reached by April 8 8pm ET
- Watch-for: No deal announcement by 4pm ET Tuesday; Pentagon briefing on expanded target set; carrier strike group repositioning
- Status: open at time of capture; linked to iran-oil-macro-trade-plan

### Market/Trade Predictions

**2026-04-06: Iran/Oil Leveraged ETF Trade Plan**
- Context: US-Iran war active since Feb 28 2026; Hormuz closed since March 9; WTI ~$112; SPY -6% from Jan peak; CPI 3.8%; Moody's recession odds ~49%
- Instruments: UCO (oil bull), SCO (hedge), SDS/SQQQ (S&P bear)
- Thesis: Oil stays elevated while macro deteriorates; leveraged ETFs used for directional exposure without options access
- Status: open; horizon 2026-04-25; explicitly conditioned on trump-iran-power-plant-strikes resolution -- the trade premise was live before its geopolitical trigger confirmed

## Cross-Cutting Themes

1. **Leakage risk is universal in backtesting** -- all 3 backtested predictions are HIGH; keyword-alignment-v1 does not detect leakage, only measures surface text overlap
2. **Confidence does not imply calibration quality** -- French election at 0.88 confidence + suspect leakage + alignment 1.0 is the worst calibration case in the set, not the best
3. **Geopolitical triggers drive market positions** -- Iran/oil trade plan is explicitly linked to trump-iran-power-plant-strikes; these predictions form a dependency graph requiring joint resolution tracking
4. **Horizon length requires different calibration treatment** -- 2-day (Iran strikes) vs 9-year (balance of power) predictions are fundamentally different epistemic products and should not be aggregated into a single accuracy score

## Last Updated

2026-04-15


## Domain Overview

This domain captures backtested geopolitical predictions generated with constrained knowledge cutoffs. All 6 articles are from a 2026-04-05 batch run. All carry HIGH leakage risk and weight 0.5 -- pending human review before use in calibration. Scoring uses keyword-alignment-v1, a proxy metric; alignment score != prediction quality.

## Sub-Domain: Geopolitical Military Conflict and Alliance Shifts

4 articles clustered (Russia-Ukraine invasion, Israel-Hamas ground invasion, Pelosi-Taiwan military response, Finland-Sweden NATO accession).

- Accuracy rate: 3 correct, 1 partial, 0 wrong. High-confidence predictions (0.82-0.92) on military escalation tend to align with outcomes.
- Russia-Ukraine (difficulty: high, confidence: 0.65) scored partial -- action predicted correctly, scale under-hedged. Suggests base-rate underestimation of full-scale war risk.
- Finland-Sweden NATO (suspect leakage flagged): alignment score 0.417 despite correct outcome -- low lexical match may indicate the prediction avoided outcome-specific language, or leakage detection underweights structural signals.
- Pelosi-Taiwan: correctly predicted no direct strikes (confidence 0.82). China's response (unprecedented exercises, EEZ missile tests) was a middle path not explicitly modeled.

## Direct-to-Context Articles: Diplomatic Normalization

2 articles below sub-domain threshold (Iran JCPOA revival, Saudi-Iran normalization). Both incorrect.

- Iran JCPOA (confidence: 0.95, outcome: wrong): Highest-confidence prediction in batch -- and the one most likely to reflect leakage given HIGH flag and suspect_leakage: true. If leakage confirmed, this data point must be excluded entirely from calibration.
- Saudi-Iran normalization (confidence: 0.55, outcome: wrong): Low confidence correctly reflected genuine uncertainty. Normalization occurred but was China-brokered -- a structural factor not derivable from 2023-01-01 knowledge cutoff. Prediction failure here is defensible.

## Cross-Cutting Themes

- Leakage risk is HIGH across all 6 predictions -- none should enter calibration without human review.
- Two predictions flagged suspect_leakage: true (Iran JCPOA, NATO Finland-Sweden). The Iran case is especially problematic: high confidence + wrong outcome + suspect leakage is a classic contamination signature.
- Diplomatic normalization is harder to predict than military escalation in this batch: 0/2 vs 3+/4.
- keyword-alignment-v1 alignment scores do not consistently predict label accuracy (NATO: 0.417 correct; Iran: 0.462 wrong). Score method needs recalibration or replacement.
- Difficulty labels (low/medium/high) correlate loosely with confidence but not outcome: high-difficulty Saudi-Iran at 0.55 failed, high-difficulty Russia-Ukraine at 0.65 was partial-correct.

## Last Updated

2026-04-15


## Overview

This domain tracks backtested predictions across geopolitical events and market outcomes. All 6 source articles are HIGH leakage-risk backtests with 0.5 weight pending human review. One suspect-leakage flag raised (mkt-bitcoin-etf-2024, confidence > 85%). Overall accuracy: 5/6 correct (83%), but calibration is unreliable until leakage audit completes.

## Sub-Domain: Market Crypto (4 articles)

- Model accuracy 3/4 correct on directional crypto calls; the single failure (mkt-crypto-bear-2022) occurred when the model under-weighted macro contagion from LUNA/3AC collapse at low confidence (0.45).
- Suspect leakage on mkt-bitcoin-etf-2024 (confidence 0.88, cutoff 2024-01-01) invalidates that sample for calibration until human confirms knowledge boundary was clean.
- Halving-cycle and ATH predictions used momentum/cycle frameworks; alignment scores cluster 0.58-0.73 suggesting partial but incomplete reasoning chains in source articles.

## Directly Tracked (< 3 articles threshold)

### Geopolitics (2 articles)

- geo-ukraine-war-six-months-2022: correct at 0.78 confidence, alignment 0.583. Model captured war-continuation inertia but likely missed Kharkiv counteroffensive dynamics.
- geo-us-election-2020: correct at 0.52 confidence, alignment 1.0. Low confidence despite perfect keyword alignment suggests hedged reasoning; Biden win driven by polling averages and COVID incumbency penalty.
- Cross-cutting: both geopolitics samples are single-outcome binary calls (ongoing/not, winner). Low sample count; no cross-validation possible yet.

## Cross-Cutting Themes

1. ALL samples are HIGH leakage risk -- no calibration use until human review batch completes.
2. Alignment score (keyword-alignment-v1) is a proxy metric, not a ground-truth calibration signal. High alignment with wrong prediction is possibl

[TRUNCATED: content exceeded 8000 char cap -- _context.md]