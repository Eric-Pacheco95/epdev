# PRD: Observability Phase 2 — JSONL++ + Health Metrics
- Status: approved
- Created: 2026-03-27
- Owner: Eric P
- Depends on: Phase 1 complete (`hook_events.py` + PostToolUse wiring) ✓

## Problem

Phase 1 captures tool call events (success/failure/input_len) via PostToolUse. It does NOT capture:
- Token cost per session (budget visibility)
- Session boundaries (start/end timestamps)
- PreToolUse events (needed for ISC gap detection)
- Any aggregation layer (no way to answer "is Jarvis healthy?" without manual jq)

Phase 3E (heartbeat / ISC gap detection) is blocked until these exist.

## Ideal State Criteria

- [ ] Stop hook captures token cost for every session | Verify: `jq '.cost' history/events/2026-03-27.jsonl`
- [ ] PreToolUse hook writes intent records to JSONL | Verify: `jq 'select(.hook=="PreToolUse")' history/events/*.jsonl`
- [ ] `query_events.py` reports all 5 health metrics | Verify: `python tools/scripts/query_events.py --report`
- [ ] ISC gap count computable from JSONL alone | Verify: `python tools/scripts/query_events.py --isc-gaps`
- [ ] Langfuse cloud optionally wired (env vars only) | Verify: `TRACE_TO_LANGFUSE=true` session creates trace in Langfuse UI

## What Phase 2 Is NOT

- No Docker Compose (deferred to Phase 3E+ if Langfuse limits hit)
- No claude_telemetry / OTel collector (adds complexity, wrong tradeoff for solo dev)
- No disler Bun/Vue dashboard (demo-quality, SQLite-backed, 100-event cap)
- No new infrastructure — everything appends to existing `history/events/JSONL`

## Implementation Plan

### Step 1 — Extend `hook_events.py` to handle PreToolUse

Add a second hook type so the same script handles PreToolUse events:

```python
# In hook_events.py — detect hook type and capture intent
hook_type = data.get("hook_event_name", "PostToolUse")
# For PreToolUse: no success/error fields — just log intent
if hook_type == "PreToolUse":
    success = None  # intent, not outcome
    error_msg = None
```

Wire in `settings.json`:
```json
"PreToolUse": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python C:/Users/ericp/Github/epdev/tools/scripts/hook_events.py"
      }
    ]
  }
]
```

### Step 2 — Add `Stop` hook for session cost

Claude Code's `Stop` hook fires at session end and receives token usage data. Add a new hook:
`tools/scripts/hook_session_cost.py`

Schema for cost records:
```json
{
  "ts": "2026-03-27T15:00:00Z",
  "hook": "Stop",
  "session_id": "...",
  "tool": "_session",
  "success": true,
  "error": null,
  "input_len": 0,
  "cost_usd": 0.042,
  "input_tokens": 12000,
  "output_tokens": 2400,
  "cache_read_tokens": 8000
}
```

Wire in `settings.json`:
```json
"Stop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python C:/Users/ericp/Github/epdev/tools/scripts/hook_session_cost.py"
      }
    ]
  }
]
```

Note: Claude Code's Stop hook may not expose raw token counts in the event payload — verify at implementation time. Fallback: parse `/usage` output written to a temp file.

### Step 3 — `query_events.py` aggregation CLI

New script: `tools/scripts/query_events.py`

Commands:
```bash
# Full health report (5 metrics)
python tools/scripts/query_events.py --report

# Last N days (default 7)
python tools/scripts/query_events.py --report --days 7

# ISC gaps only (PreToolUse without matching PostToolUse success)
python tools/scripts/query_events.py --isc-gaps

# Cost summary
python tools/scripts/query_events.py --cost

# Tool failure breakdown
python tools/scripts/query_events.py --failures
```

Output format (health report):
```
Jarvis Health — 2026-03-21 to 2026-03-27
─────────────────────────────────────────
Sessions:        23 sessions (3.3/day avg)
Tool calls:      847 total, 12 failures (1.4% failure rate) ✓
Cost:            $1.24 total, $0.054/session avg
ISC gaps:        2 gaps detected (session eb558b99, d1da17be)
Top tools:       Read(234) Edit(187) Bash(156) Write(98) Grep(72)
─────────────────────────────────────────
Status: HEALTHY  (failure rate < 5%, no cost spike)
```

### Step 4 — Langfuse cloud (optional, zero-infra)

If dashboard visualization is desired, use the free cloud tier:

1. Create account at langfuse.com, get project public + secret keys
2. Install template: `doneyli/claude-code-langfuse-template` hook
3. Set in `.claude/settings.local.json`:
   ```json
   {
     "env": {
       "TRACE_TO_LANGFUSE": "true",
       "LANGFUSE_PUBLIC_KEY": "pk-...",
       "LANGFUSE_SECRET_KEY": "sk-...",
       "LANGFUSE_HOST": "https://cloud.langfuse.com"
     }
   }
   ```
4. Sessions will appear in Langfuse trace UI automatically

Limit: 50K events/month free. At ~850 tool calls/week (current rate), that's ~3,400/month — well within free tier.

**This is optional** — the JSONL + query_events.py approach answers all health questions without it.

## The 5 Health Metrics (Phase 3E inputs)

| Metric | JSONL field | Phase 3E key |
|--------|-------------|--------------|
| Cost/session | `cost_usd` in Stop records | `session_cost_usd` |
| Tool failure rate | `success=false` / total PostToolUse | `tool_failure_rate` |
| Session frequency | Count of `_session` Stop records per day | `sessions_per_day` |
| ISC gap count | PreToolUse without PostToolUse success | `isc_gap_count` |
| Top tools | `tool` field frequency distribution | `tool_histogram` |

Latency (p95) is deferred — requires `UserPromptSubmit` hook which fires on every message and is higher volume. Add in Phase 3E when the heartbeat aggregator is built.

## Decision Record

**Langfuse self-hosted rejected** — requires 6 containers (web, worker, ClickHouse, Postgres, Redis, MinIO). No SQLite mode. Overkill for solo dev. Revisit if cloud free tier limits hit.

**claude_telemetry rejected** — replaces `claude` CLI with `claudia` wrapper + OTel collector. Adds friction to every session invocation and requires collector infrastructure. Main benefit (token cost capture) is achievable via Stop hook directly.

**disler dashboard rejected** — demo-quality (SQLite, 100-event display cap). Vue3+Bun setup cost not worth it when `query_events.py` answers the same questions in the terminal.

**JSONL++ chosen** — extends what's already working. Zero new infrastructure. All 5 health metrics capturable. Feeds Phase 3E directly.

## Phase 3E Integration Point

Once `query_events.py --report` works, the heartbeat (Phase 3E) calls it and:
1. Reads the 5 metrics
2. Compares against ISC thresholds (defined in `memory/work/observability/isc_thresholds.md`)
3. Writes a `health_snapshot` to `history/events/`
4. Fires ntfy alert if any metric is RED

## Out of Scope

- Real-time streaming dashboard (Phase 3D visual spec must come first)
- OpenTelemetry semantic conventions (GenAI spec still maturing, overkill)
- Multi-user / team observability
- Historical retention beyond local JSONL rotation

## Next Steps

1. Implement Step 1 (PreToolUse) — 20 min, wire existing script
2. Implement Step 2 (Stop hook cost capture) — 45 min, new script
3. Implement Step 3 (query_events.py) — 60 min, aggregation CLI
4. Verify all 5 metrics report correctly on today's JSONL
5. Optionally: wire Langfuse cloud (30 min, env vars only)
6. Update `session_handoff.md` with Phase 3E integration spec
