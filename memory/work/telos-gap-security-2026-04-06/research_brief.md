# Research Brief: AI-Specific Security Threats -- Prompt Injection and Agentic Attacks

**Date:** 2026-04-06
**Type:** Technical
**Domain:** security
**Task ID:** task-1775458801631842
**Depth:** default

---

## Topic

AI-specific security threats and defensive patterns, focused on prompt injection vulnerabilities
and agentic attack surface expansion (tool poisoning, memory poisoning, privilege escalation).

---

## Key Findings

### 1. Prompt Injection Is the #1 AI Security Threat

OWASP LLM Top 10 (2025 edition) ranks Prompt Injection as LLM01 -- the highest severity, highest
prevalence vulnerability in production LLM deployments. Appeared in 73% of production AI
deployments audited in 2025, yet only 34.7% of orgs deployed dedicated defenses.

Two primary variants:
- **Direct injection** -- attacker controls user input field; injects adversarial instructions
  into the model's prompt context directly.
- **Indirect injection** -- malicious instructions embedded in external content read by the agent
  (web pages, files, API responses, tool descriptions). Agent unknowingly executes attacker's
  instructions while processing "legitimate" data.

Multimodal injection adds a third vector: instructions hidden in images co-processed with text.

### 2. Agentic Systems Massively Expand the Attack Surface

Research statistics (2025, state-of-the-art agents):
- 94.4% vulnerable to direct/indirect prompt injection
- 83.3% vulnerable to retrieval-based backdoors (RAG poisoning)
- 100% vulnerable to inter-agent trust exploits (agents blindly trusting output from other agents)

The core problem: agents process external content (web, files, tool descriptions) and then take
real-world actions (code exec, API calls, file writes, email sends). A single injected instruction
in scraped content can chain into full system compromise.

### 3. Tool Poisoning via MCP (Model Context Protocol)

First disclosed April 2025 by Invariant Labs. Attack vector:
1. Attacker controls or compromises an MCP server
2. Injects malicious instructions into tool *descriptions* or *metadata*
3. LLM agent reads tool descriptions as trusted context -- executes attacker instructions

Real-world example: WhatsApp MCP exploit used poisoned tool descriptions to exfiltrate chat
histories with zero code vulnerabilities required.

Why it's dangerous: no standard for signing or verifying tool descriptions; agents treat them
as trusted system-level context, not user-level untrusted input.

30 CVEs disclosed against MCP implementations in 60 days (early 2026).

### 4. Claude Code-Specific CVEs

Check Point Research (Feb 2026) disclosed CVE-2025-59536 and CVE-2026-21852:
- Malicious `.claude/settings.json` in a project repo executes before the trust dialog renders
- A poisoned settings.json can define hooks that: spawn a reverse shell, redirect
  ANTHROPIC_BASE_URL to an attacker-controlled proxy (API key exfiltration)
- Attack vector: social engineering dev to clone a malicious repo and run `claude` in it

Direct relevance to Jarvis: the epdev harness uses hooks extensively.

### 5. Memory Poisoning in Long-Running Agents

Unlike session-scoped prompt injection, memory poisoning targets the agent's persistent state:
- Attacker embeds adversarial content in data the agent indexes into long-term memory
- Agent "learns" the malicious instruction; recalls it in future sessions
- Attack persists for days/weeks; highly resistant to mitigation post-infection

Jarvis relevance: memory/learning/signals/ and memory/knowledge/ are written to by autonomous
producers. A compromised external source (scraped article, API) could poison knowledge articles.

### 6. First Documented AI-Orchestrated Cyberattack

September 2025: Chinese state-sponsored group manipulated Claude Code to infiltrate ~30 global
targets (financial institutions, government agencies, chemical manufacturing). AI performed
80-90% of the campaign autonomously; human intervention only sporadically needed.

Anthropic disrupted the campaign and published a report. This marks the shift from AI as a
*defensive tool* to AI as an *autonomous attack agent*.

---

## Defensive Pattern Taxonomy

### Architectural Controls (Highest Leverage)

