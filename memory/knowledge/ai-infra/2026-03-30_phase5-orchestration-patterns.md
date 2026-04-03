---
domain: ai-infra
source: /research (backfill)
date: 2026-03-30
topic: Autonomous Agent Orchestration for Phase 5 — Pattern Synthesis
confidence: 9
source_files:
  - memory/work/phase5-orchestration/research_brief.md
tags: [phase5, orchestration, paperclip, n8n, sense-decide-act, task-ancestry, routines]
---

## Key Findings
- Three orchestration approaches exist: **Company-as-OS** (Paperclip — org chart: CEO → managers → workers, for multi-agent businesses), **Visual workflow** (n8n — DAG of nodes/edges, for pipelines with external integrations), **Skill-first brain** (Jarvis — single brain + skills + dispatcher); correct decision: absorb specific patterns from both into Phase 5's existing SENSE/DECIDE/ACT architecture, not adopt either tool
- **Task Parentage** (Paperclip pattern): every task traces back to a goal through a parent chain (`parent_id` field) — workers understand "why am I doing this?"; worth adding to Jarvis's flat Phase 5 backlog
- **Routines Engine** pattern: recurring tasks re-enter the backlog on schedule via a `routines.jsonl` with schedule + template; each execution logs tokens spent and output; directly maps to Phase 5C ISC
- CEO → Manager → Worker hierarchy adds latency and token cost for no benefit in a solo-operator system; Jarvis's single-brain architecture handles this through skill routing instead
- Heartbeat-driven execution (Paperclip), lockfile-based atomic task checkout (prevents double-work), and per-agent budget enforcement are all patterns Jarvis already implements — validated by Paperclip's production use

## Context
Research builds on the earlier Aron Prins brief (2026-03-29). The n8n approach is better suited to multi-step pipelines with external service integrations (email, CRM, webhooks) than to the code-generation and analysis tasks Jarvis handles. The bottom line: don't adopt Paperclip, don't adopt n8n — Jarvis's SENSE/DECIDE/ACT architecture is the right fit; the specific patterns worth absorbing are task ancestry, routines engine design, and the "Memento Man" written context discipline.

## Open Questions
- What is the right data structure for `routines.jsonl` — cron expression + prompt template + output path?
- Should task ancestry be tracked in a separate file or inline in each task entry in the backlog?
- How does the dispatcher handle a routine that generates zero output — is that a signal or just idle-is-success?
