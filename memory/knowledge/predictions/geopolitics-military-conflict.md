# Geopolitical Military Conflict and Alliance Shifts

## Overview

Four backtested predictions covering military escalation and alliance realignment decisions in 2022-2023. All generated with knowledge cutoffs prior to resolution dates. All carry HIGH leakage risk at weight 0.5. Scoring via keyword-alignment-v1.

## Key Findings

- Overall accuracy: 3 correct, 1 partial, 0 wrong across 4 predictions.
- Confidence range: 0.65 (Russia-Ukraine) to 0.92 (Finland-Sweden NATO). Higher confidence did not guarantee higher alignment score.
- Russia-Ukraine invasion (confidence: 0.65, partial): Predicted military action correctly but hedged between limited and full-scale. The hedge introduced a partial label. Lesson: for high-stakes binary questions, hedged outputs incur calibration penalties even when the directional call is right.
- Israel-Hamas ground invasion (confidence: 0.85, correct, alignment: 0.769): Highest alignment score in the cluster. Strong lexical match with outcome language suggests the prediction was specific and outcome-aligned.
- Pelosi-Taiwan military response (confidence: 0.82, correct, alignment: 0.65): Predicted no direct strikes. China's actual response -- unprecedented exercises plus EEZ missile tests -- was a coercive-but-below-threshold path. The prediction was correct in the strict binary sense but the intermediate response was not explicitly modeled.
- Finland-Sweden NATO (confidence: 0.92, correct, alignment: 0.417, suspect_leakage: true): Lowest alignment score despite correct outcome. Suspect leakage flag raises the question of whether the prediction outcome drove wording choices during generation. Must be excluded from calibration until human review clears it.

## Calibration Notes

- All 4 predictions are weighted 0.5 pending leakage audit.
- Finland-Sweden flagged suspect_leakage: true -- exclude from calibration until cleared.
- alignment_score is a keyword proxy; a correct prediction with low alignment (NATO: 0.417) and a correct one with high alignment (Israel-Hamas: 0.769) suggest the metric is not a reliable quality signal on its own.
- Partial labels (Russia-Ukraine) require a separate handling rule: directional-correct-but-scale-wrong should contribute partial calibration credit, not zero.

## Source Articles

- 2026-04-05-geo-russia-ukraine-invasion-2022.md | outcome: partial | confidence: 0.65
- 2026-04-05-geo-israel-hamas-invasion-2023.md | outcome: correct | confidence: 0.85
- 2026-04-05-geo-pelosi-taiwan-conflict-2022.md | outcome: correct | confidence: 0.82
- 2026-04-05-geo-nato-finland-sweden-2022.md | outcome: correct | confidence: 0.92 | SUSPECT LEAKAGE

## Caveats

> LLM-flagged, unverified. Review during weekly consolidation.

- [ASSUMPTION] keyword-alignment-v1 scores are treated as quality proxies but are never validated against human-judged prediction quality in these articles.
- [ASSUMPTION] 'Difficulty' labels (low/medium/high) are assigned without a stated rubric -- they may reflect post-hoc rationalization rather than pre-resolution assessment.
- [FALLACY] Survivorship bias -- the batch selects prominent geopolitical events whose outcomes are well-documented; low-salience events that were equally predictable are absent, inflating apparent accuracy.
- [FALLACY] Hasty generalization -- 3 correct predictions in one domain (military escalation) is too small a sample to establish reliable base rates for calibration.
- [ASSUMPTION] Suspect leakage detection (keyword-alignment-v1 threshold) may have false negatives; a prediction that avoided outcome-specific language would score low alignment AND evade leakage flags even if the author had outcome knowledge.
