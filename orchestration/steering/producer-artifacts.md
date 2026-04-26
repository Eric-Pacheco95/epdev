# Producer Artifact Paths

> Canonical on-disk locations for autonomous producer state, history, and provenance artifacts. Prevents orphan-path bugs (writes that drift to a second location, leaving readers and writers out of sync).

## Canonical paths

| Artifact | Path | Owner |
|----------|------|-------|
| Heartbeat snapshot (latest) | `memory/work/isce/heartbeat_latest.json` | `tools/scripts/jarvis_heartbeat.py` |
| Heartbeat history (append-only) | `memory/work/isce/heartbeat_history.jsonl` | `tools/scripts/jarvis_heartbeat.py` |
| Manifest DB (signal velocity / dedup / producer_health) | `data/jarvis_index.db` | `tools/scripts/manifest_db.py` |
| Producer report (ISC) | `data/isc_producer_report.json` | `tools/scripts/isc_producer.py` |
| Overnight rotation state | `data/overnight_state.json` | `tools/scripts/overnight_runner.py` |
| Overnight summary (per-day) | `data/overnight_summary/YYYY-MM-DD.{json,md}` | `tools/scripts/consolidate_overnight.py` |
| Dispatcher mutex | `data/dispatcher.lock` | `tools/scripts/jarvis_dispatcher.py` |
| Global claude -p mutex | `data/claude_session.lock` | `tools/scripts/lib/worktree.py` |
| Paradigm health report | `data/paradigm_health.json` | `tools/scripts/paradigm_health.py` |

## Rules

1. **One write path per artifact.** Only the script listed in the "Owner" column writes to that path. Readers must point at the canonical path, not a guess.
2. **No legacy duplicates.** If a path moves, delete the old file in the same commit — never leave both. `memory/work/jarvis/heartbeat_history.jsonl` was an orphan from before the `isce/` consolidation; deleted 2026-04-25.
3. **`data/` for state, `memory/work/<owner>/` for content.** Volatile rotation/lock/run state lives under `data/` (gitignored). Append-only history that is part of the learning loop lives under `memory/work/<producer>/` (also gitignored, but logically content).
4. **Update this table when adding a producer.** PR that introduces a new state file must update this doc and the routing in `vitals_collector.py` / `paradigm_health.py` if the artifact gates a health check.

## Why

2026-04-25 vitals investigation found two heartbeat history files: `memory/work/jarvis/heartbeat_history.jsonl` (102 bytes, last write 2026-03-27) and `memory/work/isce/heartbeat_history.jsonl` (12 MB, current). Reader paths (`vitals_collector.py:31`, `rotate_heartbeat.py:26`, `jarvis_heartbeat.py:20`) all already pointed at `isce/`; the `jarvis/` file was a one-line orphan from a pre-consolidation run. Cost: investigation cycle to figure out which was canonical. This doc removes that ambiguity for future producers.
