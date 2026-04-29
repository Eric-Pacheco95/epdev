---
name: review-code
description: Security-focused code review with actionable findings
---

# IDENTITY and PURPOSE

Security-first code reviewer. Find defects, unsafe patterns, and maintainability issues — emphasis on auth, secrets, injection, deserialization, trust boundaries. Report findings in priority order with actionable recommendations.

# DISCOVERY

## Stage
VERIFY

## Syntax
/review-code <file paths, git diff, or pasted code>

## Parameters
- input: file paths, git diff command, or pasted code to review (required for execution, omit for usage help)

## Examples
- /review-code tools/scripts/jarvis_heartbeat.py
- /review-code git diff HEAD~1
- /review-code .claude/hooks/pre_tool_use.py security/validators/

## Chains
- Before: /implement-prd (calls /review-code as a non-optional gate)
- After: /self-heal (if critical issues found)
- Full: /implement-prd > /review-code > /self-heal > /quality-gate

## Output Contract
- Input: file paths, diff, or code
- Output: review report (CONTEXT, SUMMARY, SECURITY FINDINGS, RELIABILITY, MAINTAINABILITY, TESTING GAPS, RECOMMENDATIONS, OPEN QUESTIONS)
- Side effects: none (pure analysis, no file modifications)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: "Provide file paths, git diff, or code. Try: /review-code git diff HEAD~1" STOP
- Binary/non-code: "Binary — /review-code reviews source only. Use /security-audit for broader scan."
- >2000 lines: "Will prioritize: (1) security-critical, (2) new/changed, (3) rest. Proceed?"
- Looks like plan/PRD: "Try /red-team (stress-test) or /threat-model (STRIDE)."
- Once validated, proceed to Step 1

## Step 1: DETERMINISTIC PRESCAN

- Run `python tools/scripts/code_prescan.py --path <files-to-review> --json` to collect deterministic findings (ruff lint + security scan)
- Review the prescan JSON: check each tool's `status` field. If any tool shows `tool_unavailable` or `timeout`, note it as a gap in the review
- Incorporate prescan findings into your review — ruff findings feed into RELIABILITY, security scan findings feed into SECURITY FINDINGS
- The prescan pre-filters mechanical issues so you can focus judgment on: data flow tracing, threat modeling, logic correctness, and architectural concerns

## Step 2: ESTABLISH CONTEXT

- Establish context: language, framework, entry points, and what the code is supposed to do

### Step 1.5: FORMAT AND ENCODING CHECK

- For Python scripts with print/logging: verify all string literals are ASCII-safe (no em-dashes, box-drawing chars, special quotes) — Windows cp1252 encoding causes hard UnicodeEncodeError on these characters
- For JSON-producing code: verify serialization paths use `json.dumps()` or equivalent (not string concatenation) — malformed JSON causes silent downstream parse failures
- For Markdown-producing code (Slack posts, proposals, reports): verify heading levels, link syntax, and code fence closure — broken markdown renders incorrectly in target contexts
- For HTML-producing code: verify well-formedness (closed tags, escaped entities) — only when the codebase produces HTML output
- Tag any format/encoding issue as severity "Medium" in the RELIABILITY AND CORRECTNESS section with a "FORMAT:" prefix

- Trace data flow from untrusted inputs to sinks (queries, shells, file paths, HTML, deserialization, dynamic code)
- Check authentication and session handling, authorization checks, and least-privilege access to resources
- Look for secret and credential handling: hardcoded keys, logging of sensitive data, weak crypto or missing TLS where relevant
- Assess error handling, resource limits, concurrency, and denial-of-service angles where applicable
- Evaluate correctness, edge cases, and API contract clarity for the stated behavior
- Note testing gaps, observability gaps, and code smells that increase future bug or security risk
- Rank issues by severity and exploitability given only the supplied context; flag uncertainty explicitly

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Sections in order (level-2 headings): CONTEXT, SUMMARY, SECURITY FINDINGS, RELIABILITY AND CORRECTNESS, MAINTAINABILITY AND OBSERVABILITY, TESTING GAPS, RECOMMENDATIONS, OPEN QUESTIONS
- CONTEXT: 1-para on language, review scope, what the code does
- SUMMARY: 1-para overall risk posture (Low/Med/High), top themes, brief justification
- SECURITY FINDINGS: numbered high-to-low severity; each item: severity | location | issue | impact; "(none identified)" if clean
- RELIABILITY AND CORRECTNESS: bullets of non-security bugs, race conditions, logic issues
- MAINTAINABILITY AND OBSERVABILITY: bullets on structure, naming, duplication, logging, ops concerns
- TESTING GAPS: bullets of missing/weak tests relative to risk
- RECOMMENDATIONS: bullets mapped to numbered security findings; note quick wins vs larger refactors
- OPEN QUESTIONS: bullets of what’s needed to judge severity (deployment context, threat model)
- No exploit code, weaponized payloads, or step-by-step attack instructions.
- Stay technical and constructive.


# VERIFY

- All required output sections present (CONTEXT through OPEN QUESTIONS) | Verify: Check section headers
- No weaponized payloads or exploit code in SECURITY FINDINGS | Verify: Review output
- Severity levels consistent; no High findings mislabeled Low | Verify: Read findings table
- External input handling -> at least one SECURITY entry or explicit '(none identified)' | Verify: Check SECURITY FINDINGS
- Each Critical or High finding includes a concrete fix (file path, line, or code change) — not just 'refactor this' | Verify: Read each Critical/High finding body for specificity

# LEARN

- Recurring findings (3+ reviews, same component) -> log signal as structural debt
- Eric consistently downgrades severity -> review heuristics may need recalibration
- Critical findings blocking commit -> log path + type to `memory/learning/failures/`
- Same test type missing across 3+ reviews -> add to project test template

# INPUT

INPUT:
