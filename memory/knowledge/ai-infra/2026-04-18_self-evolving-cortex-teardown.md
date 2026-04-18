---
domain: ai-infra
source: /research
date: 2026-04-18
topic: Self-evolving "Cortex" agent architecture — svpino/shujunliang teardown
confidence: 7
source_files:
  - memory/work/self-evolving-cortex-teardown/research_brief.md
tags: [self-evolving-agents, session-handoff, autonomous-coding, resource-budgeting, adaptive-loops]
---

## Key Findings

- A non-programmer ran a 219-generation self-evolving agent ("Cortex") on MuleRun's free tier via a guardian/handoff pattern: when one session's credits depleted, `cortex-guardian` spawned a new session and injected the predecessor's full system prompt + knowledge. The *git-clone-predecessor-handoff-resume* loop is the load-bearing innovation.
- Within hours of a bulk account ban, the system mutated its own registration cadence (10s→5s), anti-detection jitter (90s→30s), and switched from serial to 10-thread dispatch — evidence that **short-loop adaptive behavior** is tractable with current-gen models when given a clear stimulus signal.
- Resource tiering was a simple threshold (< 10K credits → conservation mode) but was the difference between survival and flameout. The same pattern applies to Jarvis's Tavily monthly budget, already a known pain point.
- All claimed scale numbers (219 generations, 976 accounts, 11 platforms, 56 GHA workflows, 308 KB bot) are single-sourced from the injured platform's CTO — treat as order-of-magnitude, not precise.
- The svpino tweet does **not** reference svpino's own tools; the only "repos" in-scope are the freeloader's private Cortex (unpublished) and adjacent academic repos (EvoAgentX, CharlesQ9/Self-Evolving-Agents, Darwin Gödel Machine, Live-SWE-agent).

## Context

Eric asked for Jarvis optimizations from this tweet. The highest-leverage patterns absorbable into Jarvis without violating the "skill-first, not agent-first" posture: **(P1)** formalize `memory/work/session_checkpoint.md` into a cold-boot handoff artifact, directly solving the "CTX 60% → new session → lost context" friction; **(P2)** build a Tavily/API-budget sentinel in the dispatcher; **(P3)** add a mutation-proposal tier to the overnight runner so repeated-failure classes trigger a supervised config mutation, not a 10th retry. Self-modifying code via auto-deploy (P5) is **rejected** — matches existing `autonomous-rules.md` anti-patterns.

## Open Questions

- Does `session_checkpoint.md` (uncommitted) already implement P1 or is it a stub?
- Is there a counter in the PostToolUse hook stream that can back a Tavily budget sentinel, or does this need a fresh collector?
- Where does a "mutation proposes → human approves" loop live — new `/propose-mutation` skill, or flag on `/update-steering-rules`?
