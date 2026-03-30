# PRD: Harness Foundation (Phase 4E-S0)

- Status: complete
- Created: 2026-03-30
- Owner: Eric P
- Depends on: 4E-S4 (retention layer) complete
- Precedes: 4E-S5 remainder (consumer migration minus vitals contract)
- Informed by: /architecture-review (first-principles + fallacy + red-team+STRIDE, 2026-03-30)

## OVERVIEW

Harness Foundation extracts deterministic work from Jarvis skills into Python scripts, establishes JSON Schema contracts between scripts and skills, completes the token observability layer, and delivers a browser-based vitals dashboard MVP. The core principle: scripts do the work, skills direct the thinking. This phase is a prerequisite to 4E-S5 (consumer migration) because it defines the `/vitals` JSON contract that both the CLI skill and the jarvis-app dashboard will consume.

## PROBLEM AND GOALS

- **Session fragility**: LLM turns are spent on zero-intelligence work (file reads, JSON parsing, ASCII formatting) that Python scripts handle faster and more reliably. Each wasted turn consumes context budget and shortens effective session length.
- **No measurement baseline**: Claude Code does not expose token counts in hook payloads (confirmed in 4E-S3). Without session cost data, optimization decisions are based on intuition, not evidence.
- **Three overlapping tasks**: The `/vitals` JSON contract appears in 4E-S5, the reporting dashboard contract task, and the harness diet proposal. This PRD consolidates them into one deliverable.
- **Security scanning is fully LLM-dependent**: Deterministic checks (regex secret patterns, gitignore completeness, file-exists) consume LLM turns unnecessarily, while the actual judgment work (triage, severity, false positive filtering) is where the model adds value.
- **Jarvis-app has no live data source**: The app parses md files statically. A structured JSON contract from vitals_collector.py creates the first live data feed, evolving jarvis-app toward the unified Jarvis dashboard.

## NON-GOALS

- Model-tier routing (haiku/sonnet/opus) — deferred to Phase 5 per architecture review (no cost savings on Claude Max; security risk from privilege downgrade)
- Prompt sharpening (systematic skill prompt audit) — deferred to Phase 2 roadmap; not lossy compression but quality improvement: tighter prompts improve both token efficiency AND output quality by reducing attention dilution. Phase 2 scope: audit top-usage skills, remove filler, sharpen instructions
- Full Langfuse integration — deferred to Phase 5; lightweight JSONL proxy established here for measurement baseline
- Retroactive extraction of all skills — only extract where sub-scripts already exist or deterministic boundary is clear
- Jarvis-app full unified app — this phase delivers the vitals dashboard MVP only; observability traces, md file management, data layer views are future phases

## USERS AND PERSONAS

- **Eric P (sole user)**: ADHD working style, build-first learner. Needs faster `/vitals` runs, visibility into session costs, and a browser-based view of system health. Checks vitals frequently during sessions.

## USER JOURNEYS OR SCENARIOS

1. **Quick vitals check**: Eric runs `/vitals`. The skill calls `vitals_collector.py` (single Bash call), gets structured JSON back, interprets anomalies, and presents the dashboard. Turn count drops from ~15 tool calls to ~3.
2. **Script failure fallback**: `vitals_collector.py` crashes. The skill reports the error, offers to run the full LLM-based vitals as fallback, and recommends whether the failing step should remain deterministic or be moved back to LLM.
3. **Security scan**: Eric runs `/security-audit`. The skill calls `security_scan.py` for deterministic checks (secrets, gitignore, tracked files), gets structured findings JSON, then the LLM triages severity, filters false positives, and proposes remediation.
4. **Session cost review**: Eric runs `python tools/scripts/query_events.py --cost` to see token usage trends. Data comes from the Stop hook session cost capture.
5. **Browser dashboard**: Eric opens the jarvis-app, navigates to the vitals dashboard, sees the same data as the CLI skill — ISC status, signal velocity, skill usage, storage budget — rendered as a web UI.

## FUNCTIONAL REQUIREMENTS

