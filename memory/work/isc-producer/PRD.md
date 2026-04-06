# PRD: ISC Producer -- Automated Verification & Velocity Tracker

> Status: DRAFT | Created: 2026-04-06 | Owner: Eric P
> Architecture review: COMPLETE (2026-04-06) -- standalone daily script, propose-only, wraps isc_executor.py

---

## OVERVIEW

The ISC Producer is a standalone daily script that scans all active PRDs, runs deterministic verification via the existing `isc_executor.py` engine, and produces a batch report surfacing items ready to mark complete and near-miss items that need work. It closes the gap between "ISC exists" and "ISC is verified" without consuming LLM tokens, creating a self-tightening quality loop where ISC completion trends toward 100% through daily automated evidence collection. The producer is SENSE-only -- it never writes to PRD files. Eric reviews results during the morning brief and decides what to mark complete.

---

## PROBLEM AND GOALS

- **ISC stagnation at 57%**: 92 unchecked criteria across 7 PRDs with no automated mechanism to detect when items become passing. Items stay unchecked long after the underlying work is done because verification is manual and infrequent.
- **No velocity signal**: There is no trend data showing whether ISC completion is improving, stagnant, or regressing. Eric cannot tell if build sessions are closing the gap or adding new unchecked items faster than old ones resolve.
- **Near-miss items invisible**: Some ISC items are close to passing (e.g., file exists but missing a field, partial implementation) but there is no mechanism to surface these as high-value quick wins.
- **Goal 1**: Daily automated evidence collection for all deterministic ISC criteria across all active PRDs.
- **Goal 2**: Surface ready-to-mark items in the morning brief so Eric can batch-approve completions.
- **Goal 3**: Create backlog tasks for near-miss items to close gaps incrementally.
- **Goal 4**: Provide ISC velocity trending so build sessions can be prioritized by impact on overall completion rate.

---

## NON-GOALS

- Auto-marking `[x]` in PRD files (trust contract -- only Eric or explicit `/validation` marks complete)
- LLM-powered verification (producer is deterministic only; MANUAL items are surfaced, not evaluated)
- Replacing `/validation` skill (that is interactive, single-PRD; producer is batch, all-PRD, scheduled)
- Modifying `isc_executor.py` behavior (producer wraps it as-is)
- Scanning non-PRD files for ISC-like patterns
- Historical report archival (single report overwritten each run; velocity derived from heartbeat trend)

---

## USERS AND PERSONAS

- **Eric (operator)**: Reviews ISC producer report during morning brief Step 3. Sees "N items ready to mark complete" folded into pending_review count. Approves or defers each item.
- **Jarvis (autonomous)**: Runs `isc_producer.py` daily via Task Scheduler. No LLM session needed. Writes report and backlog tasks.
- **vitals_collector.py (machine consumer)**: Reads `data/isc_producer_report.json` to compute ISC velocity and fold pass counts into pending_review metric.

---

## USER JOURNEYS OR SCENARIOS

1. **Daily scan (autonomous)**: Task Scheduler fires at 2am -> `isc_producer.py` globs active PRDs -> runs `isc_executor.py --json --skip-format-gate` per PRD -> aggregates results -> writes `data/isc_producer_report.json` -> creates up to 10 backlog tasks for near-miss items -> exits with ASCII summary to Task Scheduler log.

2. **Morning review (Eric)**: Eric runs `/vitals` -> Step 3 shows "ISC: 5 items ready to mark, 3 near-miss tasks queued" in pending_review -> Eric says "show ISC" -> Jarvis reads report and presents ready-to-mark items -> Eric approves -> Jarvis runs `/validation` on specific PRDs to mark them.

3. **Manual run (Eric)**: Eric runs `python tools/scripts/isc_producer.py` after a build session to check if new work moved any ISC items to passing before waiting for the next scheduled run.

4. **Velocity tracking**: Over 2 weeks, heartbeat history shows ISC ratio climbing from 57% to 72% -> `/vitals` terminal dashboard shows `ISC: 155/215 (72%) Trend: up` -> Eric can see build sessions are closing the gap.

---

## FUNCTIONAL REQUIREMENTS

- FR-01: Producer scans all PRDs matching `memory/work/*/PRD.md`, excluding `memory/work/_archived/` directory
- FR-02: For each PRD, producer invokes `isc_executor.py --prd <path> --json --skip-format-gate` as a subprocess
- FR-03: Producer aggregates results into a single report at `data/isc_producer_report.json` (overwritten each run)
- FR-04: Report JSON schema contains: `run_date`, `run_duration_s`, `summary` (total/pass/fail/manual), `by_prd` (array of per-PRD results), `ready_to_mark` (flat list of passing items with PRD path and criterion text)
- FR-05: Producer classifies FAIL items as "near-miss" when evidence suggests a small gap (file exists but missing content, partial grep match, count close to threshold)
- FR-06: Producer creates backlog tasks in `orchestration/task_backlog.jsonl` for near-miss items, capped at 10 tasks per run, with source field `"isc-producer"`
- FR-07: Producer skips creating duplicate backlog tasks (checks existing entries by criterion text hash before appending)
- FR-08: Global execution timeout of 300s for the full scan (individual criteria already have 60s timeout via isc_executor.py)
- FR-09: ASCII-safe stdout summary printed at end of run for Task Scheduler log visibility
- FR-10: Exit codes: 0 = ran successfully (regardless of pass/fail counts), 1 = no PRDs found or all errored, 2 = producer crash/timeout

---

## NON-FUNCTIONAL REQUIREMENTS

- All stdout output uses ASCII-only encoding (Windows cp1252 compatibility)
- No new dependencies beyond Python stdlib (subprocess, json, pathlib, datetime, hashlib)
- Report file is gitignored (`data/` is already in `.gitignore`)
- Producer must not import or modify any PRD file content -- read-only access to PRD files, write-only to report and backlog
- Single-threaded serial execution (isc_executor.py is already serial; no parallelism needed for 7 PRDs)

---

## ACCEPTANCE CRITERIA

- [x] `data/isc_producer_report.json` exists after a run with valid JSON containing `summary`, `by_prd`, and `ready_to_mark` keys | Verify: Exist: data/isc_producer_report.json + Read: data/isc_producer_report.json contains "summary" | model: haiku |
- [x] Report `by_prd` array contains only active PRDs with zero `_archived/` entries | Verify: Grep!: _archived in data/isc_producer_report.json | model: haiku |
- [x] Backlog tasks created per run do not exceed 10 | Verify: Grep: isc-producer in orchestration/task_backlog.jsonl + count | model: haiku |
- [x] `ready_to_mark` items in report correspond to isc_executor PASS verdicts with no false positives | Verify: Run executor on one PRD, cross-check ready_to_mark entries against executor JSON output [M]
- [x] No PRD file is modified by the producer during a run | Verify: Grep!: open.*mode.*w in tools/scripts/isc_producer.py | model: haiku |
- [x] `vitals_collector.py` reads `isc_producer_report.json` and folds pass count into pending_review | Verify: Read: tools/scripts/vitals_collector.py contains "isc_producer_report" | model: haiku |
- [x] Full scan completes within 300s across all active PRDs | Verify: Test: timed run with 7+ PRDs completes under 300s | model: haiku |

Anti-criterion:
- [x] No ISC checkboxes are marked `[x]` by the producer script (SENSE-only, propose-only) | Verify: Grep!: \[x\] write operations in tools/scripts/isc_producer.py [M]

ISC Quality Gate: PASS (6/6)

---

## SUCCESS METRICS

- ISC completion rate increases from 57% to 75% within 2 weeks of deployment (measured by heartbeat trend)
- At least 3 ready-to-mark items surfaced per week that Eric was not aware of
- Near-miss backlog tasks have a 50%+ resolution rate within 7 days of creation
- Zero false positives in ready_to_mark list over first 14 days (trust calibration period)
- Morning brief ISC callout reviewed by Eric in 90%+ of vitals runs

---

## OUT OF SCOPE

- Cross-project ISC scanning (crypto-bot, jarvis-app have their own PRDs but separate repos)
- LLM-assisted verification of MANUAL-type criteria
- Auto-execution of CLI verify commands (deferred per isc_executor.py non-goals)
- UI/dashboard for ISC trends (jarvis-app integration is a separate effort)
- Notification/Slack posting of ISC changes (fold into existing vitals Slack report)

---

## DEPENDENCIES AND INTEGRATIONS

- **isc_executor.py**: Core execution engine -- called via subprocess per PRD. Already handles Grep/Exist/Read/Test/Schema types with 60s timeout and secret scrubbing.
- **isc_validator.py**: Format gate -- chained by executor (skipped via `--skip-format-gate` when producer controls input quality).
- **isc_common.py**: Shared utilities (parsing, sanitization) -- used by executor, not directly by producer.
- **vitals_collector.py**: Add ~15 lines to read `isc_producer_report.json` and fold pass count into pending_review metric and ISC velocity into heartbeat data.
- **orchestration/task_backlog.jsonl**: Append near-miss tasks with `"source": "isc-producer"` field for filtering and dedup.
- **Task Scheduler**: Daily 2am entry: `python C:/Users/ericp/Github/epdev/tools/scripts/isc_producer.py`
- **data/isc_producer_report.json**: Output artifact, gitignored, overwritten each run.

---

## RISKS AND ASSUMPTIONS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| isc_executor.py hangs on a malformed verify command | LOW | MEDIUM | 60s per-criterion timeout already exists; producer adds 300s global timeout |
| Backlog flooding from repeated near-miss items across days | MEDIUM | MEDIUM | Dedup check by criterion text hash before creating; 10-task cap per run |
| Report becomes stale trust signal if Task Scheduler fails | LOW | LOW | /vitals shows `isc_producer_last_run` date; flag if >48h old |
| Near-miss classification too aggressive (creates low-value tasks) | MEDIUM | LOW | Conservative initial heuristic; tune based on 2-week task resolution rate |
| Concurrent run with /validation on same PRD | LOW | LOW | Both are read-only on PRDs; no write conflict possible |

### Assumptions

- isc_executor.py interface is stable (--json, --skip-format-gate, exit codes 0/1/2/3)
- Active PRDs live at `memory/work/*/PRD.md` (not nested deeper)
- 7 PRDs with ~30 criteria each completes well under 300s (current executor runs take ~5s per PRD)
- `data/` directory is gitignored and writable by Task Scheduler context
- Near-miss heuristic can be tuned after initial deployment without schema changes

---

## OPEN QUESTIONS

- Should the producer track which items transitioned from FAIL to PASS between runs (delta reporting), or is the flat ready_to_mark list sufficient for morning review? (Leaning toward flat list for v1; delta adds complexity with no clear user need yet.)
- What is the right near-miss heuristic? Initial proposal: FAIL items where evidence string contains "found" or "exists" (partial match). May need tuning after first week of data.
