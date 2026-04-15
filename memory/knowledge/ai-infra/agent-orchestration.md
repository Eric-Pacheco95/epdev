# Agent Orchestration Patterns

## Overview
Patterns for structuring autonomous agent loops and multi-agent pipelines. Covers low-level loop design (agentic iterations) and high-level orchestration architecture (company-as-OS). Directly applicable to Jarvis Phase 5D/5E dispatcher and autonomous runner design.

## Key Findings

### Agentic Loop Patterns (Article: 2026-03-28_agentic-loops-multi-agent-orchestration)
- Generator-Critic: most common pattern -- producer generates, critic evaluates, max 2-5 iterations. Termination condition must be defined upfront to prevent runaway loops.
- Iterative Refinement: three roles (generate, critique, refine) -- prevents the fix-one-break-another failure mode common in single-pass agents.
- Reflexion: actor + evaluator + persistent memory between attempts -- agent accumulates failure context across iterations, not just within one session.
- Brownian Ratchet (Multiclaude): always-forward progress, accepts messy intermediate code, CI tests gate merges rather than agent judgment. Optimizes for throughput over cleanliness.
- Agent power comes from its definition (prompt + context), not the runtime framework -- the leverage point is prompt engineering.

### Company-as-OS Architecture (Article: 2026-03-29_aron-prins-paperclip-pipeline)
- Paperclip AI (39K GitHub stars, MIT, launched March 2 2026): open-source orchestration for "zero-human company" model. "If OpenClaw is an employee, Paperclip is the company."
- Hierarchy: Company Goal -> CEO Agent -> Manager Agents -> Worker Agents; each layer has defined scope and escalation path.
- Supported runtimes: Claude Code, Codex, Cursor, OpenCode, Bash, HTTP webhooks, OpenRouter -- runtime-agnostic orchestration layer.
- Heartbeat pattern embedded: autonomous agents self-report status, CEO agent aggregates. Mirrors Jarvis dispatcher design.
- Stack: Node.js + React + PostgreSQL. Quick start: `npx paperclipai onboard --yes`.

## Source Articles
- 2026-03-28_agentic-loops-multi-agent-orchestration.md (confidence: 9)
- 2026-03-29_aron-prins-paperclip-pipeline.md (confidence: 8)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] Generator-Critic max 2-5 iterations is presented as a best practice without empirical backing -- optimal count likely varies by task complexity and model capability.
- [ASSUMPTION] Paperclip AI's "zero-human company" framing assumes agent autonomy levels not yet validated in production; 39K stars on a March 2026 launch may reflect hype over proven adoption.
- [ASSUMPTION] Source article for agentic-loops was truncated ("The agent's power comes from its definition, not" -- cut off); remaining findings may be incomplete.
- [FALLACY] Survivorship bias: documented loop patterns are those that worked; failed patterns (infinite loops, oscillating critiques) are not represented.
- [FALLACY] Appeal to authority: Multiclaude's Brownian Ratchet cited by name without independent validation data on when it outperforms Generator-Critic for a given task class.

# Agent Orchestration Patterns and System Visibility

## Overview
Research on autonomous agent orchestration architecture and the dashboard UI layer for surfacing system state. Covers three orchestration models with pattern-level takeaways for Jarvis Phase 5, the SENSE/DECIDE/ACT pipeline, and the local-first Next.js dashboard stack that reads directly from Jarvis file outputs.

## Key Findings

### Orchestration Models
- Three approaches evaluated: Company-as-OS (Paperclip -- CEO/managers/workers org chart, designed for multi-agent business simulation), Visual workflow (n8n -- DAG of nodes/edges, suited for pipelines with many external integrations), Skill-first brain (Jarvis -- single brain + skills + dispatcher + SENSE/DECIDE/ACT)
- Correct decision: absorb specific patterns from Paperclip and n8n into Jarvis's existing architecture; do not adopt either tool wholesale -- adoption cost exceeds integration benefit for a single-operator system
- Task Parentage (Paperclip): every subtask records its parent task ID; enables rollup reporting, accountability chains, and orphan detection -- directly applicable to Jarvis backlog/dispatcher

### SENSE/DECIDE/ACT Pipeline
- Phase 5 Jarvis: SENSE (collectors, heartbeat, signals) -> DECIDE (dispatcher, routines engine, task gate) -> ACT (worker agents, task execution, ISC validation)
- Unified intake: all producers (autoresearch, ISC producer, heartbeat remediation, security scan) write to the same backlog; no silos; overnight runner and interactive dispatcher converge on the same queue
- Concurrent-write safety required: read-modify-write race on backlog discovered 2026-04-08; file lock added same session

### Dashboard UI Stack
- Stack: Next.js 16 (App Router) + shadcn/ui + Tremor (300+ dashboard blocks, acquired by Vercel 2025, fully open-source) + Tailwind CSS v4
- Data layer: each API route (/api/heartbeat, /api/signals, /api/tasks, /api/overnight) calls fs.readFile() on existing Jarvis JSON/markdown output files -- no database, no external services, no new write paths
- Frontend polls with SWR at 30s refresh intervals; architecture is read-only from dashboard perspective; purely a visibility layer, not a control plane
- Tremor acquisition by Vercel in 2025 improves long-term maintenance confidence vs self-maintained charting libraries

## Source Articles
- 2026-03-30_phase5-orchestration-patterns.md (confidence: 9)
- 2026-03-29_jarvis-dashboard-ui.md (confidence: 8)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] Tremor's Vercel acquisition is assumed to imply continued open-source maintenance; acquisition does not guarantee investment continuity -- license terms and roadmap should be verified before committing to the stack
- [ASSUMPTION] Paperclip and n8n pattern descriptions are research summaries, not first-hand implementations; specific claims (CEO/m

[TRUNCATED: content exceeded 6000 char cap -- agent-orchestration.md]