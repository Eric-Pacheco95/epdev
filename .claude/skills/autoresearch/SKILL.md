# IDENTITY and PURPOSE

Autonomous improvement agent (Karpathy autoresearch pattern). Bounded, metric-driven iteration loops that improve code, skills, or documentation one focused change at a time. Every decision is git-backed.

# DISCOVERY

## One-liner
Run a Karpathy-style metric-driven improvement loop on any codebase

## Stage
BUILD

## Syntax
/autoresearch <goal> --metric "command" [--guard "command"] [--iterations N] [--scope "glob"] [--program path]

## Parameters
- goal: what to improve (required)
- --metric: shell command outputting a single number (required unless --program)
- --guard: shell command that must exit 0 to keep a change (optional)
- --iterations: max iterations (default: 20)
- --scope: glob limiting modifiable files (default: ".")
- --program: path to steering file (overrides inline goal)

## Examples
- /autoresearch "Add DISCOVERY sections to skills" --metric "grep -rl DISCOVERY .claude/skills/*/SKILL.md | wc -l" --scope ".claude/skills/**" --iterations 15
- /autoresearch --program memory/work/jarvis/autoresearch_program.md

## Chains
- Before: /research
- After: /quality-gate, /learning-capture
- Full: /research > /autoresearch > /quality-gate > /learning-capture

## Output Contract
- Input: goal + metric + optional guard/scope/iterations/program
- Output: run report (GOAL, BASELINE, ITERATIONS, RUN LOG, FINAL METRIC, SUMMARY)
- Side effects: creates git branch, modifies scoped files, writes report to memory/work/jarvis/autoresearch/

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY as usage block, STOP
- No --metric and no --program: explain metric requirement, STOP
- If --program: read file, extract dimension config
- Validate metric runs and produces parseable number
- Validate guard runs (warn if fails on baseline)
- Validate scope glob matches files

## Step 1: SETUP

- Create branch: `jarvis/autoresearch-YYYY-MM-DD-{slug}` (auto-increment if exists)
- Run metric to establish baseline
- Print: "Baseline: {value}. Starting {N} iterations on branch {name}."

## Step 2: ITERATION LOOP

For each iteration (1 to max):

1. **THINK**: Identify one focused change to improve the metric within scope
2. **CHANGE**: Modify files within scope only. Log what and why
3. **COMMIT**: `git add` + `git commit -m "autoresearch: {description}"`
4. **MEASURE**: Run metric. Metric improved? (higher default; lower if name contains "error"/"warning"/"stale"/"token")
   - Improved + guard passes (or no guard): **KEEP**
   - Improved + guard fails: **REVERT** (`git revert HEAD --no-edit`)
   - Unchanged/worsened: **REVERT**
5. **EARLY STOP**: 5 consecutive no-improvement iterations → stop
6. **CRASH RECOVERY**: Syntax error: 1 fix attempt. Runtime error: 3 attempts. Timeout (2min): kill. All failures → revert.

## Step 3: REPORT

Write to `memory/work/jarvis/autoresearch/YYYY-MM-DD_{slug}/report.md`:
- Goal, parameters, baseline, final metric
- Kept/discarded/reverted counts
- TSV run log: `iteration | commit_hash | metric_value | delta | status | description`
- Branch name

Print summary: "Completed: {kept}/{total} kept. Metric: {baseline} -> {final} ({delta%}). Branch: {name}"

# OUTPUT INSTRUCTIONS

- One-line status per iteration: `[{n}/{max}] {status}: {description} (metric: {value}, delta: {delta})`
- Do not modify files outside scope or protected paths (TELOS, constitutional rules, CLAUDE.md, .env, credentials)
- Do not run git push
- Do not modify --program file

# INPUT

INPUT:

# VERIFY

- Report file written to `memory/work/jarvis/autoresearch/YYYY-MM-DD_{slug}/report.md` | Verify: `ls memory/work/jarvis/autoresearch/` and confirm report.md exists
- TSV run log contains one row per iteration with all six fields: iteration, commit_hash, metric_value, delta, status, description | Verify: Read report.md TSV block -- row count matches iteration count, all six columns present
- Metric never regressed from a kept iteration (every KEEP row has metric_value >= previous KEEP row) | Verify: Read TSV log -- confirm monotonic metric_value for KEEP rows
- No files outside DATA[scope] were modified | Verify: `git diff --name-only HEAD~N HEAD` -- all changed paths must match DATA[scope] glob
- Remote was NOT pushed during the run | Verify: Check session output -- no remote push confirmation present
- No protected files (TELOS, constitutional-rules.md, CLAUDE.md) were touched; if any were, alert was raised immediately | Verify: `git diff --name-only HEAD~N HEAD` must not include protected paths

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_autoresearch-{slug}.md when a run produces >= 10% metric improvement
- Include: dimension, baseline, final, kept/discarded ratio, and any recurring failure patterns (what kinds of changes got reverted)
- Rating: 7-8 for runs that surface a systemic gap; 5-6 for steady incremental improvement; do not write signal for runs where metric did not move
