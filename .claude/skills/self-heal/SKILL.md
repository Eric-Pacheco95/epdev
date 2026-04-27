# IDENTITY and PURPOSE

Jarvis self-healing engine. Diagnose failing tests, hooks, skills, builds, and validations; apply minimal fix; verify; log the failure so it never repeats.

# DISCOVERY

## One-liner
Diagnose failures, apply minimal fixes, verify, and log so the same bug never recurs

## Stage
VERIFY

## Syntax
/self-heal <error description or failing command>
/self-heal

## Parameters
- error/failure: Description of what failed, error output, or failing command (optional -- if omitted, runs full defensive test suite as health check)

## Examples
- /self-heal "test_injection_detection.py failed with AssertionError on line 42"
- /self-heal "hook pre-commit crashed with UnicodeEncodeError"
- /self-heal -- run full defensive test suite and fix any failures

## Chains
- Before: Any failing test, hook, skill, or build step
- After: /learning-capture (failure is automatically logged to memory/learning/failures/)
- Related: /review-code (for code-level diagnosis), /update-steering-rules (if systemic issue found)
- Full: /self-heal > /learning-capture > /update-steering-rules (if systemic fix)

## Output Contract
- Input: Error description or empty (health check mode)
- Output: Diagnosis + fix applied + verification result, or UNRESOLVED after 3 cycles with escalation notes
- Side effects: Failure logged to memory/learning/failures/{date}_{slug}.md, code fixes applied, optional steering rule proposal

## autonomous_safe
false

# STEPS

## Step 0: INPUT CHECK

- If no error description or failing command was provided AND no recent failure context is visible in the session: print `'Usage: /self-heal <error description or paste the failing output>'` and STOP
- If invoked with bare `/self-heal` (no arguments): ask Eric to paste the error or describe what failed before proceeding

## Step 1: IDENTIFY FAILURE

- Identify what failed: read the error output, test result, or failure description
- Gather context: what was the system doing when it failed? What changed recently?
- Run the failing test or command again to confirm it's reproducible (don't fix phantom failures)
- Diagnose root cause using this checklist:
  - Is it a code bug? (logic error, typo, wrong variable)
  - Is it an environment issue? (missing dependency, wrong path, permissions)
  - Is it a data issue? (unexpected input, missing file, corrupt state)
  - Is it a race condition or timing issue?
  - Is it a configuration mismatch? (settings.json, hooks, paths)

### HEAL LOOP (max 3 cycles)

For each identified failure, enter the heal loop:

1. **Fix**: Apply the minimal fix — change only what's necessary to resolve the failure
2. **Verify**: Re-run the failing test/command to verify the fix works
3. **Regression check**: Run adjacent tests to verify no regressions were introduced
4. If verify PASSES and no regressions: exit loop, log success
5. If verify FAILS: diagnose what the fix didn't address, return to step 1
6. If regression detected: revert the fix, try an alternative approach, return to step 1
7. After cycle 3 still failing: STOP — log the failure as UNRESOLVED with all 3 attempted fixes documented. Do NOT keep trying. Escalate to Eric with diagnosis notes

Track loop iterations in output: "Healed in N cycle(s)" or "UNRESOLVED after 3 cycles"

### POST-HEAL

- Log the failure to `memory/learning/failures/` with full context (ONE log entry, not one per cycle — include all attempts in the single log)
- If the failure reveals a systemic issue, propose a new AI Steering Rule for CLAUDE.md
- If the failure came from a skill or hook, update that skill/hook to prevent recurrence

### DEFENSIVE TEST SUITE

When no specific failure is provided, run the full defensive test suite as a health check:
1. `python tests/defensive/test_injection_detection.py`
2. `python tests/defensive/test_secret_scanner.py`
3. If any test fails, enter the heal loop for each failure
4. Report results: N tests passed, M failed, K healed

# FAILURE LOG FORMAT

Write to `memory/learning/failures/{date}_{slug}.md`:

```markdown
# Failure: {short title}
- Date: {YYYY-MM-DD}
- Severity: {1-10}
- Component: {what broke — skill name, hook, test, script}
- Context: {what was happening when it failed}
- Error: {actual error message or output}
- Root Cause: {why it happened}
- Fix Applied: {what was changed, with file paths}
- Verification: {how the fix was confirmed}
- Prevention: {how to prevent recurrence}
- Steering Rule: {proposed CLAUDE.md addition, if applicable}
```

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Show error → diagnosis → fix in that order
- Apply fixes with Edit tool; show what changed; run verification and show result
- Log each fix attempt (feeds learning system)
- If root cause unclear: say so, log as anomaly signal
- Never suppress test failures; prefer minimal fixes over refactors
- Final summary: "Self-healed: {component} — {what was wrong}"


# VERIFY

- Failure log entry has all 6 fields (Context, Error, Root Cause, Fix Applied, Verification, Prevention) | Verify: Read entry in `memory/learning/failures/`
- Fix verified to pass | Verify: confirmation output shows error gone
- Fix did not expand into refactor/scope creep | Verify: only failing component modified
- Steering rule proposed: surfaced to Eric for approval | Verify: approval request in output

# LEARN

- Track most common failure types — after 5+ self-heals, top type becomes a pre-build check
- Same component fails 3+: structural debt; needs /review-code + refactor
- Root cause consistently unclear: self-heal diagnostic needs improvement; log signal
- After successful self-heal: run full defensive test suite to confirm no regression: `python tests/defensive/run_all.py`

# INPUT

Diagnose and fix the following failure. If no specific failure is provided, run the defensive and self-heal test suites and fix any failures found.

INPUT:
