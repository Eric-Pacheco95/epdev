# PRD: Jarvis Predictive Intelligence Layer

**Version:** 1.0
**Date:** 2026-04-05
**Owner:** Eric P
**Status:** READY FOR IMPLEMENTATION

---

## OVERVIEW

The Predictive Intelligence Layer transforms Jarvis from a passive prediction tracker into an active calibration engine. It builds on the existing `/make-prediction` skill and `data/predictions/` store with three interconnected components: a backtesting producer that bootstraps calibration by running constrained historical predictions, a weekly review task that surfaces due predictions and closes the resolution loop with Eric, and a calibration feedback loop that progressively learns Eric's domain-specific biases and injects adjustments into future predictions. Together these components form the foundation of a personal probabilistic reasoning system that compounds over time -- accuracy improves, biases become visible, and prediction quality feeds into content (Substack), knowledge (learning signals), and eventually trading signals (crypto-bot). This is Sprint 1 of a 3-sprint roadmap.

---

## PROBLEM AND GOALS

- **Problem:** Eric makes predictions using `/make-prediction` but they disappear into `data/predictions/` with no feedback loop. There is no mechanism to know whether the predictions are accurate, improving, or systematically biased. Calibration requires resolved predictions; without a resolution workflow, the data never matures.
- **G1 (Sprint 1):** Bootstrap calibration by generating backtest predictions on curated historical events with honest leakage disclosure
- **G2 (Sprint 1):** Close the resolution loop so Eric can mark predictions as resolved in under 60 seconds via Slack
- **G3 (Sprint 2):** Produce domain-level calibration adjustments that are automatically injected into `/make-prediction` to improve future accuracy
- **G4 (Sprint 2):** Convert resolved predictions into Substack content drafts via the content pipeline
- **G5 (Sprint 3):** Feed market prediction accuracy signals into crypto-bot as a domain weighting input

---

## NON-GOALS

- Real-time prediction scoring or automated outcome verification (Sprint 1 -- Eric resolves manually)
- Natural language bias narrative (Sprint 1 uses JSON calibration only; prose narrative is Sprint 2)
- Automated crypto-bot trade decisions derived from predictions (Sprint 3 is read-only signal feed only)
- Predictions for third parties or external audiences (system is Eric-only)
- Replacing `/make-prediction` skill with a separate pipeline -- all generation still flows through the existing skill

---

## USERS AND PERSONAS

- **Eric (primary):** Makes predictions, receives weekly resolution prompts, approves calibration adjustments. Primary consumer of the accuracy feedback.
- **Jarvis autonomous dispatcher:** Runs backtesting producer and weekly review task on schedule. Writes signals, generates Slack notifications.
- **`/make-prediction` skill:** Consumer of calibration adjustments at prediction-generation time.
- **crypto-bot (Sprint 3):** Downstream consumer of market prediction accuracy signals.

---

## USER JOURNEYS OR SCENARIOS

**Journey 1: Weekly resolution (Step 3 of morning brief)**
1. Monday morning, Eric runs `/vitals`
2. Slack notification arrives in #epdev: "2 predictions due for review: [BTC cycle prediction - due in 7 days] [Geopolitics 2035 - signpost check]"
3. Eric replies "correct" or "wrong" or "partial: [note]" inline in Slack thread
4. Jarvis marks prediction resolved, writes accuracy signal, checks if calibration threshold (20 resolved) is met

**Journey 2: Backtesting producer (overnight)**
1. Overnight dispatcher selects 1-3 unrun events from `data/backtest_events.yaml`
2. For each event: constructs date-injection prompt with curated "what was knowable" context, runs claude with `/make-prediction` framing, constrained to that date's knowledge state
3. Compares predicted outcome against known outcome, scores prediction
4. Writes signal tagged `backtested: true, leakage_risk: HIGH, weight: 0.5` -- requires Eric review before calibration promotion

