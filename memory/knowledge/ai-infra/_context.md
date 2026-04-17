# Ai-Infra Domain Knowledge



## Domain Overview
Six research articles spanning agent orchestration, harness tooling, and frontend UI patterns for autonomous AI systems. All findings are directly applicable to Jarvis Phase 5 development. Articles range from low-level loop design to high-level platform selection and observability infrastructure.

## Sub-Domain Summaries

### agent-orchestration
- Four core agentic loop patterns: Generator-Critic (max 2-5 iterations), Iterative Refinement (generate/critique/refine roles), Reflexion (persistent memory between attempts), Brownian Ratchet (always-forward, CI gates merges).
- Paperclip AI (39K stars, MIT, March 2026) implements company-as-OS: Company Goal -> CEO Agent -> Manager Agents -> Worker Agents; runtime-agnostic (Claude Code, Codex, Bash, webhooks).
- Agent power comes from its definition (prompt + context), not runtime -- prompt engineering is the primary leverage point.

### harness-tooling
- Phase 1 observability: PostToolUse hook -> JSONL append to history/events/ with schema {ts, hook, session_id, tool, success, error, input_len}; never log raw inputs/outputs (secret leakage risk).
- Langfuse (MIT, Docker Compose) wins for LLM tracing; doneyli/claude-code-langfuse-template provides native Claude Code integration; 50K free cloud units/month.
- Emanuel's dcg covers 49+ security pattern packs filling validate_tool_use.py gaps; WSL dependency makes direct adoption impractical -- extract pattern list instead.

### frontend-ui
- React Flow (35.6K stars, MIT) confirmed for jarvis-app canvas; Contextual Zoom built-in via useStore; zoom-layer design gates node detail by zoom level.
- React Native + Expo = lowest friction for iOS + Windows App Stores; Tauri v2 = best Windows desktop (1-10 MB vs Electron 100-150 MB, <500ms startup).
- React Native New Architecture (default since 0.76): 43% faster cold starts, 39% faster rendering, 26% lower memory.

## Cross-Cutting Themes
- All three sub-domains converge on local-first, file-backed state: JSONL for events, git for PM source-of-truth, PostgreSQL for agent state.
- Security is a recurring constraint: observability must avoid secret leakage, validators need pattern extraction, agent pipelines need trust boundaries.
- Ecosystem maturity gap: most tools are 2024-2026 vintage with rapidly shifting APIs -- prefer MIT-licensed, self-hostable options to avoid vendor lock-in.
- Phased adoption appears in two independent sub-domains (observability Phase 1/2, frontend mobile-then-desktop split) -- suggests a general principle for Jarvis infra rollout.


## Domain Overview
Six research articles covering Jarvis AI infrastructure: harness engineering and reliability architecture, agent orchestration and system visibility, local embedding models for semantic memory search, and a general-purpose prediction framework. Cross-cutting theme: determinism beats prompting for critical paths; file-based local-first architecture preferred over external services; absorb specific patterns from external frameworks rather than adopting them wholesale.

## Sub-Domain: harness-engineering
- CLAUDE.md is advisory (~80% reliable); hooks are deterministic (100%) -- critical-path enforcement (security blocks, audit logging) belongs in hooks, not instructions
- Karpathy's March of Nines: 5-step chain at 95% per-step yields 77% end-to-end; harnesses solve compounding unreliability that per-step model improvements cannot fix
- PAI v4 highest-value gap: CLI-first architecture -- build deterministic Python CLIs with --flags first, wrap with AI second; Jarvis is currently prompt-first (inverted priority); steering rule exists but is not consistently applied

## Sub-Domain: agent-orchestration
- Three orchestration models: Company-as-OS (Paperclip, multi-agent org chart), Visual workflow (n8n, DAG pipelines), Skill-first brain (Jarvis SENSE/DECIDE/ACT) -- absorb specific patterns, do not adopt external tools wholesale
- Task Parentage (Paperclip pattern): every subtask records its parent task ID, enabling rollup reporting and orphan detection; directly applicable to Jarvis backlog
- Dashboard UI: Next.js 16 + shadcn/ui + Tremor; API routes call fs.readFile() on existing Jarvis JSON/markdown files; SWR polls at 30s; no database, no external services

