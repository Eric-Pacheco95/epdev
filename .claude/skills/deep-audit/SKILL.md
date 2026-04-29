---
name: deep-audit
description: Multi-axis codebase audit (architecture, security, errors, domain, testing)
---

# IDENTITY and PURPOSE

Jarvis deep audit engine. Multi-axis codebase analysis (5 axes) for internal projects, external repos, and due diligence. Tiered severity findings, actionable output per mode.

# DISCOVERY

## One-liner
Run a 5-axis codebase audit (architecture, security, errors, domain logic, testing) and return prioritized findings.

## Stage
OBSERVE

## Syntax
/deep-audit [--onboard | --evaluate | --cherry-pick] <repo-path or GitHub URL>

## Parameters
- repo: local path or GitHub URL (required)
- --onboard: full Jarvis onboarding (audit + ISC tasklist + skills + orchestrator registration)
- --evaluate: read-only analysis + recommendations (default)
- --cherry-pick: pattern extraction with quality ratings

## Examples
- /deep-audit C:\Users\ericp\Github\crypto-bot
- /deep-audit --onboard C:\Users\ericp\Github\new-project
- /deep-audit --cherry-pick https://github.com/user/interesting-repo

## Chains
- Before: Eric's request or /project-orchestrator
- After: /create-prd (onboard), /implement-prd (fixes), /learning-capture
- Composes: /security-audit (shares security axis), /review-code (shares quality concerns)
- Full (onboard): /deep-audit --onboard > /create-prd > /implement-prd > /quality-gate > /learning-capture
- Full (fix): /deep-audit > /implement-prd (Tier 1 fixes) > /security-audit > /learning-capture

## Output Contract
- Input: repo path/URL + mode flag
- Output: tiered audit report with mode-specific sections
- Side effects: none for --evaluate; potential fixes for --onboard/--cherry-pick Tier 1 blockers

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- If no repo path or GitHub URL provided (bare `/deep-audit` with no arguments): print "Usage: /deep-audit [--onboard|--evaluate|--cherry-pick] <repo-path or GitHub URL>" and STOP
- If a flag is present and it is not one of `--onboard`, `--evaluate`, `--cherry-pick`: print "Unknown mode. Valid: --onboard, --evaluate, --cherry-pick" and STOP
- Default mode if no flag: `--evaluate`
- Proceed to Step 1

1. Accept repo path or GitHub URL. Clone if URL.
2. Determine mode from flags (default: --evaluate)
3. Launch **5 parallel analysis passes** (spawn with `model="claude-sonnet-4-6"` on every Agent() call per `memory/knowledge/harness/subagent_model_routing.md` — adversarial review downgrade):

   **Architecture**: dependency graph, circular deps, layering violations, entry points, coupling hotspots, framework/language versions
   **Security**: exposed secrets, input validation, auth/authz, dependency CVEs, injection surfaces (SQL, command, path, prompt)
   **Error Handling**: exception coverage, fail-open vs fail-closed, retry/circuit-breaker patterns, logging completeness, graceful degradation
   **Domain Logic**: algorithm correctness, data flow integrity, business rule coverage, tech debt hotspots, implicit assumptions
   **Testing**: coverage gaps, test quality (mocks vs integration), critical path coverage, flaky test indicators, CI completeness

4. Synthesize into tiered severity:
   - **Tier 1 (Blockers)**: security vulns, data loss risks, correctness bugs
   - **Tier 2 (Hardening)**: risk reduction, reliability improvements
   - **Tier 3 (Tech Debt)**: maintainability, performance, DX

   Each finding: one-line description, file:line reference, severity justification.

5. **Mode-specific outputs**:
   - `--onboard`: ISC tasklist (8-word criteria, [E]/[I]/[R] confidence, [M]/[A] verify type), domain skill proposals, orchestrator health source
   - `--cherry-pick`: extractable patterns with S/A/B/C/D ratings, adaptation difficulty (trivial/moderate/significant)
   - `--evaluate`: prioritized recommendations only

6. **Tier 1 Remediation Loop** (--onboard/--cherry-pick only, max 2 cycles): auto-fix safe Tier 1 findings → re-audit axis → resolved or "open -- requires manual fix". Never auto-fix logic/architecture/domain issues.

7. Auto-offer: "Want a `/visualize system` diagram of the architecture findings?"

# OUTPUT FORMAT

```markdown
# Deep Audit: {repo name}
- Mode: {onboard | evaluate | cherry-pick}
- Date: {YYYY-MM-DD}
- Axes: Architecture, Security, Error Handling, Domain Logic, Testing

## Executive Summary
{3-5 bullets, readable in 30 seconds}

## Tier 1 -- Blockers
## Tier 2 -- Hardening
## Tier 3 -- Tech Debt
## Strengths

## {Mode section: Recommendations | Onboarding Plan | Extractable Patterns}
```

For security findings: never expose actual secret values. ISC items follow CLAUDE.md format: `- [ ] Criterion | Verify: method`

# INPUT

Provide a local repo path or GitHub URL with optional mode flag.

INPUT:

# VERIFY

- Output contains all required sections: Executive Summary, Tier 1 — Blockers, Tier 2 — Hardening, Tier 3 — Tech Debt, Strengths, plus mode-specific section | Verify: Read output, scan for each heading
- No actual secret values exposed in output (API keys, tokens, passwords) | Verify: Review — confirm output references secret paths only, never values
- All ISC items follow the format: `- [ ] Criterion | Verify: method` | Verify: `grep '- \[ \]' output` — each hit must contain '| Verify:'
- Every Tier 1 item has at least one concrete remediation path (not just identification) | Verify: Read Tier 1 — Blockers, confirm each item includes a 'Fix:' or equivalent action
- Tier 1 secret/credential findings were flagged before audit completion (not buried in output) | Verify: If any Tier 1 item involves secret exposure, confirm it appears before the full output narrative

# LEARN

- Signal {YYYY-MM-DD}_deep-audit-{slug}.md: >= 2 Tier 1 blockers or security finding not caught by existing tests.
- Rating: 8-9 for Tier 1 security findings; 6-7 for architecture blockers; 4-5 for tech debt patterns; only write signal when findings exceed what /security-audit would have caught
- If --onboard mode: add a project entry to orchestration/tasklist.md linking to the audit findings
- If onboarded projects accumulate findings that echo each other's Tier 1 blockers, extract the shared pattern into a diagnostic check in `tools/scripts/` rather than auditing it manually each time
