# PRD: Phase 5A Verification Gates

> CLI-first deterministic verification scripts for Phase 5 autonomous execution
> Created: 2026-03-31 | Status: Ready for implementation

---

## OVERVIEW

Phase 5 introduces autonomous task execution via a dispatcher that spawns workers in git worktrees. These workers run unattended — "the LLM said it looks fine" is not a verification strategy. This PRD delivers the two deterministic scripts the dispatcher needs to verify worker output without LLM judgment: `isc_validator.py` (ISC extraction + 6-check quality gate) and `code_prescan.py` (ruff + security_scan wrapper with structured exit codes). It also sharpens the existing steering rule to formalize the CLI-first principle already proven by 5 shipped scripts.

## PROBLEM AND GOALS

- **Phase 5 dispatcher has no machine-verifiable quality gate.** ISC criteria exist in PRD markdown but cannot be extracted or validated without an LLM reading the file. The dispatcher needs a binary pass/fail primitive.
- **Code review in autonomous runs burns LLM tokens on mechanical checks.** Linting, known vulnerability patterns, and security scan results should gate the LLM review — if deterministic checks fail, don't spend tokens on LLM judgment.
- **The "script vs. LLM" boundary is informal.** The existing steering rule works but uses "Python script" as the default, which is unnecessarily specific. Formalizing "deterministic script (default Python)" codifies a principle already validated by 5 shipped tools.

## NON-GOALS

