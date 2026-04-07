---
topic: Claude API and Anthropic Product Updates
type: technical
date: 2026-04-06
depth: default
slug: claude-api-updates
domain: ai-infra
status: complete
---

# Claude API and Anthropic Product Updates

> Research brief -- April 2026. Covers current model lineup, pricing, SDK changes, and API features.

---

## What It Is

The Anthropic Claude API is the programmatic interface to Claude models -- used for
chat completions, agentic tool use, computer use, and batch processing. The API is
versioned, REST-based, and backed by official Python and TypeScript SDKs.

---

## Current Model Lineup (April 2026)

| Model | Context Window | Output Tokens | Best For |
|-------|---------------|--------------|----------|
| claude-opus-4-6 | 1M tokens | 128K | Complex reasoning, coding agents |
| claude-sonnet-4-6 | 1M tokens | 64K | Balanced performance/cost -- preferred for coding |
| claude-haiku-4-5-20251001 | 200K tokens | 32K | Fast, cheap, high-throughput |

**Key notes:**
- Opus 4.6 and Sonnet 4.6 released February 2026 (Claude 4 family launched May 2025)
- No Claude 3.7 -- versioning jumped from 4.1 -> 4.5 -> 4.6
- Sonnet 4.6 now outperforms prior Opus in coding evaluations
- 1M context window is now GA for Opus 4.6 and Sonnet 4.6 at standard pricing (no beta header, no surcharge)
- Opus 4.6 supports adaptive thinking (type: "adaptive") and fast mode (reduced latency toggle)

---

## Pricing (April 2026)

### API Token Pricing (per 1M tokens)

| Model | Input | Output | Cache Read | Cache Write |
|-------|-------|--------|-----------|------------|
| claude-opus-4-6 | $5.00 | $25.00 | ~$0.50 | ~$6.25 |
| claude-sonnet-4-6 | $3.00 | $15.00 | ~$0.30 | ~$3.75 |
| claude-haiku-4-5 | $1.00 | $5.00 | ~$0.10 | ~$1.25 |

**Price context:** Opus 4.6 is ~67% cheaper than Opus 4.1 era ($15/$75 -> $5/$25).

### Cost Multipliers

| Feature | Effect |
|---------|--------|
| Prompt caching (cache hit) | ~90% savings on input tokens |
| Batch API | 50% off all tokens (24h async window) |
| Combined (cache + batch) | Up to 95% cost reduction |
| Long context (1M) | No surcharge -- standard pricing |

### Consumer Subscription Tiers

- Claude Free: limited access (claude.ai)
- Claude Pro: ~$20/mo (priority access, higher limits)
- Claude Team/Enterprise: custom pricing

---

## API Rate Limits (Usage Tiers)

| Tier | Min Deposit | RPM | Monthly Spend Cap |
|------|-------------|-----|------------------|
| Free | $0 | ~5 | N/A |
| Tier 1 | $5 | 50 | $100 |
| Tier 2 | $40 | ~500 | ~$500 |
| Tier 3 | $200 | 2,000 | $1,000 |
| Tier 4 | $400+ | 4,000 | Uncapped |

- Token bucket algorithm (continuous replenishment, not fixed-interval resets)
- Cached tokens from prompt caching do NOT count toward ITPM limits

---

## SDK Changes (2026)

### Python SDK -- Current Version: 0.79.0 (Feb 2026)

| Version | Key Change |
|---------|-----------|
| 0.75.0 | Opus 4.5 support, computer use updates, autocompaction |
| 0.76.0 | Server-side tools in Messages API |
| 0.77.0 | Structured outputs support |
| 0.78.0 | Opus 4.6 adaptive thinking |
| 0.79.0 | Opus 4.6 fast mode enablement |

**Tool helpers (beta):**
- `@beta_tool` decorator for defining tools as pure Python functions
- Type-safe input validation baked in
- Tool runner for automated tool handling (reduces boilerplate agentic loops)
- SDK discussion thread open for feedback (GitHub discussions/1036)

**Browser support:** SDK can now run in-browser via `dangerouslyAllowBrowser: true`
(CORS headers added to API responses). Flagged: not recommended for production client-side use.

**Java SDK:** Moved from alpha to beta.

### Batch API Enhancement

- `output-300k-2026-03-24` beta header raises single-request output cap to 300K tokens
  for Opus 4.6 and Sonnet 4.6 on the Message Batches API

---

## Key API Features (Current)

### Extended Thinking / Adaptive Thinking
- Opus 4.6 and Sonnet 4.6 support `type: "adaptive"` thinking mode
- Model generates internal reasoning blocks before final response
- Improves output quality on complex multi-step problems
- Counts toward output token cost

### Computer Use Tool
- `computer_20251124` version active for Opus 4.6, Sonnet 4.6, Opus 4.5
- Enhanced: zoom functionality (`enable_zoom: true` + region coordinates)
  allows full-resolution inspection of screen sub-regions

### Tool Use / Function Calling
- Server-side tools now available (v0.76.0)
- Structured outputs support for JSON-mode responses (v0.77.0)
- Tool helpers SDK layer reduces manual schema definition

### Agent SDK (claude-agent-sdk-python)
- Separate repo: `anthropics/claude-agent-sdk-python`
- Bug fix: `type:'sdk'` MCP servers passed via `--mcp-config` no longer dropped at startup
- Supports native multi-agent collaboration patterns
- Designed for Jarvis-style autonomous worktree/dispatch loops

---

## Gotchas and Edge Cases

1. **Adaptive thinking token cost**: Thinking tokens count as output -- can significantly
   inflate costs if thinking budget is uncapped.

2. **Browser SDK flag risk**: `dangerouslyAllowBrowser: true` exposes API keys in
   client-side code. Never use for production web apps.

3. **Batch API SLA**: 24-hour window is a max, not a guarantee. Not suitable for
   real-time use cases.

4. **Rate limit reset behavior**: Token bucket (continuous) -- not hourly reset.
   Burst patterns behave differently than expected under fixed-window assumptions.

5. **1M context GA caveat**: GA for Opus 4.6/Sonnet 4.6 only. Haiku 4.5 remains
   at 200K. Confirm model before assuming long context.

6. **Model ID pinning**: Always pin exact model IDs in production (e.g.
   `claude-haiku-4-5-20251001`) -- Anthropic aliases like `claude-haiku-latest`
   can change behavior at version bumps.

7. **Structured outputs beta**: JSON-mode structured outputs are newer; behavior
   may differ from OpenAI's strict JSON mode. Test edge cases.

---

## Jarvis Integration Notes

- **Current Jarvis model**: claude-sonnet-4-6 (confirmed via session context)
- **Dispatch loop model choice**: Sonnet 4.6 at $3/$15 is the right default --
  outperforms prior Opus in coding, significantly cheaper than Opus 4.6
- **Batch API opportunity**: Overnight autonomous tasks (backtest scoring,
  signal synthesis, research) are natural Batch API candidates (50% savings)
- **Tool helpers SDK**: Worth adopting in Python orchestration scripts to reduce
  tool schema boilerplate in dispatch agents
- **Prompt caching**: High-value for CLAUDE.md + skills context that repeats
  across every dispatch invocation
- **Agent SDK**: Monitor `claude-agent-sdk-python` for MCP stability improvements;
  current bug fixes directly impact Jarvis skill routing

---

## Alternatives and Tradeoffs

| Option | vs Claude API | Use When |
|--------|--------------|----------|
| OpenAI GPT-4o | Similar pricing, weaker coding | Third-party integrations requiring OpenAI compat |
| Google Gemini 2.0 Pro | Cheaper at scale, 2M context | Need > 1M context or multimodal video |
| Local Llama 3 | Zero cost, privacy | Offline-first, non-critical tasks, embedding |
| Bedrock/Vertex | Same models, added latency/cost | Enterprise compliance requirements |

---

## Open Questions

1. Will Batch API gain sub-hour SLAs for mid-priority autonomous tasks?
2. When do tool helpers graduate from beta to stable SDK feature?
3. Is there a Claude 5 roadmap signal -- capability jump expected, or incremental versioning?

---

## Sources

- Anthropic API Docs -- Models Overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Anthropic API Docs -- Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic Release Notes: https://platform.claude.com/docs/en/release-notes/overview
- Releasebot Anthropic Tracker: https://releasebot.io/updates/anthropic
- Python SDK GitHub: https://github.com/anthropics/anthropic-sdk-python
- Agent SDK GitHub: https://github.com/anthropics/claude-agent-sdk-python
- Rate Limits Docs: https://platform.claude.com/docs/en/api/rate-limits
- Finout Pricing Guide: https://www.finout.io/blog/claude-pricing-in-2026-for-individuals-organizations-and-developers
- Morph API Pricing Analysis: https://www.morphllm.com/anthropic-api-pricing

---

## Next Steps

- `/first-principles` -- evaluate Batch API adoption for overnight Jarvis tasks
- Run cost projection: current dispatch volume * Sonnet 4.6 pricing with prompt caching
- Monitor `claude-agent-sdk-python` releases for MCP stability improvements
