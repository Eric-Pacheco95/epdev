# Research Brief: General-Purpose Prediction Framework

| Field | Value |
|-------|-------|
| Date | 2026-04-02 |
| Type | Technical |
| Depth | Deep |
| Sub-questions | 12 |
| Sources | 30+ |

---

## Executive Summary

A domain-agnostic prediction framework is achievable by combining three proven core engines — **Bayesian reasoning** (probability updating), **game theory** (actor/incentive modeling), and **scenario planning** (structured uncertainty). These form a universal chassis. Domain-specific lenses (geopolitics, markets, technology, personal decisions) layer on top as specialized pattern libraries and heuristics. The superforecasting literature (Tetlock) provides the calibration and debiasing discipline that makes the whole system honest.

---

## 1. The Universal Core: Three Engines

### Engine 1: Bayesian Reasoning (Probability Spine)

The backbone of any prediction. Bayesian inference combines prior beliefs with new evidence to produce updated probabilities.

**How it works in practice:**
1. **Set a base rate** (reference class forecasting) — "Of all situations like this historically, what % led to outcome X?"
2. **Identify evidence streams** — Each piece of new information is a likelihood ratio that shifts the probability up or down
3. **Update iteratively** — As new data arrives, the posterior becomes the new prior
4. **Output**: A probability estimate (e.g., "65% chance Russia withdraws from territory X by Q4 2026")

**Why it's domain-agnostic:** The math doesn't care about the domain. Base rates come from reference classes (historical analogues), evidence comes from domain-specific signals.

**Key insight from Tetlock:** Superforecasters update in small increments (granular Bayesian updating), not big swings. They resist the urge to anchor on initial estimates but also resist overcorrecting.

**Scoring:** Brier Score = mean squared error of probabilistic forecasts. Best = 0, worst = 2. Metaculus community averages ~0.15 (quite good). This is the scoring system we should build into `/make-prediction` for calibration tracking.

### Engine 2: Game Theory (Actor/Incentive Modeling)

Models situations as strategic interactions between rational actors pursuing self-interest.

**Practical application (not just academic):**
- **Identify actors**: Who has power, stake, and agency in this situation?
- **Map incentives**: What does each actor want? What are they willing to pay/sacrifice?
- **Assess capabilities**: What resources/leverage does each actor have?
- **Model interactions**: What happens when Actor A's best move collides with Actor B's?
- **Find equilibria**: Where do the incentive structures stabilize? (Nash equilibrium = no actor benefits from unilaterally changing strategy)

**BDM Model (Bruce Bueno de Mesquita):**
The most operationalized game-theory prediction system. Used by CIA and defense agencies. For each actor, you estimate:
- **Position** (what they want, 0-100 scale)
- **Capability** (how much power they have)
- **Salience** (how much they care about this issue)
- **Risk tolerance** (how willing they are to gamble)

The model then simulates bargaining rounds to find the equilibrium outcome. Claimed 90%+ accuracy by CIA evaluation (though this is disputed). The Predictioneer's Game (2009) documents the approach.

**Prof Jiang's approach** is essentially BDM-lite: "I use game theory and basically see geopolitics as a game played by different players who are trying to maximize their own self-interest. I don't really look at ideology. I focus on self-interest." He combines this with historical pattern matching (see Section 3).

### Engine 3: Scenario Planning (Structured Uncertainty)

Not prediction — preparation for multiple futures. But when combined with Bayesian probability assignment, it becomes a prediction tool.

**Shell/GBN Methodology (Peter Schwartz):**
1. **Identify focal question** — What decision are we trying to inform?
2. **List driving forces** — PESTLE scan (Political, Economic, Social, Technological, Legal, Environmental)
3. **Rank by importance and uncertainty** — Separate predetermined elements (will happen regardless) from critical uncertainties (could go either way)
4. **Select two critical uncertainties** as axes → creates a 2x2 matrix of four scenarios
5. **Build narratives** for each quadrant — internally consistent stories, not just labels
6. **Assign probability weights** to each scenario (this is where Bayesian engine connects)
7. **Identify signposts** — early indicators that tell you which scenario is unfolding

**What separates good scenarios from storytelling:**
- **Anti-predictive stance**: Scenarios reject single-point prediction. They explore possibility space.
- **Internal consistency**: Each scenario must be logically coherent — no cherry-picking favorable assumptions
- **Narrative form**: Stories stick where statistics don't (Pierre Wack's "gentle art of reperceiving")
- **Decision relevance**: Every scenario must have different implications for the decision at hand

---

## 2. The Calibration Layer: Superforecasting (Tetlock)

This is the meta-framework that makes the core engines honest. Without calibration discipline, any prediction framework devolves into storytelling.

### Key Superforecaster Attributes:
1. **Probabilistic thinking** — Assign specific probabilities, not vague words ("likely" → "72%")
2. **Granular decomposition** — Break big questions into smaller, answerable sub-questions (Fermi estimation)
3. **Active open-mindedness** — Actively seek disconfirming evidence
4. **Perpetual beta** — Treat every belief as a hypothesis to be tested, not a position to defend
5. **Dragonfly eye** — Aggregate multiple perspectives/models, don't commit to one lens
6. **Calibration tracking** — Keep score. Track your Brier scores. Know where you're overconfident vs. underconfident
7. **Update discipline** — Small, frequent updates as new evidence arrives. Neither anchored nor whipsawed

### Reference Class Forecasting:
The single most powerful debiasing tool. Instead of reasoning from the inside ("this situation is unique because..."), find the reference class ("of 50 similar situations, 35 resulted in X"):
1. Identify a reference class of past, comparable situations
2. Evaluate the base-rate distribution for that class
3. Make your initial estimate anchored to the base rate
4. Adjust for case-specific factors (but conservatively)

### What Makes It Domain-Agnostic:
Tetlock's GJP showed that superforecasters — ordinary people using these techniques — outperformed domain experts with classified data by ~60%. The method doesn't require domain expertise. It requires:
- Intellectual humility
- Granular probability assignment
- Systematic evidence updating
- Calibration awareness

---

## 3. Domain-Specific Lenses

These are swappable pattern libraries that plug into the universal core.

### Lens: Geopolitics (`--geopolitics`)

**Predictive History (Prof Jiang / Jiang Xueqin):**
- Yale-educated philosopher/historian teaching in Beijing
- YouTube channel "Predictive History" — 2.2M+ subscribers (as of March 2026)
- Framework inspired by Asimov's "psychohistory" — using historical data and game theory to forecast large-scale societal trends
- Core method: identify historical analogues (e.g., declining empire patterns, resource competition dynamics), map actor incentives via game theory, derive predictions from where patterns converge
- Notable: predicted Trump's return, US-Iran confrontation — both validated
- Limitation: relies heavily on the quality of historical analogues selected; critics note speculation risk

**Power Transition Theory / Thucydides Trap (Allison/Organski):**
- When a rising power approaches parity with a dominant power → conflict probability rises sharply
- Organski's original: two variables — power shift + revisionism (challenger wants to change the order)
- Allison's "Destined for War" studied 16 historical cases: 12 of 16 rising-vs-ruling power transitions led to war
- Criticism: coding is subjective, selection bias in case choice, conflates correlation with causation
- **Use in predictions**: Provides a base rate for great-power conflict probability given measured power shifts

**Geopolitical Game Theory Signals:**
- Commitment problems (can't credibly promise to keep bargains once power shifts)
- Signaling and credibility (costly signals vs. cheap talk)
- Alliance dynamics (who backs whom and why)
- Resource dependency mapping (who needs what from whom)

### Lens: Markets/Finance (`--market`)

**Ray Dalio's Big Cycle Framework:**
- Five forces: debt/credit cycles, internal order/disorder, external order/disorder, acts of nature, technology/innovation
- Short-term debt cycle (~5-8 years), long-term debt cycle (~75-100 years)
- Current position: late-stage long-term debt cycle for most developed economies
- Practical signals: debt-to-GDP ratios, central bank balance sheets, wealth gaps, political polarization, currency reserve status
- "I learned from the study of history. I studied the last 500 years of cycles."

**Cycle Analysis & Sentiment:**
- Market cycles have identifiable phases: early cycle (expansion), mid cycle (optimism), late cycle (euphoria/tightening), crisis (contraction)
- VIX as regime indicator (low = complacency, high = fear)
- Sentiment extremes as contrarian signals (everyone bullish = top signal)
- Macro regime shifts: rate expectations, dollar strength, liquidity conditions

**Use in predictions:** Identify where we are in the cycle → derive base-rate probabilities for different market outcomes → update with current evidence.

### Lens: Technology (`--tech`)

**S-Curves / Diffusion of Innovations (Rogers):**
- Technology adoption follows S-curve: slow start → exponential growth → saturation
- Rogers' adopter categories: innovators (2.5%), early adopters (13.5%), early majority (34%), late majority (34%), laggards (16%)
- Key inflection: crossing the "chasm" from early adopters to early majority
- Bass Diffusion Model: p (innovation coefficient) + q (imitation coefficient) predict adoption speed
- Historical acceleration: PCs took 16 years, internet 7 years, smartphones 5 years, AI tools projecting ~3 years

**Gartner Hype Cycle (calibration tool, not prediction):**
- Five phases: Innovation Trigger → Peak of Inflated Expectations → Trough of Disillusionment → Slope of Enlightenment → Plateau of Productivity
- Research shows the model has "incongruences" — not all technologies follow the pattern
- Best used as a **debiasing tool**: "Are we in the hype peak? Then discount enthusiasm."
- NOT a prediction model — it's a reality-check lens

**Use in predictions:** Identify where a technology sits on S-curve + hype cycle → derive probability of mainstream adoption within N years → compare with historical reference classes.

### Lens: Personal Decisions (`--personal`)

**Expected Value Calculation:**
- EV = Σ(Probability of outcome × Value of outcome)
- Forces explicit probability assignment and value quantification
- Works for career moves, purchases, life decisions

**Pre-Mortem Analysis (Gary Klein):**
1. Assume the decision has already failed spectacularly
2. Work backward: "What went wrong?"
3. Identify failure modes you wouldn't see through optimistic planning
4. Build mitigation strategies or kill criteria
- Heuer/Pherson's intelligence community version adds structured evidence weighting

**Decision Matrices + Kill Criteria (Annie Duke):**
- Pre-commit to signals that indicate the decision is failing
- Define "quit criteria" before emotional investment clouds judgment
- Track decision quality separately from outcome quality (good process can produce bad outcomes by luck)

**Use in predictions:** Frame personal decisions as predictions about outcomes → apply Bayesian base rates → run pre-mortem → define signposts for course correction.

---

## 4. Cognitive Bias Defense Layer

The #1 killer of prediction accuracy. Every prediction must pass through this filter.

| Bias | Effect on Predictions | Defense |
|------|----------------------|---------|
| **Anchoring** | Over-weighting first information received | Reference class forecasting; multiple independent estimates |
| **Confirmation bias** | Seeking evidence that confirms existing belief | Actively seek disconfirming evidence; red-team step |
| **Overconfidence** | Assigning too-narrow probability ranges | Calibration tracking; widen confidence intervals |
| **Availability bias** | Over-weighting vivid/recent events | Base rates from historical data, not memory |
| **Narrative fallacy** | Constructing coherent stories from random events | Demand mechanism, not just narrative |
| **Status quo bias** | Underestimating probability of change | Explicitly model discontinuity scenarios |
| **Hindsight bias** | "I knew it all along" — prevents learning | Record predictions BEFORE outcomes; Brier scoring |
| **Groupthink** | Consensus-seeking suppresses dissent | Pre-mortem; red-team; dragonfly eye |
| **Sunk cost fallacy** | Persisting with failing predictions | Pre-committed kill criteria |

---

## 5. Existing Tools & Scoring Systems

| Platform | Type | Scoring | Notes |
|----------|------|---------|-------|
| **Metaculus** | Community forecasting | Brier score + calibration curves | Best community accuracy (~0.084 Brier on studied questions) |
| **Good Judgment Open** | Tetlock's public platform | Brier score, daily updates | Superforecaster methodology |
| **Manifold Markets** | Prediction market | Market prices = probabilities | Slightly less accurate than Metaculus (~0.107 Brier) |
| **Polymarket** | Crypto prediction market | Market-based | Real-money incentives; regulatory constraints |
| **PredictionBook** | Personal tracking | Brier score | Lightweight personal calibration |

**Key finding:** Metaculus community predictions (wisdom of crowds) outperform Manifold market-based predictions. Aggregation method matters — recency-weighted median beats simple average.

---

## 6. Proposed `/make-prediction` Architecture

### Layered Design:

```
INPUT (question/topic)
       │
       ▼
┌─────────────────────────────────┐
│  STEP 1: DECOMPOSE              │  ← Fermi/Tetlock
│  Break into sub-questions       │
│  Identify reference classes     │
│  Set base rates                 │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  STEP 2: ACTOR MAP              │  ← Game Theory / BDM-lite
│  Who are the actors?            │
│  What are their incentives?     │
│  Where do incentives collide?   │
│  What's the equilibrium?        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  STEP 3: SCENARIO BUILD         │  ← Shell/GBN
│  Identify critical uncertainties│
│  Build 3-4 scenarios            │
│  Assign probability weights     │
│  Identify signposts per scenario│
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  STEP 4: DOMAIN LENS            │  ← Swappable
│  --geopolitics: predictive      │
│    history, power transition    │
│  --market: cycles, sentiment,   │
│    macro regime                 │
│  --tech: S-curves, hype cycle   │
│  --personal: EV calc, premortem │
│  (auto-detect if no flag)       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  STEP 5: BIAS CHECK             │  ← Debiasing
│  Red-team the prediction        │
│  Check for top biases           │
│  Apply reference class anchor   │
│  Widen/narrow confidence range  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  STEP 6: OUTPUT                 │
│  Prediction statement + %       │
│  Scenario probability tree      │
│  Key signposts to watch         │
│  Confidence + uncertainty flags │
│  → chains to /extract-alpha     │
└─────────────────────────────────┘
```

### Output Format (designed for `/extract-alpha` chaining):

```markdown
## PREDICTION: [statement]

**Probability**: X% (confidence range: Y%-Z%)
**Time horizon**: [date/range]
**Reference class**: [what historical base rate anchors this]

## ACTOR MAP
| Actor | Position | Capability | Salience | Risk Tolerance |
|-------|----------|------------|----------|----------------|

## SCENARIOS
| Scenario | Probability | Key Drivers | Signposts |
|----------|-------------|-------------|-----------|
| Bull     | X%          | ...         | Watch for: ... |
| Base     | X%          | ...         | Watch for: ... |
| Bear     | X%          | ...         | Watch for: ... |
| Black Swan | X%        | ...         | Watch for: ... |

## DOMAIN LENS APPLIED: [geopolitics/market/tech/personal]
[Domain-specific analysis here]

## BIAS CHECK
- [ ] Anchoring: checked against reference class
- [ ] Confirmation: actively sought disconfirming evidence
- [ ] Overconfidence: confidence interval appropriately wide
- [ ] Narrative fallacy: mechanism identified, not just story

## SIGNPOSTS (track these to update prediction)
1. [Signal] → would shift probability to X%
2. [Signal] → would shift probability to X%

## CONFIDENCE FLAGS
- [H/M/L] Historical data quality
- [H/M/L] Actor incentive clarity
- [H/M/L] Model fit (does game theory apply here?)
```

---

## 7. Growth Path: Adding Lenses Over Time

The architecture supports incremental lens addition:

| Phase | Lens | Source Models | Status |
|-------|------|-------------|--------|
| v1 | Core (no flag) | Bayesian + game theory + scenarios | BUILD FIRST |
| v1 | `--geopolitics` | Predictive History, power transition, BDM-lite | BUILD FIRST |
| v1 | `--market` | Dalio cycles, sentiment, macro regime | BUILD FIRST |
| v2 | `--tech` | S-curves, Rogers diffusion, hype cycle | ADD LATER |
| v2 | `--personal` | EV calc, pre-mortem, kill criteria | ADD LATER |
| v3 | `--security` | Threat modeling, TTPs, attack surface | ADD LATER |
| v3 | `--health` | Medical evidence, RCT base rates | ADD LATER |

---

## 8. `/extract-alpha` Chain

The output format is designed so that the full prediction output can be piped directly to `/extract-alpha`:
- The SCENARIOS section surfaces non-obvious outcomes
- The SIGNPOSTS section identifies actionable monitoring targets
- The ACTOR MAP exposes hidden incentive structures
- The BIAS CHECK flags where the prediction might be wrong

`/make-prediction [topic] | /extract-alpha` → extracts the highest-signal, most surprising elements from the prediction analysis.

---

## Open Questions

1. **Calibration persistence**: Should `/make-prediction` maintain a log of past predictions + outcomes for Brier scoring over time? (Recommendation: yes — `data/predictions/` directory)
2. **Research integration**: Should the skill auto-invoke `/research` for live data, or expect input? (Recommendation: optional `--research` flag)
3. **Complexity control**: Deep mode (full 6-step) vs. quick mode (Bayesian base rate + one-paragraph scenario)? (Recommendation: yes, match `/research` depth flags)
4. **Prof Jiang content**: His lectures are YouTube-based and heavily current-events-dependent. Should the geopolitics lens reference his "laws" (e.g., "Law of Eschatological Convergence", "Law of Proximity") as named heuristics? (Recommendation: yes, but as illustrative frameworks, not hard rules)

---

## Sources

### Superforecasting / Tetlock
- Tetlock & Gardner, *Superforecasting* (2015) — [Google Books](https://books.google.com/books/about/Superforecasting.html?id=_lMPDAAAQBAJ)
- DTIC/Naval Postgraduate School, *Exploring Superforecasting Methodology* — [PDF](https://apps.dtic.mil/sti/tr/pdf/AD1069556.pdf)
- One Percent Rule, *Embracing Superforecasting* — [Substack](https://onepercentrule.substack.com/p/embracing-the-skill-of-superforecasting)
- The Decision Lab, *Philip Tetlock* — [Profile](https://thedecisionlab.com/thinkers/political-science/philip-tetlock)

### Game Theory / BDM
- National Academies, *3 Applications of Game Theory in Intelligence Analysis* — [Chapter](https://www.nationalacademies.org/read/13062/chapter/6)
- Bueno de Mesquita, *The Predictioneer's Game* (2009)
- SCIRP, *Game Theory Based Model for Predictive Analytics* — [Paper](https://www.scirp.org/journal/paperinformation?paperid=130292)
- Geopolitics Report, *Introduction to Game Theory* — [Substack](https://geopoliticsreport.substack.com/p/an-introduction-to-game-theory)

### Predictive History / Prof Jiang
- SingjuPost, *Jiang Xueqin Predictions for 2026 Transcript* — [Transcript](https://singjupost.com/jiang-xueqin-predictions-for-2026-empire-rivalry-collapse-transcript/)
- Economic Times, *China's Nostradamus* — [Article](https://m.economictimes.com/news/new-updates/chinas-nostradamus-jiang-xueqin-predicted-us-iran-war-his-chilling-third-forecast-is-now-going-viral/articleshow/129095416.cms)
- FirstPost, *Who is Xueqin Jiang* — [Explainer](https://www.firstpost.com/explainers/who-is-xueqin-jiang-chinese-professor-predicting-us-defeat-in-war-against-iran-13986568.html)

### Bayesian Reasoning
- Wikipedia, *Bayesian Inference* — [Article](https://en.wikipedia.org/wiki/Bayesian_inference)
- The Decision Lab, *Bayesian Inference in Data Science* — [Guide](https://thedecisionlab.com/reference-guide/statistics/bayesian-inference-in-data-science)
- arXiv, *A Cheat Sheet for Bayesian Prediction* — [Paper](https://arxiv.org/html/2304.12218v2)

### Scenario Planning
- Futures Garden, *Scenario Planning Primer* — [Article](https://garden.johanneskleske.com/scenario-planning)
- Shell/CMR, *Three Decades of Scenario Planning* — [PDF](http://strategy.sjsu.edu/www.stable/B290/reading/Cornelius,%20P.,%20A.%20Van%20de%20Putte,%20et%20al.,%202005,%20California%20Management%20Review%2048(1)%2092-109.pdf)
- GBN, *Plotting Your Scenarios* — [PDF](https://adaptknowledge.com/wp-content/uploads/rapidintake/PI_CL/media/gbn_Plotting_Scenarios.pdf)

### Prediction Markets & Scoring
- Good Judgment Open, *FAQ / Brier Score* — [FAQ](https://www.gjopen.com/faq)
- LessWrong, *Metaculus vs Manifold Accuracy* — [Analysis](https://www.lesswrong.com/posts/rFtQCpfnzSGpLKDGW/predictive-performance-on-metaculus-vs-manifold-markets)
- EA Forum, *Forecasting Accuracy Across Time Horizons* — [Post](https://forum.effectivealtruism.org/posts/hqkyaHLQhzuREcXSX/data-on-forecasting-accuracy-across-different-time-horizons)

### Market Cycles / Dalio
- Ray Dalio, *Investing in Light of the Big Cycle* — [Substack](https://raydalio.substack.com/p/investing-in-light-of-the-big-cycle)
- HBR, *Ray Dalio on Economic Trends* — [Podcast](https://hbr.org/podcast/2026/01/ray-dalio-on-economic-trends-investing-and-making-decisions-amid-uncertainty)

### Bias & Decision-Making
- PMC, *Mitigating Cognitive Biases in Risk Identification* — [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7398041/)
- The Mind Collection, *Premortem Analysis* — [Guide](https://themindcollection.com/premortem-analysis/)
- Annie Duke, *Thinking in Bets* / Kill Criteria — [Summary](https://www.getrecall.ai/summary/decision-making/this-will-make-you-a-better-decision-maker-or-annie-duke-thinking-in-bets-former-pro-poker-player)

---

## Recommended Next Steps

1. **`/create-prd`** — Turn this research into a PRD for `/make-prediction` with ISC
2. **`/first-principles`** — Validate the 3-engine architecture isn't overengineered (could 2 engines suffice?)
3. **`/red-team`** — Stress-test: "When would this framework give dangerously wrong predictions?"
4. **`/architecture-review`** — Evaluate build vs. reference approach (full implementation vs. prompt-only skill)
