# External Monitoring Report

- **Date**: 2026-04-07
- **Dimension**: external_monitoring
- **Branch**: jarvis/overnight-2026-04-07
- **Sources checked**: 41 (38 baseline + 3 new added this cycle)
- **Period covered**: 2026-04-06 to 2026-04-07

## Executive Summary

Full monitoring pass across all registered sources. Key signals: Anthropic secured
multi-gigawatt compute with Google/Broadcom; Docker CVE-2026-34040 (CVSS 8.8) is an
exploitable auth plugin bypass; CISA KEV added Fortinet FortiClient EMS with a
2026-04-09 remediation deadline; scan-for-secrets 0.3 adds programmatic redaction;
Google open-sourced Scion multi-agent orchestration testbed. Bitcoin at $68K with
Iran deadline and mixed ETF signals. 3 new sources added: The Pragmatic Engineer,
NVIDIA Developer Blog, Weights & Biases Blog.

## Tier 1 — Daily Sources

### Anthropic Blog
**New (Apr 6)**: Anthropic expands partnership with Google and Broadcom for multiple
gigawatts of next-generation compute infrastructure.
- Signal: Major infrastructure commitment signals Anthropic is aggressively scaling
  for Claude 4/5 inference. Positive for long-term API capacity and rate limit headroom.

### Claude Code Changelog
**No new releases since v2.1.92 (Apr 4)**. Feeds current.
- v2.1.92: Bedrock setup wizard, /cost per-model breakdown, Write tool 60% faster,
  remote settings forceRemoteSettingsRefresh, /release-notes interactive, /tag and /vim removed.

### Simon Willison Blog
**New (Apr 6)**:
1. **Google AI Edge Gallery** — Official iOS app for running Gemma 4 (E2B, 2.54GB)
   locally on iPhone with Agent Skills demo (tool calling + interactive widgets).
   Stability issues noted. Relevant: device inference is becoming real.
2. **scan-for-secrets 0.3** — New `-r/--redact` flag and `redact_file()` Python API
   for programmatic secret redaction with escape-aware replacement.
   **Action signal**: evaluate for epdev security validation pipeline.
3. **datasette-ports 0.2** — Removed Datasette dependency; `uvx datasette-ports`
   now standalone.
4. **Cleanup Claude Code Paste** — Tool to strip formatting artifacts from Claude
   Code terminal output (useful for session log processing).

### Daniel Miessler
**New (Apr 6)**: "Inference Costs Are Not Sustainable" — Claude Code burning
significant subscription budget within hours of a session. Advocates multi-model
routing and local/cloud hybrid. Aligned with Jarvis overnight cost-reduction direction.

### Hacker News
**Top items (Apr 7)**:
1. **Cloudflare targets 2029 for full post-quantum security** — roadmap published.
2. **Google open-sources Scion** — experimental multi-agent orchestration testbed
   (DeepMind). Worth evaluating for Phase 5 agent research patterns.
3. **GLM-5.1: Towards Long-Horizon Tasks** — ZhipuAI open model for extended
   multi-step task completion. Previously GLM-5 matched closed frontier on agent tasks
   (per LangChain, Apr 2).
4. **"Good Taste the Only Real Moat Left"** — aesthetic judgment as competitive
   advantage in AI-saturated market.

### Anthropic Python SDK
**No new releases since v0.89.0 (Apr 3)**. Feeds current.
- Watch: client-side compaction helper deprecation in v0.89.0 may affect overnight runner.

### MLOps YouTube / Andrej Karpathy YouTube
No new content detected. Timestamps updated.

## Tier 2 — Weekly Sources

### The Hacker News (Security)
**New (Apr 7)**:
1. **Docker CVE-2026-34040** (CVSS 8.8) — incomplete patch for prior Docker auth
   plugin bypass. Attackers circumvent authorization plugins under specific conditions.
   **Action**: verify epdev Docker version; apply patch if exposed.
2. **1,000+ exposed ComfyUI instances** — cryptomining + proxy botnet. Python
   scanner sweeps major cloud IP ranges continuously. Novel scan-and-exploit pattern.
3. **GPUBreach / GDDRHammer** — academic RowHammer attack on GDDR6 memory enabling
   full CPU privilege escalation via GPU bit-flips. New hardware attack class.

### Krebs on Security
**New (Apr 6)**: Germany doxes "UNKN" — Daniil Shchukin (31, Russia) identified as
head of GandCrab and REvil ransomware gangs. 130+ German victims (2019-2021), EUR 35M
damage. Double extortion pioneers. 14-day silence on Krebs now resolved.

### LangChain Blog
**New (Apr 7)**:
1. **Deep Agents v0.5** — incremental agent framework update.
2. **Arcade.dev tools in LangSmith Fleet** — tool integration for LangSmith monitoring.

### CISA Known Exploited Vulnerabilities (KEV)
**New (Apr 6)**: CVE-2026-35616 — Fortinet FortiClient EMS Improper Access Control
(CWE-284). Unauthenticated remote code execution via crafted requests.
**Remediation deadline: 2026-04-09** — 2 days remaining from report date.

### CoinTelegraph
**New (Apr 6-7)**:
1. **Bitcoin at $68K** with Iran deadline pressure. Analyst warns potential $15K
   shakeout toward $54K over next 5 months (technical basis).
