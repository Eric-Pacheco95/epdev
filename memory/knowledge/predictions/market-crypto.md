# Market -- Crypto Predictions

## Overview

Four backtested predictions covering Bitcoin price direction, halving-cycle dynamics, and SEC regulatory approval. All carry HIGH leakage risk and 0.5 weight. One sample (mkt-bitcoin-etf-2024) is flagged SUSPECT LEAKAGE due to confidence > 85% with a knowledge cutoff only days before the approval decision.

Overall accuracy: 3/4 correct (75%). The single failure (mkt-crypto-bear-2022) is the most instructive: the model assigned only 0.45 confidence to a 'yes' prediction but the event occurred, suggesting the model under-weighted contagion risk from LUNA/3AC collapse that was already unfolding at the April 2022 cutoff.

## Key Findings

- **Halving-cycle ATH thesis (mkt-btc-ath-2021, mkt-btc-halving-ath-2024):** Both predicted new ATHs, both correct. Confidence moderate (0.62 both). Alignment scores 0.67 / 0.58 -- partial reasoning. The 2024 sample reached ATH *before* the halving (March 14 vs April 19), meaning the timing sub-claim was off even though direction was right.
- **Regulatory binary (mkt-bitcoin-etf-2024):** Correct, high confidence (0.88), but suspect leakage. The alignment score (0.727) does not resolve the leakage question. Exclude from calibration until human review.
- **Bear market call (mkt-crypto-bear-2022):** Model predicted 'no' (confidence 0.45 on the event occurring). Bitcoin fell to $17,567 on June 18 -- outcome_label 'wrong'. Root cause: macro contagion from LUNA collapse (~May 2022) was outside the April 1 knowledge cutoff but was already in motion. This is a known blind spot for cutoff-bounded backtests.

## Alignment Score Distribution

| Event | Confidence | Alignment | Outcome | Leakage |
|---|---|---|---|---|
| mkt-btc-ath-2021 | 0.62 | 0.667 | correct | no |
| mkt-btc-halving-ath-2024 | 0.62 | 0.583 | correct | no |
| mkt-bitcoin-etf-2024 | 0.88 | 0.727 | correct | SUSPECT |
| mkt-crypto-bear-2022 | 0.45 | 0.500 | wrong | no |

## Source Articles

- 2026-04-05-mkt-btc-ath-2021.md
- 2026-04-05-mkt-btc-halving-ath-2024.md
- 2026-04-05-mkt-bitcoin-etf-2024.md
- 2026-04-05-mkt-crypto-bear-2022.md

## Caveats

> LLM-flagged, unverified. Review during weekly consolidation.

- [ASSUMPTION] Halving-cycle price appreciation is treated as a near-deterministic pattern; the articles do not account for the possibility that cycle effects diminish as Bitcoin market cap grows and institutional hedging increases.
- [ASSUMPTION] SEC approval of a spot ETF is modeled as a single binary event; the articles do not address the possibility of conditional approval, limited rollout, or rapid reversal under a new administration.
- [FALLACY] Survivorship bias -- the prediction set was curated from memorable Bitcoin price events (ATH, crash, ETF). Mundane periods where Bitcoin moved sideways are absent, inflating the apparent predictability of the asset.
- [FALLACY] Hasty generalization -- three correct directional calls on BTC are extrapolated implicitly as evidence that the prediction framework is well-calibrated for crypto; four samples at 0.5 weight cannot support that claim.
- [FALLACY] Appeal to authority -- regulatory approval reasoning in mkt-bitcoin-etf-2024 leans on Grayscale lawsuit precedent without modeling political/legal reversal risk.
