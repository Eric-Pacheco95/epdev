# Jarvis — observed state

> Short-lived snapshot for humans and automation. Heartbeat JSON remains canonical metrics.

## System state

| Field | Value |
|-------|--------|
| Phase 4 PRD | `memory/work/jarvis/PRD.md` |
| Phase 3C Voice/Mobile PRD | `memory/work/jarvis/PRD_voice_mobile.md` |
| Last reviewed | 2026-03-26 |
| Autonomous jobs enabled | no (planning) |
| Voice capture (Layer 1) | not started — `memory/work/inbox/voice/` not yet created |
| Remote invocation (Layer 2) | not started — Tailscale/SSH not configured |
| Voice conversation (Layer 3) | not started — depends on Layers 1 + 2 |
| Phase 4D (internal autoresearch) | not started — see `memory/work/jarvis/PRD.md` §4D |
| Notes | Phase 3C voice/mobile added 2026-03-26. Layer 1 is a quick-win buildable in one session. |

## PAIMM milestone tracking

> From Miessler's Personal AI Maturity Model. Verify each before advancing phases. See `memory/learning/synthesis/miessler-deep-research.md` for level definitions.

| Level | Name | Verified? | How to verify |
|-------|------|-----------|---------------|
| AG1 | Basic tool use (Claude Code with file read/write) | yes ✓ | Phase 1 complete |
| AG2 | Multi-tool workflows (hooks, MCP, API calls) | partial | Hooks working; Slack script working; MCP integrations incomplete (3B) |
| AG3 | Multi-agent orchestration (parallel agents, delegation) | partial | Skills exist; not actively orchestrating in practice |
| **AS1** | **Persistent context — Jarvis knows who Eric is across sessions** | **not confirmed** | Session hook loads TELOS + projects, but learning loop not compounding (signals = 0). Gate: session banner reflects current learning + project state accurately |
| AS2 | Proactive assistance (monitors, alerts without being asked) | not started | Requires Phase 4A–4C: heartbeat running, Slack digest firing on cadence, background research producing signals |
| AS3 | Full digital companion | not started | Phase 5+ |

**Current target:** Confirm AS1 before starting Phase 4. Gate checklist in `orchestration/tasklist.md` (Phase 3E → Phase 4 Gate).

Last updated: 2026-03-27