**Journey 3: Calibration update (automatic, post-resolution)**
1. After 5th resolved prediction hits the counter (total >= 20), calibration loop triggers
2. Analyzes resolved predictions by domain (geopolitics, market, planning, other)
3. Computes per-domain accuracy rate and overconfidence/underconfidence bias
4. Writes updated `data/calibration.json` with domain adjustments bounded to [-0.15, +0.15]
5. Next `/make-prediction` run reads calibration file and injects: "Your geopolitics predictions run 7% overconfident historically -- stated probabilities adjusted down 0.07"

**Journey 4: Substack content hook (Sprint 2)**
1. Every 5 resolved predictions, content pipeline generates a "Prediction Debrief" draft
2. Draft includes: the original prediction, what happened, calibration lesson
3. Queued in Substack content pipeline as a publishable post

---

## FUNCTIONAL REQUIREMENTS

### Component 1: Backtesting Producer

- **FR-001** Backtesting producer reads curated events from `data/backtest_events.yaml`; each entry has: `event_id`, `description`, `knowledge_cutoff_date`, `known_outcome`, `domain`, `at_time_context` (what was publicly known at the cutoff date)
- **FR-002** Producer selects up to 3 unrun events per execution cycle (tracks run state in `data/backtest_state.json`)
- **FR-003** For each event, producer constructs a date-injection prompt: "It is {knowledge_cutoff_date}. You may only reference information available before this date. The following context reflects what was publicly known at this time: {at_time_context}. [/make-prediction prompt follows]"
- **FR-004** Prediction output is written to `data/predictions/backtest/` with frontmatter: `backtested: true`, `leakage_risk: HIGH`, `weight: 0.5`, `status: pending_review`, `known_outcome: {outcome}`
- **FR-005** Scoring function compares each predicted outcome's probability against whether that outcome occurred; writes accuracy score (0.0-1.0) and Brier score per prediction
- **FR-006** Any backtest with model confidence > 85% on the winning outcome triggers automatic `[SUSPECT LEAKAGE]` flag and requires Eric review before signal is written
- **FR-007** Backtest accuracy signals are written to the learning loop with `source: backtest` and `weight: 0.5` (half influence of forward-looking signals)
- **FR-008** Producer registers in dispatcher as routine `prediction_backtest` with schedule `weekly` and model `sonnet`

### Component 2: Weekly Prediction Review Task

- **FR-009** Weekly task scans `data/predictions/` (excluding `backtest/`) for predictions where `status: open` AND at least one of: due date within 30 days, a defined signpost date has passed, or prediction is past its horizon date
- **FR-010** Task posts a structured Slack message to #epdev listing each due prediction with: title, domain, confidence level, due/horizon date, and a one-line resolution prompt
- **FR-011** Task also posts any `backtest/` predictions with `status: pending_review` in a separate block, with leakage flag disclosed
- **FR-012** Eric resolves a forward-looking prediction by replying to the Slack thread: "correct", "wrong", "partial: [note]", or "defer: [new date]"
- **FR-013** Slack poller (`/absorb` pipeline) parses resolution replies and writes `status: resolved`, `resolved_date`, `outcome_label`, and `resolution_note` back to the prediction file
- **FR-014** After writing resolution, dispatcher is notified via backlog task to check calibration threshold
- **FR-015** Weekly review task is registered as routine `prediction_weekly_review` with schedule `weekly_monday` and model `haiku`

### Component 3: Calibration Feedback Loop