2. **Bitcoin ETF inflows $471M** — highest daily inflow since late February.
   Renewed institutional demand signal.
3. **CME Group adds Avalanche and Sui futures** (pending regulatory approval).
4. **US Senate Banking confirms April timeline** for crypto market structure legislation.
5. **Chaos Labs exits Aave** as risk provider over Aave v4 migration concerns.
- **Crypto-bot signal**: Mixed. Bullish institutional (ETF) vs bearish geopolitical
  (Iran) + technical (shakeout thesis). Range-bound/volatile near term.

### Google Cloud Threat Intelligence (GTIC)
Feed returned JS framework only on Apr 7 check (known issue). Last confirmed entry:
Apr 3 — axios supply chain attributed to NK UNC1069 (WAVESHAPER.V2 backdoor).

### Fabric GitHub Releases
No new releases since v1.4.442 (Mar 26). Feeds current.

### Hugging Face Blog
No new posts since Apr 2 (Gemma 4). Feeds current.

### MCP Specification
No new releases. Still on v2025-11-25 stable. Feeds current.

### Anthropic Safety & Policy
No new posts since Apr 1 (RSP v3.0). URL-only check.

### Microsoft Security Blog
No new posts since Apr 1 (axios mitigation guide). Feeds current.

### Google Security Blog
No new posts since Apr 2 (prompt injection defense). Feeds current.

### GitHub Security Advisory (npm)
No new high-severity advisories since Apr 4. Feeds current.

### Mistral AI Blog
No new posts since Mar 31. URL-only check.

### Blockworks
Feed still stale (Jan 2026 entries) — persistent issue. Crypto covered by CoinTelegraph.

### The Batch (DeepLearning.AI)
Feed still returning 404. Ongoing issue.

## Tier 3 — Monthly Sources

### Schneier on Security
**New (Apr 6-7)**:
1. **"Cybersecurity in the Age of Instant Software"** (Apr 7) — AI-generated custom
   software at scale; attacker/defender dynamics shift when every device can have
   bespoke code. Core Jarvis-adjacent theme for TELOS G2/G5.
2. **"Hong Kong Police Can Force Encryption Key Disclosure"** (Apr 7) — NSL amendments
   criminalize refusal; applies to airport transit. Relevant for travel OPSEC.
3. **"New Mexico's Meta Ruling and Encryption"** (Apr 6) — court frames E2E encryption
   as design choice enabling harm. Threat to encryption industry-wide.

### GitHub Blog
**New (Apr 6)**: "GitHub Copilot CLI combines model families for a second opinion" —
multi-model routing similar to Jarvis multi-model strategy. Validates pattern.

### AI Safety Newsletter (Zvi)
**New (Apr 6)**: Housing Roundup #13 — off-topic housing policy. No AI content this cycle.

### SANS ISC
**New (Apr 7)**: ISC Stormcast ep 9882 (audio format; minimal textual detail in RSS).

### Rekt News
No confirmed new post for Drift Protocol $280M exploit (expected; CoinTelegraph
coverage confirms exploit occurred Apr 5). Post-mortem likely this week.

### Google DeepMind, Meta AI, Microsoft AI, Python Insider, Node.js, Cohere
No new content detected. Timestamps updated.

## Notable Signals Summary

| Priority | Signal | Source | Action |
|----------|--------|--------|--------|
| P0 | CVE-2026-35616 Fortinet EMS — deadline 2026-04-09 | CISA KEV | Patch if exposed |
| P1 | Docker CVE-2026-34040 (CVSS 8.8) auth bypass | THN | Check epdev Docker version |
| P1 | scan-for-secrets 0.3 redact capability | Simon Willison | Evaluate for security pipeline |
| P2 | GPUBreach RowHammer GDDR6 privilege escalation | THN | Note new hardware attack class |
| P2 | Bitcoin ETF $471M + Iran deadline tension | CoinTelegraph | Crypto-bot: mixed signals |
| P2 | Google Scion agent testbed open-sourced | HN | Evaluate for Phase 5 research |
| P3 | Anthropic compute expansion (Google/Broadcom GW) | Anthropic Blog | Positive for long-term capacity |
| P3 | Inference costs unsustainable (Miessler) | Daniel Miessler | Align with cost-tracking goal |
| P3 | Copilot CLI multi-model second-opinion routing | GitHub Blog | Validates Jarvis multi-model pattern |
| P3 | Schneier: AI Instant Software security paradigm | Schneier | Feed into learning synthesis |

## New Sources Added This Cycle

| Source | Tier | Type | Rationale |
|--------|------|------|-----------|
| The Pragmatic Engineer | 2 | ai_engineering | Gergely Orosz weekly; covers Copilot, AI coding tools, dev market |
| NVIDIA Developer Blog | 3 | ai_engineering | GPU/CUDA; on-device inference; GPUBreach hardware context |
| Weights & Biases Blog | 3 | ai_engineering | MLOps, LLM eval, production monitoring; complements LangSmith |

## Feed Health Issues

| Source | Issue | Since |
|--------|-------|-------|
| The Batch (DeepLearning.AI) | Feed 404 | 2026-04-05 |
| Blockworks | Stale (Jan 2026) | 2026-01-xx |
| Google Cloud TI | Feed returns JS framework only | 2026-04-07 |