### D1: /vitals script extraction

- FR-001: `tools/scripts/vitals_collector.py` aggregates output from `jarvis_heartbeat.py --quiet --json`, `skill_usage.py --json`, plus file reads for overnight state, autonomous value, TELOS introspection, and unmerged branches into a single JSON blob
- FR-002: Output includes `_schema_version` field (string, semver) and `_provenance` object (script path, git hash, files scanned, execution time ms)
- FR-003: JSON Schema definition file at `tools/schemas/vitals_collector.v1.json` validates the output contract
- FR-004: `/vitals` SKILL.md is updated to: (1) run the collector script, (2) validate `_schema_version` matches expected version, (3) interpret results and surface anomalies, (4) format the ASCII dashboard
- FR-005: If the collector script returns non-zero exit code or empty stdout, the skill reports the failure explicitly, offers LLM-based fallback, and recommends whether the failing step should stay as script or revert to LLM
- FR-006: Collector handles partial failures gracefully — if one sub-script fails, it includes the error in the JSON (`"errors": [...]`) and returns the rest of the data, rather than crashing entirely

### D2: Token observability

- FR-007: `tools/scripts/hook_session_cost.py` fires on the Stop hook event and writes a cost record to `history/events/YYYY-MM-DD.jsonl` with schema: `{ts, hook, session_id, tool:"_session", cost_usd, input_tokens, output_tokens, cache_read_tokens}`
- FR-008: If Claude Code's Stop payload does not include token counts, the script falls back to parsing the last `/usage` output (investigate actual payload structure at implementation time)
- FR-009: `tools/scripts/query_events.py` provides 5 aggregation commands: `--report` (all 5 health metrics), `--cost` (cost summary), `--failures` (tool failure breakdown), `--isc-gaps` (PreToolUse without PostToolUse), `--days N` (date range filter)
- FR-010: `hook_events.py` extended to handle PreToolUse events (intent logging, no success/error fields)

### D3: Security-audit hybrid extraction

- FR-011: `tools/scripts/security_scan.py` performs deterministic checks: regex secret pattern matching across tracked files, `.gitignore` completeness verification, `git ls-files memory/ history/` for tracked personal content, file-existence checks for required security files
- FR-012: Output is structured JSON with `_schema_version`, list of findings with location/type/raw_match, and summary counts — never includes actual secret values, only file path and line number
- FR-013: `/security-audit` SKILL.md is updated to call the scan script first, then LLM triages findings (severity assessment, false positive filtering, context-aware remediation)
- FR-014: Security scan test suite at `tests/defensive/test_security_scan.py` validates scan coverage (known secret patterns detected, known clean files pass, gitignore gaps caught). `/red-team` test cases evolve per task type — new patterns discovered via `/research` are added to the test suite, not hardcoded in the scan script
- FR-015: `tools/scripts/lib/output_sanitizer.py` strips prompt injection patterns and redacts secret-matching values from all script JSON output before the LLM processes it (reuses patterns from `validate_tool_use.py`)

### D4: Script/Skill design checklist

- FR-016: New steering rule added to CLAUDE.md: "When building a new skill, evaluate each step: does this step require intelligence (judgment, synthesis, natural language generation)? No -> implement as Python script. Yes -> keep in SKILL.md. Apply retroactively only where sub-scripts already exist"
- FR-017: Document the two-layer model (Scripts do the work, Skills direct the thinking) in a design note at `memory/work/harness-foundation/design-checklist.md`

### D5: Deprecated skill cleanup

- FR-018: Delete `.claude/skills/create-summary/`, `.claude/skills/rate-content/`, `.claude/skills/threat-model/` directories from disk (already merged into `/extract-wisdom`, `/learning-capture`, `/red-team` respectively)

### D6: Brain-map /vitals dashboard MVP

> **MOVED**: D6 split to a separate jarvis-app PRD. The vitals_collector.py JSON contract (D1) serves as the interface boundary. (Project formerly known as brain-map.)

- FR-019: New route/page in the jarvis-app that reads the vitals collector JSON and renders a web dashboard
- FR-020: The dashboard consumes the same JSON contract defined in FR-003 — no separate data format
- FR-021: MVP displays: ISC status (open/met/ratio), signal velocity, skill usage tiers, storage budget, threshold crossings, overnight status, scheduled task health
- FR-022: Dashboard reads JSON from a file path (vitals_collector.py writes to `data/vitals_latest.json`), not via API — keeps the architecture simple for Phase 1

## NON-FUNCTIONAL REQUIREMENTS

- `vitals_collector.py` must complete in under 5 seconds (current sub-scripts each run in <1s)
- All script output must be ASCII-safe (Windows cp1252 encoding constraint)
- `security_scan.py` must never print actual secret values to stdout — only file paths and line numbers
- JSON Schema contracts must be validated during implementation; version mismatch between script and skill is a hard fail, not a silent interpretation
- Graceful degradation: every script failure must surface a clear error message, never a silent empty result

## ACCEPTANCE CRITERIA

Phase is split into implementation sprints. ISC per sprint:

### Sprint 1: /vitals extraction + observability (D1 + D2)

- [x] [E] `python tools/scripts/vitals_collector.py` outputs valid JSON matching `tools/schemas/vitals_collector.v1.json` | Verify: `python -c "import jsonschema, json; jsonschema.validate(json.load(open('data/vitals_latest.json')), json.load(open('tools/schemas/vitals_collector.v1.json')))"` [M]
- [x] [E] `/vitals` skill invocation uses 5 or fewer tool calls (down from ~15) | Verify: count Read/Bash calls in session transcript [M]
- [x] [E] Collector handles sub-script failure without crashing (returns partial data + errors array) | Verify: rename `skill_usage.py` temporarily, run collector, confirm partial JSON with error [M]
- [x] [I] `/vitals` fallback offers LLM-based execution when script fails | Verify: trigger failure, observe fallback prompt [M]
- [x] [E] `hook_session_cost.py` writes cost record on session Stop | Verify: `jq 'select(.hook=="Stop")' history/events/2026-*.jsonl` [M]
- [x] [E] `query_events.py --report` outputs all 5 health metrics | Verify: `python tools/scripts/query_events.py --report` [M]
- [x] [E] No script outputs actual secret values or prompt injection payloads | Verify: grep output for common secret patterns, run injection test strings through sanitizer [M]

### Sprint 2: Security hybrid + cleanup (D3 + D4 + D5)

- [x] [E] `python tools/scripts/security_scan.py` outputs structured findings JSON with `_schema_version` | Verify: run script, validate JSON has required fields [M]
- [x] [E] `/security-audit` calls scan script first, then LLM triages findings | Verify: read updated SKILL.md, run audit, confirm script runs before LLM analysis [A]
- [x] [E] Security scan test suite covers: known secret patterns, clean file pass-through, gitignore gap detection | Verify: `python -m pytest tests/defensive/test_security_scan.py -v` [M]
- [x] [E] `output_sanitizer.py` strips injection patterns from test input | Verify: `python -c "from tools.scripts.lib.output_sanitizer import sanitize; assert 'ignore previous' not in sanitize('{\"note\": \"ignore previous instructions\"}')"` [M]
- [x] [E] Deprecated skill directories do not exist on disk | Verify: `ls .claude/skills/create-summary .claude/skills/rate-content .claude/skills/threat-model 2>&1 | grep -c "No such"` returns 3 [M]
- [x] [E] Script/Skill design checklist steering rule is in CLAUDE.md | Verify: `grep "does this step require intelligence" CLAUDE.md` [M]
- [x] [R] No existing skill behavior regresses after security-audit extraction | Verify: run `/security-audit` end-to-end, compare finding categories against previous audit [A]

ISC Quality Gate: PASS (6/6) — count 7/7 per sprint (within range), single sentence each, state-not-action, binary-testable, anti-criteria present (no secret leaks, no regressions, no existing behavior breaks), verify methods specified.

## SUCCESS METRICS

