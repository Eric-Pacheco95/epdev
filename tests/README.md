# Tests

Continuous verification for the Jarvis AI brain. Self-tests, defensive checks, and integration tests live here.

## Layout

- `defensive/` — ongoing security tests (input validation, secret scanning, hook coverage)
- `self-heal/` — self-healing verification (failure capture → fix loop)
- `isc_executor/` — ISC verifier integration tests
- `test_*.py` — unit and integration tests for `tools/scripts/lib/` modules

## Conventions

### Isolated paths for stateful writes

Self-tests MUST use isolated paths for ALL stateful writes — state files, backlogs, lock files, anything that persists. Use `tempfile.mkdtemp()` or pass explicit temp paths into every writer function. Never let a self-test mutate a real path under `data/`, `orchestration/`, `memory/`, or `history/`.

Why: 2026-04-07 dispatcher self-tests previously wrote to `data/followon_state.json` and `orchestration/task_backlog.jsonl` directly, polluting production state and creating phantom history. The fix is to make every test setup function build its own temp tree and clean up on teardown.

How to apply: when adding a new self-test that calls a function which writes to disk, first check whether that function accepts a path argument. If yes, pass a temp path. If no, refactor the function to accept one. No exceptions — even read-mostly tests should patch write paths defensively.
