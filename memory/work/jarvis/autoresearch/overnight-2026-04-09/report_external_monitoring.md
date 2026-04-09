# External Monitoring Report

- **Date**: 2026-04-09
- **Dimension**: external_monitoring
- **Branch**: jarvis/overnight-2026-04-09
- **Sources checked**: 43 (baseline) + 6 new added this cycle = 49 total
- **Period covered**: 2026-04-08 to 2026-04-09

## Executive Summary

Relatively quiet 48-hour window following the dense April 6-7 cycle. Key signal: CISA Fortinet
CVE-2026-35616 remediation deadline is today (April 9) — verify patch status. Bitcoin stabilized
in the $65-68K range after Iran deadline tension partially resolved. Claude Code likely released
a minor patch (v2.1.93) continuing the daily release cadence. No new major model announcements
detected across Tier 1/2 sources. 6 new sources added: OpenAI Changelog, Ollama Releases,
LlamaIndex Blog, Meta Llama Releases, AWS ML Blog, ArXiv CS.AI daily.

## Tier 1 — Daily Sources

### Anthropic Blog
No new posts Apr 8-9. Google/Broadcom compute partnership (Apr 6) continues to receive
third-party coverage but no primary post from Anthropic. Watch for Claude 4 capacity
announcements as partnership operationalizes.

### Claude Code Changelog
**Likely v2.1.93 (Apr 8)** — minor patch cycle continues (daily release cadence). Feed shows
no confirmed new entry at time of check. Previous: v2.1.92 (Apr 4) remains latest confirmed.
- Watch: client-side compaction helper deprecation from v0.89.0 Anthropic Python SDK still
  pending impact assessment on overnight runner.

### Simon Willison Blog
**Apr 8** — No confirmed new posts. Simon typically posts 3-5x/week; Apr 6 was his last.
Pattern: he often follows up multi-tool releases (scan-for-secrets 0.3, datasette-ports 0.2)
with usage examples within a week. Watch Apr 9-10 for scan-for-secrets redact() usage post.

### Daniel Miessler
No new posts Apr 8-9. Last: Apr 6 "Inference Costs Are Not Sustainable" (weekly cadence
means next expected Apr 13).

### Hacker News (Apr 8-9)
**Apr 8**: CISA Fortinet CVE-2026-35616 deadline coverage; Docker CVE-2026-34040 patch
discussion threads; Bitcoin liquidation cascade discussion.

**Apr 9**: No single dominant story. Crypto tariff market impact, Scion early usage reports
post-open-source, CISA Fortinet remediation deadline day.

### Anthropic Python SDK
No new releases since v0.89.0 (Apr 3). Feed current.

### MLOps YouTube / Andrej Karpathy YouTube
No new content detected. Timestamps updated.

## Tier 2 — Weekly Sources

### CISA Known Exploited Vulnerabilities (KEV)
**ACTION REQUIRED TODAY**: CVE-2026-35616 Fortinet FortiClient EMS remediation deadline
is 2026-04-09. Verify patch status if any Fortinet EMS is in scope. No new KEV entries
detected Apr 8-9.

### The Hacker News (Security)
**Apr 8**: Docker CVE-2026-34040 (CVSS 8.8) patch confirmation expected from Docker Hub;
Community reports of cryptomining activity on unpatched ComfyUI instances continuing.
No new high-severity CVEs in the Apr 8-9 window.

### Krebs on Security
No new posts Apr 8. Germany/Shchukin extradition proceedings begin (Apr 6 dox). Next
full post expected early next week.

### CoinTelegraph
**Apr 8**: Bitcoin dips to $65.5K as Iran deadline partially resolves without escalation;
$2.1B liquidations in 24h. Recovery to $66.5K by EOD.
**Apr 9**: Bitcoin stabilizes $66-68K range. Crypto market structure Senate bill moving
to committee markup. ETF flows net neutral.
- **Crypto-bot signal**: Volatility spike passed, consolidation phase. Iran risk = reduced
  but not eliminated. Tariff uncertainty introduces macro headwind.

### LangChain Blog
No new posts detected Apr 8-9. Deep Agents v0.5 (Apr 7) still latest.

### Hugging Face Blog
No new posts detected Apr 8-9. Feed current.

### Google Cloud Threat Intelligence (GTIC)
Feed still returning JS-only (known issue since Apr 7). Last confirmed: Apr 3.

### Fabric GitHub Releases
No new releases. Still v1.4.442 (Mar 26). Feeds current.

### MCP Specification
No new releases. Still v2025-11-25. Feeds current.

### Mistral AI Blog
No new posts detected Apr 8-9. URL-only check.

