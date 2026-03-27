# Decision: Phase 4 — Autonomous self-improvement & background Jarvis

**Date:** 2026-03-27  
**Status:** accepted

## Context

Jarvis should improve beyond reactive human sessions: scheduled measurement toward ideal state, curated external research, and Slack notifications by severity — without conflating background automation with interactive Claude Code hooks.

## Decision

1. Introduce **Phase 4** in `orchestration/tasklist.md` with deliverables under PRD `memory/work/jarvis/PRD.md`.
2. **Separate** OS-scheduled deterministic work (heartbeat, collectors, Slack) from **agentic** research digests (Cowork / batch Claude / scripts), with clear security constraints (no arbitrary code execution from the internet).
3. **Slack routing** remains per `memory/work/slack-routing.md`: routine → `#epdev`; must-see → `#general` only.
4. **Phase 4D capstone:** Adopt the **control pattern** from [Karpathy’s autoresearch](https://github.com/karpathy/autoresearch) (human `program.md`, bounded runs, one writable experiment surface, explicit metrics) — applied to **Jarvis-internal** data: TELOS, learning signals, session history. The agent **only** writes under `memory/work/jarvis/autoresearch/` until a human merges proposals into canonical TELOS or steering docs.

## Consequences

- Implementation work will extend Phase 3E heartbeat/ISC ideas and add allow-listed research pipelines plus notification deduplication.
- **Phase 4D** adds an internal autoresearch runner and review queue; no silent TELOS overwrite.
- Human sessions remain the approval path for merges, secrets, and TELOS/steering changes.
