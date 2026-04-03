---
domain: ai-infra
source: /research (backfill)
date: 2026-03-28
topic: Agentic Loops & Multi-Agent Orchestration Patterns for Claude Code
confidence: 9
source_files:
  - memory/work/agent-orchestration-research/research_brief.md
tags: [agentic-loops, multi-agent, generator-critic, reflexion, claude-code, orchestration]
---

## Key Findings
- Four core loop patterns: **Generator-Critic** (most common — producer + evaluator with max 2–5 iterations), **Iterative Refinement** (three roles: generate, critique, refine — prevents fix-one-break-another), **Reflexion** (actor + evaluator + persistent memory between attempts — agent learns from failures), **Brownian Ratchet** (Multiclaude: always forward, accept messy code, CI tests gate merges)
- The agent's power comes from its definition, not its implementation — best developers spend more time on agent persona design and orchestration architecture than on framework code
- Claude Code native: `Task` tool spawns subagents with own context window and restricted tools; subagents cannot spawn their own subagents (no recursion); parent aggregates results
- **Context anxiety** (model wraps up prematurely) and **poor self-evaluation** (model praises mediocre work) are the two dominant failure modes in long-running agents; Anthropic's 3-agent architecture (planner, generator, evaluator) addresses both
- Karpathy's "March of Nines": a 5-step chain at 95% per-step reliability = 77% end-to-end; at 10 steps = 60% — harness engineering (deterministic rails, validation gates) is the answer, not better per-step prompting

## Context
Research sourced from 22 references. The Generator-Critic pattern is what Google, AWS, LangChain, and every major framework has converged on. The Reflexion pattern maps directly to Jarvis's learning signal system — persistent memory between attempts is already the design. The Brownian Ratchet is used by Multiclaude and is appropriate for autonomous overnight runs where some duplicate work is acceptable in exchange for forward progress.

## Open Questions
- What is the right max_iterations safety valve for Jarvis's overnight dispatcher — 2, 3, or 5?
- How should subagent results be aggregated when they produce conflicting outputs?
- Is the Reflexion pattern's verbal self-reflection worth storing as a signal vs. just rerunning?
