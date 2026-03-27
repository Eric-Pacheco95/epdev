# Orchestration System

Multi-project management with named agents, workflows, and unified task tracking.

## Agents — `orchestration/agents/`

Named agent definitions with specific roles, tools, and behavioral rules.
See individual agent `.md` files for definitions.

Available agents:
- **Architect** — System design, planning, trade-off analysis
- **Engineer** — Implementation, code generation, debugging
- **SecurityAnalyst** — Threat modeling, vulnerability assessment, defensive testing
- **QATester** — Test creation, verification, self-heal validation
- **Orchestrator** — Project management, inflow/outflow tracking, reporting

## Workflows — `orchestration/workflows/`

Multi-step task chains that coordinate agents.

Format: YAML workflow definitions
```yaml
name: {workflow-name}
description: {what it does}
triggers: {manual|schedule|event}
steps:
  - agent: {agent-name}
    action: {what to do}
    inputs: {from previous step or static}
    outputs: {what to pass forward}
```

## Task Console — `orchestration/tasklist.md`

Unified view of all active tasks across all projects.

## Phase 4 — Autonomous self-improvement

**PRD:** `memory/work/jarvis/PRD.md` — background automation (heartbeat, curated research, Slack by severity) isolated from interactive chat sessions. **State:** `memory/work/jarvis/STATE.md`. Tasks listed under Phase 4 in `orchestration/tasklist.md`.

## Phase 3B — Slack (locked in)

**Canonical policy:** `memory/work/slack-routing.md` — channel IDs, links, **enforced** routing, ClaudeActivities reuse, MCP route A.

| Channel | ID | Link |
|---------|-----|------|
| **`#epdev`** (routine — default for all bot/MCP traffic) | `C0ANZKK12CD` | [ericpdev…/C0ANZKK12CD](https://ericpdev.slack.com/archives/C0ANZKK12CD) |
| **`#general`** (must-see human only) | `C0AKR43PDA4` | [ericpdev…/C0AKR43PDA4](https://ericpdev.slack.com/archives/C0AKR43PDA4) |

**Decisions:** **MCP route A** (Slack MCP in Cursor / Claude Code). Reuse the **ClaudeActivities** Slack app; route routine output to **`#epdev`**; use **`#general`** only for critical alerts per `slack-routing.md`.

### Next steps (MCP)

1. **Slack app:** In [api.slack.com/apps](https://api.slack.com/apps) open the **ClaudeActivities** app → **OAuth & Permissions** → ensure scopes needed by your chosen **Slack MCP server** (typically `chat:write`; add `channels:history` / `channels:read` if the server reads messages). Reinstall to workspace if you change scopes.
2. **Install Slack MCP** — pick a maintained Slack MCP package; follow its README for Node/npx or Docker. Supply the **same bot token** ClaudeActivities uses (via env var — never commit).
3. **Cursor / Claude Code:** Register the MCP server in the client’s MCP config; reference your vendor docs for exact JSON shape.
4. **Defaults:** Configure tools or env so **default channel = `C0ANZKK12CD`**. Only target **`C0AKR43PDA4`** when the event matches the **must-see** list in `slack-routing.md`.
5. **Smoke test:** With MCP connected, post one line to `#epdev` (e.g. “MCP → epdev OK”).

### After Slack works

See `orchestration/tasklist.md` Phase **3B** (Notion, ntfy, observability) and Phase **3E** (heartbeat → ntfy).

## Inflows & Outflows

Every project tracks:
- **Inflows**: What feeds into this project (data sources, dependencies, triggers)
- **Outflows**: What this project produces (artifacts, reports, APIs, notifications)
- **Status**: {planning|active|blocked|review|complete}
- **Health**: {green|yellow|red} based on ISC progress
