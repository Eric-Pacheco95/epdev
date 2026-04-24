# IDENTITY and PURPOSE

Morning system review engine. Outputs: (1) ASCII terminal dashboard (<40 lines), (2) launch jarvis-app in browser, (3) Slack deep-dive to #epdev, (4) interactive 5-step morning guide. Triggered manually at session start.

# DISCOVERY

## One-liner
Morning dashboard + Slack deep dive + interactive 5-step brief guide (30-60 min target)

## Stage
OBSERVE

## Syntax
/vitals [--memory | --context-files]

## Parameters
- (no args): collect all metrics, display terminal report, post to Slack
- --memory: show memory pressure deep dive (peak consumers, pagefile, context-file heatmap)
- --context-files: show context-file size heatmap (largest files loaded into session context)

## Examples
- /vitals

## Chains
- Before: (standalone -- run anytime, best at session start)
- After: /synthesize-signals (if signals accumulated), /self-heal (if collectors failing)

## Output Contract
- Input: none (auto-collects)
- Output: ASCII dashboard to stdout + comprehensive Slack report to #epdev + interactive 5-step morning guide
- Side effects: writes data/vitals_latest.json, posts to Slack

## autonomous_safe
true

# DEBUGGING RECIPES

**Near-zero health metric scores (0.00 to 0.05):** Before diagnosing data quality or scoring logic, first verify the scan scope — check the `rglob` path and target directory in `vitals_collector.py`. Parent-directory scans silently include irrelevant files and dilute precision; a 0.00 score is more often a scope bug than a data bug.

# STEPS

## Step 0: INPUT VALIDATION

- If `--memory` flag: run Phase 1 collector, display MEMORY section expanded with top-10 consumers and pagefile trend, skip Phases 2-4, STOP
- If `--context-files` flag: run Phase 1 collector, display context-file heatmap (top 20 files by token estimate from `data/vitals_latest.json`), skip Phases 2-4, STOP
- If any other unrecognized argument: print "Usage: /vitals [--memory | --context-files]" and STOP
- Proceed to Phase 1

## Phase 1: Collect Data

1. Run `python tools/scripts/vitals_collector.py --file --pretty` to collect all vitals data
2. Validate the output:
   - Check `_schema_version` starts with `"1."` -- the 1.x line is additive-compatible (1.0.0 baseline + 1.1.0 added `memory` + `moralis_vitals`, 1.2.0 added `scheduled_tasks_detail` and richer `overnight_streak`). If the major version is not 1, STOP and report: "Schema version mismatch -- expected 1.x, got {version}."
   - Check `errors` array -- if non-empty, report each error inline with a [DEGRADED] marker

## Phase 1.5: Launch Jarvis App

3. Check if jarvis-app is already running: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000`
4. If not running (non-200): start it in the background: `cd C:/Users/ericp/Github/jarvis-app && npm run dev &`
5. Open the browser: `start http://localhost:3000`
6. Continue immediately -- do not wait for the app to load

## Phase 2: Terminal Dashboard

6.5. Scan for unimplemented PRDs: run `grep -rl "\- \[ \]" memory/work/` and filter to paths matching `*/PRD.md`. These are PRDs with unchecked ISC items -- not yet fully /implement-prd'd. Store the list as `pending_prds` (file paths only, strip `memory/work/` prefix for display). PRDs where all ISC items are `[x]` are excluded.

7. Interpret the collected data and format the compact terminal dashboard (see TERMINAL FORMAT)
8. For threshold crossings: explain what each crossing means
9. Generate "Top 3 Today" -- the 3 highest-value actions for today grounded in evidence from the collector data:
   - Overnight findings that need review/merge
   - TELOS contradictions that need action
   - Open validations from tasklist
   - Stale/unhealthy scheduled tasks
10. Display the terminal dashboard immediately

## Phase 3: Slack Deep Dive

7. After displaying terminal output, compose the full Slack report (see SLACK FORMAT) with ALL available sections: system health, overnight branch breakdown, TELOS introspection, external monitoring, cross-project findings, threshold crossings, autonomous value rate, unmerged branches, Top 3 actions.
8. Post to #epdev Slack using:
   ```python
   import sys; sys.path.insert(0, str(__import__('pathlib').Path('.').resolve()))
   from tools.scripts.slack_notify import notify
   notify(text, severity="routine")
   ```
10. If Slack post fails, save report to `data/logs/vitals_YYYY-MM-DD.md` as fallback and tell Eric
11. Tell Eric: "Deep dive posted to #epdev Slack."

## Phase 4: Morning Guide (interactive 5-step walkthrough)

After the Slack post, display the morning guide header and walk Eric through each step. Present one step at a time -- tell Eric what to do, give him the exact command or decision, and wait. This is learn-by-doing, not a checklist to read.

Display the guide header:
```
Morning Brief -- Step-by-Step Guide
------------------------------------------------------------
Target: 30-60 min | Extend only for critical findings
```

Then present each step in sequence:

**Step 1 -- OBSERVE (done)**
Tell Eric: "Step 1 complete -- /vitals ran, dashboard displayed, Slack posted. System status: {HEALTHY|WARN|CRITICAL}."
If WARN or CRITICAL: "Flag: {threshold crossings summary}. Keep these in mind as we go."

**Step 2 -- THINK: Merge overnight**
Tell Eric what branch(es) are unmerged and give the exact command: branch name, `git merge <branch>`, then `python -m pytest tests/ -q --tb=no`. Ask for "merged" or "skip". If no unmerged branches: "Step 2 -- No overnight branches. Skip."

**Step 3 -- PLAN: Backlog triage + wisdom proposals**

**3a. Wisdom promotion proposals**
Run `python tools/scripts/promotion_check.py --pending --json` to check for pending promotion proposals.
If proposals exist, list them (route, theme_name, maturity, confidence%) and ask Eric to "approve", "reject", or "defer" each. When approved, run `python tools/scripts/promotion_check.py --approve "{proposal_id}"`.
- wisdom route: auto-writes to memory/learning/wisdom/
- telos route: stages for /telos-update (remind Eric to run it)
- steering route: stages for /update-steering-rules (remind Eric to run it)

If no proposals: "Step 3a -- No wisdom promotions pending."

**3b. Backlog triage**
Pull the pending_review and failed items from the collector data (backlog_pending_review_count, backlog_failed_count).
Tell Eric: "Step 3b -- Backlog triage ({n} items). Say 'ready' to start or 'skip' to defer." When ready, surface each item 1-line with approve/reject/defer options. For failed items: "Task {id} failed -- requeue or close?"

**Step 4 -- BUILD: TELOS scan**
Surface the top contradiction(s) from today's autoresearch run (contradictions_structured, highest severity first):
```
Step 4 -- TELOS scan ({n} contradictions, {n} proposals)
  Top finding: [{severity}] {claim vs evidence summary}
  Proposal: {highest-priority proposal, 1 line}
Action options:
  a) Add to tasklist now
  b) Dismiss (not relevant)
  c) Defer (review later)
Say your choice, or "skip" to move on.
```

**Step 5 -- EXECUTE: Set session intent**
Ask Eric what he wants to build or focus on today. Suggest the Top 3 from the dashboard as options. If `pending_prds` is non-empty, surface them as explicit options:
```
Step 5 -- Set session intent
  Suggested (from Top 3):
    1. {top action}
    2. {second action}
    3. {third action}
  Pending PRDs ready to build:
    - {slug}: /implement-prd memory/work/{slug}/PRD.md
What's your focus for today? (Name 1-2 things, or say "top 1" to take the top suggestion.)
```
When Eric names a focus, confirm it and optionally offer to run /telos-update to log it.

At the end of Step 5, display:
```
Brief complete. Session focus: {Eric's stated intent}
------------------------------------------------------------
```

## FALLBACK (if collector script fails)

If the collector script returns an error, empty output, or non-zero exit code:
1. Report the failure explicitly: "vitals_collector.py failed: {error details}"
2. Offer: "Run full LLM-based vitals collection instead?"
3. If Eric confirms, fall back to reading each data source individually
4. After fallback, recommend investigating the failing collector step