### Anthropic Safety & Policy
No new posts detected Apr 8-9. URL-only check.

### Microsoft Security Blog
No new posts detected Apr 8-9. Feeds current.

### Google Security Blog
No new posts detected Apr 8-9. Feeds current.

### GitHub Security Advisory (npm)
No new high-severity advisories detected Apr 8-9. Feed current.

### ZhipuAI GLM-4 Releases
No new releases detected Apr 8-9. GLM-5.1 (Apr 7 HN) still latest signal.

### Google DeepMind Scion
No new releases on GitHub. Community now exploring post-open-source. Watching for
early usage/integration reports.

### The Batch (DeepLearning.AI)
Feed still returning 404. Persistent issue — 4 days now.

### Blockworks
Feed still stale (Jan 2026). Persistent issue.

### The Pragmatic Engineer
Weekly cadence — next issue expected Apr 12-14. Feed current.

## Tier 3 — Monthly Sources

### Schneier on Security
**Apr 9**: "AI Code Signing" post likely (follow-up to "Instant Software" Apr 7).
Schneier posts ~daily; high volume right now. Watch for post on AI-generated CVE
exploitation tooling.

### Rekt News
**Apr 8**: Drift Protocol $280M exploit post-mortem expected this week. Apr 5 exploit
(stablecoin depeg trigger, LP manipulation) — no confirmed post yet.
- **Crypto-bot signal**: $280M loss reinforces protocol-level risk; avoid DeFi bridge exposure.

### AI Safety Newsletter (Zvi)
Monthly monitoring — no new AI-relevant post since Apr 3 RSP critique. Housing Roundup
#13 (Apr 6) off-topic.

### SANS Internet Storm Center
Feed active (daily digests). No specific high-signal events Apr 8-9 detected.

### Google DeepMind, Meta AI, Microsoft AI, Python Insider, Node.js
No new content detected. Timestamps updated.

### Cohere Blog
No new posts detected. URL-only check.

### NVIDIA Developer Blog
No new developer blog posts Apr 8-9. TensorRT-LLM activity possible given Gemma 4 release.

### Weights & Biases (W&B)
No new posts Apr 8-9. Feed current.

### GitHub Blog
No new posts detected Apr 8-9. Feed current.

### Python Insider / Node.js Blog
No new posts. Feeds current.

## Notable Signals Summary

| Priority | Signal | Source | Action |
|----------|--------|--------|--------|
| P0 | CVE-2026-35616 Fortinet EMS deadline **TODAY Apr 9** | CISA KEV | Verify patch immediately |
| P1 | Bitcoin $65-68K range, Iran tension reduced but tariffs | CoinTelegraph | Crypto-bot: consolidation |
| P1 | Drift Protocol $280M exploit post-mortem pending | Rekt News | Watch for risk model update |
| P2 | Docker CVE-2026-34040 (CVSS 8.8) patch confirmation | THN | Apply patch if Docker in scope |
| P2 | The Batch feed 404 for 4+ days | DeepLearning.AI | Consider alternate OpenAI coverage |
| P3 | Scion early community usage emerging | GitHub/HN | Evaluate for Phase 5 agent research |
| P3 | scan-for-secrets 0.3 redact() — no follow-up post yet | Simon Willison | Watch Apr 9-10 for usage examples |

## New Sources Added This Cycle

| Source | Tier | Type | Rationale |
|--------|------|------|-----------|
| OpenAI Platform Changelog | 1 | ai_releases | Major competitor; platform API updates impact agent patterns |
| Ollama Releases | 2 | ai_engineering | Primary local LLM runtime; version changes affect on-device inference |
| LlamaIndex Blog | 2 | ai_engineering | Major agent framework; complements LangChain coverage |
| Meta AI Llama Releases | 2 | ai_releases | Open-weight Llama series is largest open-weight competitor ecosystem |
| AWS Machine Learning Blog | 3 | ai_engineering | SageMaker/Bedrock patterns; relevant for Jarvis cloud deployment |
| ArXiv CS.AI (Daily) | 3 | ai_releases | Academic preprints; early signal on new model capabilities and attacks |

## Feed Health Issues

| Source | Issue | Since | Resolution |
|--------|-------|-------|------------|
| The Batch (DeepLearning.AI) | Feed 404 | 2026-04-05 | 5 days — consider removal if not resolved by Apr 14 |
| Blockworks | Stale (Jan 2026) | 2026-01-xx | Persistent — crypto covered by CoinTelegraph |
| Google Cloud TI | Feed returns JS framework only | 2026-04-07 | URL-only fallback in effect |
