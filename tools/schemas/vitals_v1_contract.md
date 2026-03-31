# Vitals JSON Contract — epdev <-> jarvis-app

> Defines the data contract between `vitals_collector.py` (producer) and `jarvis-app/vitals` route (consumer).
> Schema: `tools/schemas/vitals_collector.v1.json`
> Version: 1.0.0

## Data Flow

```
epdev heartbeat (Task Scheduler, 60min)
  -> heartbeat_latest.json (snapshot)
  -> heartbeat_history.jsonl (append)

vitals_collector.py --file
  -> reads heartbeat, skill_usage, overnight, autoresearch, autonomous_value
  -> computes trend_averages from heartbeat_history
  -> writes data/vitals_latest.json

jarvis-app /api/vitals
  -> reads data/vitals_latest.json via configured path
  -> serves to /vitals dashboard route
```

## Fields Consumed by jarvis-app

| Field | Type | Source | Dashboard Card |
|-------|------|--------|----------------|
| `_schema_version` | string | vitals_collector.py | Schema mismatch warning banner |
| `_provenance.collected_at` | ISO datetime | vitals_collector.py | Data freshness indicator |
| `heartbeat.isc_ratio` | metric obj | heartbeat | ISC health gauge |
| `heartbeat.signal_count` | metric obj | manifest DB | Signal counter |
| `heartbeat.signal_velocity` | metric obj | manifest DB | Velocity indicator |
| `heartbeat.autonomous_signal_rate` | metric obj | manifest DB | Autonomous rate |
| `heartbeat.producer_health` | metric obj | manifest DB | Producer status |
| `heartbeat.signal_volume` | metric obj | manifest DB | Volume breakdown |
| `heartbeat.repo_size` | metric obj | disk_usage | Storage gauge |
| `heartbeat_meta.signals` | int/null | heartbeat | Signal delta badges |
| `heartbeat_meta.open_tasks` | int/null | heartbeat | Task count |
| `trend_averages` | object | heartbeat_history | Trend sparklines (future) |
| `autonomous_value` | object | autonomous_value.jsonl | Value rate card |
| `telos_introspection` | object | autoresearch dir | Introspection status |
| `skill_evolution` | object | skills dir scan | Skill maturity card |
| `unmerged_branches` | string[] | git | Unmerged branch alerts |
| `overnight_deep_dive` | object | overnight logs + git | Overnight summary |
| `errors` | string[] | collector errors | Degraded state indicators |

## Metric Object Shape

All `heartbeat.*` fields follow this shape:

```json
{
  "value": <number | null>,
  "unit": "<string>",
  "detail": "<string | null>"
}
```

## Trend Averages Shape

```json
{
  "<metric_name>": {
    "avg": <number>,
    "min": <number>,
    "max": <number>,
    "samples": <integer>
  }
}
```

Key metrics tracked: `isc_ratio`, `signal_velocity`, `signal_count`, `autonomous_signal_rate`, `tool_failure_rate`.

## Versioning Rules

- `_schema_version` follows semver
- **Patch** (1.0.x): new optional fields, detail string changes
- **Minor** (1.x.0): new required fields (jarvis-app must handle gracefully)
- **Major** (x.0.0): breaking shape changes (requires jarvis-app code update)
- jarvis-app validates `_schema_version` on load; mismatch shows warning banner

## Data Sources After 4E-S5 Migration

| Collector | Before (4E-S4) | After (4E-S5) |
|-----------|----------------|---------------|
| signal_count | file_count (glob *.md) | manifest_signal_count (SQLite) |
| signal_velocity | file_count_velocity (mtime) | manifest_signal_velocity (SQLite date) |
| autonomous_signal_rate | rglob + read_text | manifest_autonomous_signal_rate (SQLite source) |
| signal_volume | already manifest | unchanged |
| producer_health | already manifest | unchanged |