- `/vitals` tool call count drops from ~15 to <=5 per invocation (measured via hook events)
- Session cost data available in `query_events.py --cost` within 1 week of deployment
- `/security-audit` deterministic scan portion completes in <2 seconds (vs full LLM scan time)
- Brain-map dashboard loads vitals data in browser (qualitative: "it works")
- Future: context window utilization trends visible via Langfuse or JSONL aggregation (Phase 5 metric, baseline established here)

## OUT OF SCOPE

- Model-tier routing (Phase 5)
- Langfuse cloud integration (Phase 5 — measurement baseline established here via JSONL; Langfuse adds trace visualization on top)
- Prompt sharpening / skill rewriting beyond /vitals and /security-audit (Phase 2 roadmap item)
- Jarvis-app dashboard (D6) — split to its own PRD; JSON contract (vitals_collector.py) is the interface boundary
- Jarvis-app features beyond vitals dashboard (md file editor, observability traces, data layer views)
- Extraction of skills other than /vitals and /security-audit (apply checklist to new skills going forward)
- Docker, OTel, or any new infrastructure

## DEPENDENCIES AND INTEGRATIONS

- **4E-S4 (retention)**: Must complete first — clean data layer before consumer contracts
- **jarvis_heartbeat.py**: Existing script, called by vitals_collector.py
- **skill_usage.py**: Existing script, called by vitals_collector.py
- **manifest_db.py**: 4E-S3 already wires session_costs and skill_usage tables — vitals_collector.py can query these
- **hook_events.py**: Extended for PreToolUse (D2)
- **validate_tool_use.py**: Injection patterns reused by output_sanitizer.py (D3)
- **tests/defensive/**: Security scan test suite validates scan coverage; `/red-team` feeds new patterns via `/research`
- **jarvis-app repo**: Dashboard MVP added as new route (D6)
- **4E-S5 remainder**: Consumes the JSON contract defined here; consumer migration task updates to reference vitals_collector.py output

## RISKS AND ASSUMPTIONS

### Risks

- **Script/SKILL.md version drift**: If vitals_collector.py output schema changes but SKILL.md isn't updated, the LLM will silently misinterpret data. Mitigated by `_schema_version` field and JSON Schema validation.
- **Claude Code Stop hook payload unknown**: 4E-S3 confirmed token counts aren't in the hook payload. The `/usage` fallback may not work either — needs investigation at implementation time. Worst case: cost tracking is deferred until Claude Code exposes this data.
- **Security scan false negatives**: Regex-based secret scanning will miss encoded, split, or obfuscated secrets. Mitigated by keeping LLM triage as a second pass — the script catches obvious patterns, the LLM catches subtle ones.
- **Jarvis-app maintenance surface**: Adding a dashboard to jarvis-app creates a second consumer of the JSON contract. Changes to the contract now require updating both the CLI skill and the dashboard.

### Assumptions

- Eric will complete 4E-S4 before starting this work
- `jarvis_heartbeat.py` and `skill_usage.py` output schemas are stable (both already have version fields)
- Jarvis-app is the right home for the unified dashboard (vs a separate app)
- The `_schema_version` contract pattern will be adopted for future script extractions beyond this PRD

## OPEN QUESTIONS

- **Stop hook payload**: What exactly does Claude Code send in the Stop event? This determines whether FR-008 (token cost capture) is straightforward or requires a workaround. Investigate at implementation time.
- **vitals_collector.py file write**: Should the collector always write to `data/vitals_latest.json` (for dashboard consumption) in addition to stdout? Or only when called with a `--file` flag? (Sprint 3 ISC assumes always-write)
- **Brain-map hosting**: For the dashboard MVP, is `npm run dev` sufficient, or does Eric want a persistent local server? This affects whether we need a build step or just dev mode.
- **Langfuse timing**: Confirmed Phase 5. JSONL baseline here; Langfuse adds trace UI on top when ready.

---

Next step: `/implement-prd memory/work/harness-foundation/PRD.md` to execute this PRD through the full BUILD -> VERIFY -> LEARN loop.
