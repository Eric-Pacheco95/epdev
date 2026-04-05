# Overnight Run Report — external_monitoring — 2026-04-05

**Branch:** jarvis/overnight-2026-04-05  
**Dimension:** external_monitoring  
**Scope:** memory/work/jarvis/  
**Goal:** Check sources for new releases/updates, write findings to monitoring report, update last_checked timestamps.

## Summary

- **Baseline:** 28 sources with `last_checked` timestamps
- **Final:** 38 sources with `last_checked` timestamps
- **Delta:** +10 new sources added
- **Kept:** 10 iterations (10 commits)
- **Discarded:** 0 iterations
- **Guard failures:** 0

## All Sources Updated

All 28 existing sources updated to `last_checked: "2026-04-05"`. 10 new sources added.

---

## Key Findings by Source

### CRITICAL / ACTION-REQUIRED

**1. Anthropic Python SDK v0.89.0 — Deprecated client-side compaction helpers (Apr 3)**
- Source: Anthropic Python SDK Releases (NEW SOURCE, tier 1)
- `client-side compaction helpers` deprecated in v0.89.0
- **Impact:** Jarvis overnight runner and dispatcher may use these; verify before next upgrade
- Verify: `grep -r "compaction" tools/scripts/ orchestration/`

**2. openclaw GHSA-9jpj-g8vv-j5mf — OAuth PKCE verifier exposure (Apr 4, High)**
- Source: GitHub Advisory Database (NEW SOURCE, tier 2)
- Gemini OAuth exposed PKCE verifier through state parameter in openclaw
- **This directly explains** the HN signal about Anthropic removing OpenClaw support from Claude Code
- Action: Confirm no active openclaw integration in Jarvis toolchain

**3. 36 malicious npm packages (Strapi plugin supply chain, Apr 5)**
- Source: The Hacker News (updated)
- Packages disguised as Strapi CMS plugins; deploy Redis/PostgreSQL exploitation + reverse shells
- **Impact:** If Jarvis or crypto-bot has any Strapi plugin dependencies, audit immediately
- Matches pattern: axios (UNC1069) → Strapi (unknown actor) — supply chain attacks ongoing

**4. Fortinet FortiClient EMS CVE-2026-35616 — Actively exploited (Apr 5)**
- Source: The Hacker News (updated)
- Pre-authentication API bypass; emergency patches released
- Action: If FortiClient EMS in environment, patch immediately

**5. Trivy CVE-2026-33634 in CISA KEV — Supply chain compromise (Mar 26)**
- Source: CISA KEV (NEW SOURCE, tier 2)
- Trivy scanner supply chain compromise; CI/CD secrets exfiltration
- **Impact:** If Jarvis pipeline uses Trivy for container scanning, verify scanner binary integrity

---

### AI ENGINEERING UPDATES

**Claude Code v2.1.90-92 (Apr 1-4)**
- v2.1.92: Bedrock setup wizard, per-model cost breakdown, Write tool 60% faster, `forceRemoteSettingsRefresh` policy
- v2.1.91: MCP tool result persistence override via `_meta["anthropic/maxResultSizeChars"]` (up to 500K), `disableSkillShellExecution` setting — **directly relevant to Jarvis skill execution model**
- v2.1.90: `/powerup` interactive lessons, faster SSE transport (linear not quadratic)

**Simon Willison — scan-for-secrets 0.1→0.2 (Apr 5, NEW TODAY)**
- Python tool scanning dirs for API keys and encoded variations; README-driven development with Claude Code
- Potential tool for Jarvis security pre-commit hooks; evaluate vs existing credential scanners

**LangChain — Open models crossing agent task threshold (Apr 2-3)**
- GLM-5 and MiniMax M2.7 now match closed frontier on file ops, tool use, instruction following
- Self-healing agents in production: auto-PR on regression, no human in loop until review
- **Signal:** Jarvis autonomous executor could potentially route tier-2 tasks to open models at lower cost

**Hermes Agent — Breakout open-source agent framework (via Latent Space, Apr 3)**
- Called out as the "breakout open-source agent framework" in AINews Good Friday coverage
- TODO: Research Hermes Agent GitHub for evaluation against Jarvis architecture needs

**MCP Specification — Stable release 2025-11-25 (NEW SOURCE, tier 2)**
- No new spec releases since Nov 2025; current stable is 2025-11-25
- Version negotiation introduced in 2025-06-18; Jarvis on current stable

**Anthropic RSP v3.0 (Apr 1)**
- Source: Zvi critique (Apr 3): lacks concrete commitments, vague "strong argument" safety thresholds
- Anthropic Safety & Policy added as separate tracked source from Anthropic Blog

---

### SECURITY LANDSCAPE

