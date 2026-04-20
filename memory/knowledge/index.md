# Knowledge Index

> Auto-maintained by /research Phase 3. Each entry: date, domain, topic, key finding, path.
> Used by /research Phase 0 (prior-knowledge scan) and /make-prediction (domain priors).

## crypto

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-03-27 | Crypto Trading Bot Market & Technology Landscape | Overfitting kills 44% of strategies; backtested Sharpe R²<0.025 as live predictor; CCXT+Freqtrade stack is solved; regime detection is the unsolved problem | `crypto/2026-03-27_crypto-trading-bot-landscape.md` |
| 2026-04-06 | DeFi Market Structure, MEV, and Algorithmic Trading 2026 | ETH L1 MEV dominated by ~20 entities (sandwich avg $3, 30% bots losing); cross-chain arb + Solana-Jito are viable solo entry points; $3B+ MEV/yr; SEC/CFTC classified ETH/SOL as commodities Mar 2026 | `crypto/2026-04-06_crypto-defi-market-structure.md` |

## security

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-04-06 | AI-Specific Security Threats | Agentic AI expands attack surface: indirect injection via tool outputs, MCP tool poisoning (43% of servers vulnerable), multi-agent collusion; merge gate is last reliable defense for autonomous pipelines | `security/2026-04-06_security-ai-threats.md` |
| 2026-04-06 | Prompt Injection and Agentic Attack Patterns | No complete technical solution exists for prompt injection in current transformers; MCP tool poisoning and memory poisoning are highest-leverage new vectors; defense must be layered and assume-breach | `security/2026-04-06_telos-gap-security-2026-04-06_prompt-injection-agentic-attacks.md` |
| 2026-04-19 | Six LLM Attack Vectors + ModernBERT Guardrails | GCG attack breaks Claude alignment via gibberish suffix tokens (transferable); RAG poisoning needs only 5 chunks in 8M docs; MCP iceberg effect; agentic RCE documented; ModernBERT = $1 self-hosted 35ms classifier | `security/2026-04-19_carpentero-six-vectors-modernbert-guardrails.md` |

## ai-infra
Sub-domains: `ai-infra/agent-orchestration.md`


| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-03-27 | AI Agent Observability for Claude Code | Phase 1: PostToolUse hook → JSONL (no deps, free); Phase 2: Langfuse (MIT, Docker, 50K/mo free tier); OpenTelemetry is overkill for solo dev | `ai-infra/2026-03-27_ai-agent-observability.md` |
| 2026-03-27 | Jarvis App — AI-Native Graph PM Tool | React Flow confirmed (35.6K stars, 4.59M installs, MIT); Contextual Zoom is built-in; no tool combines git-native + semantic nodes + AI co-pilot + write-back | `ai-infra/2026-03-27_jarvis-jarvis-app-graph-pm.md` |
| 2026-03-27 | Jeffrey Emanuel's Agentic Tooling | dcg covers security gaps (git destructive, inline scripts, DB/cloud); meta_skill becomes critical at 50-75+ skills; CASS provides cross-session search with Windows support | `ai-infra/2026-03-27_jeffrey-emanuel-agentic-tooling.md` |
| 2026-03-28 | Cross-Platform Framework Comparison | React Native + Expo = best iOS path (no Mac needed); Tauri v2 = best Windows desktop (1-10MB installers); PWA fails on iOS App Store; Flutter requires Dart pivot | `ai-infra/2026-03-28_cross-platform-framework-comparison.md` |
| 2026-03-28 | Agentic Loops & Multi-Agent Orchestration | Generator-Critic is industry-standard; context anxiety + poor self-evaluation are dominant failure modes; Karpathy's March of Nines proves harness > per-step skill improvement | `ai-infra/2026-03-28_agentic-loops-multi-agent-orchestration.md` |
| 2026-03-29 | Jarvis Dashboard UI | Next.js + shadcn/ui + Tremor stack; API routes read existing JSON/markdown files; no database; poll every 30s; never expose .env through API routes | `ai-infra/2026-03-29_jarvis-dashboard-ui.md` |
| 2026-03-29 | Aron Prins — Paperclip AI Pipeline | Paperclip (39K stars) runs agent "companies"; key patterns: task ancestry, heartbeat execution, routines engine, atomic checkout, budget enforcement; CEO hierarchy is wrong for solo operators | `ai-infra/2026-03-29_aron-prins-paperclip-pipeline.md` |
| 2026-03-30 | Harness Engineering for Claude Code | CLAUDE.md is 80% advisory; hooks are 100% deterministic; keep CLAUDE.md under 60 lines; three nested loops (project/task/tool); context anxiety + poor self-evaluation are key failure modes | `ai-infra/2026-03-30_harness-engineering.md` |
| 2026-03-30 | PAI v4.0.3 vs Jarvis Architecture | Highest gap: CLI-first architecture (deterministic Python tools vs prompt-first skills); also: notification system (ntfy.sh), spotcheck pattern; Jarvis ahead on self-healing + decision logging | `ai-infra/2026-03-30_pai-v4-jarvis-comparison.md` |
| 2026-03-30 | Autonomous Orchestration for Phase 5 | Don't adopt Paperclip or n8n; absorb: task ancestry (parent_id), routines engine (routines.jsonl), CEO hierarchy wrong for solo; existing SENSE/DECIDE/ACT architecture is correct | `ai-infra/2026-03-30_phase5-orchestration-patterns.md` |
| 2026-04-02 | Local Embedding Models for Jarvis Memory | Winner: nomic-embed-text v1.5 (Ollama-native, 8K context, ~100MB); Vector DB: ChromaDB (embedded, no Docker); cloud APIs violate offline-first principles | `ai-infra/2026-04-02_local-embeddings-vector-search.md` |
| 2026-04-02 | General-Purpose Prediction Framework | Universal chassis: Bayesian + BDM game theory + Shell/GBN scenarios; Brier Score for calibration tracking; base rate (reference class) is more predictive than domain expertise alone | `ai-infra/2026-04-02_prediction-framework.md` |
| 2026-04-06 | AI Agent Frameworks -- LangGraph, CrewAI, AutoGen, Agentless | AutoGen in maintenance mode (replaced by MAF); LangGraph wins for stateful/human-in-the-loop; Agentless pattern outperforms agentic for structured tasks; Jarvis already implements Agentless correctly | `ai-infra/2026-04-06_ai-agent-frameworks.md` |
| 2026-04-06 | Claude API and Anthropic Product Updates | Sonnet 4.6 ($3/$15) outperforms prior Opus on coding at 1/5 the cost; 1M context GA; Batch API (50% off) + prompt caching (90% off) = up to 95% cost reduction for autonomous pipelines | `ai-infra/2026-04-06_claude-api-updates.md` |
| 2026-04-06 | Prediction Market Platforms and Calibration Mechanics | Metaculus Brier 0.111 (best public platform); proper scoring rules reward calibration not just accuracy; Polymarket hybrid CLOB + UMA oracle; Manifold real-money mode sunset March 2025 | `ai-infra/2026-04-06_prediction-market-mechanics.md` |
| 2026-04-06 | Autonomous Coding Agent Capabilities -- Devin, SWE-agent, Claude Code, Cursor | Claude Code 80.8% SWE-bench (highest); mini-SWE-agent 74% in 100 lines; context overflow is silent not fatal; harness-first dominates for solo operators | `ai-infra/2026-04-06_autonomous-coding-agents.md` |
| 2026-04-08 | Claude Managed Agents — Anthropic's hosted agent runtime | Sandbox-cloud-only + enterprise-fleet-shaped; do not migrate; absorb 3 patterns: typed event taxonomy, declarative permissions.yaml, agent+environment=session decomposition; $0.08/session-hour idle-excluded billing validates Idle Is Success | `ai-infra/2026-04-08_claude-managed-agents.md` |
| 2026-04-18 | Self-evolving Cortex parasite — svpino/shujunliang teardown | 219-generation agent handoff via git-clone + system-prompt injection is load-bearing; P1 = formalize session_checkpoint.md into cold-boot handoff; P2 = Tavily budget sentinel; reject P5 auto-deploy (matches autonomous-rules.md anti-pattern); all scale numbers single-sourced from injured-party CTO | `ai-infra/2026-04-18_self-evolving-cortex-teardown.md` |
| 2026-04-19 | Postgres-as-everything — Coding Gopher analysis + Jarvis fit | Markdown stays canonical, Postgres only as derived layer for Tier 1 (signals/dispatcher/vitals/predictions/vectors); 5 of 9 video claims map to Jarvis; reject PostgREST+RLS-as-backend; ChromaDB→pgvector is cheapest first move | `ai-infra/2026-04-19_postgres-as-everything-jarvis-fit.md` |

## automotive

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-03-27 | BYD EVs Coming to Canada — Best Model & Incentive Analysis | BYD Seal = Eric's IS250 replacement; $5K EVAP rebate gap (BYD is Chinese-built, excluded); Ioniq 6 wins at ~$41.8K effective unless Seal prices below ~$43K CAD | `automotive/2026-03-27_byd-canada-ev.md` |

## smart-home

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-04-01 | AI Smart Home Middleware Market | Consumer play is risky — Google/Amazon/Apple bundle AI free; B2B property management is the viable niche ($50-200/mo WTP, 20-35% ROI); Home Assistant has no paid add-on marketplace | `smart-home/2026-04-01_smart-home-ai-middleware-market.md` |

## fintech

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-04-03 | AI Automation Consulting for Canadian Banking | Big 5 spend C$5B+/yr on tech; OSFI E-23 (May 2027) creates compliance demand; practitioner-level consulting gap is real; employment agreement is #1 blocker for side-hustle | `fintech/2026-04-03_banking-ai-consulting-market.md` |
| 2026-04-06 | Fintech and Banking AI Adoption -- Enterprise, Vendors, Consulting | $73B bank AI spend in 2025; 95% of GenAI still in pilot; Pilot Graveyard is #1 deployment blocker; EU AI Act Aug 2026 + OSFI E-23 May 2027 = non-discretionary consulting demand | `fintech/2026-04-06_fintech-ai-adoption.md` |

## general

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-03-27 | Evolution and the Big Bang — Cosmic and Biological Origins | Four independent Big Bang evidence lines; all elements heavier than iron forged in supernovae/neutron star mergers; RNA World + hydrothermal vents is current abiogenesis consensus | `general/2026-03-27_evolution-big-bang.md` |

## geopolitics

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| (synthesized) | Geopolitical strategy and multi-stakeholder dynamics | Iran trap + AI datacenter supply constraints; multi-stakeholder incentive misalignment as strategic trap | `geopolitics/_context.md` |

## predictions

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| (synthesized) | Prediction framework, calibration, and backtest results | Bayesian + BDM game theory chassis; Brier Score calibration; base rate more predictive than domain expertise | `predictions/_context.md` |

## cooking

Sub-domains: `cooking/techniques.md`, `cooking/pairings.md`, `cooking/eric-preferences.md`

| Date | Topic | Key Finding | Path |
|------|-------|-------------|------|
| 2026-04-18 | Cooking domain seeded (techniques, pairings, Eric profile) | Pilaf method (bloom fat → toast rice → liquid → rest) works with any spice blend; TJ Chile Lime + cinnamon + garlic + butter = Mexican-leaning combo, pairs with chicken | `cooking/_context.md` |
