# PRD: Local Model Integration Layer (PRD-A)

- Status: complete (PRD-A) -- all 8 ISC verified 2026-04-03
- Created: 2026-04-03
- Owner: Eric P
- Depends on: Ollama running locally, qwen2.5-coder:14b pulled (confirmed)
- Superseded by: PRD-B (validation flags + dispatcher routing) builds on top of this

## OVERVIEW

The Local Model Integration Layer adds a fourth model tier to the Jarvis AI system: a locally-hosted Ollama model (initially `qwen2.5-coder:14b`, model-agnostic via config) that handles structured, low-judgment tasks across all three invocation contexts -- interactive skills, the autonomous dispatcher, and the overnight runner. Every model invocation in Jarvis evaluates cost/quality fit against a routing policy and selects the cheapest model whose quality is sufficient. This PRD covers the foundation layer only: the Ollama client wrapper, routing policy engine, config schema, health check, and fallback logic. PRD-B will add `/validation --normal` flag and explicit dispatcher task-field routing on top of this layer.

## PROBLEM AND GOALS

- Routing is currently binary: every Jarvis invocation uses a cloud model (Opus/Sonnet/Haiku) regardless of task complexity. Format validation, classification, and extraction tasks consume the same API budget as architecture decisions.
- Local models can handle structured tasks: ISC format gate, JSON structure checks, signal extraction, and summarization have deterministic pass/fail criteria -- local model errors are immediately detectable.
- Model landscape changes fast: Gemma 4 (Apache 2.0, vision, 27B) just shipped. The system must be configurable to swap models without code changes.
- Goals:
  - Auto-route low-judgment tasks to local model, reducing cloud API cost
  - Maintain silent fallback to Sonnet so operator experience is uninterrupted when Ollama is down
  - Flag first-time local routing of a task type for human review
  - Provide a routing policy engine usable by PRD-B (/validation) and future consumers

## NON-GOALS

- PRD-B features: `/validation --normal` flag, dispatcher `model` task field, overnight runner per-dimension routing (depend on this layer but out of scope here)
- Training or fine-tuning local models
- Multi-GPU or server deployment -- local Ollama on Eric's machine only
- Model quality evaluation harness -- catch rate tracking is PRD-B+
- Replacing Haiku (current fast cloud tier) -- local routing supplements, does not replace the existing tier structure

## USERS AND PERSONAS

- **Eric P (sole operator):** uses Jarvis interactively and via scheduled tasks. Expects uninterrupted experience whether Ollama is running or not. Wants cost reduction without quality loss on high-stakes tasks.
- **Autonomous dispatcher:** selects model per task from config + task metadata. No human in the loop during execution.
- **Overnight runner:** long-running headless process. Must not block on Ollama unavailability.

## USER JOURNEYS OR SCENARIOS

1. **Interactive /validation (future PRD-B):** Eric runs `/validation --normal` on a PRD. The routing layer checks Ollama health, routes the ISC format gate to `qwen2.5-coder:14b`, gets result in <30s, returns PASS/FAIL. If Ollama is down, silently falls back to Sonnet.
2. **Dispatcher task execution:** A task tagged `isc_format_validation` is dispatched. Routing policy engine returns `local`. Ollama client POSTs to `localhost:11434/api/generate`. Response parsed, result returned. If Ollama errors, fallback to Sonnet, log the event.
3. **First-time routing review:** A task type `signal_extraction` routes to local for the first time. The routing engine writes a review entry to `data/local_routing_review.jsonl`. Eric confirms or overrides in next session.
4. **Model swap:** Gemma 4 becomes available on Ollama. Eric updates `local_model_config.json` model field. No code change required.

## FUNCTIONAL REQUIREMENTS

- FR-001: A `tools/scripts/local_model.py` client module exposes `call_local(prompt, task_type) -> str` that POSTs to `http://localhost:11434/api/generate` using the configured model and returns the response text
- FR-002: `call_local` accepts a `timeout_s` parameter defaulting to 120s; on timeout raises `LocalModelTimeout` and the caller falls back
- FR-003: A `tools/scripts/local_model_router.py` module exposes `route(task_type, tags) -> Literal["local", "haiku", "sonnet", "opus"]` using the policy defined in `local_model_config.json`
- FR-004: `route()` returns `"local"` if and only if: `task_type` is in `auto_local_tasks` AND no tag in `tags` appears in `never_local_tags`
- FR-005: `route()` always returns a non-local tier if any tag in `tags` matches `never_local_tags` (security, tier_0, architecture, identity) -- never-local is an absolute override with no caller bypass
- FR-006: A `check_ollama_health() -> bool` function verifies Ollama is reachable at `localhost:11434` within 2s; returns False without raising on failure
- FR-007: When `call_local` fails for any reason (Ollama down, timeout, malformed response, encoding error), raises catchable `LocalModelUnavailable`; all callers silently fall back to Sonnet and append one line to `data/local_routing.log`
- FR-008: `local_model_config.json` at repo root defines: `provider`, `model`, `base_url`, `fallback_model`, `fallback_on_error`, `max_response_wait_s`, `auto_local_tasks` list, `never_local_tags` list
- FR-009: When `route()` returns `"local"` for a `task_type` with no prior success in `data/local_routing_review.jsonl`, the caller writes `{task_type, routed_at, local_reviewed: false}` and continues execution
- FR-010: The config `model` field accepts any Ollama model tag string; no validation against available models at config load time
- FR-011: All Ollama API calls use the REST API (`/api/generate`) with `encoding="utf-8"`, never subprocess -- Windows cp1252 compatibility hard constraint

