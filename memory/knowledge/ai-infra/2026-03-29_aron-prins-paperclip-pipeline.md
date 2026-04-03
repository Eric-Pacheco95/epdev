---
domain: ai-infra
source: /research (backfill)
date: 2026-03-29
topic: Aron Prins — Autonomous Project Lifecycle Pipeline & Paperclip AI
confidence: 8
source_files:
  - memory/work/aron-prins-research/research_brief.md
tags: [paperclip, autonomous-agents, orchestration, multi-agent, company-as-os, heartbeat]
---

## Key Findings
- **Paperclip AI** (39K GitHub stars, MIT, launched March 2 2026): open-source orchestration platform for running teams of AI agents as a "zero-human company" — "If OpenClaw is an employee, Paperclip is the company"; Node.js + React + PostgreSQL; `npx paperclipai onboard --yes` to start
- Architecture: Company Goal → CEO Agent → Manager Agents → Worker Agents; supports Claude Code, Codex, Cursor, OpenCode, Bash, HTTP webhooks, OpenRouter as agent runtimes
- Key patterns: **Task Parentage** (every task traces back to company goal through parent chain), **Heartbeat-Driven Execution** (agents wake on schedule, read memory, check queue, work, report, sleep), **Routines Engine** (recurring tasks re-enter backlog on schedule with token cost logging), **Atomic Task Checkout** (only one agent works a task at a time — prevents double-work)
- "Memento Man" mental model: agents wake capable but with zero memory — need heartbeat checklists, persona prompts, and written context; "if it's not written down, it doesn't exist"
- Budget enforcement matters in practice — Aron hit $130 in one session with nothing working; per-agent monthly spend caps with auto-pause at 100% and warning at 80% are essential

## Context
Aron Prins is a Netherlands-based indie hacker who is both a power user and contributor to Paperclip. His full stack includes Paperclip + OpenClaw + Claude Code + Codex + GWS CLI (15+ Google Workspace agents). The CEO→Manager→Worker hierarchy is appropriate for multi-agent businesses but adds unnecessary latency and token cost for a solo-operator system like Jarvis. The heartbeat-driven execution pattern is already validated in Jarvis's overnight runner.

## Open Questions
- Does Paperclip's "Routines Engine" design map cleanly to Jarvis's Phase 5C routines ISC?
- Is OpenClaw (the primary Paperclip agent runtime) a meaningful capability upgrade over Claude Code alone?
- What is Aron's actual monthly spend across all agents, and what is the ROI breakdown?
