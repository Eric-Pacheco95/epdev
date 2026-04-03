---
domain: ai-infra
source: /research (backfill)
date: 2026-03-30
topic: PAI v4.0.3 vs Jarvis Architecture Comparison
confidence: 9
source_files:
  - memory/work/pai-v4.0.3-comparison/research_brief.md
tags: [pai, architecture, cli-first, notification, voice, agent-composition, comparison]
---

## Key Findings
- PAI v4.0.3 has 63 skills, 21 hooks, 338 workflows, 202 tips, Algorithm v3.6.0; Jarvis and PAI share the same DNA (7-phase Algorithm, TELOS, ISC, 3-tier memory, constitutional security) but diverge in execution model
- **Highest-value PAI gap for Jarvis**: CLI-first architecture — PAI builds deterministic Python CLI tools with `--flags` first, then wraps with AI; Jarvis skills are prompt-first; the steering rule "does this step require intelligence? No → Python script" exists but isn't consistently applied; audit targets: `/vitals`, `/synthesize-signals`, `/security-audit` scan steps
- **Medium-high value gap**: Notification system — PAI has multi-channel routing (Voice, ntfy.sh, Discord, Desktop) with duration-aware escalation; Jarvis has Slack only; ntfy.sh is zero-friction to add for Phase 5 background agent completion alerts
- **Medium value gap**: Actions/Pipelines/Flows system (three-tier: single-step Actions → sequential Pipelines → cron-scheduled Flows); Jarvis's autonomous loop is functionally a flow but not formalized; worth adopting during Phase 5 for composability
- PAI's "Spotcheck" pattern (always verify multi-agent output with a separate agent after parallel execution) is worth adopting immediately; trait-based dynamic agent composition is interesting but may be overengineered for solo use

## Context
PAI's Cloud Execution Layer ("Arbol" via Cloudflare Workers) is not a gap to close — Jarvis's local-first architecture is a deliberate choice. PAI's voice server (ElevenLabs, per-agent voice IDs) provides ambient awareness (hear when tasks complete) — low priority vs core autonomous capabilities but ergonomically interesting for Phase 5+. Jarvis is ahead of PAI in self-healing, decision logging, and learning signal maturity.

## Open Questions
- Which skills are highest-priority candidates for conversion from prompt-first to CLI-first?
- Is ntfy.sh the right notification channel or should Slack (#jarvis-inbox) be extended instead?
- Does the spotcheck-after-parallel pattern belong as a hook, a skill step, or a dispatcher policy?
