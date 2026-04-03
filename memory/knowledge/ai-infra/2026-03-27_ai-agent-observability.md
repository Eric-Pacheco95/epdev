---
domain: ai-infra
source: /research (backfill)
date: 2026-03-27
topic: AI Agent Observability for Claude Code / Jarvis
confidence: 9
source_files:
  - memory/work/observability/research_brief.md
tags: [observability, hooks, langfuse, jsonl, telemetry, claude-code]
---

## Key Findings
- Phase 1 (build now): `PostToolUse` hook → append JSONL to `history/events/` — zero dependencies, schema: `{ts, hook, session_id, tool, success, error, input_len}`; never log raw inputs/outputs (secret leakage risk)
- Phase 2: Langfuse (MIT, Docker Compose) is the clear winner for LLM tracing — token counts, cost per session, trace graphs, tool call chains; free cloud tier at 50K units/month; `doneyli/claude-code-langfuse-template` provides native Claude Code integration
- OpenTelemetry GenAI semantic conventions are still maturing — overkill for a solo dev; commercial tools (Datadog, Honeycomb) are also overkill
- `claude_telemetry` (OTel wrapper replacing the `claude` CLI) is interesting but adds friction and requires an external backend
- Hook performance must stay under 100ms — JSONL append is fast enough; cap file growth with date-based rotation

## Context
PAI and disler's multi-agent observability repo both independently converged on the same JSONL-via-hooks pattern, validating it as the correct Phase 1 approach. The full loop (hook → JSONL → file watcher → Vue3 dashboard) is demonstrated by disler's repo. Langfuse is deferred to after Phase 3E when the ISC gap detection engine is built and cost tracking becomes a priority.

## Open Questions
- Which specific metrics matter most for ISC gap detection? (Phase 3D defines this)
- Should cost tracking live in event JSONL or Langfuse only?
- Is `claude_telemetry` worth a closer evaluation as an alternative to custom hooks?
