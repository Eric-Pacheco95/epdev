# PRD-B: Model-Agnostic Routing Layer

- Version: 1.0
- Author: Jarvis / Eric P
- Date: 2026-04-03
- Status: complete -- all 8 ISC verified 2026-04-03
- Depends on: PRD-A (local_model.py + local_model_router.py — shipped 2026-04-03)

---

## OVERVIEW

PRD-B wires the local model tier (PRD-A) into two primary consumers: the `/validation` skill and the autonomous dispatcher. It adds a `--normal` flag to `/validation` that routes ISC format checking, output structure validation, and code review (normal severity) through the local Ollama model instead of full cloud inference. It also makes `jarvis_dispatcher.py` fully model-agnostic by intercepting `"local"` as a valid `model` task field value and routing to `call_local()` rather than `claude -p`. Finally, it adds optional per-dimension model hints to the overnight runner so individual overnight dimensions can declare their preferred model tier.

---

## PROBLEM AND GOALS

- `/validation` currently runs every check through `isc_validator.py` with no cost-tier differentiation — structured format checks (ISC quality gate, output schema, code lint) cost the same as judgment tasks
- The dispatcher's `resolve_model()` returns `"local"` correctly from a task's `model` field, but then passes it directly to `claude -p --model local`, which fails (unknown model)
- The overnight runner has no mechanism for per-dimension model selection — all dimensions default to Opus regardless of task complexity
- Goal: route structured, deterministic checks to local model; keep judgment, security, and architecture tasks on Opus/Codex

---

## NON-GOALS

- `/validation --deep` with Codex adversarial review (PRD-C scope)
- Replacing the `isc_validator.py` script — it remains the execution engine; this PRD adds a routing layer on top
- Automatic Ollama startup — if Ollama is unavailable, silent fallback to Sonnet applies (from PRD-A)
- Overnight runner dimension-level ISC or scheduling changes (config shape only)

---

## USERS AND PERSONAS

- **Eric (operator)**: invokes `/validation --normal` for fast, cheap format checks during interactive builds
- **Autonomous dispatcher**: selects model via task `model` field; `"local"` routes to Ollama
- **Overnight runner**: reads optional per-dimension `model` hint to select appropriate tier per dimension

---

## USER JOURNEYS OR SCENARIOS

1. Eric runs `/validation --normal memory/work/foo/PRD.md` — ISC format gate, output structure check, and code review (normal severity) run via local model; result appears in <10s; no Codex call made
2. Dispatcher picks up a `task_classification` task with `"model": "local"` — routes to `call_local()`, worktree not created, result returned inline
3. Overnight runner executes `scaffolding` dimension (Sonnet-appropriate) — reads `"model": "sonnet"` from dimension config, passes it to dispatcher; `knowledge_synthesis` dimension (Opus-appropriate) uses default
4. Ollama is stopped; Eric runs `/validation --normal` — local fallback fires, Sonnet handles the check, `data/local_routing.log` records the fallback; Eric sees no error

---

## FUNCTIONAL REQUIREMENTS

- FR-001: Add `--normal` flag to `/validation` SKILL.md DISCOVERY syntax and parameter list
- FR-002: `--normal` STEPS route ISC format gate, output structure check, and code review (normal severity only — no Critical/High re-review loop) to `call_local()` from `tools/scripts/local_model.py`
- FR-003: `--normal` steps explicitly document that Codex adversarial review is NOT invoked
- FR-004: When `call_local()` raises `LocalModelUnavailable` in `--normal` mode, catch and silently re-route to Sonnet via the existing `fallback_model` mechanism; log to `data/local_routing.log`
- FR-005: `jarvis_dispatcher.py` — in `run_task()`, after `resolve_model()`, add a branch: if `model == "local"`, call `call_local(prompt, task_type)` and skip `claude -p` subprocess entirely
- FR-006: If `model == "local"` but task has a never_local tag (`security`, `tier_0`, `architecture`, `identity`), reroute to Sonnet and log the override — the local_model_router.py `route()` function enforces this; dispatcher must call `route()` before executing
- FR-007: `resolve_model()` self-tests (lines 1440-1443 in jarvis_dispatcher.py) must include `"local"` as an explicit valid value
- FR-008: `overnight_runner.py` reads an optional `model` key from each dimension's config block and forwards it as the task's `model` field when enqueuing dimension tasks

---

## NON-FUNCTIONAL REQUIREMENTS

