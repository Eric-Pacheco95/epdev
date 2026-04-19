# Testing & Sentinel-Structure Governance — Steering Rules

> Behavioral constraints for test writing, sentinel-structure maintenance, and ISC-proof verification. Loaded by SKILL.md files that write or audit tests (`quality-gate`, `implement-prd`, `create-prd`, `review-code`, `self-heal`) and referenced during test-related `/architecture-review` runs. Extracted from `CLAUDE.md` 2026-04-19 during synthesis 2026-04-19f audit.

## Test Determinism

- **Tests that exist as proof of a specific behavior must use deterministic setup — not mocks, not best-effort fixtures.** (a) Git-manipulation tests: use real `git init` in `tmp_path`, not mock subprocess — mocks pass on semantically wrong ops (2026-03 `git rm --cached` staged a deletion that passed 9/11 tests and code review). (b) ISC-proof tests: never `pytest.skip` on setup races — skipped counts as pass toward PRD completion; use PID files / `tmp_path` / sync primitives, not stdout buffering for inter-process PID capture (2026-04-18 orphan-prevention-oom — a stdout-buffering race would have silently shipped an unverified cascade-kill guarantee).

## Sentinel-Structure Maintenance

- **When changing sentinel structures (PROTECTED_DIR_PREFIXES, COLLECTOR_TYPES, _OPTIONAL_DEFAULTS, any registry/enum set), grep for test assertions on the old values in the same change.** Stale assertions are invisible until a carry-forward or CI run surfaces them.

## Loaded by

- `.claude/skills/quality-gate/SKILL.md` — test deterministic setup gate
- `.claude/skills/implement-prd/SKILL.md` — test authoring phase
- `.claude/skills/create-prd/SKILL.md` — ISC-proof test design
- `.claude/skills/review-code/SKILL.md` — test-discipline review
- `.claude/skills/self-heal/SKILL.md` — before writing regression tests
- `CLAUDE.md` — Context Routing table (Testing/sentinel keyword match)
