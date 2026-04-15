# Autonomous Coding Agent Capabilities and Claude API Economics

## Overview

Covers coding agent performance benchmarks (SWE-bench Verified) and Claude API pricing/SDK features as of 2026-04-06. Core finding: scaffolding architecture quality dominates model complexity; layered API cost optimizations enable economically viable autonomous overnight runners.

## Key Findings

### Coding Agent Benchmarks (Article 2, 2026-04-06)
- Claude Code (Opus 4.5) holds highest public SWE-bench Verified score: 80.8%.
- mini-SWE-agent (100 lines Python) achieves 74% -- outperforms complex multi-agent frameworks on the same benchmark.
- Devin 2.0 achieves 13.86% on full SWE-bench (different benchmark variant from SWE-bench Verified -- not directly comparable to Claude Code's score).
- Scaffolding beats model complexity: architectural correctness of the harness matters more than framework sophistication.
- SWE-bench measures GitHub issue resolution only -- not a proxy for production task quality, deploy safety, or multi-step autonomous work.

### Claude API Economics (Article 3, 2026-04-06)
- Current model tier: Opus 4.6 ($5/$25), Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5) per 1M tokens input/output.
- Opus 4.6 is 67% cheaper than prior Opus generation; Sonnet 4.6 now preferred over old Opus for coding tasks at lower cost.
- 1M token context window is GA at standard pricing for Opus 4.6 and Sonnet 4.6 -- no surcharge, no beta header required.
- Batch API: 50% token discount for 24h async processing.
- Prompt caching: ~90% savings on repeated context blocks.
- Combined Batch + caching: up to 95% cost reduction -- primary lever for autonomous overnight dispatcher workers.

### Jarvis Implications
- Dispatcher workers should default to Sonnet 4.6 for coding tasks; escalate to Opus 4.6 only when output quality requires it.
- All overnight batch jobs should use Batch API + prompt caching; do not run synchronous API calls for non-interactive dispatcher tasks.
- Mini-SWE-agent architecture principle validates epdev's scaffolding-first design -- do not over-engineer orchestration layers.

## Source Articles
- 2026-04-06_autonomous-coding-agents.md (raw_article, confidence 8)
- 2026-04-06_claude-api-updates.md (raw_article, confidence 8)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] SWE-bench Verified 80.8% for Claude Code assumes the Verified subset is representative of real-world coding tasks; benchmark composition changes over time and the Verified subset may exclude the hardest cases by design.
- [ASSUMPTION] "Scaffolding beats model complexity" conclusion drawn from one data point (mini-SWE-agent vs complex frameworks) -- may not generalize outside SWE-bench's GitHub-issue-resolution scope; broader task diversity untested.
- [FALLACY] Comparing Devin 2.0's 13.86% (full SWE-bench) against Claude Code's 80.8% (SWE-bench Verified) implies equivalence where none exists -- false dichotomy; the two scores are not comparable without normalization.
- [FALLACY] "Up to 95% cost reduction" (Batch + caching) is a ceiling estimate assuming maximum cache hit rate and full batch utilization -- actual savings depend heavily on workload cache locality and batch fill rate; appeal to best-case framing.
- [ASSUMPTION] Pricing data reflects 2026-04-06 snapshot; Anthropic pricing and model availability change without advance notice -- reverify before cost modeling any new project.