- **FR-016** Calibration loop is triggered when resolved prediction count (forward-looking only, `backtested: false`) crosses a multiple of 5 AND total resolved >= 20
- **FR-017** Loop reads all resolved predictions, groups by `domain` field, computes per-domain: accuracy rate, mean confidence on correct outcomes, mean confidence on incorrect outcomes, overconfidence delta
- **FR-018** Writes `data/calibration.json` with structure: `{"version": N, "updated": "YYYY-MM-DD", "domains": {"geopolitics": {"adjustment": -0.07, "n_resolved": 12, "accuracy": 0.58}, ...}}`
- **FR-019** Calibration adjustments are bounded to [-0.15, +0.15] per domain; values outside this range are clamped and flagged in the output
- **FR-020** `/make-prediction` SKILL.md Step 0 is updated to read `data/calibration.json` and inject a calibration context block: "Calibration active for {domain}: your historical accuracy is {pct}%, adjust stated probabilities by {delta}" when the file exists and the domain matches
- **FR-021** Calibration loop writes a signal to the learning loop: `source: calibration`, containing the domain adjustment delta and the n_resolved count
- **FR-022** Backtest predictions contribute to calibration only after Eric marks them `status: reviewed` (not auto-promoted)
- **FR-023** Calibration loop is registered as dispatcher routine `prediction_calibration_check` triggered after each resolution event, model `haiku` for counting, `sonnet` for analysis

### Sprint 2 Extensions (design now, build later)

- **FR-024** After every 5 resolved predictions, content pipeline generates a "Prediction Debrief" draft and queues it in the Substack content pipeline
- **FR-025** Calibration narrative (`data/calibration_narrative.md`) is generated by Sonnet and summarizes domain biases in plain English alongside the JSON adjustments

### Sprint 3 Extensions (design now, build later)

- **FR-026** Market domain prediction accuracy is written as a signal to crypto-bot's signal intake (read-only; does not affect trade execution directly)
- **FR-027** crypto-bot displays prediction accuracy rate for market domain in its Slack status report

---

## NON-FUNCTIONAL REQUIREMENTS

- **Leakage transparency:** Every backtested prediction file and signal must carry `leakage_risk: HIGH` metadata -- no exceptions; this field is never optional for backtest outputs
- **Calibration safety bounds:** Adjustments to `/make-prediction` output are bounded to [-0.15, +0.15] per domain; the skill must clamp and log any out-of-range values
- **Idempotency:** Backtesting producer must not re-run events already in `backtest_state.json`; weekly review must not duplicate Slack posts for the same prediction in the same week
- **Worktree isolation:** Backtesting producer operates in a git worktree (per autonomous systems steering rule); no main working tree mutations
- **Resolution latency:** A prediction must be resolvable by Eric in <= 60 seconds from the Slack notification (single reply, no context-switching required)
- **Signal weight enforcement:** The learning loop and calibration loop must respect `weight: 0.5` on backtest signals; weighted input must be visibly documented in calibration computation

---

## ACCEPTANCE CRITERIA

### Sprint 1 ISC

- [ ] `data/backtest_events.yaml` exists with >= 25 curated events, each with `event_id`, `knowledge_cutoff_date`, `known_outcome`, `domain`, and `at_time_context` | Verify: Read | [E][A]
- [ ] Backtesting producer runs end-to-end for a single event and writes a valid prediction file to `data/predictions/backtest/` with all required frontmatter fields | Verify: Test + Read | [E][M] | model: sonnet |
- [ ] All backtest prediction files carry `backtested: true`, `leakage_risk: HIGH`, and `weight: 0.5` in frontmatter | Verify: Grep `data/predictions/backtest/` | [E][A]
- [ ] Predictions with model confidence > 85% on winning outcome carry `[SUSPECT LEAKAGE]` flag in frontmatter | Verify: Test with synthetic high-confidence fixture | [E][M] | model: haiku |
- [ ] Weekly review task posts Slack notification listing all open predictions with due dates within 30 days | Verify: Run task + check #epdev Slack | [E][M] | model: sonnet |
- [ ] Slack resolution reply "correct", "wrong", "partial: [note]", or "defer: [date]" is parsed and written back to prediction file within one poller cycle | Verify: End-to-end test | [E][M] | model: sonnet |
- [ ] No backtest signal is written to the learning loop without `status: reviewed` on the source prediction file | Verify: Test attempt to run calibration loop with unreviewed backtests -- confirm it skips | [E][M] (anti-criterion)

