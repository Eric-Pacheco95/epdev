# MCP Class Taxonomy

> Classification of MCP servers by credential ownership and extractability. Referenced by CLAUDE.md steering rule on `/architecture-review` pre-BUILD gate. Consult before any "native extraction" migration proposal. Created 2026-04-19 after MCP native migration architecture-review caught inverted OAuth-ownership assumption.

## Class 1 — API key (extractable; migration possible if ROI positive)

**Credential model:** user owns an API key from the vendor, stored locally (`.env`, keyring, or config file under user control).

**Migration status:** can be converted to Jarvis-native subprocess calls. Decision gate is ROI, not feasibility — before migration, confirm context cost is actually load-bearing (check if deferred-tool loading already solves it) and that the native call matches the MCP's stateful semantics.

**Known members (2026-04-19):**
- `mcp__tavily__*` — Tavily API key in `.env`
- `mcp__nanobanana__*` — Gemini API key; NOTE: stateful session tools (`set_aspect_ratio`, `set_model`, `clear_conversation`) would break in subprocess-per-call model — migration requires either persistent session state or scope reduction to stateless tools only

## Class 2 — Anthropic-managed OAuth (NOT extractable)

**Credential model:** injected by Claude Code harness via the `claude.ai` account OAuth flow. Tokens live in Anthropic infrastructure. User does not own, cannot access, cannot refresh, and cannot transfer these tokens.

**Migration status:** **not extractable** — conversion would require registering a new OAuth app with the vendor (Notion, Slack, etc.), implementing local token storage, token refresh, and per-user consent flow. That is a net-new permanent credential attack surface with negative ROI. Never propose native migration.

**Known members (2026-04-19):**
- `mcp__claude_ai_Notion__*` — Notion via Anthropic OAuth proxy
- `mcp__claude_ai_Slack__*` — Slack via Anthropic OAuth proxy
- `mcp__claude_ai_Google_Drive__*` — Google Drive via Anthropic OAuth proxy

**Identifier:** any MCP prefix starting `mcp__claude_ai_` is Class 2 by convention.

## Class 3 — Unknown origin (investigate before planning)

**Credential model:** not yet classified. Could be Class 1 or Class 2 depending on how credentials were established.

**Migration status:** **block migration planning until classified.** Investigation steps: (1) check `.mcp.json` for a local server definition — if present, likely Class 1; (2) if absent, check whether the MCP was installed via `claude mcp add` vs. the Claude Code harness — harness-injected = Class 2; (3) if still unclear, treat as Class 2 (safer default) until vendor credential model is confirmed.

**Known candidates (2026-04-19):**
- `mcp__claude_ai_google-calendar__*` — likely Class 2 (`claude_ai_` prefix), not independently verified

## Reference incident

2026-04-19: MCP native-migration proposal initially framed "full native is best" based on a 22% context-cost claim (Soria Parra keynote). Architecture-review caught five failure modes:
1. Wrong MCP count (missed Slack + google-calendar)
2. Phantom motivation — context cost already solved by deferred tool loading (~200-300 tokens, not 22%)
3. **Inverted OAuth ownership** — assumed `claude_ai_*` tokens were user-owned and extractable; they are Anthropic-managed
4. nanobanana stateful-session mismatch with subprocess-per-call model
5. Inverted burden of proof

Lesson: Class 2 MCPs are structurally unmigrable; proposals that target them are dead before review. Consult this taxonomy before opening the proposal, not after.
