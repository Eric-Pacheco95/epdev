# Model Context Protocol (MCP) — Architecture and Jarvis Relevance

> Source: TheCodingGopher "MCP Explained" (85K views, 2026-04-19 extraction)
> Confidence: 8 — well-structured explainer; Anthropic is the protocol author

## Evolution Path (why MCP exists)

Static LLMs → In-context learning (stuffing prompts) → RAG (read-only retrieval from vector DBs) → Tool-augmented agents (ad-hoc connectors) → **MCP (standardized protocol)**

- RAG was read-only: models could observe data but not act on it
- Tool-augmented agents solved action but created the M×N problem: every model+tool pair needed a custom connector
- MCP reduces M×N to M+N: any conforming client talks to any conforming server

## Architecture: Host → Client → Server

```
LLM
 └─ Host (orchestrator)
      └─ Client (1:1 with server, translation layer)
           └─ Server (external tool/service)
```

- **Host**: runs the LLM, manages client lifecycle, routes requests, enforces permission scopes and security policies
- **Client**: translates LLM intents (JSON requests) into structured calls to the server; handles session management; interprets server responses back to the model
- **Server**: implements MCP spec; exposes capabilities via structured JSON schemas

## Transport Modes

| Mode | Use case | Mechanism |
|------|----------|-----------|
| stdio | Local tools, CLI utilities | Client+server as subprocesses; data piped via stdin/stdout; no network latency |
| HTTP + SSE | Remote/cloud tools | Client sends HTTP POST; server streams responses via Server-Sent Events; supports incremental/async results |

## What Servers Expose

- **Resources**: retrievable objects (files, documents, data)
- **Tools**: actions that perform changes or execute operations
- **Prompts**: reusable LLM-callable templates

## Self-Describing / Introspection

- Each server exposes an `introspect` endpoint declaring its full interface
- Host/model queries capabilities dynamically at runtime — similar to OpenAPI or GraphQL introspection
- Enables hot-plugging: new servers added without retraining or reconfiguring the model

## Security Model

- Client never accesses raw secrets or internal infra directly
- All operations go through defined methods in the protocol
- Host enforces permission scopes — LLM can only call what's been granted

## Jarvis Relevance

- Claude Code operates as an MCP **host**; Claude Code hooks (PreToolUse, PostToolUse) fire at the host layer, before/after the client dispatches to external servers
- Understanding the host→client→server flow explains why hooks fire on every tool call regardless of which MCP server handles it — the hook enforcement point is the host
- MCP introspection (self-describing servers) is what enables Claude Code to discover tools dynamically without hard-coded tool lists
- Security implication: validate tool intents at the host layer (hooks) since that's the only layer that sees all calls before dispatch

## MoE Architecture Note (from DeepAgent video, same extraction batch)

- Mixture of Experts (MoE): model has large total params (e.g., DeepSeek R1: 671B) but only routes ~37B active per task via a learned routing mechanism
- Benefit: high knowledge capacity at low per-task compute cost
- Multi-LLM orchestration pattern: specialized models per task type (Claude for agentic coding, DeepSeek R1 for math/reasoning, Gemini for high-volume multimodal) — same principle as Jarvis skill routing but at the model layer

## Caveats

> LLM-flagged, unverified.
- [ASSUMPTION] MCP adoption described as "increasingly adopted" — Anthropic-authored protocol; actual ecosystem adoption breadth vs. Claude Code ecosystem not independently verified
- [ASSUMPTION] Security model claim (client never accesses raw secrets) assumes conforming server implementations; a malicious or misconfigured MCP server can still leak secrets via tool responses
- [ASSUMPTION] MoE 37B/671B figures from DeepAgent explainer video, not DeepSeek R1 technical paper — treat as directionally correct, not precise