**ISC Quality Gate: PASS (6/6)**
Count: 7 (within 3-8) | Single-sentence: PASS | State-not-action: PASS | Binary-testable: PASS | Anti-criterion: present (FR-022 enforced) | Verify method: present on all

### Sprint 2 ISC (design complete, build deferred)

- [ ] `data/calibration.json` created after 20th resolved forward-looking prediction, with domain-keyed structure | Verify: Read | [E][A] | model: haiku |
- [ ] `/make-prediction` injects calibration context block when `data/calibration.json` exists and domain matches | Verify: Read SKILL.md Step 0 + Test run | [E][M] | model: sonnet |
- [ ] Calibration adjustments are clamped to [-0.15, +0.15] per domain and out-of-range values are flagged in output | Verify: Test with synthetic extreme values | [E][M] | model: haiku |
- [ ] Calibration loop does NOT trigger on fewer than 20 resolved forward-looking predictions | Verify: Test with 19 resolved predictions -- confirm loop skips | [E][M] (anti-criterion)
- [ ] Substack content pipeline receives a "Prediction Debrief" draft after every 5 resolved predictions | Verify: Check content pipeline queue after resolution event | [I][M] | model: sonnet |

---

## SUCCESS METRICS

- **Calibration velocity:** >= 1 prediction resolved per week (needed to reach 20 for calibration in ~5 months)
- **Backtest coverage:** >= 25 events run within first 2 weeks of Sprint 1 deployment
- **Resolution friction:** Eric resolves a prediction in <= 60 seconds from Slack notification (measured by Slack thread timestamp delta)
- **Calibration accuracy:** After 20 resolved predictions, per-domain accuracy rate is measurable (any value -- the point is instrumentation, not a target)
- **Leakage catch rate:** >= 20% of backtested events trigger [SUSPECT LEAKAGE] flag (validates the detector is working; if 0%, the threshold is too high)
- **Sprint 3 gate:** Market domain has >= 10 resolved predictions before crypto-bot integration begins

---

## OUT OF SCOPE

- Automated outcome verification via web search (deferred to Sprint 2 stretch goal after B workflow is validated)
- `/make-prediction` UI changes beyond calibration context injection
- Predictions for domains not currently used (the 4 existing domains are: geopolitics, market, planning, other)
- Multi-user prediction tournaments or external sharing
- Real-time signpost monitoring (monitoring sources are in external_monitoring overnight dimension, not real-time)

---

## DEPENDENCIES AND INTEGRATIONS

| Dependency | Type | Notes |
|-----------|------|-------|
| `data/predictions/` | Storage | Existing. Backtest predictions go in `data/predictions/backtest/` subdirectory |
| `/make-prediction` SKILL.md | Skill | Step 0 updated to read calibration.json (Sprint 2) |
| `orchestration/task_backlog.jsonl` | Dispatcher | All 3 routines register via `routine_id` dedup pattern |
| `data/routine_state.json` | Scheduler | Weekly routines register here (pattern: `prediction_backtest`, `prediction_weekly_review`) |
| Slack poller (`/absorb`) | Integration | Parses resolution replies from #epdev threads |
| Learning loop (`memory/learning/signals/`) | Output | Backtest and calibration signals write here |
| `data/jarvis_index.db` | Index | Signal lineage tracking for prediction signals |
| `data/calibration.json` | Runtime state | Created by Sprint 2 calibration loop; read by `/make-prediction` |
| Substack content pipeline | Sprint 2 | Debrief drafts queued via existing content pipeline |
| crypto-bot signal intake | Sprint 3 | Read-only market accuracy signal feed |

---

## RISKS AND ASSUMPTIONS

### Risks

