# AI Security: Prompt Injection and Agentic Attack Patterns

**Date:** 2026-04-06
**Domain:** security
**Topic:** Prompt Injection and Agentic AI Attack Vectors
**Key Finding:** No complete technical solution exists for prompt injection in current transformer
architectures; defense must be layered and assume-breach; MCP tool poisoning and memory poisoning
are the highest-leverage new attack vectors for agentic systems like Jarvis.
**Research Brief:** `memory/work/telos-gap-security-2026-04-06/research_brief.md`

---

## Core Threat Model

Prompt injection is ranked OWASP LLM01 -- the #1 vulnerability in production LLM deployments.
Found in 73% of assessed deployments; only 34.7% had dedicated defenses.

The threat compounds in agentic systems: agents read external content AND take real-world actions.
A single injected instruction in a scraped page can chain into code execution, file writes, or
credential exfiltration.

---

## Attack Vector Taxonomy

### Direct Prompt Injection
- Attacker controls user input; injects adversarial instructions into the model's context
- Scope: session-level; ends when chat closes
- Severity: HIGH in user-facing chatbots; lower in autonomous agents with no direct user input

### Indirect Prompt Injection
- Malicious instructions embedded in external content the agent reads (web, files, API responses)
- Agent unknowingly executes attacker instructions while processing "legitimate" data
- Scope: any data ingestion path; persists as long as the content is accessible
- Severity: CRITICAL for autonomous agents that ingest external data without sanitization

### Tool Poisoning (MCP-Specific)
- Attacker injects malicious instructions into MCP tool descriptions or metadata
- Agent reads tool descriptions as trusted system context; follows attacker instructions
- No standard for signing/verifying tool descriptions as of 2026
- 30 CVEs against MCP implementations in 60 days (early 2026)
- Real example: WhatsApp MCP exploit exfiltrated chat histories via poisoned tool descriptions

### Memory Poisoning
- Adversary plants false/malicious content in agent's long-term persistent storage
- Agent "learns" the instruction; recalls it in future sessions (days/weeks persistence)
- Bypasses session-scoped defenses; extremely difficult to detect post-infection
- High relevance for any agent with write access to a knowledge base

### Multimodal Injection
- Instructions hidden in images co-processed with text
- Bypasses text-based content filters
- Risk level grows as multimodal inputs (screenshots, diagrams) are added to agent context

### Inter-Agent Trust Exploits
- Agents in multi-agent pipelines blindly trust outputs from peer agents
- 100% of tested state-of-the-art agents vulnerable
- An attacker who compromises one agent in a pipeline can compromise the entire chain

### Privilege Escalation via Tool Misuse
- Agents granted broad tool permissions use them in unintended ways
- 520 reported tool misuse incidents tracked in 2025
- Common chain: read permissions used to enumerate → write permissions used to persist

---

## Defense Patterns (Ranked by Leverage)

### Tier 1: Architectural (Deterministic)

**System Prompt Isolation**
- System instructions injected server-side only; never from user or external input
- Never expose system prompts in context window as editable text
- Separates trusted instruction path from untrusted data path

**Least Privilege**
- Agents get only the permissions required for their specific scoped task
- Read-only agents must not have write tools; single-domain agents must not have cross-domain creds
- Scope tool grants to match task duration, not session duration

**Agent Sandboxing**
- Each agent operates in an isolated environment with defined inflow/outflow boundaries
- Prevents lateral movement when one agent is compromised

**Tool Description Integrity**
- Maintain cryptographic hashes of approved tool descriptions
- Reject connections to MCP servers with changed or unrecognized tool descriptions
- Use `mcp-scan` for ongoing integrity checks

### Tier 2: Input Guardrails (Probabilistic, Fast)

- Prompt injection classifiers applied before model call
- Input format validation and allowlists
- PII detection and redaction at ingestion point
- Content length and rate limits

### Tier 3: Output Guardrails

- Output schema validation (reject unexpected structure)
- Regex scrubbing for secrets/credentials in responses
- Semantic output classifiers detecting exfiltration patterns