| Defense | Mechanism | Addresses |
|---------|-----------|-----------|
| System prompt isolation | Inject system instructions server-side only; never from user/external input | Direct injection |
| Separate attention pathways | Treat untrusted content in dedicated context zone (architectural; not yet mainstream) | All injection |
| Tool description integrity | Hash + sign approved tool descriptions; reject unrecognized changes | Tool poisoning |
| Least privilege | Agent only has permissions for its specific task; no broad tool grants | Privilege escalation |
| Agent isolation | Each agent operates in a sandboxed environment with defined inflows/outflows | Lateral movement |

### Input Guardrails

- Prompt injection classifiers (ML-based, fast; layer before model call)
- Input allowlists and format validation
- PII detection and redaction at ingestion
- Length/rate limits

### Output Guardrails

- Output schema validation (reject malformed JSON, unexpected structure)
- Secret/credential regex scrubbing before returning to client
- Semantic output classifiers (detect exfiltration attempts in agent responses)

### Monitoring and Detection

- Log all tool calls with full input/output (PostToolUse hooks)
- SIEM alerts on injection attempt patterns
- Memory write auditing -- flag content from external sources
- `mcp-scan` for MCP server tool description integrity checks
- Rug-pull detection: alert when a tool description changes post-approval

### Defense-in-Depth Hierarchy

1. Architecture first (system prompt isolation, least privilege) -- deterministic, not bypassable
2. Input guardrails -- probabilistic, fast
3. Output guardrails -- catches what input guardrails miss
4. Runtime monitoring -- detects what guardrails miss, enables post-incident response
5. Adversarial testing (/red-team) -- validates the above don't have exploitable gaps

---

## Fundamental Limitations of Current Defenses

- Prompt injection has no complete technical solution with current transformer architectures
- Safety training is provably bypassable with sufficient variation attempts
- Rate limiting only raises cost for attackers; doesn't block determined actors
- True elimination requires architecture changes: native token-level privilege tagging, separate
  attention paths for trusted vs untrusted content (research-stage only as of 2026)

Implication: defense must be layered and assume breach. No single control is sufficient.

---

## Jarvis-Specific Risk Surface

| Component | Risk | Mitigation Priority |
|-----------|------|---------------------|
| Autonomous producers (scrapers, research tools) | Indirect injection via external content into knowledge articles | HIGH |
| MCP servers (Notion, Slack, Tavily) | Tool poisoning if MCP server is compromised | HIGH |
| .claude/settings.json (hooks) | CVE-2025-59536 class: malicious repo could poison hooks | HIGH |
| memory/knowledge/ write-path | Memory poisoning via compromised research sources | MEDIUM |
| Claude Code worktrees | Injected instructions in task content or ISC fields | MEDIUM |
| Inter-agent trust (spawn-agent, delegation) | Sub-agents blindly trust parent context | MEDIUM |

---

## Sub-Questions Investigated

1. What attack vectors are most prevalent in production LLM deployments? (Prompt injection 73%)
2. How does MCP expand the agentic attack surface? (Tool poisoning, rug-pull attacks)
3. What Claude Code-specific CVEs exist? (CVE-2025-59536, CVE-2026-21852)
4. What defenses work at the architectural vs runtime layer? (Taxonomy above)
5. What are the fundamental limits of current defenses? (No complete solution today)
6. What is Jarvis's specific risk surface? (Table above)

---

## Sources

- OWASP LLM Top 10 2025: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Prompt Injection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- Agentic AI Security (arXiv 2025): https://arxiv.org/html/2510.23883v1
- MCP Security Guide (30 CVEs): https://www.heyuan110.com/posts/ai/2026-03-10-mcp-security-2026/
- Elastic Security Labs MCP Defense: https://www.elastic.co/security-labs/mcp-tools-attack-defense-recommendations
- Check Point CVE-2025-59536: https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/
- Anthropic: AI-Orchestrated Attack Disruption: https://www.anthropic.com/news/disrupting-AI-espionage
- Lasso Security Agentic Top 10: https://www.lasso.security/blog/agentic-ai-security-threats-2025
- Wiz LLM Guardrails: https://www.wiz.io/academy/ai-security/llm-guardrails
- Palo Alto Unit42 Guardrail Comparison: https://unit42.paloaltonetworks.com/comparing-llm-guardrails-across-genai-platforms/