- **Leakage degrades calibration quality:** Date-injection prompts are a best-effort constraint. Claude may still use future knowledge for well-known historical events. Mitigation: `at_time_context` field in backtest events provides explicit knowledge boundaries; `[SUSPECT LEAKAGE]` detector catches statistically anomalous confidence; backtest signals are weighted at 0.5x.
- **Calibration adjustments overshoot:** Small sample sizes (20-30 resolved predictions) can produce noisy calibration adjustments that overcorrect. Mitigation: Hard cap at [-0.15, +0.15]; adjustments only update on multiples of 5 resolved predictions (not every single resolution).
- **Resolution loop breaks on Slack poller failures:** If the Slack poller is suspended or fails, resolutions accumulate without being processed. Mitigation: Weekly review task also checks for unprocessed threads; Eric can also resolve by directly editing the prediction file.
- **crypto-bot integration (Sprint 3) requires clean domain taxonomy:** Market predictions must be consistently tagged to be useful as signals. Risk that early predictions use inconsistent domain labeling. Mitigation: Validate all existing predictions for `domain: market` consistency before Sprint 3 begins.

### Assumptions

- Eric will resolve at least 1 prediction per week once the weekly review task is active
- The Slack poller (`/absorb`) can be extended to parse prediction resolution syntax without full rewrite
- `/make-prediction` calibration injection is opt-out (always active when `calibration.json` exists), not opt-in
- `data/backtest_events.yaml` is seeded manually by Eric + Jarvis in a design session before backtesting producer runs (not auto-generated)

---

## OPEN QUESTIONS

- **Backtest event curation session:** Who seeds the initial 25 events in `data/backtest_events.yaml`? Recommendation: Jarvis proposes 40 candidates (10 per domain) in a structured Slack message; Eric approves/rejects in a single review session before Sprint 1 build begins.
- **Resolution syntax in Slack:** Should "partial: [note]" be a free-form note or structured (e.g., "partial outcome 1 correct, outcome 3 wrong")? This affects the parser complexity.
- **Calibration injection UI:** When calibration is applied, should `/make-prediction` show Eric the raw adjustment ("Adjusted geopolitics -7%") or absorb it silently? Recommendation: always show it (transparent calibration builds trust).
- **Sprint 2 timing:** What is the trigger to start Sprint 2? Option A: After 10 forward-looking predictions are resolved (shows the loop works). Option B: After Sprint 1 has been running 30 days. Recommendation: Option A.
- **Domain taxonomy expansion:** "Other" is a catch-all domain. As predictions accumulate, should it be split? (e.g., technology, health, personal) Defer to Sprint 2 calibration analysis -- the data will show where splits are warranted.

---

## SPRINT ROADMAP

### Sprint 1: Bootstrap (this sprint)
**Goal:** Resolution loop + backtesting producer + leakage safeguards live

| Component | Deliverable |
|-----------|------------|
| `data/backtest_events.yaml` | Seeded with 25+ events (design session first) |
| `tools/scripts/prediction_backtest_producer.py` | Autonomous backtesting producer |
| `tools/scripts/prediction_review_task.py` | Weekly review Slack notification |
| `tools/scripts/prediction_resolver.py` | Parses Slack replies, writes resolution to prediction file |
| Dispatcher registration | `prediction_backtest` (weekly) + `prediction_weekly_review` (weekly_monday) |
| Test suite | `tests/test_prediction_backtest.py`, `tests/test_prediction_resolver.py` |

### Sprint 2: Calibration + Content (after 10 resolved predictions)
**Goal:** Calibration loop live, `/make-prediction` improved, Substack debrief pipeline

| Component | Deliverable |
|-----------|------------|
| `tools/scripts/prediction_calibration.py` | Calibration analysis + `data/calibration.json` writer |
| `/make-prediction` SKILL.md | Step 0 updated to inject calibration context |
| `data/calibration_narrative.md` | Prose bias summary generated by Sonnet |
| Content pipeline hook | "Prediction Debrief" draft generator |

### Sprint 3: Crypto-bot Integration (after 10 resolved market predictions)
**Goal:** Market accuracy as trading signal input

| Component | Deliverable |
|-----------|------------|
| Signal feed adapter | Market accuracy → crypto-bot signal intake |
| crypto-bot Slack status | Prediction accuracy rate in daily status report |
