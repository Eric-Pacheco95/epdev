# PRD: isc_executor.py — Deterministic VERIFY Phase Execution Engine

> Status: DRAFT | Created: 2026-04-01 | Owner: Eric P
> Architecture review: COMPLETE (2026-04-01) — all key decisions locked

---

## OVERVIEW

`isc_executor.py` is the deterministic execution engine for Jarvis's VERIFY phase. It parses ISC criteria from a PRD file, dispatches each `| Verify:` method to the appropriate handler, and emits a structured JSON report with per-criterion pass/fail evidence. The companion `SKILL.md` wrapper at `.claude/skills/validation/SKILL.md` chains the existing `isc_validator.py` (format gate) to `isc_executor.py` (execution) and renders the final markdown summary. No LLM reasoning is in the execution path; all judgment is deferred to the MANUAL verdict classification which is routed to a human checklist. This is Phase 5B infrastructure — the Phase 5 dispatcher uses the exit code to route worker results without human intervention.

---

## PROBLEM AND GOALS

- **Problem:** The Jarvis VERIFY phase is manual. After every `/implement-prd` build, Eric reads ISC criteria and checks them by eye — no evidence is captured, results are not reproducible, and the Phase 5 dispatcher has no machine-readable completion signal.
- **Goal 1:** Automate all deterministic ISC verify types so verification requires zero LLM tokens for the majority of criteria.
- **Goal 2:** Surface MANUAL items (informal prose, Review types, CLI) explicitly as a human checklist, routed to `#jarvis-inbox` by the Phase 5 dispatcher — never silently skipped.
- **Goal 3:** Provide the Phase 5 dispatcher with a reliable exit code (0/1/2/3) to route worker outcomes without human chat intervention.
- **Goal 4:** Establish a security boundary: AI-authored CLI verify methods are never auto-executed. v1 is read-only with zero OS execution risk from ISC content.

---

## NON-GOALS