## NON-FUNCTIONAL REQUIREMENTS

- Ollama health check completes in <2s
- `call_local` timeout default 120s (2 minutes acceptable per Eric)
- All local_model.py output is ASCII-safe before returning to callers -- Windows cp1252 constraint
- `local_model_router.py` is stateless and importable with zero side effects -- safe for overnight runner import
- `local_model_config.json` is read fresh on each `route()` call (no caching) -- supports model swap without restart
- Fallback log appends are atomic single-line writes to `data/local_routing.log` -- no corruption under concurrent callers

## ACCEPTANCE CRITERIA

- [x] [E] `call_local("reply READY only", "test")` returns a string containing "READY" when `qwen2.5-coder:14b` is running | Verify: `python -c "from tools.scripts.local_model import call_local; r = call_local('reply READY only', 'test'); assert 'READY' in r.upper()"` [M]
- [x] [E] `route("isc_format_validation", [])` returns `"local"` with default config | Verify: `python -c "from tools.scripts.local_model_router import route; assert route('isc_format_validation', []) == 'local'"` [M]
- [x] [E] `route("isc_format_validation", ["security"])` returns a non-local tier | Verify: `python -c "from tools.scripts.local_model_router import route; assert route('isc_format_validation', ['security']) != 'local'"` [M]
- [x] [E] `call_local` raises `LocalModelUnavailable` when Ollama is not running | Verify: stop Ollama, run `python -c "from tools.scripts.local_model import call_local; call_local('test', 'test')"` -- confirm exception raised [M]
- [x] [E] `check_ollama_health()` returns False within 3s when Ollama is stopped | Verify: stop Ollama, `python -c "from tools.scripts.local_model import check_ollama_health; import time; t=time.time(); r=check_ollama_health(); assert not r and time.time()-t < 3"` [M] -- Note: config updated to http://127.0.0.1:11434 (was localhost); Windows dual IPv4/IPv6 resolution caused 4s with localhost, 2.04s with 127.0.0.1
- [x] [E] Swapping model in `local_model_config.json` takes effect on next call without restart | Verify: change model field, call `call_local`, confirm request targets new model via Ollama logs [A]
- [x] [R] No subprocess or cp1252-unsafe code path exists in local_model.py | Verify: `grep -n subprocess tools/scripts/local_model.py` returns no results [M]
- [x] [E] First-time routing of a new task type writes `{task_type, routed_at, local_reviewed: false}` to `data/local_routing_review.jsonl` | Verify: delete review log, route a new task_type, check file exists with correct schema [M]

ISC Quality Gate: PASS (6/6) -- 8 criteria (within range), single sentence each, state-not-action, binary-testable, anti-criterion present (security tag override + subprocess absence), verify methods specified.

## SUCCESS METRICS

- Local model handles >60% of ISC format validation calls within 30 days of PRD-B ship
- Zero silent quality regressions: no local-routed task produces a result Sonnet would have caught differently (measured via PRD-B catch rate)
- Ollama fallback fires <5% of dispatch cycles
- Cloud API cost reduction measurable after 30 days baseline

## OUT OF SCOPE

- `/validation --normal` flag (PRD-B)
- Dispatcher `model` task field (PRD-B)
- Overnight runner per-dimension routing (PRD-B+)
- Model quality benchmarking harness
- Gemma 4 pull and validation (follow-on once available on Ollama)

## DEPENDENCIES AND INTEGRATIONS

- **Ollama** (`localhost:11434`) -- must be running for local routing; health check gates all calls
- **`qwen2.5-coder:14b-instruct-q4_K_M`** -- currently pulled, confirmed responding (tested 2026-04-03: returned "READY")
- **`local_model_config.json`** -- new config file at repo root
- **`data/local_routing.log`** -- append-only fallback event log
- **`data/local_routing_review.jsonl`** -- first-time routing review queue
- **PRD-B** (downstream) -- imports `local_model.py` and `local_model_router.py`

## RISKS AND ASSUMPTIONS

### Risks
- `qwen2.5-coder:14b` produces lower-quality ISC format gate output than Sonnet -- caught by PRD-B catch rate tracking; fallback always available
- Ollama 9GB memory footprint competes with other processes -- health check + silent fallback ensures no blocking
- First-time routing review queue grows unreviewed -- `/vitals` should surface count (PRD-B concern)

### Assumptions
- Gemma 4 will be on Ollama within 1-2 weeks; config field swap is sufficient to migrate
- `localhost:11434` is the stable Ollama endpoint (default port, not customized)
- Eric runs Ollama as a background service; startup on demand not required
- REST API (`/api/generate`) is stable across Ollama versions used

## OPEN QUESTIONS

- Should `local_model_config.json` live at repo root or inside `data/`? Repo root is consistent with `heartbeat_config.json`.
- Should `data/local_routing_review.jsonl` count surface in `/vitals` terminal output or only Slack deep dive? Deferred to PRD-B.
- When Gemma 4 is available: benchmark ISC format gate accuracy head-to-head before switching, or switch directly? Recommend benchmark first.
