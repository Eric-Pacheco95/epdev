# PRD: /make-prediction

## OVERVIEW

`/make-prediction` is a structured prediction skill for the Jarvis AI brain — designed for daily use. It takes a question about the future, clarifies the prediction parameters conversationally, then produces committed probability estimates across multiple outcomes with scenario analysis, reference-class anchoring, and signposts for monitoring. The skill uses a 2-layer architecture (scenario structure + calibration discipline) delivered through a 4-step pipeline (ORIENT, STRUCTURE, CALIBRATE, OUTPUT), with domain-specific lenses. It supports short-horizon (months) through long-horizon (10-15 year) predictions. Output is designed to spark further session work: research, project ideas, business/finance opportunities.

## PROBLEM AND GOALS

- Eric reasons about future outcomes daily (economy direction, geopolitical power shifts, AI's impact on humanity, market moves) without a structured framework, leading to ad-hoc reasoning vulnerable to cognitive biases
- Unstructured predictions lack reference-class anchoring, multi-outcome scenario enumeration, and signposts — making them hard to revisit, update, or learn from
- Goal: produce committed probability estimates across multiple outcomes (not single-point prediction) — show all sides of the issue with probability weights
- Goal: force conversational parameter clarification (the skill must understand exactly what it's predicting) while firewalling against influencing how it thinks about the outcome
- Goal: output drives session direction — predictions spark `/research`, project ideas, business opportunities, and Jarvis feature work
- Goal: build a tracked prediction record over time (50+ predictions) for calibration learning and eventual backtesting
- Goal: grow domain knowledge incrementally — each new domain lens increases prediction accuracy for that domain

## NON-GOALS

- No BDM-style actor tables (Position/Capability/Salience/Risk Tolerance) — false precision from LLM-estimated values; use structured prose instead
- No self-auditing bias checklist — LLM cannot meaningfully audit its own biases; replaced with user-facing interrogation questions
- No epistemic disclaimers in output — Eric knows these aren't 100% accurate; disclaimers waste space and get ignored
- `--tech` domain lens deferred to v2
- `--personal` lens not a separate mode — absorbed into default behavior
- No automatic `/extract-alpha` chaining in v1 — evaluate after verifying `/make-prediction` usefulness independently

## USERS AND PERSONAS

- **Primary**: Eric P (epdev) — sole operator of the Jarvis AI brain. Uses predictions daily to shape session direction across geopolitics, markets, technology, and life choices
- Eric is a build-first learner with ADHD session patterns. Values committed answers over hedged ones. Wants to see all outcomes with honest probability weights, not caveated non-answers
- Long-term: Eric is committed to building a 50+ prediction track record for calibration learning

## USER JOURNEYS OR SCENARIOS

1. **Daily geopolitical prediction (primary use case)**: Eric asks "What will the state of US-China relations look like in 10 years?" → Skill clarifies parameters ("Are you asking about economic decoupling, military posture, or overall relationship? By 2036?") → Eric confirms → Skill orients with reference class (historical great-power rivalry trajectories), builds 3-4 outcomes with probability weights, identifies key actors inline, outputs prediction with signposts. Eric reads output → sees an outcome that sparks curiosity → runs `/research` on that angle → discovers a business opportunity or Jarvis feature idea.

2. **Deep market analysis**: Eric runs `/make-prediction --deep --market "Where is BTC heading in the next cycle?"` → Conversational clarification on timeframe and what "heading" means → Full pipeline with Dalio cycle positioning, sentiment analysis, macro regime signals, historical cycle analogues. Multiple price-range outcomes with probabilities.

3. **Long-horizon AI impact**: Eric asks "How will AI change the job market by 2040?" → Skill auto-detects general/tech domain → Builds 4 scenarios across a 15-year horizon (full automation, augmentation, bifurcation, regulatory freeze) with probability weights and decade-level signposts.

4. **Tracked prediction**: Eric runs `/make-prediction --track "Will the US dollar lose reserve currency status by 2035?"` → Normal prediction output + prediction record saved to `data/predictions/2026-04-02-usd-reserve-status.md` for future review and eventual backtesting.

5. **Planning mode**: Eric runs `/make-prediction --planning "What happens if I start an AI consulting business?"` → Same analysis but probability weights suppressed; scenarios ranked by impact severity instead. Pre-mortem framing. Output designed for strategic planning, not probability anchoring.

6. **Auto-research chain**: Eric asks about something requiring current data → Skill detects post-cutoff dependency → Suggests running `/research` first, or auto-invokes if `--research` flag is set.

## FUNCTIONAL REQUIREMENTS

### Conversational Parameter Clarification (Step 0)

- FR-001: Before producing a prediction, the skill must clarify the prediction parameters conversationally: what specifically is being predicted, time horizon, and domain scope
- FR-002: Clarification must be brief (1-3 targeted questions max, not an interrogation)
- FR-003: The skill MUST NOT allow clarification to influence its thinking about the outcome direction — it clarifies WHAT is being predicted, not WHAT the answer should be. If Eric hints at a preferred outcome during clarification, the skill must acknowledge it and explicitly set it aside

### Core Pipeline

- FR-004: Skill accepts a free-text question and optional flags (`--deep`, `--geopolitics`, `--market`, `--tech`, `--track`, `--planning`, `--research`)
- FR-005: If no domain flag is provided, auto-detect domain from question content. If ambiguous, ask Eric during clarification
- FR-006: ORIENT step restates the question in one precise, falsifiable form with time horizon (confirmed during clarification)
- FR-007: ORIENT step identifies a reference class and states a base-rate probability as the starting anchor. If no reference class exists, state "No clear reference class — estimate is unanchored" and note the confidence impact
- FR-008: STRUCTURE step builds 3-4 outcome scenarios with domain-appropriate labels. Each scenario gets: label, committed probability (single number, not range), key driver (one sentence), one observable signpost
- FR-009: Scenario probabilities must sum to 100%
- FR-010: For long-horizon predictions (5+ years), scenarios should include intermediate signposts at multiple timeframes (e.g., "By 2028: X, By 2032: Y, By 2036: Z")
- FR-011: Actor analysis appears as a structured "Key Actors" section for geopolitics and competitive market predictions — prose format (2-3 sentences per actor: what they want, what leverage they have, what would change their behavior). Omitted for non-actor domains
- FR-012: CALIBRATE step states the overall most-likely outcome and its probability, then the strongest counterargument in one sentence
- FR-013: OUTPUT includes 3 user-facing interrogation questions that Eric should answer before acting on the prediction
- FR-014: `--track` is the default behavior (always track unless `--no-track` is specified) — builds the prediction journal automatically

### Deep Mode

- FR-015: `--deep` flag activates extended pipeline: full actor dynamics section + domain lens deep dive (framework-specific analysis) + historical analogue quality audit
- FR-016: Deep geopolitics mode applies Prof Jiang's Predictive History framework: civilizational cycle analysis, game-theoretic actor modeling (self-interest focus, not ideology), financial/institutional drivers, and historical pattern matching. Named heuristics (Law of Asymmetry, Law of Escalation, Law of Proximity, etc.) referenced where applicable
- FR-017: Deep geopolitics mode includes historical analogue quality audit — for each analogue: how it matches + at least 2 critical ways it does NOT match
- FR-018: Deep market mode includes Dalio Big Cycle positioning (which phase of short-term and long-term debt cycle), sentiment extremes, macro regime identification

### Planning Mode

- FR-019: `--planning` flag suppresses probability percentages and replaces with impact severity (HIGH/MEDIUM/LOW). Adds pre-mortem framing: "Assume this failed — what went wrong?" Includes note: "Scenarios ranked by impact, not likelihood"

### Research Integration

- FR-020: `--research` flag auto-invokes `/research` on the prediction topic before running the pipeline, injecting current data into the analysis
- FR-021: If the skill detects the question requires post-training-cutoff information, suggest `/research` first (or auto-invoke with `--research`)

### Tracking and Calibration

- FR-022: `--track` (default on) writes a prediction record to `data/predictions/YYYY-MM-DD-[slug].md` containing: question, falsifiable statement, probability per outcome, scenarios with signposts, timestamp, domain lens, and reference class used
- FR-023: Prediction records include a `## Resolution` section (empty at creation) with fields for: actual outcome, date resolved, which scenario materialized, what was missed, lessons learned
- FR-024: Future `/review-prediction` skill will read prediction records and score them (not built in v1, but record format must support it)

### Input Validation

- FR-025: If no input is provided, print the DISCOVERY section as a usage block and STOP
- FR-026: If input is fewer than 5 words, enter conversational clarification rather than rejecting

## NON-FUNCTIONAL REQUIREMENTS

- Quick mode output stays under 400 words (includes multi-outcome scenarios — slightly larger than original 300)
- Deep mode output stays under 1000 words
- Skill is prompt-only (SKILL.md) — no external scripts, no code, no mathematical computation
- All output uses ASCII-only characters (Windows cp1252 compatibility per steering rules)
- `--track` output files use UTF-8 encoding with slugified filenames
- Skill must be fast enough for daily use — no unnecessary overhead in quick mode

## ACCEPTANCE CRITERIA

- [ ] Skill produces conversational clarification questions before generating a prediction for ambiguous inputs | Verify: run with vague question ("What about China?"), confirm it asks clarifying questions
- [ ] Quick mode produces 3-4 outcome scenarios with committed probability numbers summing to 100% | Verify: run 3 test questions, check format and sum
- [ ] Probabilities are committed single numbers (not hedged ranges) per scenario | Verify: grep output for format `X%` without range brackets in scenario lines
- [ ] `--geopolitics` deep mode applies Predictive History framework (civilizational cycles, game-theoretic actors, financial drivers) | Verify: run `--deep --geopolitics` on a geopolitical question, check for framework elements
- [ ] `--geopolitics` deep mode includes historical analogue with quality audit (matches + 2 non-matches) | Verify: run `--deep --geopolitics`, check analogue section
- [ ] `--market` deep mode produces Dalio cycle positioning and macro regime signals | Verify: run `--deep --market` on a market question
- [ ] `--planning` mode suppresses all probability percentages from scenarios and uses impact severity | Verify: run `--planning` and grep for `%` in scenario section (should be absent)
- [ ] `--track` writes a prediction record file to `data/predictions/` with resolution section template | Verify: run `--track`, check file exists with all required fields including empty Resolution section
- [ ] Skill does not allow outcome-direction influence during clarification — if Eric hints at preferred outcome, skill acknowledges and sets it aside | Verify: test with leading question ("Don't you think BTC will moon?"), check skill doesn't anchor on it
- [ ] Long-horizon predictions (5+ years) include intermediate signposts at multiple timeframes | Verify: run a 10-year prediction, check for multi-timeframe signposts
- [ ] Actor analysis appears as structured prose section for geopolitical predictions but is omitted for non-actor domains | Verify: run geopolitical vs. personal question, compare sections
- [ ] Anti-criterion: output does NOT contain epistemic disclaimers, bias checklists, or self-audit checkboxes | Verify: grep output for "epistemic", "bias check", "calibrated forecasting", checkbox patterns

ISC Quality Gate: PASS (6/6)

## SUCCESS METRICS

- Eric uses `/make-prediction` daily or near-daily in the first 2 weeks after deployment (adoption signal — target: 10+ uses)
- Predictions spark follow-up work (research, project ideas, business opportunities) in at least 50% of uses (session-driver signal)
- At least 20 predictions tracked via `--track` within the first month (journal-building pace for calibration goal)
- Eric does not report that predictions feel hedged, wishy-washy, or non-committal (commitment signal)
- Prediction output format is compact enough to scan in <30 seconds in quick mode (efficiency signal)
- (v2 metric) After 50+ tracked predictions, backtesting reveals measurable patterns in prediction accuracy by domain

## OUT OF SCOPE

- Quantitative Brier score calibration in v1 (deferred until 20+ resolved predictions; record format supports future scoring)
- Automated backtesting pipeline (v2/v3 — the feature Eric is most excited about; requires significant tracked prediction volume first)
- `--tech` domain lens (deferred to v2 — add S-curves, Rogers diffusion, hype cycle)
- `--security` domain lens (deferred to v3 — threat modeling, TTP prediction)
- `--health` domain lens (deferred to v3 — medical evidence, RCT base rates)
- `--legal` domain lens (deferred — regulatory outcome prediction)
- `/review-prediction` skill (companion skill for resolving and scoring tracked predictions — v2)
- `/extract-alpha` chaining (evaluate after v1 proves useful independently)
- External model routing (Codex adversarial review of predictions — v3)
- Standalone prediction project repo (evaluate after prediction volume justifies separation from epdev)

## DEPENDENCIES AND INTEGRATIONS

- **SKILL.md file**: `.claude/skills/make-prediction/SKILL.md` — the skill definition (prompt-only, no code)
- **data/predictions/ directory**: must be created during implementation for `--track` records
- **Existing skills**:
  - `/research` (upstream — auto-invoked with `--research` flag, or suggested when post-cutoff data needed)
  - `/analyze-claims` (downstream — verify surprising claims in the analysis)
  - `/red-team` (downstream — stress-test the prediction before acting)
  - `/extract-alpha` (downstream — evaluate for v2 after proving v1 usefulness)
- **Research brief**: `memory/work/make-prediction/research_brief.md` — source material for domain lens content
- **Absorbed content**: `memory/learning/absorbed/` — Prof Jiang lectures and other domain knowledge already in Jarvis's learning system

## RISKS AND ASSUMPTIONS

### Risks
- **Outcome-influence during clarification** (HIGH): Conversational step could inadvertently anchor the skill toward Eric's implied preferred outcome. Mitigation: explicit instruction to acknowledge hints and set them aside; firewall between parameter clarification and outcome reasoning
- **Long-horizon accuracy decay** (HIGH): 10-15 year predictions have fundamentally higher uncertainty than 1-year predictions. Mitigation: more scenarios (4 vs 3), intermediate signposts, explicit acknowledgment of compounding uncertainty
- **Domain auto-detection error** (MEDIUM): LLM misclassifies a market question as geopolitics or vice versa. Mitigation: clarification step catches most mismatches; explicit flag override available
- **Post-training-cutoff blindness** (MEDIUM): Predictions about current events may be built on stale information. Mitigation: `--research` flag for auto-fetching current data; skill suggests `/research` when post-cutoff dependency detected
- **Daily-use fatigue** (LOW): If output is too verbose or repetitive, daily use drops off. Mitigation: quick mode default is compact; format designed for scanning

### Assumptions
- Quick mode (~400 words) is sufficient for daily-use predictions; deep mode handles occasional deep dives
- Two domain lenses (geopolitics + market) cover Eric's most frequent prediction domains at v1
- The `data/predictions/` directory will be created during implementation
- LLM domain auto-detection is reliable enough for most questions (clarification step handles edge cases)
- Prof Jiang's Predictive History framework (civilizational cycles + game theory + financial/institutional analysis) is a valid and useful lens for geopolitical predictions
- Eric will resolve tracked predictions when outcomes become clear (essential for future calibration/backtesting)
- Committed probability numbers (single %, not ranges) are more useful for Eric's decision-making than hedged ranges, even at the cost of false precision

## OPEN QUESTIONS

1. **Resolved: --track default** — `--track` is default on (always build the journal). Use `--no-track` to suppress.
2. **Resolved: epistemic disclaimers** — dropped entirely per Eric's preference.
3. **Resolved: multi-outcome** — multiple outcomes with probability weights is the default, not single-point prediction.
4. Should `--track` also create a signpost-monitoring task via `/backlog` for prediction review at the signpost date?
5. Should the skill support `--update <slug>` to revise an existing tracked prediction when new evidence arrives? (Likely yes for v2)
6. At what prediction count should we trigger the first backtesting analysis? (Proposed: 25 resolved predictions)
7. Should deep mode be the default for `--geopolitics` (since geopolitical predictions almost always benefit from historical analogue audit and actor analysis)?
8. How should Prof Jiang's named "laws" be treated — as fixed heuristics that always apply, or as a library the skill selects from based on the specific question?

## VISION: v2/v3 ROADMAP

### v2: Calibration + More Domains
- `/review-prediction` companion skill — resolve tracked predictions, score accuracy, identify calibration patterns
- `--tech` domain lens (S-curves, Rogers diffusion, hype cycle as debiasing tool)
- `--update <slug>` for revising predictions with new evidence
- Automated backtesting on historical data — the feature Eric is most excited about
- `/research` auto-chain as default (not just a flag)

### v3: Prediction Engine
- Backtesting pipeline — test prediction framework against known historical outcomes to improve accuracy
- External model adversarial review (Codex reviews prediction logic)
- Cross-prediction pattern analysis ("your geopolitical predictions tend to be overconfident by X%")
- Standalone project repo if prediction volume and domain knowledge justifies separation
- Additional domain lenses: `--security`, `--health`, `--legal`
