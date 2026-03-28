# Heartbeat Config Reference

Configuration file for the Jarvis ISC Engine heartbeat (`tools/scripts/jarvis_heartbeat.py`).

## Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | int | 1 | Config schema version |
| `root_dir` | string | `"."` | Repository root. Absolute or relative (resolved to repo root). |
| `snapshot_dir` | string | `"memory/work/isce"` | Where to write heartbeat_latest.json and history JSONL |
| `signal_output_dir` | string | `"memory/learning/signals"` | Where auto-signals are written on threshold crossing |
| `cooldown_minutes` | int | 60 | Minimum time between auto-signals for the same metric |

## Collectors

Each entry in the `collectors` array defines one metric to collect.

### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique metric name (used in snapshot keys) |
| `type` | string | yes | Collector type (see types below) |
| `thresholds` | object | no | Threshold config for severity evaluation |

### Threshold Fields

| Field | Description |
|-------|-------------|
| `warn_above` | WARN when value >= this |
| `warn_below` | WARN when value <= this |
| `crit_above` | CRIT when value >= this |
| `crit_below` | CRIT when value <= this |

CRIT is evaluated before WARN. If no thresholds, severity is always OK.

### Collector Types

#### `file_count`
Count files matching extension in a directory.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Directory path (relative to root_dir or absolute) |
| `ext` | string | `".md"` | File extension to count |

#### `file_count_velocity`
Files per day over a rolling window (uses file mtime).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Directory path |
| `ext` | string | `".md"` | File extension |
| `window_days` | int | 7 | Rolling window size |

#### `checkbox_count`
Count open checkboxes (`- [ ]`) in a markdown file.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Path to markdown file |

#### `checkbox_delta`
Task completion velocity via snapshot diff. Requires `open_task_count` in previous snapshot.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Path to tasklist markdown file |
| `window_days` | int | 7 | Window label (actual delta is between runs) |

#### `prd_checkbox`
Count ISC checkboxes across PRD files. Skips fenced code blocks.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prd_glob` | string | `"memory/work/*/PRD.md"` | Glob pattern for PRD files |
| `checkbox_state` | string | `"open"` | `"open"` for `[ ]`, `"met"` for `[x]` |

#### `derived`
Computed from other collector results in the same run.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | required | Human-readable formula (implementation is hardcoded per name) |

Currently supported: `isc_ratio` (isc_met / (isc_met + isc_open)).

#### `query_events`
Pull a field from `query_events.py --json` subprocess output. Subprocess is called once and cached per run.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `field` | string | same as `name` | JSON key to extract from query_events output |

#### `file_recency`
Days since the newest file was modified in a directory (or since a single file was modified).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | File or directory path |
| `ext` | string | `".md"` | Extension filter (for directories) |

#### `dir_count`
Count subdirectories in a directory.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Directory path |

#### `disk_usage`
Directory size in MB (recursive).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | File or directory path |

#### `hook_output_size`
Run a hook script and measure stdout character count.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hook_script` | string | required | Path to Python script |

## Alert Routing

```json
"alert_routing": {
  "stdout": { "min_severity": "INFO" },
  "slack": { "min_severity": "WARN", "channel": "#epdev" },
  "ntfy": { "min_severity": "CRIT", "topic": "jarvis" }
}
```

Channels are optional. Remove `slack` or `ntfy` keys to disable those channels. `stdout` is always available.

Severity levels: OK < INFO < WARN < CRIT.

## Daily Alert Caps

```json
"daily_alert_caps": { "slack": 20, "ntfy": 5 }
```

Prevents alert fatigue. Tracked in `alert_counts.json` (resets daily).

## Retention

```json
"retention": { "raw_days": 90, "rollup_after_days": 30, "gzip_after_days": 180 }
```

Used by `tools/scripts/rotate_events.py`:
- `raw_days`: keep raw JSONL files for this many days (unused currently, for future deletion)
- `rollup_after_days`: aggregate daily files into monthly summaries after this many days
- `gzip_after_days`: compress JSONL files older than this