- CLI auto-execution from ISC files (deferred to v2 — requires allowlist design and security review)
- Codex / external model integration (deferred to v2 — no eval track record yet)
- Parallel criterion execution (serial is adequate for 3-8 criteria; optimize when evidence demands it)
- Auto-discovery of verify methods by scanning code (scope creep — ISC author's responsibility)
- Writing results back to ISC checkboxes or tasklist (ACT-layer behavior; `isc_executor.py` is SENSE-only)
- Mid-build incremental verification (end-of-phase only; `/implement-prd` build loop stays LLM-driven)

---

## USERS AND PERSONAS

- **Eric (primary):** Invokes `/validation` at end of a build phase to get a reproducible verification report before marking a task complete. Also uses standalone `python tools/scripts/isc_executor.py --prd <path>` from the terminal.
- **Phase 5 dispatcher (machine consumer):** Calls `isc_executor.py` after each autonomous worker completes; routes on exit code (0=complete, 1=self-heal, 2=alert, 3=Slack MANUAL checklist).

---

## USER JOURNEYS OR SCENARIOS

**Scenario A — Interactive use (Eric)**
1. Build phase completes. Eric runs `/validation` (or `python tools/scripts/isc_executor.py --prd memory/work/foo/PRD.md`)
2. `isc_validator.py` runs first as a format gate — exits 1 if ISC is malformed, stops execution
3. `isc_executor.py` runs each criterion's verify method and emits JSON + markdown report
4. All PASS: exit 0 — Eric marks task complete
5. Any FAIL: exit 1 — evidence shown; Eric diagnoses and fixes
6. MANUAL items present, no FAILs: exit 3 — human checklist printed; Eric works through it

**Scenario B — Autonomous dispatch (Phase 5)**
1. Worker completes task, produces PRD at known path
2. Dispatcher calls `isc_executor.py --prd <path> --json`
3. Exit 0: dispatcher marks task complete, routes to LEARN phase
4. Exit 1: dispatcher routes failure evidence back to worker for self-heal loop
5. Exit 2: dispatcher raises infrastructure alert (executor crashed)
6. Exit 3: dispatcher posts MANUAL checklist to `#jarvis-inbox` via Slack

---

## FUNCTIONAL REQUIREMENTS

- **FR-001** — `isc_executor.py` parses ISC criteria from a PRD file using the same `- [ ] Criterion text | Verify: method` regex pattern as `isc_validator.py`
- **FR-002** — Grep-type verify methods execute via Python `re.search` against the target file — no subprocess call to grep
- **FR-003** — Exist-type verify methods execute via `Path.exists()` — no subprocess call
- **FR-004** — Read-type verify methods check file existence; optionally check for a substring if provided after the path
- **FR-005** — Test-type verify methods execute via `subprocess.run` with a 60-second timeout and return PASS if exit code is 0
- **FR-006** — Schema-type verify methods parse a JSON file and evaluate a simple field assertion (field existence or field value comparison)
- **FR-007** — CLI-type, Review-type, and any unrecognized prefix emit MANUAL verdict with the original method text as the human instruction — never executed
- **FR-008** — Informal prose verify methods (no recognized type prefix) are classified UNEXECUTABLE and emitted as MANUAL with explicit instruction
- **FR-009** — All criteria are initialized to verdict ERROR before execution begins; incomplete runs surface as ERROR, never as PASS
- **FR-010** — Evidence strings are scrubbed for common secret patterns (API keys, tokens, passwords) before appearing in any output
- **FR-011** — `isc_executor.py` accepts `--prd <path>` (required) and `--json` (optional) flags; default output is ASCII markdown table; `--json` emits machine-readable JSON
- **FR-012** — The SKILL.md wrapper at `.claude/skills/validation/SKILL.md` calls `isc_validator.py` first (format gate), then `isc_executor.py`, then renders the combined markdown report
- **FR-013** — On Windows, `subprocess.run` with `TimeoutExpired` explicitly calls `.kill()` on the child process before re-raising

---

## NON-FUNCTIONAL REQUIREMENTS

- **NFR-001** — All terminal output is ASCII-only (no Unicode box-drawing chars); compatible with Windows cp1252 encoding
- **NFR-002** — `isc_executor.py` never writes to any file; all output is stdout only
- **NFR-003** — Grep handler uses Python `re.search` — no subprocess dependency; works on Windows without grep on PATH
- **NFR-004** — Test-type subprocess calls include a 60-second timeout; Windows child processes are explicitly killed on timeout
- **NFR-005** — Total execution time for a 8-criterion ISC set should complete in under 90 seconds (bounded by Test timeout ceiling)
- **NFR-006** — JSON output schema is versioned (`_schema_version` field) and matches the `isc_validator.py` output schema conventions

---

## ACCEPTANCE CRITERIA

### Phase 1: Core executor — deterministic handlers + MANUAL classification

- [x] `isc_executor.py` returns exit code 0 when all non-MANUAL criteria PASS [E] [M] | Verify: Test: pytest tests/isc_executor/test_exit_codes.py::test_all_pass | model: sonnet
- [x] `isc_executor.py` returns exit code 1 when at least one criterion FAILs [E] [M] | Verify: Test: pytest tests/isc_executor/test_exit_codes.py::test_one_fail | model: sonnet
- [x] `isc_executor.py` returns exit code 3 when MANUAL items are present and no FAILs exist [E] [M] | Verify: Test: pytest tests/isc_executor/test_exit_codes.py::test_manual_no_fail | model: sonnet
- [x] Any verify method with a CLI or Review prefix emits MANUAL verdict without subprocess execution [E] [A] | Verify: Grep!: subprocess.*CLI in tools/scripts/isc_executor.py | model: sonnet
- [x] All criteria are initialized to ERROR verdict before execution begins so incomplete runs do not false-PASS [E] [A] | Verify: Grep: ERROR.*verdict\|verdict.*ERROR in tools/scripts/isc_executor.py | model: sonnet
- [x] No file write operations exist in `isc_executor.py` [E] [A] | Verify: Grep!: open\( in tools/scripts/isc_executor.py | model: sonnet
- [x] Evidence output is scrubbed for common secret patterns before emission [E] [A] | Verify: Grep: SECRET_PATTERNS\|scrub_secrets in tools/scripts/isc_executor.py | model: sonnet

ISC Quality Gate: PASS (6/6)

### Phase 2: SKILL.md wrapper + integration

- [x] `/validation` skill file exists at `.claude/skills/validation/SKILL.md` [E] [M] | Verify: Exist: .claude/skills/validation/SKILL.md | model: sonnet
- [x] SKILL.md calls `isc_validator.py` before `isc_executor.py` in its workflow [E] [A] | Verify: Grep: isc_validator in .claude/skills/validation/SKILL.md | model: sonnet
- [x] Running `python tools/scripts/isc_executor.py --prd memory/work/isc-executor/PRD.md` against this PRD's own ISC returns exit 0 [E] [M] | Verify: Test: python tools/scripts/isc_executor.py --prd memory/work/isc-executor/PRD.md | model: sonnet
- [x] `--json` flag emits valid JSON with `_schema_version`, `criteria`, and `gate_passed` fields [E] [M] | Verify: Test: pytest tests/isc_executor/test_json_output.py | model: sonnet
- [x] No Unicode characters appear in terminal output on Windows (all output passes through `_sanitize_ascii`) [E] [A] | Verify: Grep: _sanitize_ascii in tools/scripts/isc_executor.py | model: sonnet

ISC Quality Gate: PASS (6/6)

---

## SUCCESS METRICS

- VERIFY phase of any `/implement-prd` run produces a machine-readable exit code and per-criterion evidence within 90 seconds
- Zero false PASSes from incomplete or errored runs (ERROR initialization enforces this)
- Phase 5 dispatcher correctly routes all 4 exit codes without human intervention for 5 consecutive autonomous task completions
- MANUAL verdict rate tracked per PRD — target: <30% of all criteria are MANUAL in well-formed PRDs (higher rate = ISC quality problem, not executor problem)

---

## OUT OF SCOPE

- CLI auto-execution (v2 — requires allowlist + security review first)
- Codex adversarial second-opinion layer (v2 — no eval track record)
- Parallel criterion execution
- Checkbox/tasklist mutation
- Mid-build incremental verification
- Auto-discovery of testable assertions from source code

---

## DEPENDENCIES AND INTEGRATIONS

- `tools/scripts/isc_validator.py` — already shipped; called by SKILL.md as format gate before executor runs
- `isc_validator.py` parser internals — `parse_isc_items()` and `_sanitize_ascii()` to be imported or duplicated in `isc_executor.py`
- Phase 5 dispatcher (`tools/scripts/dispatcher.py`) — consumes exit codes; no code changes needed in dispatcher for v1
- `.claude/skills/validation/SKILL.md` — new file; integrates into the skill registry
- Slack `#jarvis-inbox` — receives MANUAL checklists routed by dispatcher on exit 3 (dispatcher change, not executor change)
- Python stdlib only: `re`, `pathlib`, `subprocess`, `json`, `argparse`, `sys` — no new dependencies

---

## RISKS AND ASSUMPTIONS

**Risks:**
- Test-type subprocess commands with side effects (file writes, installs) violate VERIFY phase read-only semantics — executor is faithful, not safe-by-design on all inputs; ISC author responsibility; document clearly
- Schema-type field assertions need a simple but unambiguous syntax — a poorly designed syntax causes false PASSes from malformed expressions; design syntax with explicit test cases before implementation
- Subprocess stdout from Test-type commands may contain secrets — secret scrubber must run before any output is emitted (FR-010 is load-bearing)

**Assumptions:**
- `isc_validator.py` parser regex and `parse_isc_items()` function are stable and can be imported without modification
- All Test-type commands complete in under 60 seconds — if not, the ISC author should split or refactor the verify method
- Phase 5 dispatcher already handles exit codes from subprocesses — only the routing table needs updating for exit code 3

---

## OPEN QUESTIONS

- **Schema syntax:** What is the exact syntax for Schema-type assertions? Options: (a) `Schema: path/to/file.json .field_name` (field existence), (b) `Schema: path/to/file.json .field_name == value` (equality), (c) jmespath expressions. Recommendation: start with (a) + (b), defer jmespath to v2.
- **Grep negation:** Should `Grep:` support a negation mode (expect zero matches)? Real anti-criteria like "no open() in write mode" need this. Syntax proposal: `Grep: pattern NOT IN file` or `Grep!: pattern`. Needs decision before implementation.
- **`parse_isc_items()` import vs copy:** Import from `isc_validator` (cleaner, DRY) or duplicate the function (no cross-script dependency)? Import preferred but needs a test to catch if `isc_validator.py` parser changes break `isc_executor.py`.
- **SKILL.md for `/validation` — new skill or sub-step of `/implement-prd`?** Architecture review recommends standalone. Confirm before building SKILL.md.
