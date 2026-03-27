# Signal: Dispatch + remote-control is the correct mobile Jarvis pattern
- Date: 2026-03-26
- Rating: 6
- Category: pattern
- Source: session
- Observation: Eric got claude remote-control running in epdev/ and verified Dispatch connects to it. Dispatch IS Claude Code on mobile — not an alternative. All hooks (UserPromptSubmit, PreToolUse, Stop) fire through the remote-control session. claude.ai mobile is generic chat with no hooks, no CLAUDE.md, no Jarvis context.
- Implication: For any Jarvis-related mobile interaction, always use Dispatch → remote-control running in epdev/. Remote-control must be kept running persistently (startup script or saved terminal profile). claude.ai mobile is only for non-Jarvis general chat.
- Context: User verified the connection works this session. Startup script for Windows to keep remote-control persistent is the next step.