- No retroactive refactoring of existing skills (architecture review: working skills don't need rewriting for aesthetic reasons)
- No evals framework (deferred to Phase 5D when real worker execution data exists)
- No PDF generation, image gen multi-backend, or market intelligence (independent projects, not Phase 5 prerequisites)
- No semgrep custom rules, radon complexity metrics, or pip-audit in code_prescan.py v1 (add when Phase 5 failure analysis demonstrates need)
- No new skill creation — these scripts integrate into existing skills (/implement-prd, /review-code, /quality-gate)

## USERS AND PERSONAS

- **Phase 5 dispatcher (primary)**: Autonomous process that spawns workers and must verify their output with exit codes, not LLM judgment
- **Eric via /implement-prd (secondary)**: Interactive PRD execution benefits from deterministic ISC validation before LLM-powered verification
- **Eric via /review-code (secondary)**: Code prescan provides structured input so the LLM focuses on judgment, not mechanical checks

## USER JOURNEYS OR SCENARIOS

1. **Dispatcher verifies worker output**: Worker claims ISC items are met -> dispatcher runs `python tools/scripts/isc_validator.py --prd path/to/PRD.md` -> gets exit code 0 (all pass) or 1 (failures) + JSON report listing which criteria passed/failed the 6-check gate
2. **Dispatcher gates code review**: Worker submits code changes -> dispatcher runs `python tools/scripts/code_prescan.py --path path/to/changed/files/` -> gets exit code 0 (clean) or 1 (findings) + JSON with per-tool status -> if exit 1, worker is told to fix before LLM review
3. **/implement-prd validates ISC at PLAN stage**: User runs /implement-prd -> skill calls `isc_validator.py --prd PRD.md` -> if quality gate fails, skill reports which criteria need fixing before BUILD begins
4. **/review-code pre-filters**: User runs /review-code -> skill calls `code_prescan.py --path <files>` -> LLM receives structured prescan JSON alongside the code, focusing judgment on non-mechanical issues

## FUNCTIONAL REQUIREMENTS

### isc_validator.py

- FR-001: Extract ISC criteria from any PRD file matching the format `- [ ] Criterion text | Verify: method`
- FR-002: Run the 6-check quality gate on extracted criteria: (1) count 3-8 per phase, (2) single sentence / no compound "and", (3) state-not-action phrasing, (4) binary pass/fail testable, (5) at least one anti-criterion exists, (6) every criterion has `| Verify:` suffix
- FR-003: Normalize Unicode before regex parsing — replace smart quotes, em-dashes, curly apostrophes with ASCII equivalents (mobile-originated PRDs)
- FR-004: Output structured JSON with `_provenance` block (script name, version, git hash, timestamp), extracted criteria list, per-criterion check results, and overall pass/fail
- FR-005: Exit code 0 when all criteria pass all 6 checks; exit code 1 when any check fails
- FR-006: Support `--json` (machine output), `--pretty` (human-readable JSON), and default table format
- FR-007: Support `--prd PATH` to specify PRD file (required argument)
- FR-008: Report `extracted_count` in output — if 0 criteria found, always fail (0 is never valid for a non-trivial PRD)

### code_prescan.py

- FR-009: Run ruff on specified path and capture findings as structured JSON
- FR-010: Run existing `security_scan.py` and capture its output
- FR-011: Emit explicit per-tool status field: `pass`, `fail`, `tool_unavailable`, `timeout`, `partial` — the LLM must never interpret missing output as "no findings"
- FR-012: Output structured JSON with `_provenance` block, per-tool results, aggregated finding count, and overall pass/fail
- FR-013: Exit code 0 when all tools report `pass` or `tool_unavailable` with 0 findings; exit code 1 when any tool reports findings
- FR-014: Support `--path PATH` (directory or file to scan), `--json`, `--pretty` flags
- FR-015: Timeout each sub-tool at 60 seconds; emit `timeout` status if exceeded
- FR-016: Detect missing tools (ruff not installed) and emit `tool_unavailable` rather than crashing

### Steering Rule Update

- FR-017: Update CLAUDE.md steering rule from "does this step require intelligence (judgment, synthesis, natural language generation)? No -> implement as Python script" to "No -> implement as a deterministic script (default Python)"

## NON-FUNCTIONAL REQUIREMENTS

- NFR-001: Both scripts must produce ASCII-only terminal output (Windows cp1252 compatibility per existing steering rule)
- NFR-002: Both scripts must run in under 10 seconds for typical inputs (single PRD, <50 changed files)
- NFR-003: Zero external dependencies beyond Python stdlib + ruff (already installed) + existing security_scan.py
- NFR-004: All file I/O via `pathlib` (Windows path compatibility)
- NFR-005: Both scripts follow the `_provenance` pattern established by `security_scan.py` — script name, version, git hash, timestamp, checks run

## ACCEPTANCE CRITERIA

### Phase 1: isc_validator.py (4 criteria)

- [x] isc_validator.py extracts all ISC criteria from the Jarvis Phase 4 PRD (`memory/work/jarvis/PRD.md`) with 0 missed items [E] | Verify: `python tools/scripts/isc_validator.py --prd memory/work/jarvis/PRD.md --json` returns extracted_count matching manual count
- [x] Each of the 6 quality gate checks produces correct pass/fail for a test PRD containing known good and known bad criteria [E] | Verify: `python -m pytest tests/defensive/test_isc_validator.py` passes
- [x] isc_validator.py normalizes Unicode smart quotes and em-dashes before parsing, correctly extracting criteria from mobile-originated PRDs [I] | Verify: Test case with smart quotes in test suite passes
- [x] isc_validator.py never crashes on malformed PRD input — returns exit code 1 with `extracted_count: 0` and descriptive error [E] | Verify: Run against empty file, non-markdown file, file with no ISC section

### Phase 2: code_prescan.py (4 criteria)

- [x] code_prescan.py runs ruff and security_scan.py, producing a unified JSON report with per-tool status fields [E] | Verify: `python tools/scripts/code_prescan.py --path tools/scripts/ --json` returns valid JSON with `tools[].status` fields
- [x] When ruff is not installed, code_prescan.py emits `"status": "tool_unavailable"` for ruff instead of crashing [E] | Verify: Rename ruff binary temporarily, run prescan, confirm `tool_unavailable` status
- [x] code_prescan.py exits 0 only when all tools ran and found 0 issues; exits 1 on any findings or tool failure [E] | Verify: Run against known-clean and known-dirty paths, confirm exit codes
- [x] No tool output is silently swallowed — `"status": "pass"` with `"findings": []` is distinct from `"status": "tool_unavailable"` with no findings field [E] [A] | Verify: JSON schema check in test suite

### Phase 3: Steering Rule + Skill Wiring (3 criteria)

- [x] CLAUDE.md steering rule updated to "deterministic script (default Python)" without creating a duplicate or conflicting rule [E] | Verify: `grep -c "deterministic script" CLAUDE.md` returns 1
- [x] /review-code SKILL.md references code_prescan.py as a pre-step before LLM analysis [E] | Verify: `grep "code_prescan" .claude/skills/review-code/SKILL.md` matches
- [x] /implement-prd SKILL.md references isc_validator.py for ISC quality gate validation at PLAN stage [E] | Verify: `grep "isc_validator" .claude/skills/implement-prd/SKILL.md` matches

### Anti-criteria

- [x] Neither script writes to any file outside stdout/stderr unless `--file` flag is explicitly passed [E] [A] | Verify: Review — no open() calls in write mode without flag check

ISC Quality Gate: PASS (6/6) — count: 4/4/3 per phase (within 3-8), single sentence each, state-based phrasing, binary-testable with verify methods, anti-criterion present, all have `| Verify:` suffix

## SUCCESS METRICS

- Phase 5 dispatcher can verify ISC criteria and code quality with exit codes alone — no LLM call required for pass/fail decisions
- isc_validator.py correctly parses 100% of existing PRDs in `memory/work/*/PRD.md`
- code_prescan.py reduces /review-code LLM token usage by pre-filtering mechanical findings (measure after 10 reviews)
- Zero false "clean" reports from code_prescan.py when tools fail to run (the silent-failure prevention goal)

## OUT OF SCOPE

- semgrep integration (add in v2 when custom rules are authored)
- radon complexity scoring (informational, not gating — add when Phase 5 failure data shows missed complexity issues)
- pip-audit dependency scanning (periodic, not per-commit — separate scheduled job)
- Model-based grading / evals framework (Phase 5D)
- Retroactive refactoring of skills that already work
- Any new skill creation — scripts wire into existing skills only

## DEPENDENCIES AND INTEGRATIONS

| Dependency | Type | Status |
|---|---|---|
| `security_scan.py` | Script (subprocess) | Exists, v1.0.0 — code_prescan.py calls it |
| `quality_gate_check.py` | Script (reference) | Exists — isc_validator.py shares ISC regex pattern, does not import it |
| `ruff` | External CLI tool | Installed via pip — code_prescan.py calls via subprocess |
| `/review-code` SKILL.md | Skill (wiring) | Add code_prescan.py as pre-step |
| `/implement-prd` SKILL.md | Skill (wiring) | Add isc_validator.py at PLAN stage |
| `/quality-gate` SKILL.md | Skill (wiring) | Already uses quality_gate_check.py; isc_validator.py adds the 6-check gate |
| CLAUDE.md | Config | Steering rule one-word edit |

## RISKS AND ASSUMPTIONS

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| ISC format varies across PRDs | Medium | Normalize Unicode first; regex handles `[-*]` bullets and `[ ]/[x]/[X]` checkboxes; test against all existing PRDs |
| ruff version changes alter rule set | Low | Pin version in requirements; emit version in `_provenance` |
| security_scan.py output format changes | Low | code_prescan.py validates JSON schema version before parsing |
| "State-not-action" check is hard to make deterministic | Medium | Use heuristic (starts with verb = likely action); flag for LLM review rather than hard-fail |
| quality_gate_check.py already has ISC parsing — duplication | Low | isc_validator.py focuses on the 6-check quality gate; quality_gate_check.py focuses on deliverable verification. Different concerns, shared regex |

### Assumptions

- ruff is installed in the Python environment (it is — used in pre-commit)
- security_scan.py's JSON output contract (v1.0.0) is stable
- PRDs follow the ISC format documented in CLAUDE.md
- The Phase 5 dispatcher will consume JSON stdout and exit codes (standard Unix pattern)

## OPEN QUESTIONS

1. **Should isc_validator.py reuse quality_gate_check.py's `parse_isc_items()` function (import) or duplicate the regex?** Importing creates a coupling; duplicating risks drift. Recommendation: duplicate + add a shared test that validates both parsers produce identical output on the same input.
2. **Should the "state-not-action" check (quality gate #3) be a hard fail or a warning?** It's the hardest check to make deterministic. Recommendation: start as warning, promote to hard fail after calibrating against existing PRDs.
3. **Should code_prescan.py also run `mypy` if available?** Out of scope for v1 but worth considering for v2 if type errors are common in Phase 5 worker output.
