# Adversarial Fallacy Detection: "Cheap Failures" Proposals

**Generated**: 2026-04-03
**Analyst**: Adversarial review agent (Claude Sonnet 4.6)
**Evidence base**: jarvis_dispatcher.py (1700+ lines, read in full), 4 dispatcher run reports, consolidate_overnight.py (570 lines), overnight_state.json, overnight_summary/2026-03-31.json, memory/learning/signals/ (10 files)

---

## Grounding: What the Code Actually Does

Before evaluating proposals against "cheap failures," establish what is actually true:

**The dispatcher never writes to `memory/learning/` at any path.**
`grep -rn "learning/signals\|learning/failures"` on jarvis_dispatcher.py returns zero results. The learning pipeline receives no signal from dispatcher runs -- successful or failed. `save_run_report()` writes only to `data/dispatcher_runs/`. `handle_task_failure()` routes tasks to statuses (pending, failed, manual_review) and writes to the backlog JSONL. Nothing else.

**Signals in `memory/learning/signals/` come from workers themselves**, not from dispatcher infrastructure. The 10 current signals (e.g., `2026-04-03_telos-introspection-findings.md`) were written by autonomous task agents as part of their task outputs. The signal producer is the task agent, not the orchestrating dispatcher.

**The 3 failures in the run history:**
- `auto-40018` (2026-04-02): Rate limited -- `claude -p` hit usage limit, returned exit 1 with no TASK_RESULT line. Failure reason: "No TASK_RESULT line in output."
- `auto-40018` (2026-04-03): ISC failure -- isc_passed=0/1 but exit_code=0. Worker created TASK_FAILED.md. Status: "failed."
- `5b-001` (2026-03-31): Status "done" but both ISC verifications internally failed due to WSL bash not found -- the worker self-reported PASS but the dispatcher ISC runner got WSL errors. This is a verification environment bug, not a task failure.

**The overnight branch has 47 commits ahead of main, 0 reviewed.** `overnight_state.json` confirms `total_reviewed_by_human: 0, total_merged_to_main: 0`. The consolidation script exists and ran on 2026-03-31 but merged 0 branches (no unmerged overnight work that day -- the only branch was a dispatcher task, not an overnight run).

---

## Bantilan's "Cheap Failures" -- What It Actually Means

Bantilan's framework (Union.ai/Flyte context) refers to infrastructure-level failure recovery:
- Spot instance preemption: task was interrupted by the cloud provider, not by bad logic
- OOM kill: resource exhaustion, not correctness failure
- Network timeout: transient connectivity, not code error
- The key property: **the failure reason is external, known, and the task is genuinely retryable without modification**

The mechanism is checkpointing: save intermediate state so a retry can resume from the last checkpoint rather than restarting from zero. Cost of failure = time since last checkpoint, not total task time.

---

## P1: Failure-to-Signal Producer

**Claim**: Auto-write learning signals from dispatcher failures.

### Fallacy 1: False Analogy with Bantilan (confirmed)

Bantilan's cheap failures are about infrastructure preemption making retries cheap. P1 is about extracting training signal from failures. These are different concerns. Bantilan never proposes turning failures into training data -- he proposes making failures not matter because retries resume from checkpoints. Invoking Bantilan to justify P1 is concept laundering: the "cheap failures" framing provides rhetorical credibility to a proposal that has nothing to do with the original meaning.

**However**, the training-data argument is independently valid and doesn't need the Bantilan framing to stand. This is not a fatal objection to P1 -- it's an objection to the framing.

### Fallacy 2: Adding Pipes to a Broken System

The learning pipeline has zero failures logged despite 3 dispatcher failures. The question to ask before P1: why is `memory/learning/failures/` empty?

The answer from the code: **the dispatcher was never wired to write there**. This is not a volume problem -- it is an architecture omission. The existing signal producers (workers writing signals as task outputs) work correctly; that's how the 10 current signals arrived. The gap is not "signals are being lost" -- it is "dispatcher-level events were never treated as signal-worthy."

P1 is therefore a legitimate fill-the-gap proposal, not an "add pipes to a broken system" antipattern. The system that IS working (worker-written signals) is not broken. The gap (dispatcher infrastructure failures as signals) was always empty by design omission, not by malfunction.

**What does NOT survive scrutiny**: The scale argument. With 10 total runs and 3 failures (30% failure rate), P1 would generate approximately:
- Current rate: ~3 failures / 10 runs
- Runs per month at current cadence: dispatcher runs appear ~daily (auto-40018 ran on 04-02 and 04-03), overnight runner appears scheduled
- Projected: 5-10 dispatcher failure signals/month at current volume

That is trivially low volume. Building a dedicated failure signal producer for 5-10 signals/month is overhead-to-value negative. The better path: when a dispatcher failure occurs, write a one-line signal manually, or add 8 lines to `handle_task_failure()`. This does not require its own infrastructure.

**What genuinely survives**: The failure_type taxonomy already in `handle_task_failure()` (scope_creep, partial_work, worker_request, isc_fail, no_output) is well-structured and would map cleanly to learning signal categories. The data exists; it just isn't being written anywhere useful beyond the run reports.

**Verdict**: The core idea is sound. The "Failure-to-Signal Producer" framing overstates the scope. The actual implementation is ~10 lines in `handle_task_failure()` that append to `memory/learning/failures/` when status becomes "failed" or "manual_review". Not a new producer -- a minor extension to existing routing logic.

---

## P2: Overnight Branch Auto-Consolidation

**Claim**: Consolidate overnight output into a review branch to make it reviewable in 2 minutes.

### Fallacy 3: Misidentifying the Bottleneck

The consolidation script already exists (`consolidate_overnight.py`, 570 lines). It already creates `jarvis/review-YYYY-MM-DD` branches. It already generates human-readable morning reports (`data/overnight_summary/`). **P2 is partially already built.**

The real question: why are 47 commits unreviewed despite the consolidation machinery existing?

The run data tells the story: `overnight_summary/2026-03-31.json` shows `branches_merged: 0`. The overnight runner generated 47 commits on `jarvis/overnight-2026-04-03`, but the consolidation script either wasn't scheduled to run after it, or the branch wasn't detected correctly.

Two possible root causes:
1. **Scheduling gap**: consolidation isn't running after overnight_runner completes
2. **Review habit gap**: Eric doesn't have a daily review ritual even when the summary exists

### Fallacy 4: Assuming the Review Problem Is a Format Problem

P2 assumes that if the output were more consolidated, review would happen. But `total_reviewed_by_human: 0` at 47 commits suggests the bottleneck is not format -- it is habit and workflow. A 2-minute review summary still requires Eric to open it. If the overnight output is arriving but not being looked at, making it more compact changes nothing about the review rate.

**Evidence against the format hypothesis**: The `data/overnight_summary/2026-03-31.md` file was generated. Eric has never opened it (inferred from 0 reviews). The consolidation script works. The format problem is already solved.

**What genuinely survives**: There is a real gap -- the consolidation script is not being triggered consistently. The overnight runner produces commits, but there is no confirmed post-runner step that runs consolidate_overnight.py and surfaces the summary. Fixing the scheduling (adding consolidate_overnight.py to the post-overnight Task Scheduler chain) is legitimate and low-risk. But it solves the "consolidation not running" problem, not the "Eric doesn't review" problem.

**What does NOT survive**: Any framing of P2 as making overnight output "reviewable." It is already reviewable. The problem is delivery + habit, not format.

---

## P3: Retry-from-Branch

**Claim**: Start retries from the prior branch instead of clean main.

### Fallacy 5: False Analogy with Bantilan (strongest case)

This is the proposal most directly analogous to Bantilan's checkpointing. His cheap failures specifically enable resuming from intermediate state. P3 is applying this reasoning to agent task retries. The analogy is at least structural.

**But it breaks down on the key property of Bantilan's model**: Bantilan's intermediate state is deterministic and unambiguous. A spot-preempted ML training run has a checkpoint that exactly captures model weights, optimizer state, and current epoch. There is no ambiguity about "what was done vs what still needs doing."

A partially-executed agent task branch does NOT have this property. Consider the auto-40018 failure: the worker ran, failed ISC 0/1, and wrote TASK_FAILED.md. The branch contains some commits. But the TASK_FAILED.md says the worker explicitly stopped and flagged for manual review. Retrying from that branch means the next worker agent reads partial work of unknown quality from an agent that itself declared failure. The retry agent must then determine:

- Which files were correctly written vs incorrectly written
- Whether the partial commits should be kept, reverted, or amended
- What the failure analysis in TASK_FAILED.md means for its approach

This is not "cheap" -- it is cognitively expensive. The retry agent now has to reason about another agent's failure state, which is harder than starting clean. Bantilan's preempted spot instance doesn't leave behind bad data; it leaves behind good data that was simply interrupted.

### Fallacy 6: Confusion Between Failure Types

The retry-from-branch logic matters differently per failure_type:

- **rate_limited**: Clean retry from main is correct. The branch has no work. Nothing to resume from.
- **isc_fail with commits**: Resuming from branch might help if partial work is correct. But see above -- the retry agent can't verify which parts are correct without re-doing most of the work.
- **no_output**: Nothing on the branch. Resuming from branch is identical to starting from main.
- **scope_creep**: Branch explicitly went in the wrong direction. Resuming from it is actively harmful.
- **worker_request (TASK_FAILED.md)**: Worker declared itself stuck. The branch state is known-bad.

P3 only helps in the specific case of isc_fail with a substantial amount of correct partial work. Looking at the actual failures: all three involved either rate limits, WSL environment bugs, or ISC check failures on tasks where the core work was complete. None of them had "significant correct partial work that a retry should build on."

### Fallacy 7: Scale Mismatch

With 3 failures in 10 runs, and at most 1 of those failures (partial_work type) potentially benefiting from retry-from-branch, P3 is solving a problem that has occurred approximately 0.4 times in the system's entire history. Building the infrastructure to detect, preserve, and inject prior branch state for retries is disproportionate to a problem that hasn't clearly manifested as a real bottleneck.

**What genuinely survives**: The failure context injection already in the dispatcher (`generate_worker_prompt()` lines 697-741) is the correct, lighter-weight version of P3's insight. The retry worker already receives `failure_type`, `failure_reason`, and `_prior_task_failed_md`. This gives the retry agent the knowledge of what went wrong without forcing it to inherit potentially broken branch state. This is already implemented and is the right tradeoff.

**If P3 were to be built**, it should be scoped to `partial_work` failures only (where commit_count > 0 and retries_exhausted is true but a re-run is being forced manually). That is a rare edge case, not a core retry mechanism.

---

## Cross-Cutting Finding: The Real Bottleneck

All three proposals address symptoms. The actual bottleneck revealed by the data:

**47 overnight commits exist. None have ever been reviewed. The compound learning score is 0.65. `memory/learning/failures/` is empty.**

These are not three separate problems -- they are one problem: **the feedback loop from autonomous output back to human learning is broken**. The dispatcher produces run reports that go into `data/dispatcher_runs/` and nowhere else. The overnight runner produces branches that go unreviewed. The learning pipeline receives signals only when worker agents happen to include signal-writing in their task definitions.

The proposals treat this as an infrastructure problem (more producers, better consolidation, smarter retries). The evidence suggests it is a **workflow loop problem**: autonomous output is not reliably arriving in a human-readable, time-bounded, dailyritual-compatible format.

The highest-leverage fix is not any of P1-P3. It is ensuring the morning summary actually reaches Eric (Slack message with the overnight_summary.md link, sent at 9am), and that the dispatcher's failure/success run reports are included in that summary. This is a 20-line addition to an existing script, not a new capability.

---

## Verdicts

| Proposal | Bantilan Analogy | Scale Fit | Root Cause Correct | Sound Core | Recommendation |
|----------|-----------------|-----------|-------------------|------------|----------------|
| P1: Failure-to-Signal | Weak (different concern) | Poor (5-10 signals/month) | Yes -- gap is real | Yes | Reduce to ~10 lines in handle_task_failure(), not a new producer |
| P2: Auto-Consolidation | N/A | N/A | No -- script exists, scheduling may be broken | Partial | Fix the scheduling gap; acknowledge habit problem separately |
| P3: Retry-from-Branch | Structural analogy only, breaks on agent ambiguity | Very poor (0-1 actual use cases) | No -- existing failure context injection already addresses this | Narrow | Scope to manual-forced reruns of partial_work only, if at all |

**Highest-ROI action not in any proposal**: Pipe dispatcher run reports and TASK_FAILED.md contents into the morning Slack summary. Failures become visible within 24 hours without any new infrastructure.
