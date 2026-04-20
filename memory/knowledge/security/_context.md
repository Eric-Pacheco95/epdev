# Security Domain Knowledge

## Domain Overview

This domain covers AI-specific security threats, attack surfaces for agentic systems, and defensive architectures. As of 2026-04, prompt injection (OWASP LLM01) is the dominant production vulnerability class, compounded by agentic pipelines that give exploited models real-world tool access. No complete technical mitigation exists at the model layer; all viable defenses are layered, assume-breach architectures.

Note: One article in this batch (2026-03-30_geo-strategy-iran-trap.md, domain: geopolitics) was misrouted to the security domain. Its findings are excluded from security synthesis and flagged as a routing error.

## Key Findings by Sub-Topic

### Prompt Injection and Agentic Attack Surfaces
- Prompt injection is OWASP LLM01:2025 -- found in 73% of production AI deployments, but only 34.7% had dedicated defenses. The gap is the exploitable surface.
- Agentic systems compound the risk: indirect injection arrives through tool outputs (web fetch, file read, MCP responses), not just user input. Single-model input guards miss the entire indirect path.
- MCP tool poisoning and multi-agent collusion are the highest-leverage NEW vectors: a poisoned MCP server can silently redirect all tool calls; collusion bypasses single-agent trust boundaries without triggering any per-agent defense.
- No transformer architecture today provides a complete prompt injection fix. Defense must be layered: input sanitization + tool output sandboxing + human merge gate + assume-breach incident response.
- The merge gate -- human review before any agent-generated code or action is committed -- is the last reliable choke point in autonomous pipelines.

### NEW (2026-04-19): Three Material Gaps from Carpentero Research
- **GCG attack (Model Internals vector):** Gibberish suffix tokens exploit the geometry of refusal boundaries, which are geometrically similar across models trained with similar RLHF pipelines. Transferable to black-box models including Claude. No model-layer defense exists; requires a pre-inference classifier layer.
- **RAG poisoning specificity:** Only 5 malicious chunks needed in an 8M-document knowledge base. Two easily-satisfied conditions: semantic similarity + convincing text. Jarvis `memory/knowledge/` + vector store is directly in scope.
- **Guardrails option (ModernBERT):** Fine-tuned encoder as binary safety discriminator. $1, 35ms, self-hosted, retrain in hours. Deterministic classification layer that doesn't rely on probabilistic model alignment.

## Cross-Cutting Themes

- **Assume-breach posture**: Both AI-security articles converge on assume-breach as the required default. Preventive controls alone are insufficient given the 73% prevalence and architectural inability to fully solve injection at the model layer.
- **Agentic amplification**: Each additional tool or agent in a pipeline multiplies the attack surface nonlinearly. The threat model for a single chatbot does not transfer to a multi-agent, multi-tool autonomous system.
- **Defense in depth at trust boundaries**: Every external data source (web, file system, MCP, other agents) is an untrusted input channel and must be treated as such -- not just user-facing chat input.
- **Human gates remain essential**: Despite automation goals, human review at merge/commit/action-commit points is the only currently reliable backstop against indirect injection exploits.

## Sub-Domains

3 on-domain articles now exist — sub-domain threshold met. Recommend creating sub-domain files:
- `attack-vectors.md` — full taxonomy (Vectors 1-6 + OWASP LLM01-LLM03 + ASI rankings)
- `defensive-architectures.md` — all defense patterns, tier ranking, Jarvis-specific gap map
- `guardrails-classifiers.md` — ModernBERT approach, LLM-as-judge tradeoffs, implementation options

## Routing Error

- Article 2026-03-30_geo-strategy-iran-trap.md (domain: geopolitics) was included in this security synthesis batch. Content: US-Iran conflict analysis, military overextension, asymmetric warfare. No security relevance. Recommend re-routing to geopolitics domain.

## Source Articles

- 2026-04-06_security-ai-threats.md (raw_article)
- 2026-04-06_telos-gap-security-2026-04-06_prompt-injection-agentic-attacks.md (raw_article)
- 2026-04-19_carpentero-six-vectors-modernbert-guardrails.md (raw_article)
- 2026-03-30_geo-strategy-iran-trap.md (absorbed, OFF-DOMAIN)

**Last updated:** 2026-04-19