- `/validation --normal` must complete ISC format gate in < 30s on a running Ollama instance
- Dispatcher `"local"` branch must not create a git worktree (local tasks are stateless inference only)
- All local model calls use `urllib.request` only — no subprocess, no cp1252 encoding path (inherited from PRD-A)
- Fallback logging must not expose prompt content in `data/local_routing.log` — log task_type and timestamp only

---

## ACCEPTANCE CRITERIA

- [x] [E] `validation/SKILL.md` DISCOVERY section lists `--normal` flag with description and example | Verify: `grep -c "\-\-normal" .claude/skills/validation/SKILL.md` returns >= 2 [M]
- [x] [E] `--normal` STEPS reference `call_local()` or `local_model` for ISC format, structure, and code review routing | Verify: `grep -c "call_local\|local_model" .claude/skills/validation/SKILL.md` returns >= 1 [A]
- [x] [E] `--normal` STEPS explicitly state Codex adversarial review is not invoked | Verify: Read `--normal` steps in SKILL.md; confirm no Codex invocation or adversarial routing in that branch [A]
- [x] [E] `jarvis_dispatcher.py` contains a branch on `model == "local"` that calls `call_local()` and skips `claude -p` | Verify: `grep -n '"local"' tools/scripts/jarvis_dispatcher.py` shows conditional routing branch [M]
- [x] [E] `resolve_model()` self-tests include assertion for `"local"` explicit model value | Verify: `grep -n "local" tools/scripts/jarvis_dispatcher.py` shows `resolve_model({"model": "local"}) == "local"` assertion [M]
- [x] [R] A task with `"model": "local"` AND a `security` tag routes to Sonnet, not local | Verify: add self-test `resolve_model_with_tags({"model": "local"}, ["security"]) != "local"` to dispatcher self-tests [M]
- [x] [E] Fallback from local to Sonnet appends an entry to `data/local_routing.log` when Ollama unavailable | Verify: stop Ollama, invoke dispatcher with `"model": "local"` task, confirm log entry written [M]
- [x] [E] `overnight_runner.py` reads optional `model` key from dimension config and sets it on enqueued tasks | Verify: `grep -n "model" tools/scripts/overnight_runner.py` shows dimension config read and task field set [M]

ISC Quality Gate: PASS (6/6) — 8 criteria (within range), single sentence each, state-not-action, binary-testable, anti-criterion present (ISC 6: security tag overrides local), verify methods specified.

---

## SUCCESS METRICS

- `/validation --normal` API cost reduced vs current (no cloud call for format-only checks when Ollama running)
- Dispatcher successfully executes at least one `"model": "local"` task from backlog within 1 overnight run after deployment
- Zero `Unknown model` errors in dispatcher logs after deployment

---

## OUT OF SCOPE

- `/validation --deep` Codex adversarial integration (PRD-C)
- New overnight dimension definitions or scheduling changes
- Haiku as a routing target (PRD-A scope only covers local + claude tiers; Haiku routing is unchanged)

---

## DEPENDENCIES AND INTEGRATIONS

- **PRD-A** (shipped 2026-04-03): `tools/scripts/local_model.py`, `tools/scripts/local_model_router.py`, `local_model_config.json` — all must be present
- **`jarvis_dispatcher.py`**: `resolve_model()` at line 384, `run_task()` at line 789, self-tests at lines 1440-1443
- **`overnight_runner.py`**: dimension config structure (exact key name TBD in BUILD)
- **`validation/SKILL.md`**: DISCOVERY, Step 0, and STEPS sections require updates

---

## RISKS AND ASSUMPTIONS

**Risks:**
- Dispatcher `"local"` branch skips worktree creation — tasks that write files would fail silently; mitigation: only `autonomous_safe: true` + stateless task types should use `"local"`
- Overnight dimension model hints require config schema agreement — if dimension config structure changes, hints silently drop

**Assumptions:**
- PRD-A is in main branch and importable from dispatcher (confirmed: committed 2026-04-03)
- `call_local()` is safe to call from dispatcher process context (no session contention — it uses urllib, not claude CLI)
- Ollama is the only local provider in scope; `"local"` is synonymous with Ollama/call_local for PRD-B

---

## OPEN QUESTIONS

- What is the exact key name for dimension model hints in `overnight_runner.py` dimension configs? (resolve in BUILD by reading current config structure)
- Should dispatcher `"local"` tasks write their output to a file or return inline? (assume inline for PRD-B; file output is PRD-C scope)
- Should `resolve_model_with_tags()` be a new function or merged into `resolve_model(task)` by reading task tags? (resolve in BUILD)
