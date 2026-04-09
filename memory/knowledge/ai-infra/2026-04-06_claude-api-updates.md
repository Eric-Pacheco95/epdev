---
domain: ai-infra
source: /research
date: 2026-04-06
topic: Claude API and Anthropic Product Updates (Models, SDK, Pricing)
confidence: 8
source_files:
  - memory/work/claude-api-updates/research_brief.md
tags: [claude, anthropic, api, pricing, sdk, models, agents]
---

## Key Findings

- Current model tier: Opus 4.6 ($5/$25), Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5) per 1M tokens -- Opus 4.6 is 67% cheaper than prior Opus generation; Sonnet 4.6 now preferred over old Opus for coding
- 1M token context window is GA at standard pricing for Opus 4.6 and Sonnet 4.6 (no surcharge, no beta header required)
- Batch API gives 50% token discount for 24h async processing; prompt caching gives ~90% savings on repeated context; combining both = up to 95% cost reduction -- major lever for autonomous overnight Jarvis tasks
- Python SDK v0.79.0 added tool helpers (beta): define tools as Python functions with `@beta_tool`, type-safe validation, automated tool runner -- reduces agentic loop boilerplate significantly
- Adaptive thinking (`type: "adaptive"`) available on Opus 4.6 and Sonnet 4.6 -- thinking tokens count toward output cost; Opus 4.6 supports up to 128K output tokens

## Context

Jarvis currently runs on claude-sonnet-4-6, which is the right default -- it outperforms the prior Opus generation on coding benchmarks at a fraction of the cost. The Batch API and prompt caching together represent a significant cost optimization opportunity for the autonomous dispatch pipeline, where the same CLAUDE.md + skills context repeats on every invocation. The tool helpers beta is worth tracking for simplifying tool schema management in Python orchestration scripts.

## Open Questions

- When do tool helpers graduate from beta to stable SDK release?
- Will Batch API gain sub-hour SLAs for mid-priority autonomous tasks (vs current 24h max)?
- Claude 5 roadmap -- capability jump or continued incremental versioning?
