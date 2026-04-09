---
domain: ai-infra
source: /research
date: 2026-04-06
topic: AI Agent Frameworks -- LangGraph, CrewAI, AutoGen, Agentless
confidence: 8
source_files:
  - memory/work/ai-agent-frameworks/research_brief.md
tags: [langgraph, crewai, autogen, agentless, agent-frameworks, orchestration]
---

## Key Findings

- **AutoGen is in maintenance mode** -- Microsoft replaced it with Microsoft Agent Framework (MAF), consolidating AutoGen + Semantic Kernel. No new features; migrate away from AutoGen for new projects.
- **LangGraph is the production default** for stateful, human-in-the-loop workflows. Its pause/serialize/resume checkpoint model is unique and battle-tested (Replit, Elastic, LinkedIn). CVE-2025-67644 (SQL injection in SQLite checkpointer) -- patch and pin versions.
- **CrewAI wins on time-to-production** for role-based workflow automation; 40% faster setup than LangGraph but less control. Best for content pipelines and business process automation, not code-gen.
- **Agentless pattern outperforms agentic frameworks** for structured coding tasks (50.8% on SWE-bench Verified) -- removes LLM from control flow entirely; fixed pipeline: localize, repair, validate. Jarvis already implements this pattern.
- **Every major AI lab launched its own framework in 2026** -- OpenAI Agents SDK, Google ADK, Anthropic Agent SDK, Smolagents. Ecosystem is fragmenting; no universal standard yet.

## Context

The framework landscape shifted significantly in early 2026. AutoGen going maintenance-only is a strategic signal: Microsoft is consolidating on MAF for enterprise. LangGraph has won the "serious production agent" niche due to checkpoints. CrewAI owns rapid prototyping. The Agentless academic pattern (OpenAutoCoder) is quietly the most reliable for well-defined task shapes -- and is structurally identical to how Jarvis's dispatcher+ISC tasks already work. Jarvis does not need to adopt any of these frameworks.

## Open Questions

- Does Anthropic's Agent SDK change how Claude Code's `Task` tool spawns subagents -- would it eventually replace the current pattern?
- As frontier models improve self-evaluation, does the Agentless vs. Agentic performance gap close?
- Is LangGraph's checkpoint pattern worth backporting for Jarvis's overnight long-running tasks?
