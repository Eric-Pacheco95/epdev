# PRD: Phase 4E Data Layer (Hybrid Architecture)

- **Date**: 2026-03-29
- **Status**: Design complete, ready for implementation
- **Owner**: Eric P
- **Architecture Decision**: `history/decisions/2026-03-29_data-layer-hybrid-architecture.md`
- **Data Flow Audit**: `memory/work/observability/data_flow_audit.md`
- **Architecture Review**: 3-agent parallel review (first-principles + fallacy + STRIDE red-team), 2026-03-29

## Mission

Build a robust data layer that makes all of Jarvis's autonomous activity queryable, traceable, and self-monitoring -- enabling Jarvis to learn faster, self-heal sooner, and give Eric full visibility into system health, cost, and behavioral patterns.

## Architecture

**Hybrid model:**
- Markdown/JSONL files remain the source of truth for all content and relationships
- Existing `jarvis_index.db` (SQLite FTS5) extended with manifest tables as a read-optimized query accelerator
- SQLite is a **rebuildable cache** -- every table can be regenerated from files at any time
- If SQLite and files disagree, **files win** and the DB is rebuilt

**Key constraints validated by architecture review:**
- Signals are `.gitignored` -- no git auditability concerns with compression/deletion
- WAL mode already enabled in `jarvis_index.py` (line 88)
- `jarvis_index.py build` uses `DELETE FROM` not `DROP TABLE` -- custom manifest tables survive rebuilds
- `_init_db()` uses `CREATE TABLE IF NOT EXISTS` -- additive, non-destructive

## Design Decisions (from collaborative session)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Lineage authority: `signal_lineage.jsonl` | File-backed, append-only, SQLite mirrors for queries. Single source of truth (retire informal synthesis markdown references as decoration). |
| D2 | Producer runs: derived from `data/logs/*.log` | Logs already contain timestamps + exit codes. SQLite `producer_runs` table is a queryable cache, rebuildable from logs. |
| D3 | Retention: tiered | Metadata forever in SQLite. Raw signal files kept 90 days post-synthesis. Delete after 90 days. |
| D4 | Consumer fallback: hard | Every consumer that migrates to manifest queries must have a directory-scan fallback if DB is unavailable. System degrades gracefully, never stops. |
| D5 | Job exclusion: Task Scheduler only | "Do not start new instance" checkbox. Jobs write to different directories -- no SQLite contention risk under WAL. No lockfile complexity. |
| D6 | Session transcripts: use Claude Code native | Drop `memory/session/` concept. FTS already indexes `~/.claude/projects/` JSONL. No duplication needed. |
| D7 | Signals are .gitignored | Compress/delete/archive freely. No git binary blob concern. |
| D8 | Query ambitions: 4 dimensions | Cost/tokens, skill usage, temporal patterns, decision outcomes -- all queryable from manifest tables + event JSONL. |

## Non-Goals

- No external database (Langfuse, Postgres, etc.) -- SQLite only
- No real-time streaming dashboard -- batch queries via `/vitals` and heartbeat
- No file format changes to existing signals/synthesis (additive metadata only)
- No changes to brain-map parser (it reads markdown, not SQLite)
- No lockfile/mutex between scheduled jobs (WAL + different directories = sufficient)

## What This Enables (17 target questions)

### Cost & Efficiency
1. How much did Jarvis cost me this week in API tokens?
2. Which autonomous job uses the most tokens per run?
3. What's my cost trend -- is it going up or down?

### Learning & Growth
4. What topics am I learning fastest about? (signal category velocity)
5. What TELOS goals have zero signal activity in 30 days? (behavioral gaps)
6. How many overnight runner proposals actually got merged?

### System Health
7. Which producer has the highest failure rate?
8. When was the last time every scheduled job ran successfully?
9. How stale is my FTS index right now?

### Behavioral Patterns (Phase 5 preview)
10. What time of day am I most productive?
11. Do I work on crypto-bot more after market volatility?
12. How long do my sessions typically last?
13. Which skills do I invoke most vs least?
14. Am I spending more time in THINK phase or BUILD phase?

