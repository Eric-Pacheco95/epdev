# Overnight Run Report — external_monitoring

- Date: 2026-04-03
- Branch: jarvis/overnight-2026-04-03
- Dimension: external_monitoring
- Baseline metric: 26 (last_checked count in sources.yaml)
- Final metric: 26
- Iterations: 8
- Kept: 8
- Discarded: 0

## Summary

Checked all 26 sources across 3 tiers for new content since last monitoring pass (2026-03-30 for most, 2026-04-01 for YouTube). Updated all `last_checked` timestamps to 2026-04-03. Fixed 2 stale URLs (LangChain .dev->.com, Microsoft AI redirect). Identified 2 sources returning 403 (OpenAI Blog, CoinDesk RSS).

## Key Findings

### HIGH PRIORITY — Action Items for Eric

1. **Claude Code v2.1.91** (Apr 2) — MCP tool result persistence override, `disableSkillShellExecution` setting, multi-line prompt support in deep links. **v2.1.90** (Apr 1) — `/powerup` interactive lessons, `--resume` prompt-cache fix, PowerShell security hardening.
2. **Gemma 4 launched** (Apr 2) — Google DeepMind open models (2B-31B), vision-capable, Apache 2.0. Trending on HN, covered by Willison, HuggingFace, Latent Space.
3. **CVE-2025-55182 Next.js breach** (Apr 3) — 766 hosts compromised via React2Shell, credential theft.
4. **Schneier: US bans foreign routers** (Apr 2) + **iPhone hacking tool "Coruna" leaked** (Apr 2).
5. **GitHub Copilot `/fleet`** (Apr 1) — parallel multi-agent execution in Copilot CLI. Relevant to Jarvis autonomous execution design.

### NOTABLE — AI/LLM Ecosystem

- **Qwen3.6-Plus** — real-world agents focus (HN trending)
- **OpenAI acquires TBPN** (HN)
- **Cursor 3** released (HN trending)
- **AMD Lemonade** — open-source local LLM server using GPU+NPU
- **LangChain**: open models crossing threshold on agent tasks; MongoDB partnership
- **HuggingFace**: Holo3 computer use, Falcon Perception, Granite 4.0 3B Vision, TRL v1.0
- **Zvi AI #162**: Anthropic Mythos model leaked, OpenAI $122B funding round
- **Latent Space**: causal world models episode (Moonlake)
- **Willison**: agentic engineering podcast on Lenny's, llm-gemini 0.30

### NOTABLE — Security

- **TheHackerNews**: Cisco 9.8 CVSS IMC/SSM flaw, mining ops via ISO lures, trusted OSS report
- **Schneier**: US "hackback" policy debate
- **Krebs**: no new posts since Mar 23

### NOTABLE — Crypto

- **$169M stolen from 34 DeFi protocols in Q1** (CoinTelegraph)
- **BTC supply in profit heading toward bear market levels** — 8.2M BTC at a loss
- **Stablecoins flip ACH volume** — $7.2T vs $6.8T in February
- **Circle launching cirBTC** wrapped Bitcoin

### Feed Health Issues

| Source | Issue | Action |
|--------|-------|--------|
| OpenAI Blog | 403 (no feed URL, scraping blocked) | Need feed_url or API |
| CoinDesk RSS | 403 blocked | Feed may require auth header |
| LangChain Blog | 301 redirect .dev -> .com | URL updated in sources.yaml |
| Microsoft AI Blog | 301 redirect | URL updated in sources.yaml |

## Metric Note

The metric (last_checked count) stays at 26 because no new sources were added. All iterations updated existing timestamps. All 26/26 sources now have `last_checked: "2026-04-03"`.

## Run Log

| Iteration | Commit Hash | Metric Value | Delta | Status | Description |
|-----------|-------------|-------------|-------|--------|-------------|
| 0 (baseline) | fb5ac84 | 26 | - | - | Baseline measurement |
| 1 | f42a177 | 26 | 0 | kept | Anthropic Blog + Claude Code releases |
| 2 | 20b9d91 | 26 | 0 | kept | Simon Willison + Daniel Miessler |
| 3 | f91aac7 | 26 | 0 | kept | HN + YouTube sources |
| 4 | b27e19e | 26 | 0 | kept | OpenAI, Krebs, TheHackerNews |
| 5 | 793f507 | 26 | 0 | kept | LangChain, HuggingFace, Fabric, OWASP |
| 6 | 32b0cf0 | 26 | 0 | kept | Latent Space, CoinDesk, CoinTelegraph |
| 7 | 0ebcae1 | 26 | 0 | kept | DeepMind, Meta AI, Schneier |
| 8 | 76f9bb6 | 26 | 0 | kept | MS AI, Python, Node, GitHub, Zvi |
