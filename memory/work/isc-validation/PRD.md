# PRD: ISC Validation Skill

**Status**: Draft  
**Created**: 2026-04-01  
**Owner**: Eric P (epdev)  
**Architecture review**: completed 2026-04-01 (arch-review-20260401-222027)

---

## OVERVIEW

The ISC Validation skill closes the VERIFY-phase gap for interactive Jarvis sessions by extending the existing `isc_validator.py` script with a `--execute` flag that runs ISC verify methods automatically, extracting shared sanitization logic into a reusable `isc_common.py` module, and hardening the command execution path against two HIGH-severity security gaps identified in the architecture review. A thin `/validation` SKILL.md wrapper makes the capability discoverable. This is a refactor-and-extend, not a new build: approximately 85% of the implementation already exists across `isc_validator.py` and `jarvis_dispatcher.py`.

---

## PROBLEM AND GOALS

- **Problem**: Interactive Jarvis sessions require Eric or Claude to manually run each ISC `| Verify:` command, read output, and judge pass/fail — error-prone for ISC sets with 5+ criteria and inconsistent with the automated verification already working in the autonomous dispatcher.
- **Goal 1**: Automate the deterministic half of VERIFY (CLI, Grep, Test commands) so Eric can run one command and get a structured pass/fail report with evidence.
- **Goal 2**: Harden the existing `sanitize_isc_command()` execution path against two HIGH-severity findings (sandbox escape via `python -c`, secret exposure via unguarded subprocess calls) — these are pre-existing bugs in the dispatcher that must be fixed regardless of this skill.
- **Goal 3**: Eliminate code duplication by extracting shared ISC sanitization logic into `tools/scripts/lib/isc_common.py`, importable by both the dispatcher and the validator.
- **Goal 4**: Surface the capability through a discoverable `/validation` SKILL.md so Eric knows it exists and how to invoke it.

---

## NON-GOALS

- No Codex / OpenAI adversarial review integration (deferred to v2 with clean JSON interface)
- No auto-gating of `/implement-prd` task completion on validation results
- No automation of `Review`-type verifications (flagged as `manual_required`, not executed)
- No changes to the autonomous dispatcher's execution flow (security fixes apply to the shared module, dispatcher imports unchanged behavior)
- No scheduled/autonomous validation runs (dispatcher already handles this)

---

## USERS AND PERSONAS

- **Eric (interactive)**: Runs `/validation` at end of a build sprint to verify ISC criteria before marking a task complete. Wants a one-command summary with evidence, not a manual checklist.
- **Jarvis autonomous dispatcher** (indirect): Imports `sanitize_isc_command()` from the shared module. Benefits from security hardening transparently.

---

## USER JOURNEYS OR SCENARIOS

1. **Interactive VERIFY**: Eric finishes implementing a PRD phase. Runs `/validation memory/work/foo/PRD.md`. Gets a report: 4 criteria executed (3 pass, 1 fail with evidence), 2 criteria flagged `manual_required`. Reviews the fail, fixes the issue, re-runs.
2. **Security hardening (transparent)**: Dispatcher runs `sanitize_isc_command()` as before. Imported from `isc_common.py` instead of inline. `python -c "os.system(...)"` now blocked. `.env` path now blocked at argument level.
3. **Audit trail**: Every `/validation` run writes a timestamped report to `history/validations/YYYY-MM-DD_<slug>.md`. Eric can point to the file as evidence when marking a task done.

---

## FUNCTIONAL REQUIREMENTS

