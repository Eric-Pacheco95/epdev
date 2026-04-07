---
domain: ai-infra
source: /research
date: 2026-04-06
topic: Autonomous Coding Agent Capabilities -- Devin, SWE-agent, Claude Code, Cursor
confidence: 8
source_files:
  - memory/work/autonomous-coding-agents/research_brief.md
tags: [autonomous-agents, devin, swe-agent, claude-code, cursor, swe-bench, coding-agents]
---

## Key Findings
- Claude Code (Opus 4.5) holds highest public SWE-bench Verified score at 80.8%; mini-SWE-agent (100 lines Python) achieves 74%; Devin 2.0 achieves 13.86% on full SWE-bench -- benchmark measures GitHub issue resolution, not production task quality
- Scaffolding beats model complexity: mini-SWE-agent (100 lines) outperforms complex multi-agent frameworks on SWE-bench -- architectural correctness of the harness matters more than framework sophistication
- Context overflow is silent, not fatal: agents do not crash on context limit -- they silently truncate, lose thread, and produce incomplete answers; enterprise codebases exceed all context windows by orders of magnitude; retrieval beats raw context for large codebases
- Devin's real-world sweet spot is junior-level, well-defined tasks (4-8h human equivalent): code migrations, test writing, CRUD features; 67% PR merge rate (2025) vs 34% (2024); struggles with ambiguous requirements and architectural decisions
- For solo operators, harness-first (Claude Code) dominates: highest benchmark, lowest vendor lock-in, composable with existing architectures; Cursor is IDE-assistant with new cloud agent features (April 2026) but credit pricing is volatile

## Context
Research triggered by Jarvis ai-infra knowledge accrual (watchlist). Prior articles covered agentic loops (Generator-Critic, Reflexion patterns) and harness engineering (CLAUDE.md vs hooks). This article fills the gap on specific tool architectures, benchmarks, and enterprise deployment patterns. Jarvis's current architecture (Claude Code + worktree dispatch + ISC gates) aligns with the dominant strategy for solo operators.

## Open Questions
- Can Memory Pointer Pattern (store large tool results in state, pass pointer to context) be implemented as a PostToolUse hook in Jarvis's dispatcher?
- At what SWE-bench score threshold does autonomous execution become reliable enough for unsupervised overnight runs without human PR review?
- Does Devin's Interactive Planning (upfront clarifying questions before execution) add value for pre-spec'd Jarvis tasks or add unnecessary friction?
