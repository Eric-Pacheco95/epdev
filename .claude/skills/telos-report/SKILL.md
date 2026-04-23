# IDENTITY and PURPOSE

TELOS reporting engine. Generate "What has Jarvis learned about you?" from recent TELOS file changes, learning signals, and synthesis docs.

# DISCOVERY

## One-liner
Generate a "What has Jarvis learned about you?" report from TELOS changes and signals

## Stage
VERIFY

## Syntax
/telos-report
/telos-report <period>

## Parameters
- period (optional, default: "7 days"): Reporting period -- e.g., "7 days", "30 days", "2026-03-01 to 2026-03-31"

## Examples
- /telos-report -- last 7 days (default)
- /telos-report 30 days -- last 30 days
- /telos-report "2026-03-01 to 2026-03-15" -- custom date range

## Chains
- Before: /telos-update (generates the changes this skill reports on), /learning-capture (generates signals)
- After: /notion-sync push report (auto-pushes report to Notion Jarvis Reports page)
- Related: /vitals (system health), /synthesize-signals (signal distillation)

## Output Contract
- Input: Optional period string
- Output: Markdown report with sections: REPORT PERIOD, TELOS CHANGES, TOP LEARNINGS, SYSTEM HEALTH, RECOMMENDATIONS
- Side effects: Report auto-pushed to Notion Jarvis Reports page (32fbf5ae-a9e3-81ec-9a62-cb0e35bae73a)

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- If input contains an unrecognized flag (starts with `--`): print "Usage: /telos-report [period]  Examples: /telos-report 30 days | /telos-report "2026-03-01 to 2026-03-31"" and STOP
- If no period argument provided: use default period "7 days"
- Proceed with determined period

- Determine the reporting period (default: last 7 days, or as specified)
- Check git history for changes to `memory/work/telos/` files in the period using `git log`
- Read current state of `memory/work/telos/LEARNED.md` for accumulated observations
- Read recent signals from `memory/learning/signals/` written in the period
- Read any synthesis documents from `memory/learning/synthesis/` written in the period
- For each TELOS file that changed, summarize what was added, modified, or removed
- Identify the top 3-5 most significant learnings or changes
- Assess TELOS system health:
  - Which files are being actively updated? (healthy)
  - Which files are still empty templates? (opportunity)
  - Is the learning capture running? (signal count trend)
  - Are synthesis runs happening when signals accumulate? (compound learning health)
- Generate recommendations: what should Eric focus on populating next?

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Sections: REPORT PERIOD, TELOS CHANGES, TOP LEARNINGS, SYSTEM HEALTH, RECOMMENDATIONS
- REPORT PERIOD: date range
- TELOS CHANGES: bullets per changed file with summary
- TOP LEARNINGS: numbered 3-5 most significant learnings about Eric
- SYSTEM HEALTH: table — file | status (active/template/stale) | last updated
- RECOMMENDATIONS: bullets of what Eric should focus on next
- Conversational tone — personal report, not corporate doc
- If no changes: say so and suggest /telos-update or populating empty files


# NOTION AUTO-WRITE

After generating the report, automatically push it to the Notion Jarvis Reports page:

1. Use `mcp__claude_ai_Notion__notion-fetch` to get the current content of page `32fbf5ae-a9e3-81ec-9a62-cb0e35bae73a`
2. Find the line `*(Jarvis writes dated reports below — newest at top)*` followed by `---`
3. Use `mcp__claude_ai_Notion__notion-update-page` with command `update_content` to insert the new report between that line and the `---` separator
   - old_str: the `---` immediately after the "newest at top" line
   - new_str: the full report in Markdown (with `### YYYY-MM-DD` heading) followed by `---`
4. Confirm to Eric: "Report pushed to Notion Jarvis Reports."

If the Notion write fails, log the error but do not fail the skill — the local output is the primary deliverable.

# VERIFY

- All required sections present (IDENTITY STATE through RECOMMENDATIONS) | Verify: Check section headers
- GOAL PROGRESS has measurable indicator for each active goal | Verify: Check for numeric/ratio data
- SYSTEM HEALTH includes all TELOS files | Verify: Count rows vs `memory/work/telos/`
- Notion write attempted -> confirmation or error in output | Verify: Check output
- Report date is today's date | Verify: Check report heading
- TELOS files freshly Read before report generation | Verify: Review session tool calls

# LEARN

- Flat/declining goal progress -> candidate for re-evaluation
- File consistently stale in SYSTEM HEALTH -> add to /backlog
- Repeated Notion write failures -> signal + /self-heal investigation

# INPUT

Generate a TELOS report for the specified period. Default: last 7 days.

INPUT:
