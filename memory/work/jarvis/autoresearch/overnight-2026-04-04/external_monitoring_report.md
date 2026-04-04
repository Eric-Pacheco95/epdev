# Overnight Run Report — external_monitoring

- Date: 2026-04-04
- Branch: jarvis/overnight-2026-04-04
- Dimension: external_monitoring
- Baseline metric: 26 (last_checked count in sources.yaml)
- Final metric: 28
- Iterations: 6
- Kept: 6
- Discarded: 0

## Summary

Checked all 26 sources (now 28 after additions) across 3 tiers for new content since last monitoring pass (2026-04-03). Updated all `last_checked` timestamps to 2026-04-04. Annotated `last_notable` fields with key findings per source. Fixed 1 stale URL (Blockworks 308 redirect: blockworks.co -> blockworks.com). Added 2 new high-value security sources: Google Cloud Threat Intelligence (Mandiant/GTIG) and Microsoft Security Blog.

Today's signal density is high — two critical security events (axios supply chain attack, OpenClaw CVE) and one significant Claude Code release (v2.1.92) all landed within 24h.

---

## Key Findings

### CRITICAL — Action Required

1. **OpenClaw CVE-2026-33579** (CVSS 8.6 HIGH, Apr 3-4)
   - Privilege escalation in OpenClaw via `/pair approve` command path (CWE-863, incorrect authorization)
   - 63% of 135,000+ public instances run without authentication — full admin takeover by any network visitor
   - Fix: update to OpenClaw >= 2026.3.28 immediately
   - **Also**: Anthropic is removing Claude Code subscription support for OpenClaw (HN top story Apr 4)
   - *Action*: If Eric uses OpenClaw, update or stop using it. This is also a Jarvis security posture signal — any tooling that pairs with Claude Code is an attack surface.

2. **Axios npm Supply Chain Compromise (North Korea UNC1069)** (Apr 1-3)
   - DPRK threat actor compromised axios npm package (100M+ weekly downloads) for ~3 hours (Mar 31 00:21-03:20 UTC)
   - Malicious versions 1.14.1 and 0.30.4 deployed WAVESHAPER.V2 backdoor (Windows/macOS/Linux)
   - Attack vector: social engineering of package maintainer via fake company founder identity
   - Attributed by Google Cloud/GTIG, mitigated by Microsoft, covered by THN/Palo Alto/Tenable
   - *Action*: Verify node_modules in crypto-bot and any other JS projects do not have axios 1.14.1 or 0.30.4 installed. Run `npm ls axios` in affected repos.

### HIGH PRIORITY — AI Tool Updates

3. **Claude Code v2.1.92** (Apr 4 — today)
   - Interactive Bedrock setup wizard for AWS auth + model pinning
   - `/cost` now shows per-model and cache-hit breakdown
   - `/release-notes` now has interactive version picker
   - Write tool diff computation 60% faster
   - `/tag` and `/vim` commands removed
   - **v2.1.91** (Apr 2): MCP tool result persistence override (up to 500K chars via `_meta["anthropic/maxResultSizeChars"]`)
   - **v2.1.89** (Apr 1): Named subagents in `@` mention typeahead; "defer" permission for PreToolUse hooks in headless sessions

4. **Vulnerability Research Is Cooked** (Willison/Ptacek, Apr 3-4)
   - Frontier AI models dramatically accelerating exploit development speed
   - Kernel security reports: 2-3/week -> 5-10/day since early 2026 (Tarreau)
   - cURL maintainer spending hours/day on AI-generated security reports
   - *Signal*: AI is compressing the window between disclosure and exploitation — security patching velocity matters more than ever

5. **Gemma 4 Launch** (Google DeepMind, Apr 2) — confirmed by HuggingFace, Latent Space, HN
   - Open models 2B-31B, multimodal/vision capable, Apache 2.0
   - Immediate ecosystem support: vLLM, llama.cpp, Ollama
   - Relevant for Jarvis model routing: Gemma 4 as a local option for extraction/classification tasks

### NOTABLE — AI/LLM Ecosystem

- **LangChain (Apr 3)**: Self-healing agents in production — auto-PR on detected regression; demonstrates production-grade agentic reliability pattern
- **LangChain (Apr 2)**: Open models (GLM-5, MiniMax M2.7) crossing threshold on agent tasks — file ops, tool use, instruction following at frontier quality
- **Marc Andreessen on Latent Space (Apr 3)**: AI as "80-year overnight success" — reasoning + agents "actually working" now differs from prior cycles; infrastructure buildout risk lower than dot-com due to immediate demand
- **HuggingFace Holo3 (Apr 1)**: New computer use frontier model — relevant to Jarvis agentic capability tracking
- **GitHub velocity (Apr 4)**: 275M commits/week, 2.1B GitHub Actions minutes/week — platform-level indicator of AI-assisted dev surge
- **Daniel Miessler (Mar 28)**: "Soft AGI" vs "Hard AGI" distinction — economically significant threshold is Soft AGI (onboard, learn, execute knowledge work); useful framing for Jarvis's mission positioning
- **Latent Space/Andreessen**: "Death of the Browser" framing — agents replacing browser-based workflows

### NOTABLE — Security

- **Schneier (Apr 3)**: WebinarTV company secretly recording and publishing Zoom meetings without consent — relevant to Claude Code session security (transcripts stored by Anthropic noted in CLAUDE.md)
- **Schneier (Apr 2)**: US bans all foreign-made consumer routers — FCC approval required for import/sale; supply chain security policy shift
- **THN (Apr 3)**: China-linked TA416 resumes targeting European governments with PlugX (after 2-year lull)
- **THN (Apr 3)**: PHP web shells using HTTP cookies as command channels — evades URL-based detection
- **Krebs**: No new posts since March 23 (CanisterWorm wiper targeting Iran). Monitor for resumption.

### NOTABLE — Crypto

- **CoinTelegraph (Apr 4)**: Tether potentially delaying fundraising if demand falls short at $500B valuation — macro signal for stablecoin market confidence
- *Blockworks feed is stale* (last content Jan 2026 despite URL fix) — may need alternative institutional crypto source in next review

---

## Feed Health Issues

| Source | Issue | Action |
|--------|-------|--------|
| Blockworks | 308 permanent redirect .co -> .com (fixed); feed content stale since Jan 2026 | URL updated; monitor for feed recovery; consider adding Decrypt.co as backup |
| Krebs on Security | No new posts since Mar 23 | Monitor for resumption |
| OWASP News | No feed_url configured | Low priority — security coverage via Krebs/THN sufficient |
| MLOps YouTube / Karpathy YouTube | No feed_url (YouTube RSS not supported) | Manual check only; low frequency signal |
| Google DeepMind Blog | No feed_url | Manual check only |
| Meta AI Blog | No feed_url | Manual check only |
| Microsoft AI Blog | No feed_url | Manual check only |

## New Sources Added

| Source | Type | Tier | Rationale |
|--------|------|------|-----------|
| Google Cloud Threat Intelligence | security | 2 | Primary Mandiant/GTIG attribution source; produced axios/UNC1069 attribution |
| Microsoft Security Blog | security | 2 | MSRC + Defender research; first coverage of axios mitigation; Patch Tuesday complement to Krebs |

---

## Run Log

| Iteration | Commit Hash | Metric Value | Delta | Status | Description |
|-----------|-------------|-------------|-------|--------|-------------|
| 0 (baseline) | 09272e3 | 26 | - | - | Baseline measurement |
| 1 | 89d3355 | 26 | 0 | kept | Tier 1 timestamps -> 2026-04-04 + findings annotated |
| 2 | 25a075a | 26 | 0 | kept | Tier 2 timestamps -> 2026-04-04 + Blockworks URL fix |
| 3 | 66db50d | 26 | 0 | kept | Tier 3 timestamps -> 2026-04-04 + findings annotated |
| 4 | 2cec113 | 27 | +1 | kept | Add Google Cloud Threat Intelligence (Tier 2 security) |
| 5 | 6f1e253 | 28 | +1 | kept | Add Microsoft Security Blog (Tier 2 security) |
| 6 | — | 28 | 0 | kept | Write this monitoring report |
