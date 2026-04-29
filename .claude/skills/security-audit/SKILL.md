---
name: security-audit
description: Deterministic security scan + LLM triage -- secrets, gitignore, config, compliance
---

# IDENTITY and PURPOSE

Jarvis security audit engine. `security_scan.py` does deterministic scanning; you direct the thinking: severity assessment, false positive filtering, context-aware remediation, constitutional compliance.

# DISCOVERY

## Stage
VERIFY

## Syntax
/security-audit [scope]

## Parameters
- (no args): full security audit (gitignore gate + secrets scan + TELOS + constitutional rules)
- `secrets-only`: run only the secrets/credential scan step
- `post-commit`: run the gitignore gate and secrets check appropriate for post-commit context

## Examples
- /security-audit
- /security-audit secrets-only
- /security-audit post-commit

## Chains
- Before: (standalone -- run anytime, especially before commits and PRs)
- After: /self-heal (if critical findings need auto-fix), /review-code (if code-level fixes needed)
- Full: /security-audit > /self-heal (Criticals) > /commit

## Output Contract
- Input: optional scope (default: full audit)
- Output: audit report with severity-rated findings + remediation
- Side effects: writes audit log to history/security/, may auto-fix Critical/High gitignore/tracking issues

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- Valid scope values: (none), `secrets-only`, `post-commit`
- If a scope argument is provided and it is not one of those values: print "Usage: /audit [secrets-only|post-commit]" and STOP
- If no scope argument: run full audit (gitignore gate + scan + TELOS + constitutional rules)
- Proceed to Phase 1 with determined scope

## Phase 1: Deterministic Scan

1. Run `python tools/scripts/security_scan.py --pretty --filter-fp --run-tests --audit-log` to collect all scan data with false positive filtering, defensive test execution, and automatic audit logging
2. Validate the output:
   - Check `_schema_version` is `"1.0.0"` -- if mismatched, STOP and report: "Schema version mismatch -- security_scan.py and this skill are out of sync. Expected 1.0.0, got {version}."
   - Check `errors` array -- if non-empty, report each error inline with a [DEGRADED] marker
   - Check `defensive_tests.status` -- if "fail", report failing tests before proceeding
   - Check `summary.real_findings` vs `summary.false_positives` -- the script pre-filters test fixtures and upstream vendored patterns
3. Parse `real_findings` from the JSON output (false positives are already separated)

## Phase 2: LLM Triage

4. For each finding, assess with judgment the script cannot provide:
   - **Severity**: Critical / High / Medium / Low / Info
   - **False positive check**: Is this a test fixture? A documentation example? A pattern match in a comment?
   - **Exploitability**: How easy is this to exploit in this specific repo context?
   - **Impact**: What is the worst case if exploited?
   - **Remediation**: Specific, actionable fix
5. Filter out confirmed false positives (e.g., fake secrets in test files like `test_secret_scanner.py`, `test_injection_detection.py`)
6. Cross-reference findings against `security/constitutional-rules.md` for compliance gaps

## Phase 3: Deep Scan (LLM-only checks)

7. These checks require intelligence and cannot be scripted:
   - **Injection vector review**: Review hooks, validators, and code processing external input for command injection, path traversal, or prompt injection risks
   - **Constitutional compliance**: Verify all validators and hooks enforce the constitutional rules
   - **TELOS data protection**: Verify personal identity files are not exposed in ways the script cannot detect
   - **Dependency risks**: If package files exist, check for known vulnerable patterns
8. Add any new findings to the triage list

## Phase 4: Remediation Loop (max 2 cycles)

9. For Critical and High findings that are safely auto-fixable (gitignore gaps, tracked personal content, exposed files):
   a. **Fix**: Apply the remediation (e.g., `git rm --cached`, add gitignore entries)
   b. **Rescan**: Run `python tools/scripts/security_scan.py --pretty` again to confirm fix
   c. If FIXED: update finding status to "fixed"
   d. If STILL PRESENT after cycle 2: mark as "open -- manual intervention required"
   e. Scope constraint: only auto-fix safe, reversible operations. Do NOT auto-fix code-level vulnerabilities
10. Medium/Low/Info findings are reported but do NOT trigger the remediation loop

## Phase 5: Defensive Test Suite

11. The defensive tests already ran in Phase 1 via `--run-tests`. Check `defensive_tests` in the JSON output:
    - If `status: pass` -- all tests passing, report count
    - If `status: fail` -- invoke `/self-heal` on the failures listed in `output_tail`

## Phase 6: Report

13. The audit log was already written in Phase 1 via `--audit-log` to `history/security/{date}_audit.md`. If remediation was performed, re-run `python tools/scripts/security_scan.py --pretty --filter-fp --audit-log` to append the post-remediation results
14. Report remediation loop metrics: N findings auto-fixed, M open, K defensive tests passed

## FALLBACK (if scanner script fails)

If `security_scan.py` returns an error, empty output, or non-zero exit code:
1. Report the failure explicitly: "security_scan.py failed: {error details}"
2. Offer: "Run full LLM-based security scan instead?"
3. If Eric confirms, fall back to scanning each attack surface individually (the old approach)
4. After fallback, recommend investigating the failing scanner

# AUDIT LOG FORMAT

Write to `history/security/{date}_audit.md`:

```markdown
# Security Audit -- {date}
- Scope: {what was scanned}
- Scanner: security_scan.py v{schema_version} ({execution_time_ms}ms)
- Findings: {count by severity}
- False positives filtered: {count}
- Overall Risk: {Critical/High/Medium/Low}

## Findings

### [{severity}] {finding title}
- Location: {file path and line}
- Source: {scanner | llm-deep-scan}
- Description: {what is wrong}
- Exploitability: {Easy/Medium/Hard}
- Impact: {what could happen}
- Remediation: {specific fix}
- Status: {open/fixed/false-positive}
```

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Run scanner FIRST (Phase 1 JSON) before any LLM analysis
- Order findings by severity (Critical first); include file + line number per finding
- Clean audit = no findings after triage (still log this)
- Never expose secret values in report — reference by location only
- Summary table: severity counts + overall risk rating; flag Critical findings prominently
- Log every audit to `history/security/` regardless of findings


# CONTRACT

## Errors
- **scanner-failure:** security_scan.py fails or returns invalid JSON -> offer LLM fallback
- **schema-mismatch:** version != 1.0.0 -> STOP and report
- **test-failure:** defensive tests fail -> invoke /self-heal

# SKILL CHAIN

- **Composes:** security_scan.py (subprocess), tests/defensive/ (health check)
- **Escalate to:** /delegation if findings require architectural changes

# VERIFY

- Audit log at `history/security/YYYY-MM-DD_audit.md` | Verify: `ls history/security/ | tail -3`
- Scanner output processed | Verify: Phase 1 results in report
- No secret values in report (location only, not values) | Verify: scan report for literal key/token values
- Defensive test results included | Verify: test suite section in output
- Critical findings have remediation or accepted-risk rationale | Verify: Read Critical section

# LEARN

- Same vulnerability 3+ consecutive audits: add rule to `security/constitutional-rules.md` + high-rated signal
- Track Critical count — zero 30+ days = maturity signal
- Audit with Critical findings: run /red-team to probe exploitability
- Scanner fails: log failure type; recurring = /self-heal fix

# INPUT

Run a security audit on the Jarvis system. If specific scope is provided, focus on that area. Otherwise, run a full audit.

INPUT:
