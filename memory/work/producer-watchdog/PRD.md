# PRD: Producer Registry + Zero-Execution Watchdog

**Project:** Jarvis AI Brain — Phase 5C Sprint 2
**Status:** READY FOR IMPLEMENTATION
**Last updated:** 2026-04-04
**Architecture review:** Completed (3 Sonnet agents — first-principles + fallacy + red-team, 2026-04-04)

---

## OVERVIEW

A minimal producer registry and zero-execution watchdog that makes silent autonomous producer failures detectable and actionable. When a scheduled producer (overnight runner, dispatcher, research producer, etc.) stops executing without error — due to security gate blocks, PATH issues, or other silent failures — the heartbeat detects it within one alert cycle, sends a Slack alert to `#jarvis-decisions`, and sets a suspend flag that a BAT wrapper checks before allowing the producer to run again. New producers are enrolled via a registry entry requirement baked into the PRD ISC process.

---

## PROBLEM AND GOALS

- **Silent failure is indistinguishable from correct idle behavior** — the dispatcher ran for 14+ days with zero executions, no error log, and no alert (root cause: `||` in ISC verify commands blocked by sanitizer)
- **New producers can be wired without monitoring enrollment** — no mechanism ensures future sprints register producers in any watchdog
- **API usage burns on broken producers** — a suspended or broken producer keeps consuming Task Scheduler quota and API calls with no useful output
- Goal: Any producer silent for longer than its threshold triggers a Slack alert + suspend within one heartbeat cycle
- Goal: Enrollment of new producers is enforced at PRD/ISC authoring time, not discovered at failure time
- Goal: Suspension actually prevents autonomous execution (not just a flag nobody reads)

---

## NON-GOALS