## Single-Article Findings (directly summarized)

### Local Embeddings for Memory Search (Article 5, confidence 8)
- Winner: nomic-embed-text v1.5 (137M params, 768-dim Matryoshka, 8192-token context, ~100MB RAM, Ollama-native via `ollama pull nomic-embed-text`)
- Current grep-based retrieval across ~126 markdown files misses semantic connections; embedding layer is the next memory milestone
- Similarity threshold must be empirically calibrated -- 0.80 floor is too low for sparse corpora; ChromaDB is the recommended vector store

### Prediction Framework (Article 6, confidence 9)
- Three engines: Bayesian (probability spine, base rates, iterative evidence updates), Game Theory/BDM (actor/incentive modeling, position/capability/salience/risk-tolerance per actor, claimed 90%+ CIA accuracy), Scenario Planning (Shell/GBN 2x2 matrix, four internally-consistent futures)
- Domain-agnostic; calibration via Brier score; Superforecasting reference-class method for base rates
- Framework is fully composable: each engine can be run independently or in combination

## Cross-Cutting Themes
- Local-first file-based architecture across all sub-domains: no external databases or services where avoidable
- Determinism over intelligence: automate what does not require judgment; reserve LLM calls for genuine uncertainty
- Composability: absorb specific patterns from external tools (Paperclip task parentage, PAI CLI-first) rather than adopting whole frameworks
- Calibration as a discipline: both the prediction framework (Brier score) and embeddings (similarity threshold) require empirical tuning, not assumed defaults


## Domain Overview

Six articles spanning 2026-03-30 to 2026-04-08 covering agent orchestration runtimes, autonomous coding agent benchmarks, Claude API economics, prediction calibration, and one out-of-domain geopolitics signal. Two sub-domains synthesized; two singles held in context only.

## Sub-Domain Summaries

### agent-orchestration (Articles 1, 5)
- AutoGen is deprecated -- Microsoft replaced it with MAF; LangGraph is the production default for stateful/human-in-the-loop workflows with pause/serialize/resume checkpointing (battle-tested: Replit, Elastic, LinkedIn).
- CVE-2025-67644: SQL injection in LangGraph SQLite checkpointer -- patch and pin versions.
- Claude Managed Agents (beta 2026-04-08) is a hosted stateful agent runtime at $0.08/s compute -- estimated 10-20x more expensive than self-hosted equivalents; absorb-not-adopt posture warranted until pricing and feature set stabilize.

### autonomous-coding (Articles 2, 3)
- Claude Code (Opus 4.5) leads SWE-bench Verified at 80.8%; mini-SWE-agent (100 lines Python) achieves 74% -- scaffolding architecture dominates framework complexity.
- Claude API model tier (2026-04-06): Opus 4.6 ($5/$25), Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5) per 1M tokens; 1M context window GA with no surcharge.
- Batch API (50% discount) + prompt caching (~90% savings) combine for up to 95% cost reduction -- primary lever for autonomous overnight runners and dispatcher workers.

### Singles (in-context only)

**prediction-calibration** (Article 4)
- Metaculus is best for personal calibration tracking: Brier Score 0.111, proper scoring rules (log + Brier), accuracy-weighted community aggregation, REST API with Python SDK (forecasting-tools).
- Brier Score = mean((p - outcome)^2), 0=perfect, 2=worst; Jarvis target: beat 0.111.
- Caution: calibration score reflects historical performance only; base rates shift with domain and time horizon.

**geo-strategy-iran** (Article 6 -- DOMAIN MISMATCH)
- Flagged: this article belongs in memory/knowledge/geopolitics/, not ai

[TRUNCATED: content exceeded 8000 char cap -- _context.md]