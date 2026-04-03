---
domain: ai-infra
source: /research (backfill)
date: 2026-03-30
topic: Harness Engineering for Claude Code — Making AI Agents Reliable
confidence: 9
source_files:
  - memory/work/harness-engineering/research_brief.md
tags: [harness, claude-code, CLAUDE.md, hooks, karpathy, reliability, determinism]
---

## Key Findings
- Karpathy's "March of Nines": each additional step compounds unreliability — 5-step chain at 95% per-step = 77% end-to-end; harnesses put AI on deterministic rails with validation gates, solving what per-step skill improvements cannot
- **CLAUDE.md is advisory (~80% reliable); hooks are deterministic (100%)** — anything that must happen without exception (security blocks, formatting, audit) belongs in hooks; guidance and conventions belong in CLAUDE.md; skills encode repeatable preferences
- Community consensus: keep CLAUDE.md under 60 lines; use progressive disclosure (routing table to deeper docs); Jarvis at ~200 lines + 45 steering rules pushes the boundary but is mitigated by the Context Routing table
- Three nested loops: **Outer** (project level — CLAUDE.md, governance, drift detection), **Middle** (task level — session handoffs, validation gates), **Inner** (tool use — hooks fire at every tool invocation)
- Two dominant failure modes in long-running agents: **context anxiety** (model wraps up prematurely before work is done) and **poor self-evaluation** (model praises its own mediocre output); Anthropic's 3-agent architecture (planner/generator/evaluator) addresses both

## Context
Triggered by The AI Automators Episode 6 ("Andrej Karpathy's Math Proves Agent Skills Will Fail"). The core reframe: a specialized harness codifies the process so the model executes within guardrails rather than freestyling. Deterministic phases with validation gates between each phase turn demos into production systems. Ep 7 (115K views in 5 days) validated the 3-agent architecture by building a Tetris clone and Digital Audio Workstation without human intervention using ~4 hours on Opus.

## Open Questions
- At what CLAUDE.md length does signal-to-noise degradation measurably hurt session quality?
- What is the right validation gate between each phase of the Algorithm loop for Jarvis?
- Should CLAUDE.md have an explicit "compression budget" that triggers pruning at N tokens?