**Supply Chain Attack Pattern Escalating (Apr 3-5)**
- axios (UNC1069/North Korea WAVESHAPER.V2) — Apr 3
- 36 Strapi npm packages (unknown actor) — Apr 5
- Trivy scanner compromise (CISA KEV, Mar 26)
- Pattern: targeting developer tooling and CI/CD secrets
- Defense: audit all npm dependencies; prefer signed packages; validate scanner binaries

**Google Workspace indirect prompt injection defense (Apr 2)**
- Source: Google Security Blog (NEW SOURCE, tier 2)
- Multi-layered: human red-teaming + automated testing + continuous model hardening
- **Signal for Jarvis:** Similar multi-layer defense applies to Jarvis autonomous worker prompt assembly (existing steering rule on sanitization checklist)

**US Router Ban (Apr 2)**
- All foreign-manufactured consumer routers banned for import/sale
- Supply chain risk to critical infrastructure
- Monitor for home network equipment impact

**Krebs on Security — 13 days silent (last post Mar 23)**
- Unusual silence; last post was CanisterWorm wiper targeting Iran
- Not a source failure — Krebs publishes infrequently by design

---

### CRYPTO / DeFi

**Drift Protocol $280M exploit (Apr 5)**
- Source: CoinTelegraph (updated)
- "Months of deliberate preparation"; linked to prior $58M Radiant Capital hack
- **Impact for crypto-bot:** Large protocol-level exploit; check exposure in paper trading positions
- Rekt News post-mortem likely incoming (added as new source)

**Bitcoin bearish social sentiment — 5-week high (Apr 5)**
- Santiment detecting elevated negative sentiment — potential contrarian signal

**Tether fundraise delay (Apr 4)**
- Mulling delay if demand < $500B valuation; macro liquidity signal

---

### NEW SOURCES ADDED (10)

| Source | Type | Tier | RSS? | Key Value |
|--------|------|------|------|-----------|
| Google Security Blog | security | 2 | Yes (feedburner) | Application security, AI prompt injection defense, VRP |
| Mistral AI Blog | ai_releases | 2 | No | Voxtral TTS, Spaces CLI, Forge enterprise |
| SANS Internet Storm Center | security | 3 | Yes | Daily threat diary, early-warning CVE exploitation |
| GitHub Security Advisory DB (npm) | security | 2 | No (GraphQL API) | npm supply chain, openclaw OAuth CVE |
| CISA KEV | security | 2 | JSON | Authoritative actively-exploited CVE list |
| Rekt News | crypto | 3 | No | DeFi exploit post-mortems, crypto-bot risk model |
| Anthropic Safety & Policy | ai_safety | 2 | No | RSP milestones, constitutional AI, interpretability |
| MCP Specification | ai_engineering | 2 | Yes (Atom) | Spec changes that break Jarvis tool servers |
| Anthropic Python SDK Releases | ai_engineering | 1 | Yes (Atom) | SDK breaking changes for claude -p and dispatcher |
| Cohere Blog | ai_releases | 3 | No | Enterprise RAG, Embed models (nomic-embed context) |

---

## TSV Run Log

```
iteration	commit_hash	metric_value	delta	status	description
1	e70f9b9	29	+1	kept	Update tier-1 timestamps + add Google Security Blog
2	468bd67	30	+1	kept	Update tier-2 timestamps + add Mistral AI Blog
3	2d06712	31	+1	kept	Update tier-3 timestamps + add SANS ISC
4	7e5357e	32	+1	kept	Add GitHub Security Advisory DB (npm) + openclaw finding
5	a995615	33	+1	kept	Add CISA KEV catalog
6	0363840	34	+1	kept	Add Rekt News (DeFi exploits)
7	85a08bc	35	+1	kept	Add Anthropic Safety & Policy tracking
8	506f26d	36	+1	kept	Add MCP Specification releases
9	bd45268	37	+1	kept	Add Anthropic Python SDK releases (ALERT: compaction deprecation)
10	9821d11	38	+1	kept	Add Cohere Blog
```

## Feed Health Notes

| Source | Feed Status | Note |
|--------|-------------|------|
| The Batch (DeepLearning.AI) | **BROKEN** (404) | feed at /the-batch/feed/ returns 404; monitor for recovery |
| Blockworks | Stale since Jan 2026 | feed exists but may be stale; monitor for recovery |
| MLOps YouTube | No RSS | URL-only monitoring required |
| Andrej Karpathy YouTube | No RSS | URL-only monitoring required |
| Google DeepMind Blog | No RSS | URL-only monitoring required |
| Meta AI Blog | No RSS | URL-only monitoring required |
| Microsoft AI Blog | No RSS | URL-only monitoring required |
| OWASP News | No RSS | URL-only monitoring required |
| Mistral AI Blog | No RSS | No feed detected on 2026-04-05 |
| Rekt News | No RSS | URL-only monitoring required |
| Anthropic Safety & Policy | No RSS | URL-only monitoring required |
| Cohere Blog | No RSS | URL-only monitoring required |
