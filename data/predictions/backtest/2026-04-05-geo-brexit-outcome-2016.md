---
date: 2026-04-05
event_id: geo-brexit-outcome-2016
domain: geopolitics
knowledge_cutoff_date: 2016-06-20
backtested: true
leakage_risk: HIGH
weight: 0.5
status: "resolved"
known_outcome: "Leave wins 51.9% to 48.1%. Turnout 72.2%. Scotland and Northern Ireland voted Remain; England and Wales voted Leave."
difficulty: high
primary_confidence: 0.75
alignment_score: 0.4
suspect_leakage: false
score_method: keyword-alignment-v1
resolved_date: "2026-04-05"
outcome_label: "correct"
resolution_note: "geo-brexit-outcome-2016"---

# Backtest Prediction: Will the UK vote to Leave or Remain in the EU in the June 2016 referendum, and what will the margin be?

> **BACKTESTED** -- Knowledge constrained to 2016-06-20.
> Leakage risk: HIGH. Weight: 0.5. Requires human review before calibration use.

## Known Outcome

Leave wins 51.9% to 48.1%. Turnout 72.2%. Scotland and Northern Ireland voted Remain; England and Wales voted Leave.

## Model Prediction (as of 2016-06-20)

## Outcomes

| # | Outcome | Prob | Reasoning |
|---|---------|------|-----------|
| 1 | **Remain wins by 4-8 points** | 30% | Consistent with polling averages showing slight Remain lead, plus historical "status quo bias" where undecideds break toward the safe option late. This is the scenario most prediction markets are pricing. |
| 2 | **Remain wins by 1-3 points** | 25% | Polls are within margin of error. Even if Remain wins, the campaign energy on the Leave side and turnout differentials (older, more motivated Leave voters vs. younger, less reliable Remain voters) could compress the margin significantly. |
| 3 | **Leave wins by 1-3 points** | 28% | Polling has systematically underestimated euroskeptic sentiment in UK elections before (2015 general election polls missed the Conservative majority). Leave enthusiasm and turnout advantage among older demographics could overcome a narrow polling deficit. The Jo Cox assassination may produce a temporary sympathy bump for Remain that fades by vote day. Phone polls show tighter races than online polls â€” the true state is uncertain. |
| 4 | **Leave wins by 4-8 points** | 12% | "Shy Leaver" effect analogous to 2015's shy Tories. If polls are systematically wrong in the same direction as 2015, this is plausible. Requires both polling error AND differential turnout. |
| 5 | **Either side wins by 9+** | 5% | Would require polls to be catastrophically wrong. Unlikely but not impossible given the unprecedented nature of this vote. |

## Primary Prediction

**Leave wins by 1-3 points â€” 28%**

This is not the modal outcome in most models, but I am notably more skeptical of Remain than prediction markets (75% Remain). My reasoning:

- **2015 polling failure**: UK polls missed the Conservative majority by a wide margin just 13 months ago. The same dynamics â€” social desirability bias, differential turnout modeling â€” apply here.
- **Turnout asymmetry**: Leave voters skew older and more motivated. Remain voters skew younger with historically lower turnout. Polling likely models turnout poorly for an unprecedented referendum.
- **Prediction market overconfidence**: Markets are pricing Remain at ~75%, but this reflects elite/financial-sector consensus more than ground-level sentiment. Markets are not polls â€” they reflect who is betting, not who is voting.
- **Late movement patterns**: The Cox assassination paused campaigning and likely created a temporary Remain bump in polls taken June 17-19. This may not hold through to actual votes on the 23rd.

However, I assign Remain (combined) at 55% vs Leave at 45% â€” Remain is still more likely than not, just not as dominant as markets suggest. The honest answer is this is close to a coin flip with a slight Remain edge.

## Signposts

1. **Turnout in Labour heartlands (Sunderland, Sheffield, etc.)**: If turnout exceeds 65% in traditionally low-turnout areas, it signals Leave enthusiasm the polls missed. Early declaration results from these areas will be the first real signal on vote night.

2. **Final-day undecided break**: If post-vote analysis shows undecideds broke 60%+ for Remain, the status quo effect held. If they split evenly or broke Leave, it confirms the polls were masking true sentiment.

3. **Weather on June 23**: Rain in London and major cities suppresses younger/urban Remain turnout disproportionately. A clear day helps Remain; poor weather helps Leave at the margin.

## Confidence Note

- My knowledge boundary is 2016-06-20. Final polls from June 20-22 could shift this estimate.
- This referendum is genuinely unprecedented â€” there is no reliable base rate for UK-wide binary referenda on EU membership. All models are operating with thin priors.
- I am deliberately discounting prediction markets more than a pure Bayesian update would suggest, because I believe the 2015 polling miss is a strong structural analogue that markets are underweighting.
- The Jo Cox effect on polling is real but its durability through to June 23 is uncertain â€” I treat it as transient.

---
*Generated by prediction_backtest_producer.py on 2026-04-05*


---

## Resolution (2026-04-05)

**Verdict**: REVIEWED
**Date resolved**: 2026-04-05
**Note**: geo-brexit-outcome-2016
**Resolved by**: Eric (via Slack reply)
*Logged at 2026-04-06T00:33:17Z*


---

## Resolution (2026-04-05)

**Verdict**: CORRECT
**Date resolved**: 2026-04-05
**Note**: (none)
**Resolved by**: Eric (via Slack reply)
*Logged at 2026-04-06T01:02:08Z*