### Tier 4: Runtime Monitoring

- Log all tool calls with full input/output (PostToolUse hooks)
- SIEM alerts on injection pattern signatures
- Memory write auditing -- flag writes from external/untrusted sources
- Rug-pull detection: alert when tool descriptions change post-approval

### Tier 5: Adversarial Testing

- Regular /red-team runs against injection patterns
- Test all external data ingestion paths for injection susceptibility
- Validate guardrails haven't drifted since last test

---

## CVEs Relevant to Claude Code / Jarvis

### CVE-2025-59536 + CVE-2026-21852 (Check Point Research, Feb 2026)

**Vulnerability:** Malicious `.claude/settings.json` in a project repo executes before the
trust dialog finishes rendering.

**Attack:** Clone a malicious repo, run `claude`. The poisoned settings.json defines hooks that:
- Spawn a reverse shell on session start
- Redirect ANTHROPIC_BASE_URL to an attacker proxy (exfiltrates API key)

**Mitigation:**
- Never clone unknown repos and run `claude` without inspecting settings.json first
- Pin allowed hook commands in settings.json to known-safe absolute paths
- Consider a hook that alerts on settings.json changes (git diff check)

---

## Fundamental Limits of Current Defenses

Current transformer architectures have no complete solution for prompt injection:
- Safety training is bypassable with sufficient variation attempts
- Rate limiting raises cost but doesn't block determined actors
- Content filters can be defeated through systematic variation
- Attack success rates against state-of-the-art defenses exceed 85% (adaptive attacks)

Research-stage solutions (not yet production):
- Native token-level privilege tagging (separate trusted vs untrusted tokens at the model level)
- Separate attention pathways for trusted vs untrusted content
- Incompatible embedding spaces for different trust zones

**Operational conclusion:** Defense must be layered and assume-breach. No single control is
sufficient. Architecture controls + monitoring + adversarial testing is the minimum viable stack.

---

## Jarvis Risk Surface (Priority Order)

| Risk | Component | Notes |
|------|-----------|-------|
| HIGH | Autonomous research producers | External content -> knowledge articles = indirect injection path |
| HIGH | MCP servers (Notion, Slack, Tavily) | Tool poisoning if server compromised |
| HIGH | .claude/settings.json | CVE-2025-59536 class; repo-delivered hook poisoning |
| MEDIUM | memory/knowledge/ write-path | Compromised source -> memory poisoning |
| MEDIUM | Worktree task content | Injected instructions in ISC or task fields |
| MEDIUM | spawn-agent / delegation | Inter-agent trust; sub-agents trust parent context blindly |
| LOW | Direct user input | Eric is the only user; low adversarial surface |

---

## Action Items for Jarvis Hardening

1. **Audit autonomous producer write paths** -- verify scraped/API content is sanitized before
   writing to memory/knowledge/ (strip non-ASCII is necessary but not sufficient for injection)
2. **MCP server allowlist** -- enumerate read tools explicitly in allow lists (already in steering
   rules: "Never use mcp__<server>__* wildcards for servers with mutation tools")
3. **settings.json hook audit** -- verify all hook commands use absolute paths and known scripts;
   add git-diff check on settings.json to detect unexpected changes
4. **mcp-scan integration** -- run mcp-scan periodically against active MCP server tool
   descriptions; alert on unexpected changes
5. **Inter-agent trust model** -- sub-agents spawned by spawn-agent/delegation must be treated
   as untrusted output sources; validate their output against expected schemas

---

## Signal Connections

- Relates to: `ai-infra/2026-03-27_jeffrey-emanuel-agentic-tooling.md` (dcg covers git
  destructive, inline scripts, DB/cloud gaps)
- Relates to: `ai-infra/2026-03-30_harness-engineering.md` (hooks as 100% deterministic layer
  -- also 100% deterministic attack surface if poisoned)
- Supersedes: security KB entry "No articles yet" -- this is the first security knowledge article
