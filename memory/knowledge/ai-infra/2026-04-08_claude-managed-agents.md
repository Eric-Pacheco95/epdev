---
domain: ai-infra
source: /research
date: 2026-04-08
topic: Claude Managed Agents — Anthropic's hosted agent runtime
confidence: 8
source_files:
  - memory/work/claude-managed-agents/research_brief.md
tags: [anthropic, managed-agents, orchestration, harness, dispatcher, absorb-not-adopt]
---

## Key Findings

- **Claude Managed Agents** (public beta 2026-04-08, beta header `managed-agents-2026-04-01`) is a hosted runtime for stateful agents. Primitives: agent + environment = session, driven by typed event stream (`agent.message`, `agent.tool_use`, `session.status_idle`). Built-in toolset (`agent_toolset_20260401`): bash/read/write/edit/glob/grep/web_fetch/web_search — all operate on a sandbox FS at `/mnt/session/...`, NOT the host machine.
- **Pricing**: standard token costs + **$0.08/session-hour** active runtime (millisecond-billed, idle excluded) + $10/1k web searches. No platform fee. Idle exclusion validates Jarvis's "Idle Is Success" stance.
- **Architecturally wrong fit for epdev/Jarvis**: cloud-sandbox-only filesystem, no PreToolUse hook equivalent, no CLAUDE.md/skill-registry surface, no Task Scheduler integration, no local memory/history access. Multi-agent orchestration and advanced memory tooling are still research preview, not GA.
- **Three patterns worth absorbing into existing dispatcher** (cheaper than migration): (1) typed event taxonomy for dispatcher emit + brain-map dashboard; (2) declarative `permissions.yaml` layered over `security/validators/`; (3) `agent + environment = session` decomposition for Tier-2 task records — bundle with data-relocation backlog.
- **Verdict: do not migrate.** This is the third "should I adopt an external orchestration platform" decision (after Paperclip 2026-03-29 and n8n 2026-03-30); same absorb-not-adopt answer. Aakash Gupta's "obsoleted every orchestration startup" framing is influencer hype — the docs describe a hosted runtime for enterprise teams shipping customer-facing agents, not a replacement for solo-operator skill-first brains.

## Context

Anthropic stepping up the stack from selling models to selling workers. Lands 4 days after Anthropic blocked OpenClaw from using subscription credentials — Managed Agents is the first-party replacement for third-party harnesses on consumer auth. For solo operators with local-first stacks, the relevant absorption is event-stream taxonomy + declarative permission policy + agent/environment/session decomposition, not migration.

## Open Questions

- Does the agent definition support file-based skill libraries (like `.claude/skills/`), or only inline tools? Affects parity gap evolution.
- Will multi-agent orchestration (still research preview) eventually offer a "BYO local sandbox" endpoint that would let local-first stacks gain the dashboard without losing FS access?
- When multi-agent orchestration ships GA, does single-brain architecture become structurally inferior or just smaller-scale-equivalent?