- **FR-001**: `tools/scripts/lib/isc_common.py` is created and exports: `ISC_ALLOWED_COMMANDS`, `sanitize_isc_command()`, and `SECRET_PATH_PATTERNS`.
- **FR-002**: `jarvis_dispatcher.py` imports `sanitize_isc_command` and `ISC_ALLOWED_COMMANDS` from `isc_common.py`; no behavior change to dispatcher.
- **FR-003**: `python` and `python3` are removed from `ISC_ALLOWED_COMMANDS` in `isc_common.py`. Inline `-c` execution is blocked. Explicit script paths (e.g., `python tools/scripts/foo.py`) are permitted via a path-prefix allowlist.
- **FR-004**: `echo` is removed from `ISC_ALLOWED_COMMANDS` in `isc_common.py` or flagged as a trivial-pass pattern in the execution report.
- **FR-005**: `sanitize_isc_command()` in `isc_common.py` applies `_protected_path()` checks to all command arguments (not just the command name), blocking `.env`, `.pem`, `.key`, `.ssh`, and equivalent secret-file patterns.
- **FR-006**: `sanitize_isc_command()` applies `_inline_script_destructive()` checks for any argument containing `os.remove`, `shutil.rmtree`, `os.system`, `subprocess.run`, or equivalent destructive patterns.
- **FR-007**: `isc_validator.py` gains a `--execute` flag that, after the format quality gate, iterates over criteria with non-empty `verify_method` and attempts execution.
- **FR-008**: For each criterion with a `verify_method`, the executor classifies the method as `executable` (shell command passable to `sanitize_isc_command`) or `manual_required` (Review, Slack, freeform description). Only `executable` methods are run.
- **FR-009**: Execution results are appended to the existing output schema as an `execution_results` array: each entry contains `criterion`, `status` (pass/fail/manual_required/blocked), `command`, `exit_code`, `output` (truncated to 500 chars), and `elapsed_ms`.
- **FR-010**: A per-run aggregate timeout of 120 seconds is enforced across all criteria; individual command timeout remains 30 seconds.
- **FR-011**: Every `--execute` run writes a timestamped Markdown report to `history/validations/YYYY-MM-DD_HH-MM-SS_<prd-slug>.md` containing the full execution results.
- **FR-012**: The report includes a count header: `Executed: N | Passed: N | Failed: N | Manual required: N | Blocked: N`.
- **FR-013**: The report is secret-scanned before writing: any line matching `SECRET_PATH_PATTERNS` or containing a key-value pattern (`KEY=value`) is redacted.
- **FR-014**: `.claude/skills/validation/SKILL.md` is created as a thin wrapper that invokes `python tools/scripts/isc_validator.py --prd PATH --execute` and presents results.
- **FR-015**: `--execute` mode emits a warning if `git status` shows uncommitted changes in the working tree that could affect verify results.

---

## NON-FUNCTIONAL REQUIREMENTS

- All terminal output from `isc_validator.py` must be ASCII-safe (cp1252 compatible) — use `_sanitize_ascii()` for execution output before printing.
- `isc_common.py` must have zero external dependencies beyond the Python standard library.
- Shared module extraction must not break existing dispatcher self-tests (`tests/` must pass after extraction).
- Report files in `history/validations/` must not be added to git (add to `.gitignore`).
- Aggregate 120s timeout must apply even if individual subprocess calls hang (use `concurrent.futures` or signal-based approach compatible with Windows).

---

## ACCEPTANCE CRITERIA

### Phase 1: Security hardening + shared module

- [x] `tools/scripts/lib/isc_common.py` exists and exports `ISC_ALLOWED_COMMANDS`, `sanitize_isc_command`, `SECRET_PATH_PATTERNS` [E] | Verify: test -f tools/scripts/lib/isc_common.py
- [x] `jarvis_dispatcher.py` imports from `isc_common` and all existing dispatcher tests pass [E] | Verify: python -m pytest tests/ -q --tb=short
- [x] `python` and `python3` are absent from `ISC_ALLOWED_COMMANDS` [E] | Verify: grep -c "python" tools/scripts/lib/isc_common.py
- [x] `sanitize_isc_command` blocks a `.env` argument regardless of which allowed command precedes it [E] | Verify: python -c "from tools.scripts.lib.isc_common import sanitize_isc_command; assert sanitize_isc_command('x | Verify: grep pattern .env') is None"
- [x] No ISC command containing `os.system` or `shutil.rmtree` passes sanitization [E][A] | Verify: Review isc_common.py destructive-pattern check coverage

**ISC Quality Gate: PASS (6/6)**

### Phase 2: isc_validator.py --execute flag

- [x] `isc_validator.py --execute` runs deterministic verify methods and reports pass/fail with command output [E] | Verify: python tools/scripts/isc_validator.py --prd memory/work/isc-validation/PRD.md --execute --json
- [x] Criteria with `Review`, `Slack`, or freeform descriptions are classified `manual_required` and not executed [E] | Verify: python -c "from tools.scripts.isc_validator import classify_verify_method; assert classify_verify_method('Review -- check file') == 'manual_required'"
- [x] Execution output is truncated to 500 chars per criterion [E][A] | Verify: Review _build_output execution_results truncation logic
- [x] No `--execute` run completes in more than 120 seconds total [E] | Verify: python tools/scripts/isc_validator.py --prd memory/work/isc-validation/PRD.md --execute
- [x] A warning is printed when `git status` shows uncommitted changes [E] | Verify: git stash && python tools/scripts/isc_validator.py --prd ... --execute (no warning); git stash pop && touch dirty && python ... (warning present); rm dirty

**ISC Quality Gate: PASS (6/6)**

### Phase 3: Audit trail + /validation skill

- [x] Every `--execute` run produces a timestamped Markdown file in `history/validations/` [E] | Verify: python tools/scripts/isc_validator.py --prd ... --execute && find history/validations -name "*.md" -newer history/validations
- [x] Report contains the count header `Executed: N | Passed: N | Failed: N | Manual required: N | Blocked: N` [E] | Verify: grep -c "Executed:" history/validations/*.md
- [x] `history/validations/` is in `.gitignore` [E] | Verify: grep -c "history/validations" .gitignore
- [x] `.claude/skills/validation/SKILL.md` exists and invoking `/validation` runs the extended script [E] | Verify: test -f .claude/skills/validation/SKILL.md
- [x] No secret-matching content (KEY=value, .env paths) appears in a written report after execution [E][A] | Verify: Review secret-scan logic applied before file write

**ISC Quality Gate: PASS (6/6)**

---

## SUCCESS METRICS

- All existing dispatcher and isc_validator tests pass after shared module extraction (zero regressions)
- At least one real PRD in the repo can be run through `--execute` and produce a mixed pass/manual_required report (proves the classifier works on actual ISC content)
- The two HIGH-severity STRIDE findings (E1: python escape, I1: subprocess hook bypass) are confirmed closed by a `/review-code` pass on `isc_common.py`

---

## OUT OF SCOPE

- Codex / OpenAI adversarial review integration
- Auto-gating `/implement-prd` task completion
- Automation of `Review`-type verifications
- Scheduled or autonomous `/validation` runs
- Changes to the autonomous dispatcher's task selection or execution flow
- `Review` type re-definition (deferred — needs separate design)

---

## DEPENDENCIES AND INTEGRATIONS

- `tools/scripts/isc_validator.py` — extended in Phase 2
- `tools/scripts/jarvis_dispatcher.py` — updated to import from shared module in Phase 1
- `tools/scripts/lib/` — new directory for shared modules; `isc_common.py` created here
- `tests/` — existing test suite must pass after all phases
- `history/validations/` — new directory for audit reports; added to `.gitignore`
- `.claude/skills/validation/SKILL.md` — new skill file
- `validate_tool_use.py` — source of `_protected_path()` and `_inline_script_destructive()` patterns to port (read-only reference)

---

## RISKS AND ASSUMPTIONS

**Risks**
- Shared module extraction could introduce an import cycle if dispatcher and validator both import from `isc_common` and `isc_common` imports from either — verify import graph is acyclic before merging.
- Removing `python`/`python3` from the allowlist may break existing autonomous tasks in `orchestration/task_backlog.jsonl` that use Python verify commands — audit backlog before removing.
- Aggregate 120s timeout on Windows requires `concurrent.futures.ThreadPoolExecutor` (no `signal.alarm`) — test in Task Scheduler context, not just Git Bash.

**Assumptions**
- `tools/scripts/lib/` directory does not yet exist (will be created as part of Phase 1).
- Existing `tests/defensive/test_isc_validator.py` covers the format quality gate; execution tests will be added in Phase 2.
- The `_protected_path()` and `_inline_script_destructive()` functions in `validate_tool_use.py` are pure functions with no Claude Code SDK dependencies — safe to port as-is.

---

## OPEN QUESTIONS

- Should `python tools/scripts/foo.py` (explicit script path) be permitted in the allowlist as a replacement for bare `python -c`? If yes, what validation is needed on the script path (exists in repo, no `../`, etc.)?
- Are there any existing ISC entries in `orchestration/task_backlog.jsonl` that use `python` or `echo` as verify commands? (Audit required before removing from allowlist — do not break running autonomous tasks.)
- Should `history/validations/` reports be kept indefinitely or pruned after N days? (Low priority for v1 — `history/` is append-only by convention.)
- Does `isc_common.py` belong in `tools/scripts/lib/` or directly in `tools/scripts/`? (`lib/` follows Python convention for shared modules; confirm with existing repo layout.)
