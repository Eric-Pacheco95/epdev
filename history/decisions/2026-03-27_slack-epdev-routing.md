# Decision: Slack routing for epdev (MCP + ClaudeActivities)

**Date:** 2026-03-27  
**Status:** Accepted  

## Context

epdev needs consistent Slack destinations: routine Jarvis/automation traffic vs rare critical human attention.

## Decision

1. Use workspace **ericpdev** with channels **`#epdev`** (`C0ANZKK12CD`) and **`#general`** (`C0AKR43PDA4`) per `memory/work/slack-routing.md`.
2. Integrate via **MCP (route A)** for Cursor / Claude Code.
3. Reuse the existing **ClaudeActivities** Slack app for tokens/scopes; do not duplicate bots for routine traffic without cause.
4. **Enforce:** default post target = `#epdev`; `#general` only for must-see criteria listed in `slack-routing.md`.

## Rationale

Matches established `#crypto-bot` pattern, minimizes Slack noise in workspace-wide channels, and keeps policy in-repo for agents and scripts.

## Consequences

- Any new automation must read `slack-routing.md` before choosing a channel.
- ClaudeActivities job definitions should align channel IDs with this policy.