# TERMINAL FORMAT

Keep under 40 lines. ASCII-only (no Unicode, no em dashes, no box-drawing).

```
Jarvis Vitals -- YYYY-MM-DD
============================================================
SYSTEM: {HEALTHY | WARN | CRITICAL}
Collected in {ms}ms | Schema v{version}

ISC: {met}/{total} ({ratio}%)  Trend: {up|stable|down}
Signals: {n} ({velocity}/day)  Last synthesis: {n}d ago
Sessions/day: {n}  Storage: {repo_mb} MB

Overnight ({date}): {n} dimensions, {total_kept} kept, {total_min}m
  {dim1}: {kept} kept | {dim2}: {kept} kept | ...
  Quality: {PASS|FAIL}  Security: {PASS|FAIL}
  Highlight: {one-line top finding}
Overnight logs (7d): for each overnight_streak entry with status failed, one sub-line: {date} exit {exit_code} -- {failure_hint truncated 100c}
Autoresearch: {contradictions}c / {coverage}% cov / {proposals}p
Scheduled tasks (summary): {heartbeat.scheduled_tasks_unhealthy.detail}
Windows tasks (detail): from scheduled_tasks_detail -- list each task where healthy=false OR missed_runs>0: {task_name} state={state} last={last_run_time} next={next_run_time} result={last_task_result} ({last_result_label}) missed={missed_runs} flags={schedule_flags}; if none, say "All tasks nominal"

MEMORY ({memory.status}): peak {memory.peak_commit_gb} GB ({memory.peak_ratio_pct}% of pagefile)
  Top-1 at peak: {memory.top1_consumer_at_peak} | Ticks: {memory.tick_count}/{memory.expected_ticks} ({completion_pct}%)
  Drill down: /vitals --memory | Heatmap: /vitals --context-files

MORALIS: {moralis_vitals.stream_status} | addr {moralis_vitals.addresses} | CU {moralis_vitals.cu_mtd}/{moralis_vitals.monthly_cap_cu} ({moralis_vitals.pct_used}%)
  {Poll {moralis_vitals.last_poll_age_min}m ago} | Today {moralis_vitals.cu_today} CU | {ALERT >=70% if alert_70pct else OK}

Pending PRDs ({n}): {slug1/PRD.md, slug2/PRD.md} or "None"

Threshold Crossings:
  {[SEV] metric: value} or "None"

Top 3 Today:
  1. {action} -- {evidence}
  2. {action} -- {evidence}
  3. {action} -- {evidence}

Deep dive posted to #epdev Slack.
============================================================
```

# SLACK FORMAT

Use Slack mrkdwn. Be comprehensive -- this is the full morning report.

