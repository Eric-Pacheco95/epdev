# Fallacy Detection: Overnight Runner as Backlog Producer (5C-5)

**Date**: 2026-04-02
**Reviewer**: Jarvis Fallacy Analyst
**Proposal**: Make overnight runner emit backlog tasks via `backlog_append()` after its iterative loop

---

## Evidence gathered before analysis

- `data/overnight_state.json`: `{"test": true, "last_dimension": "scaffolding"}` — only test data; no production run has ever completed with real output
- `data/logs/overnight_2026-04-02.log`: All 6 dimensions completed in 0.0-0.1 min with "0 kept, 0 discarded" and "QUALITY_GATE: UNKNOWN (no result line found)" — the `claude -p` calls are returning immediately with no agent work
- `data/logs/overnight_2026-04-01.log`: Failed with `NameError: 'os' not imported` on the first dimension run — self-heal patched it, then today's run "succeeded" but produced zero output
- The overnight runner's `OVERNIGHT_RESULT:` line is only emitted when the agent completes real iterative work and prints the structured result. Today it was never printed.
- Current backlog producers: heartbeat (auto-proposes remediation tasks), routines engine (scheduled tasks), /backlog skill (session captures) — all three propose work that **has not yet been done**

---

## 1. False Equivalence: "Overnight output is the same kind of thing as heartbeat/routine/session tasks"

**Verdict: Real fallacy — and the most significant one in this proposal.**

The proposal frames overnight output as another "producer" alongside heartbeat, routines, and /backlog. This is a category error.

The three existing producers all emit tasks that represent **future work**: heartbeat says "signal_velocity crossed threshold — go synthesize"; routines says "it's Monday, run the weekly review"; /backlog says "Eric wants this done later." The backlog is a queue of *pending intentions*.

The overnight runner — when it works — produces a different artifact class: **completed improvements**. It makes commits, measures metrics, reverts failures, and writes a TSV run log. Its OVERNIGHT_RESULT line reports `kept=N discarded=M` — past tense. The work is done. Committing it to a branch is the deliverable.

Emitting a backlog task *after* a dimension runs creates an ambiguity: does the task represent the improvement that was already made, or a follow-on action that wasn't? If it's the former, adding it to the backlog is misleading — the dispatcher would pick it up and attempt to re-execute completed work. If it's the latter, the overnight runner would need to identify and articulate unfinished follow-ons, which is a qualitatively different capability than what it currently does.

The equivalence breaks down further when you consider verification: heartbeat tasks have ISC written by the heartbeat code at proposal time; session tasks have ISC written by Eric or Jarvis during the session. Both are written before execution. Overnight-sourced tasks would need ISC written *after* execution, which means the overnight agent is retroactively constructing testable criteria for work it either did or couldn't finish. That's a fundamentally different authoring context.

**The valid version of this idea** is not "overnight runner becomes a backlog producer" but "overnight runner flags unresolved gaps as backlog proposals." Those are separable concerns and the proposal conflates them.

---

## 2. Premature Optimization: Building a producer interface for a dormant system

**Verdict: Confirmed — building atop an unvalidated base.**

The overnight state file contains only test data: `{"test": true, "last_dimension": "scaffolding"}`. Today's run "completed" with all 6 dimensions at 0.0-0.1 min, zero output, and two UNKNOWN quality gates — this is a silent success that represents zero real work. The `claude -p` subprocesses are returning without the agent doing anything meaningful (no OVERNIGHT_RESULT line printed means the iterative loop never ran to completion).

Building a backlog producer interface now means building a system that will never fire until the underlying runner is producing real dimension output. That's not just wasted effort — it creates a false sense of progress. When the runner is eventually fixed and starts producing output, the producer interface will activate in an untested state on real data.

The correct sequencing is:
1. Fix overnight runner so dimensions complete with real kept/discarded counts
2. Validate that the Slack summary and run reports reflect actual work
3. Then, if unresolved gaps are being identified, add producer logic

Building the producer first inverts this dependency chain. There is no benefit to having a backlog producer attached to a system that outputs nothing.

**Counterargument considered**: One could argue that building the interface now means the code is ready when the runner is fixed. This has merit only if the interface is trivial. It is not (see fallacy #3). The prompt engineering investment required to generate structured ISC from dimension output is non-trivial, and building it against dummy data means the prompts won't be calibrated on real output patterns.

---

## 3. Hidden Complexity: ISC generation from overnight dimension output

**Verdict: Confirmed — this is not a trivial addition.**

The proposal requires overnight dimension output to be transformed into structured, verifiable ISC criteria suitable for dispatcher execution. The current overnight prompt (`build_dimension_prompt()`) instructs the agent to: run a metric, iterate, commit, print an OVERNIGHT_RESULT line. It does not instruct the agent to produce structured recommendations, formulate testable criteria, or assess what follow-on work is needed.

Adding this capability requires:

1. **Prompt engineering work**: The dimension prompt would need an additional section instructing the agent to assess what it *couldn't* fix and emit a structured proposal block (description, ISC array with verify commands, tier, autonomous_safe flag). This needs to be in a machine-parseable format — JSONL or a delimited block — that the overnight runner's result parser can extract reliably.

2. **Failure mode surface**: The agent may emit a proposal block for something it partially fixed, creating a backlog task that duplicates committed work. Or it may emit no proposal when a gap is obvious. Or the ISC it generates may not be binary-testable by the dispatcher's verifier. Each of these is a new failure mode.

3. **Testing requirement**: The proposal-emitting path can only be validated when the overnight runner is actually producing real kept/discarded output. You cannot test ISC generation quality against a runner that returns nothing.

4. **Calibration challenge**: For Alternative 1 (one task per dimension), you'd need up to 6 well-formed ISC sets per run, each grounded in that dimension's specific metric and scope. For Alternative 2 (one summary task), you'd need a synthetic aggregation that's coherent enough to be actionable. Neither is trivial to prompt-engineer correctly.

The CLAUDE.md rule applies directly here: "When building a new skill, evaluate each step: does this step require intelligence (judgment, synthesis, natural language generation)? Yes -> keep in SKILL.md." ISC generation from dimension output requires judgment. It cannot be a deterministic post-processing step.

---

## 4. Scope Bundling: Dispatcher budget controls bundled with overnight convergence

**Verdict: Confirmed — two separable concerns bundled by sprint label.**

Dispatcher budget controls (max tasks/day, max time/task, daily aggregate cap) are a dispatcher concern. They answer the question: "how do I prevent the dispatcher from over-spending resources?" This question exists independently of the overnight runner and would be valid even if overnight runner never emits a single backlog task.

The overnight runner producer proposal answers a different question: "should the overnight runner feed the dispatcher?" These have different stakeholders (dispatcher safety vs. overnight output quality), different implementation locations (dispatcher config vs. overnight runner code), and different validation criteria.

The bundling appears to be a 5C-5 label artifact — both changes feel like "completing the pipeline" so they get grouped. But if the overnight producer idea is deferred (as this analysis suggests it should be), the budget controls have independent value and should not be deferred with it.

**Risk of bundling**: If this sprint is approved as a unit, both features ship together or neither does. That creates unnecessary coupling. Budget controls are low-risk, high-value, and uncontroversial. The producer interface is high-risk, low-current-value, and depends on an unvalidated system. They should be separate backlog items with separate ISC.

---

## 5. Goodhart Risk: No quality feedback loop on overnight recommendations

**Verdict: Real structural gap — not a fallacy per se, but a design flaw that the proposal ignores.**

The proposal's execution chain is: overnight runner completes -> emits backlog task -> dispatcher picks it up -> verifies against ISC -> marks done. The ISC verification is written by the overnight runner itself. There is no external quality gate on whether the overnight runner's recommendations were correct, safe, or aligned with Eric's actual goals.

The existing backlog producers have implicit quality gates:
- Heartbeat tasks are grounded in metric thresholds with defined pass/fail criteria
- Routines tasks are human-authored and reviewed at design time
- /backlog tasks are Eric-authored in-session

Overnight-generated tasks would be the only self-referential proposals in the pipeline: a system assessing its own output quality, writing ISC for its own recommendations, and having those recommendations executed without human review.

This is a concrete instance of the Goodhart risk: the overnight runner optimizes its stated metric for a dimension, then proposes a follow-on task to continue that optimization. The metric may not correctly proxy for the actual goal. The follow-on task may deepen an optimization that was already wrong. The dispatcher verifies the ISC, not the intent.

**The missing layer**: Any overnight-sourced backlog task should route through a human review gate before becoming `autonomous_safe: true`. The proposal does not mention this. Without it, the pipeline has an unreviewed path from autonomous observation to autonomous execution — which violates the three-layer SENSE/DECIDE/ACT pattern in CLAUDE.md.

**What this means concretely**: If overnight runner detects that `prompt_quality` metric improved when it simplified prompts, and then proposes a task "continue simplifying prompts in [X area]", the dispatcher would execute that autonomously. The original improvement may have been valid; the follow-on recommendation may reduce prompt quality in a context the runner couldn't measure. There is no catch.

---

## 6. What Is Sound

The following elements of the proposal are logically well-grounded:

**Alternative 3 (conditional per-dimension) is the right shape if the feature is built.** Only emitting when actionable recommendations exist is sound reasoning. It avoids noise, respects the "Idle Is Success" doctrine already embedded in the codebase, and prevents the backlog from being flooded by low-signal tasks. Alternatives 1 and 2 emit tasks regardless of whether there's anything worth doing.

**The underlying intuition is valid.** The overnight runner and the dispatcher *should* eventually be connected. If the runner identifies a class of improvements it couldn't complete in N iterations, that is exactly the kind of signal the backlog should capture for human or dispatcher follow-up. The direction is right; the timing and mechanism are wrong.

**Dispatcher budget controls are independently sound.** Max tasks/day and daily aggregate cap are necessary guardrails as the backlog grows. They're well-scoped, low-risk, and the correct response to having multiple producers that could saturate the dispatcher. These should be built regardless of what happens with the overnight producer idea.

**The lock mechanism design is correct.** The overnight runner and dispatcher both use claude locks, operate in separate worktrees, and have no shared state. The proposal doesn't break this boundary. The architecture is sound.

---

## Summary Verdict

| Claim | Verdict | Severity |
|---|---|---|
| Overnight output is the same kind of thing as other backlog producers | False equivalence | High |
| This is the right time to build the producer interface | Premature optimization | High |
| ISC generation from dimension output is a trivial addition | Hidden complexity | Medium |
| Budget controls belong in this sprint | Scope bundling | Medium |
| The dispatcher verifying ISC is sufficient quality assurance | Goodhart risk / structural gap | High |

**Recommended decomposition:**
1. Fix overnight runner so it produces real output (blocker — prerequisite to everything else)
2. Build dispatcher budget controls as a standalone backlog item (independent, high value)
3. After the overnight runner has at least 3 successful production runs with non-zero kept counts, revisit the producer interface with real output as calibration data
4. If the producer is built, require overnight-sourced tasks to have `autonomous_safe: false` until a human-review gate is designed and implemented
