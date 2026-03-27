# Slack routing — epdev (enforced)

> **Workspace:** [ericpdev.slack.com](https://ericpdev.slack.com)  
> **Slack app:** Reuse **ClaudeActivities** (same app as crypto-bot flows). Do not create a second bot for routine epdev traffic unless ClaudeActivities cannot satisfy MCP scopes.  
> **Integration path:** **MCP (route A)** for Cursor / Claude Code — interactive post/read within granted OAuth scopes.

## Canonical channels

| Role | Channel | Channel ID | Link |
|------|---------|------------|------|
| **Routine** — Jarvis runs, summaries, heartbeat, dev logs, session digests (same spirit as `#crypto-bot`) | `#epdev` | `C0ANZKK12CD` | [Open #epdev](https://ericpdev.slack.com/archives/C0ANZKK12CD) |
| **Must-see only** — human attention required: expired auth, security incidents, blocked production actions, irreversible choices | `#general` | `C0AKR43PDA4` | [Open #general](https://ericpdev.slack.com/archives/C0AKR43PDA4) |

## Rules (enforce)

1. **Default destination** for any automated or agent-generated Slack message (ClaudeActivities, MCP, scripts, heartbeat) is **`#epdev`** — use channel ID **`C0ANZKK12CD`** in API/MCP calls unless a rule below applies.
2. **`#general`** (`C0AKR43PDA4`) is **only** for items that match **at least one**:
   - Authentication or credential failure that blocks work (e.g. “token expired — fix before next run”).
   - Confirmed **security** event or policy violation affecting the workspace or repos.
   - **Must-act-soon** operational block (e.g. production deploy stuck, legal/compliance escalation) where broad visibility is intentional.
3. **Do not** post routine progress, daily runs, summaries, or noise to **`#general`** — those belong in **`#epdev`**.
4. When implementing MCP or scripts, set **`SLACK_CHANNEL_EPDEV=C0ANZKK12CD`** and **`SLACK_CHANNEL_CRITICAL=C0AKR43PDA4`** (or equivalent names) in environment — **never** commit tokens; IDs are not secrets but keep tokens out of git.

## Implementation notes

- **ClaudeActivities:** Point routine workflows at **`C0ANZKK12CD`**. Reserve **`C0AKR43PDA4`** for the narrow alerts above (configure in the same app’s job definitions or templates).
- **MCP:** After the Slack MCP server is installed, confirm tools target **`C0ANZKK12CD`** by default; escalate to **`C0AKR43PDA4`** only when the user or policy explicitly requests a critical alert.

Last updated: 2026-03-27