- Lint gate based on file naming conventions — naming is already inconsistent (`dream.py`, `jarvis_autoresearch.py` don't match `*_runner/*_producer` patterns); deferred to Sprint 3 after naming is standardized
- Output-side monitoring (did the producer produce _useful_ output, not just run) — requires per-producer output schema knowledge; deferred until 15+ runs provide calibration data
- Windows Task Scheduler API integration — suspend works via BAT wrapper file check, not scheduler XML mutation
- Multi-repo producer tracking — only epdev producers in scope

---

## USERS AND PERSONAS

- **Eric (primary):** Receives `#jarvis-decisions` Slack alert when a producer is suspended; reviews and either fixes the root cause or manually clears the suspend file to re-enable
- **Jarvis heartbeat:** Reads registry, checks producer recency, sets suspend signal, sends alert
- **Autonomous producers:** Each checks for a sentinel file at startup before executing

---

## USER JOURNEYS OR SCENARIOS

1. Overnight runner fails silently for 2 days → heartbeat reads `producers.json`, checks `data/overnight_state.json` → `last_run_date` field, sees it's 48h+ stale → writes `data/producers/overnight_runner.suspend`, sends Slack alert to `#jarvis-decisions` → next Task Scheduler invocation of `run_overnight.bat` calls `check_suspend.py`, finds sentinel file, exits with message "overnight_runner suspended — check #jarvis-decisions"
2. Eric diagnoses root cause, fixes it → deletes `data/producers/overnight_runner.suspend` → producer runs normally on next schedule; heartbeat clears the stale alert
3. New producer PRD is written → ISC items must include "Entry for `<name>` exists in `orchestration/producers.json`" as a required criterion per steering rule → `/implement-prd` verifies the entry before marking the ISC PASS

---

## FUNCTIONAL REQUIREMENTS

- FR-001: `orchestration/producers.json` exists with one entry per active producer: `name`, `state_file` (path), `state_key` (JSON key containing ISO datetime, or `"file_mtime"` for non-JSON state), `alert_threshold_hours` (int), `first_run_grace_until_utc` (ISO datetime, suppresses alerts during first deployment)
- FR-002: A new `producer_recency` collector type is implemented in `tools/scripts/jarvis_heartbeat.py` that reads each producer's state value, parses it as an ISO datetime, computes age in hours, and emits WARN or CRIT if age exceeds `alert_threshold_hours`
- FR-003: `heartbeat_config.json` contains one `producer_recency` collector entry per registered producer, wired to its `producers.json` entry
- FR-004: When a `producer_recency` collector exceeds its threshold, heartbeat writes a sentinel file `data/producers/{name}.suspend` AND sends a Slack alert to `#jarvis-decisions` with producer name and hours since last run
- FR-005: `tools/scripts/check_suspend.py` checks for `data/producers/{name}.suspend` and exits non-zero with a clear message if found; each producer's BAT wrapper calls this before invoking the Python script
- FR-006: `orchestration/producers.json` is added to `AUTONOMOUS_BLOCKED_PATHS` in `security/validators/validate_tool_use.py` and noted in `security/constitutional-rules.md` Layer 5
- FR-007: Slack re-alert for a suspended producer is capped at once per 24 hours (not on every heartbeat cycle) using the existing heartbeat `min_delta` pattern
- FR-008: `data/producers/` directory is created with a `.gitkeep`; suspend sentinel files are gitignored

---

## NON-FUNCTIONAL REQUIREMENTS

- All new Python must be ASCII-safe output (Windows cp1252)
- `producer_recency` collector must handle missing state files gracefully: emit WARN (not crash) if `state_file` path doesn't exist, with message "state file not found — producer may never have run"
- `check_suspend.py` must be callable from CMD/BAT without Python PATH issues (use absolute path in BAT, same pattern as existing `run_heartbeat.bat`)
- `first_run_grace_until_utc` must be set to 48h from registration date for all initial entries on first deployment; prevents false positives on day 1
- Bootstrap: on first deployment, all 6 current producers are registered simultaneously; none should alert before their grace period expires

---

## ACCEPTANCE CRITERIA

### Phase 1: Registry + Watchdog

- [x] `orchestration/producers.json` exists with entries for all 6 current producers: overnight_runner, jarvis_dispatcher, jarvis_heartbeat, research_producer, jarvis_autoresearch, slack_poller | Verify: Read | [E] | [M] | model: haiku
- [x] `producer_recency` collector type in `jarvis_heartbeat.py` reads `state_key` from `state_file`, parses ISO datetime, emits WARN at threshold | Verify: CLI | [E] | [M] | model: sonnet
- [x] Heartbeat writes `data/producers/{name}.suspend` sentinel file when a producer exceeds its `alert_threshold_hours` | Verify: CLI | [E] | [M] | model: sonnet
- [x] `check_suspend.py` exits non-zero with message when sentinel file exists for the named producer | Verify: CLI | [E] | [M] | model: sonnet
- [x] Each active producer BAT wrapper (`run_overnight.bat`, `run_dispatcher.bat`, etc.) calls `check_suspend.py` before invoking the Python script | Verify: Grep | [E] | [M] | model: haiku
- [x] `orchestration/producers.json` is listed in `AUTONOMOUS_BLOCKED_PATHS` in `validate_tool_use.py` | Verify: Grep | [E] | [M] | model: haiku
- [x] No producer with a valid `first_run_grace_until_utc` in the future emits a WARN or CRIT from the `producer_recency` collector | Verify: CLI | [E] | [M] | anti-criterion

ISC Quality Gate: PASS (6/6)

---

## SUCCESS METRICS

- Zero silent producer failures lasting 48h+ without a Slack alert within 30 days of deployment
- All new producers added in Sprint 3+ have a `producers.json` entry as a verified ISC item (verifiable via PRD history)
- No false-positive alerts within the first 48h of deployment (grace period working)

---

## OUT OF SCOPE

- Lint gate based on naming conventions (deferred to Sprint 3)
- Output-side useful-output monitoring (deferred until 15+ run data)
- Windows Task Scheduler XML mutation for suspend
- Multi-repo producer tracking

---

## DEPENDENCIES AND INTEGRATIONS

- `tools/scripts/jarvis_heartbeat.py` — new `producer_recency` collector type added
- `heartbeat_config.json` — 6 new collector entries (one per producer)
- `orchestration/producers.json` — new file (authoritative producer registry)
- `security/validators/validate_tool_use.py` — `AUTONOMOUS_BLOCKED_PATHS` addition
- `security/constitutional-rules.md` — Layer 5 write-protection note
- `run_overnight.bat`, `run_dispatcher.bat`, `run_heartbeat.bat`, and equivalents — `check_suspend.py` call added
- Slack `#jarvis-decisions` channel — alert destination (existing integration)
- `data/producers/` directory — new, gitignored sentinel files

---

## RISKS AND ASSUMPTIONS

**Risks:**
- `dream.py` and `jarvis_autoresearch.py` write state to non-standard locations (`data/dream_last_run.txt` text file, unclear for autoresearch) — `state_key: "file_mtime"` fallback handles text files but is less robust than JSON key reads
- Slack poller state is keyed by channel ID (`C0ANYP16PE3`), not a top-level `last_run` key — state_key path may need dot-notation (`C0ANYP16PE3.last_run`) or a sentinel field added to slack_poller_state.json
- `jarvis_dispatcher.py` writes to `data/dispatcher_runs/` directory (per-run JSONs), not a single state file — will need a wrapper that reads the latest file in the directory or a `last_run_utc` field added to dispatcher on each run

**Assumptions:**
- All producer BAT wrappers already exist (confirmed: `run_heartbeat.bat`, `run_dispatcher.bat` exist); missing ones created as part of this sprint
- `check_suspend.py` can be called from BAT before Python is invoked (Python is on PATH in the BAT execution context)
- Slack integration (`slack_notify.py`) is available and working for `#jarvis-decisions` alerts

---

## OPEN QUESTIONS

- `slack_poller_state.json` structure — does it have a top-level `last_run` field or does it need one added? (check before implementing FR-001 for that entry)
- `jarvis_autoresearch.py` state file location — confirm path and key before registering it
- `jarvis_dispatcher.py` state strategy — add `last_run_utc` field to the latest `dispatcher_runs/*.json` report, or write a separate `data/dispatcher_state.json`? (recommendation: add field to dispatcher on each run completion)