### Decision Quality
15. How many decisions did I make this month, and how many reversed?
16. What percentage of overnight proposals did I accept vs reject?
17. Which steering rules were added from autonomous signals vs manual sessions?

## SQLite Schema

### Existing tables (preserved, not modified)
```sql
-- FTS5 content table (from jarvis_index.py)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source_type TEXT,     -- 'signal', 'synthesis', 'failure', 'decision', etc.
    source_file TEXT,     -- absolute path
    content TEXT,
    mtime REAL
);
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, source_type, source_file);
CREATE TABLE IF NOT EXISTS indexed_files (source_file TEXT PRIMARY KEY, mtime REAL);
```

### New manifest tables
```sql
-- Signal metadata (rebuildable from signal file frontmatter)
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,         -- relative path from repo root
    title TEXT,
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    source TEXT,                            -- 'manual', 'autonomous', 'voice', 'heartbeat'
    category TEXT,                          -- from frontmatter
    rating INTEGER,                         -- 1-10
    processed INTEGER DEFAULT 0,            -- 0=raw, 1=synthesized
    synthesis_id INTEGER,                   -- FK to lineage.synthesis_id after processing
    deleted_at TEXT,                         -- ISO timestamp when raw file was cleaned up
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_processed ON signals(processed);

-- Lineage edges (rebuildable from signal_lineage.jsonl)
CREATE TABLE IF NOT EXISTS lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_filename TEXT NOT NULL,           -- matches signals.filename
    synthesis_filename TEXT NOT NULL,         -- e.g. '2026-03-29_synthesis.md'
    date TEXT NOT NULL,                       -- date of synthesis run
    UNIQUE(signal_filename, synthesis_filename)
);

-- Producer run history (rebuildable from data/logs/*.log)
CREATE TABLE IF NOT EXISTS producer_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer TEXT NOT NULL,                   -- 'heartbeat', 'overnight', 'autoresearch', 'morning_feed'
    run_date TEXT NOT NULL,                   -- YYYY-MM-DD
    started_at TEXT,                          -- ISO timestamp (parsed from log)
    completed_at TEXT,                        -- ISO timestamp (parsed from log)
    duration_seconds REAL,
    status TEXT NOT NULL DEFAULT 'unknown',   -- 'success', 'failure', 'timeout', 'unknown'
    exit_code INTEGER,
    artifact_count INTEGER DEFAULT 0,
    log_path TEXT,                            -- relative path to log file
    UNIQUE(producer, run_date, started_at)
);
CREATE INDEX IF NOT EXISTS idx_producer_runs_producer ON producer_runs(producer);
CREATE INDEX IF NOT EXISTS idx_producer_runs_date ON producer_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_producer_runs_status ON producer_runs(status);

-- Cost tracking (rebuildable from event JSONL Stop records)
CREATE TABLE IF NOT EXISTS session_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    date TEXT NOT NULL,
    session_type TEXT,                        -- 'interactive', 'claude-p', 'overnight', 'autoresearch'
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cost_usd REAL,
    duration_seconds REAL,
    tools_used INTEGER DEFAULT 0,
    skills_invoked TEXT,                      -- JSON array of skill names
    UNIQUE(session_id)
);
CREATE INDEX IF NOT EXISTS idx_session_costs_date ON session_costs(date);
CREATE INDEX IF NOT EXISTS idx_session_costs_type ON session_costs(session_type);

-- Skill invocation tracking (rebuildable from event JSONL)
CREATE TABLE IF NOT EXISTS skill_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    invoked_at TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_skill_usage_skill ON skill_usage(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_usage_date ON skill_usage(date);

-- Schema version (for migration safety)
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    migrated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Ideal State Criteria

### Step 1: Foundation
- [x] Orphaned `data/jarvis_events.db` is deleted | Verify: `test ! -f data/jarvis_events.db` [E][M]
- [x] `jarvis_index.py update` runs daily at 3am via Task Scheduler | Verify: `schtasks /query /tn "\Jarvis\JarvisIndexUpdate"` returns Ready [E][M]
- [x] WAL checkpoint runs after each producer write (add `PRAGMA wal_checkpoint(TRUNCATE)` call) | Verify: Grep for `wal_checkpoint` in producer scripts [E][M]
- [x] FTS resilience verified: delete a processed signal, query index, content retained | Verify: test script output [E][M]
- [x] `memory/session/` directory removed from scaffold (FTS indexes Claude Code native JSONL) | Verify: `test ! -d memory/session` [E][M]
- [x] No consumer assumes DB availability without a directory-scan fallback | Verify: `/review-code` on all consumers [I][A]

### Step 2: Manifest Tables
- [ ] All 6 new tables created in `jarvis_index.db` with schema version 1 | Verify: `sqlite3 jarvis_index.db ".tables"` shows signals, lineage, producer_runs, session_costs, skill_usage, schema_version [E][M]
- [ ] Signal metadata backfilled from existing signal files (276+ rows) | Verify: `sqlite3 jarvis_index.db "SELECT COUNT(*) FROM signals"` >= 276 [E][M]
- [ ] Lineage backfilled from `signal_lineage.jsonl` (33+ rows) | Verify: `sqlite3 jarvis_index.db "SELECT COUNT(*) FROM lineage"` >= 33 [E][M]
- [ ] Producer runs backfilled from `data/logs/*.log` | Verify: `sqlite3 jarvis_index.db "SELECT COUNT(DISTINCT producer) FROM producer_runs"` >= 4 [E][M]
- [ ] `jarvis_index.py build` preserves manifest tables (regression test) | Verify: run build, confirm manifest row counts unchanged [E][M]
- [ ] Schema version check at connection time rejects version mismatches | Verify: test with wrong version number [E][M]

### Step 3: Wire Producers
- [ ] `/synthesize-signals` writes lineage rows to DB after processing | Verify: run synthesis, check `SELECT COUNT(*) FROM lineage` increased [E][M]
- [ ] Heartbeat writes `producer_runs` row on each run | Verify: `SELECT * FROM producer_runs WHERE producer='heartbeat' ORDER BY run_date DESC LIMIT 1` [E][M]
- [ ] Overnight runner writes `producer_runs` row on completion | Verify: same query with producer='overnight' [E][M]
- [ ] Autoresearch writes `producer_runs` row on completion | Verify: same query with producer='autoresearch' [E][M]
- [ ] Morning feed writes `producer_runs` row on completion | Verify: same query with producer='morning_feed' [E][M]
- [ ] `producer_health` heartbeat collector alerts on stale/failed producer runs | Verify: mock a failed run, confirm WARN signal generated [E][M]
- [ ] Stop hook writes `session_costs` row with token counts (if available from Claude Code) | Verify: end a session, check `SELECT * FROM session_costs ORDER BY id DESC LIMIT 1` [I][M]
- [ ] `hook_events.py` detects and records skill invocations to `skill_usage` table | Verify: invoke a skill, check `SELECT * FROM skill_usage ORDER BY id DESC LIMIT 1` [I][M]

### Step 4: Retention
- [ ] Processed signals older than 90 days are automatically deleted | Verify: create a backdated test signal, run retention, confirm deleted [E][M]
- [ ] Signal metadata row persists in SQLite after raw file deletion (`deleted_at` populated) | Verify: `SELECT COUNT(*) FROM signals WHERE deleted_at IS NOT NULL` after retention run [E][M]
- [ ] Heartbeat history rotation: raw JSONL kept 30 days, monthly summary for older | Verify: `du -sh memory/work/isce/heartbeat_history.jsonl` stays bounded after retention [E][M]
- [ ] `autonomous_signal_rate` heartbeat collector alerts on runaway signal production | Verify: check collector exists in `heartbeat_config.json` with daily cap threshold [E][M]
- [ ] `signal_volume` collector reads from `signals` table, not directory scan | Verify: Grep for `SELECT COUNT` in collector code [E][M]
- [ ] No file is deleted without its metadata existing in the `signals` table first | Verify: `/review-code` on retention script [I][A]
- [ ] Retention runs on Task Scheduler cadence (weekly or daily) | Verify: `schtasks /query /tn "\Jarvis\JarvisRetention"` returns Ready [E][M]

### Step 5: Consumer Migration & Query Layer
- [ ] Heartbeat `signal_count` and `signal_velocity` collectors query `signals` table with directory-scan fallback | Verify: Grep for fallback in collector code [E][M]
- [ ] Event metrics pre-aggregated: sessions_per_day, tool_failure_rate, top_tools queryable from SQLite | Verify: `sqlite3 jarvis_index.db "SELECT COUNT(*) FROM session_costs"` > 0 [E][M]
- [ ] Heartbeat trend detection: 3-5 run moving average from heartbeat_history | Verify: consecutive heartbeat runs show trend values in snapshot [E][M]
- [ ] `/vitals` reads from manifest tables for signal velocity, producer health, cost summary | Verify: run `/vitals`, confirm cost and producer health sections appear [E][M]
- [ ] All 17 target questions answerable via SQL queries against manifest tables | Verify: query script with all 17 queries produces non-empty results [E][M]
- [ ] Brain-map JSON data contract defined and emitted by heartbeat | Verify: `heartbeat_latest.json` contains `manifest_summary` key [I][M]

### Anti-criteria
- [ ] No consumer fails silently when `jarvis_index.db` is unavailable -- all degrade to directory scan | Verify: rename DB, run heartbeat, confirm it completes with warnings [E][M]
- [ ] No signal file is deleted if its metadata is not in the `signals` table | Verify: `/review-code` retention script [E][A]
- [ ] No manifest table contains data that cannot be rebuilt from files | Verify: delete DB, run rebuild, compare row counts before/after [E][M]
- [ ] `jarvis_index.py build` does not drop or clear manifest tables | Verify: add test rows, run build, confirm rows survive [E][M]
- [ ] Token/cost tracking does not log prompt content (only counts and costs) | Verify: `/review-code` on stop hook cost capture [E][A]

## Build Order

```
Step 1: Foundation (gate: FTS test passes + index scheduled)
    |
    v
Step 2: Manifest Tables (gate: backfill complete + build regression test passes)
    |
    v
Step 3: Wire Producers (gate: lineage populated after next synthesis run)
    |
    v
Step 4: Retention (gate: retention run deletes test signal + metadata persists)
    |
    v
Step 5: Consumer Migration (gate: all 17 questions answerable)
```

## Cost Tracking Implementation Notes

Token/cost data sources:
- **Interactive sessions**: Claude Code Stop hook payload may include token counts (needs verification -- check what `stop_reason` JSON contains)
- **`claude -p` sessions**: overnight runner and autoresearch can capture subprocess stdout which may include usage stats
- **Anthropic API direct**: morning feed uses `anthropic` SDK which returns `usage` in response objects -- capture `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
- **Fallback**: if token counts unavailable, track session count and duration only; estimate cost from known model pricing

## Risks & Mitigations (from architecture review)

| Risk | Severity | Mitigation |
|------|----------|------------|
| DB corruption takes down query consumers | High | Hard fallback to directory scan in every consumer (D4) |
| Schema migration under concurrent access | Medium | Run DDL in `BEGIN EXCLUSIVE` transaction; schedule during low-activity window |
| WAL file growth on Windows | Medium | `wal_checkpoint(TRUNCATE)` after producer writes; WAL size heartbeat collector |
| Retention deletes signal before metadata captured | Medium | Anti-criterion: no deletion without metadata in DB first |
| Three lineage sources diverge | Medium | Single authority: `signal_lineage.jsonl`. Synthesis markdown references are decoration only. |
| Producer self-reports false success | Low | Cross-check: producer_health collector verifies expected artifacts exist, not just status row |

## Open Items for Phase 5

- Retention window (90 days) may need adjustment based on Phase 5 behavioral analysis requirements
- Session transcript depth -- FTS indexes session JSONL but may need richer extraction for behavioral patterns
- Cost optimization -- once tracking is live, use data to identify token reduction opportunities
