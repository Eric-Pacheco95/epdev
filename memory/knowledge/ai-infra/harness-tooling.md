# Harness Tooling -- Observability and Security Validation

## Overview
Tooling layer for Claude Code / Jarvis harness: event observability via hooks + Langfuse, and security validation patterns derived from Jeffrey Emanuel's dcg tool. Both address the same core concern -- making the harness instrumented and defensible without adding heavy runtime dependencies.

## Key Findings

### Observability Pipeline (Article: 2026-03-27_ai-agent-observability)
- Phase 1 (zero-dependency): PostToolUse hook -> append JSONL to history/events/; schema: {ts, hook, session_id, tool, success, error, input_len}. Never log raw inputs or outputs -- secret leakage risk.
- Phase 2: Langfuse (MIT, self-hostable via Docker Compose) wins for LLM tracing -- token counts, cost per session, trace graphs, tool call chains. Free cloud tier at 50K units/month.
- Native integration: doneyli/claude-code-langfuse-template provides ready-made Claude Code hooks. OpenTelemetry GenAI semantic conventions provide vendor-neutral schema (article truncated -- full spec details unavailable).
- Correct rollout order: JSONL first (no new dependencies), Langfuse second (only when trace depth is needed).

### Security Validation Patterns (Article: 2026-03-27_jeffrey-emanuel-agentic-tooling)
- Emanuel's dcg (Rust binary, SIMD-accelerated): 49+ security pattern packs covering git reset --hard, inline script AST scanning, database/cloud destructive commands -- gaps in current validate_tool_use.py.
- WSL requirement makes direct dcg adoption impractical on Windows; correct move is extracting dcg's pattern list into the existing Python validator without the Rust binary dependency.
- Of Emanuel's 8 tools, only 3 deliver immediate Jarvis ROI; the rest assume parallel Claude Code sessions (multi-agent infra not yet needed at current phase).
- Meta-skill pattern (CASS): session search + structured retrieval enables cross-session knowledge continuity -- relevant to Jarvis signal pipeline design.

## Source Articles
- 2026-03-27_ai-agent-observability.md (confidence: 9)
- 2026-03-27_jeffrey-emanuel-agentic-tooling.md (confidence: 8)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] Langfuse free tier (50K units/month) is assumed sufficient for Jarvis usage volume -- actual unit consumption per session is not estimated; heavy hook usage could exhaust the free tier quickly.
- [ASSUMPTION] dcg's 49+ patterns are assumed to cover the most critical gaps in validate_tool_use.py without a formal cross-reference gap analysis; overlap with existing checks is unknown.
- [ASSUMPTION] Observability article was truncated ("OpenTelemetry GenAI semantic con" -- cut off); the full OTel schema and integration guidance may contain additional relevant detail.
- [FALLACY] False dichotomy: observability article frames JSONL vs Langfuse as sequential phases; both can coexist from Phase 1 for different telemetry purposes.
- [FALLACY] Hasty generalization: Emanuel's 3-of-8 ROI assessment is point-in-time for Jarvis's current architecture; multi-agent expansion would shift the calculus significantly.