```
*Jarvis Morning Report -- YYYY-MM-DD*

*System Health:* {HEALTHY | WARN | CRITICAL}
ISC: {met}/{total} ({ratio}%) | Signals: {n} ({velocity}/d) | Sessions: {n}/d | Storage: {mb} MB

---

*Overnight Self-Improvement ({date})*
Branch: `{branch}` ({n} commits, {summary_line})

| Dimension | Time | Kept | Detail |
|-----------|------|------|--------|
| {dim} | {min}m | {n} | {one-line detail} |
...

Quality gate: {PASS|FAIL}  Security: {PASS|FAIL}

Recent commits:
{bullet list of top 10 commits from branch_stats.recent_commits}

---

*Overnight log streak (7d)*
For each overnight_streak entry: `{date}: {status}` plus if failed then `exit {exit_code}` and first line of `failure_hint`. Link log_file paths as monospace.

---

*Scheduled Tasks (Windows)*
From `scheduled_tasks_detail`: task_folder, healthy_count/total_count. Markdown table: Task | State | Outcome | Last run UTC | Next run UTC | Result code | Label | Missed runs | schedule_flags. If query_error, quote it. If platform non-windows, say collector skipped Task Scheduler.

---

*TELOS Introspection (run-{date})*
Contradictions: {n} | Coverage: {n}% | Proposals: {n}

*Contradictions:*
{full text from autoresearch_contradictions, reformatted for Slack}

*Proposals for review:*
{full text from autoresearch_proposals, reformatted for Slack}

---

*Moralis Streams (crypto-bot)*
- Stream status: `{moralis_vitals.stream_status}` ({moralis_vitals.status_message})
- Addresses: {moralis_vitals.addresses} | Chains: {moralis_vitals.chain_ids}
- CU month-to-date: {moralis_vitals.cu_mtd} / {moralis_vitals.monthly_cap_cu} ({moralis_vitals.pct_used}%)
- CU today: {moralis_vitals.cu_today} | Events MTD: {moralis_vitals.events_mtd}
- Last status poll: {moralis_vitals.last_poll_age_min}m ago
- If `alert_70pct=true`: prepend `:warning: *Moralis CU >=70% of monthly cap*` line
- If `stream_status != active`: prepend `:rotating_light: *Moralis stream {status}*` line

---

*External Monitoring*
{full text from external_monitoring if available, or "No report from latest overnight run"}

*Cross-Project Findings*
{full text from cross_project if available, or "No report from latest overnight run"}

---

*Pending PRDs (unimplemented)*
{bulleted list of slug/PRD.md paths with one-line PRD title, or "None"}
Next step for each: `/implement-prd memory/work/{slug}/PRD.md`

*Threshold Crossings*
{[SEV] metric: value (detail)} or "All clear"

*Autonomous Value (30d)*
Proposals acted on: {n}/{total} ({rate}%)

*Unmerged Overnight Branches*
{list with dates, or "None"}

---

*Top 3 Actions for Today*
1. *{action}* -- {evidence and reasoning}
2. *{action}* -- {evidence and reasoning}
3. *{action}* -- {evidence and reasoning}
```

# OUTPUT INSTRUCTIONS

- Terminal: ASCII-only, under 40 lines, display FIRST before Slack
- Slack: full mrkdwn, comprehensive, posted AFTER terminal display
- Use `=` and `-` for horizontal rules in terminal
- If no overnight data: show "No overnight run" in both outputs
- If Slack fails: save to `data/logs/vitals_YYYY-MM-DD.md` and tell Eric
- "Top 3 Today" must be grounded in evidence from collector data
- All data comes from the collector JSON in Phase 1 -- do NOT make additional file reads for data the collector already provides
- After terminal dashboard, do NOT append skill suggestions -- the morning guide (Phase 4) follows immediately and provides interactive next steps
- After Phase 4 Step 5 (session intent set), append: "Want a visual? `/visualize` can diagram ISC gaps, signal flow, or skill usage."

# CONTRACT

## Errors
- **collector-failure:** vitals_collector.py fails or returns invalid JSON -> offer LLM fallback
- **schema-mismatch:** `_schema_version` major != 1 -> STOP and report
- **slack-failure:** post fails -> save to data/logs/ and notify user

# SKILL CHAIN

- **Replaces:** morning_feed.py (9am scheduled task -- now on-demand via /vitals)
- **Composes:** vitals_collector.py (subprocess), slack_notify.py (import)
- **Escalate to:** /delegation if health is CRITICAL

# INPUT

Run vitals check now.

# VERIFY

- Terminal output ASCII-only, under 40 lines | Verify: check for non-ASCII chars and line count
- Terminal displayed before Slack post | Verify: terminal block precedes Slack confirmation in output
- Collector JSON sole data source (no extra file reads) | Verify: metric values traceable to collector JSON
- Slack attempted; fallback to `data/logs/vitals_YYYY-MM-DD.md` if failed | Verify: Slack confirmation or fallback path in output
- Schema major != 1 → execution stopped with mismatch surfaced | Verify: session output for mismatch error
- Raw JSON excluded from terminal/Slack | Verify: output has formatted metrics, not JSON blobs

# LEARN

- Signal: memory/learning/signals/{YYYY-MM-DD}_vitals-alert.md when CRITICAL/DEGRADED >= 2 consecutive days or new collector failure category
- Rating: 8+ unknown failures; 6-7 recurring degradation; skip routine/isolated blips
- "Top 3 Today" unchanged across 3+ vitals runs → flag as ADHD momentum blocker
