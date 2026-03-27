# PRD: Phase 3C — Voice & Mobile Interface

> **Project:** epdev Jarvis
> **Status:** planning
> **Companion:** `orchestration/tasklist.md` Phase 3C; `memory/work/jarvis/STATE.md`
> **Slack policy:** `memory/work/slack-routing.md` — routine → `#epdev`; must-see → `#general` only.

## Mission

Eric must be able to interact with Jarvis **away from his desktop** — via voice on mobile — with the same learning fidelity as a Claude Code session. Voice sessions must feed the TELOS/signal pipeline automatically. A `/voice-capture` skill lets Eric speak ideas, reflections, or commands into Jarvis's memory without needing to type or be at a computer.

This is not a luxury feature. If Jarvis only learns during desktop sessions, it misses the majority of Eric's thinking — the commute insight, the shower idea, the late-night reflection. Voice is the primary **off-desktop input channel**.

## Ideal State

When this phase is complete:

- Eric picks up his iPhone, speaks a thought, and it lands in Jarvis's memory system within minutes
- Voice sessions produce TELOS signals identical in quality to chat sessions
- Eric can invoke Jarvis remotely for a full agentic response (not just capture)
- The desktop does not need to be attended for capture to work

## Architecture

Three independent capability layers — build in order:

```
Layer 1: Voice Capture (capture → inbox → signals)
Layer 2: Remote Jarvis Invocation (mobile → Claude Code session)
Layer 3: Conversational Voice Loop (STT → Jarvis → TTS → response)
```

### Layer 1: Voice Capture (COMPLETE)

**Flow:**

```
iPhone mic
  → Notion app (built-in voice transcription — no shortcut needed)
  → Jarvis Brain > Inbox page (Notion page ID: 32fbf5ae-a9e3-8198-9975-cbc6293c8690)
  → /voice-capture skill reads Inbox via Notion MCP
  → extract-wisdom → signals (Source: voice) → optional TELOS update
```

**Components:**

| Component | Choice | Why |
|-----------|--------|-----|
| STT | Notion app built-in voice transcription | Native, zero-config, no shortcut required. Works on iPhone today. |
| Transport | Notion cloud sync | Zero infrastructure. No iCloud for Windows, no OneDrive, no file watcher. |
| Inbox | Jarvis Brain > Inbox (Notion MCP) | Captures land in Notion; Jarvis reads via MCP on demand |
| Processing skill | `/voice-capture` | Fetches Notion Inbox via MCP → extracts signals → queues TELOS-relevant content |

**How to capture a voice note:**

1. Open Notion on iPhone → navigate to Jarvis Brain > Inbox
2. Tap into the Captures section → tap the mic / "Start transcribing"
3. Speak your thought — Notion transcribes it inline
4. At next Jarvis session: say "process my Notion inbox" or run `/voice-capture`

No iCloud for Windows required. No `voice_inbox_sync.py`. `memory/work/inbox/voice/` remains as a fallback local inbox if needed.

**Note:** `voice_inbox_sync.py` is archived (no longer needed for Layer 1 with Notion approach).

### Layer 2: Remote Jarvis Invocation

Eric can trigger a real Jarvis session (Claude Code) from mobile for tasks that need a response, not just capture.

**Options ranked by build effort:**

| Option | Effort | Capability | Requirements |
|--------|--------|------------|--------------|
| **SSH + tmux** (Blink Shell on iOS) | Low (1h setup) | Full Claude Code terminal | SSH server on desktop; desktop must be on |
| **Local HTTP endpoint** (`jarvis_voice_server.py`) | Medium (1 day) | Batch mode response, inbox routing | Desktop awake; local network or Tailscale |
| **Tailscale + SSH** | Low (30min) | Full terminal anywhere on internet | Tailscale installed both sides |
| **RemoteTrigger** (Claude Code native) | Low if available | Native agentic trigger | Needs investigation |

**Recommended path:**
1. Start with **Tailscale + Blink Shell SSH** — full terminal, zero custom code, works globally
2. Add **local HTTP server** for voice-specific flows (receives transcript, runs batch Claude Code session, returns/Slacks response)

### Layer 3: Conversational Voice Loop (later)

Full STT → Jarvis response → TTS loop. Planned for after Layers 1 and 2 are stable.

| Component | Choice | Notes |
|-----------|--------|-------|
| STT | Whisper (local via whisper.cpp or API) | Local = private; API = faster setup |
| LLM | Claude Code batch mode or API | Claude Code preferred to keep skill/hook system intact |
| TTS | ElevenLabs API | Already on roadmap (Phase 3C original backlog) |
| UI | iOS Shortcut → HTTP → response → speak | Siri Shortcuts can speak text back |

## `/voice-capture` Skill

New Claude Code skill that processes voice transcripts from inbox into the Jarvis learning pipeline.

**Trigger:** `voice-capture [file]` or run automatically via file watcher

**Steps:**
1. Read transcript from `memory/work/inbox/voice/[file]` (or latest unprocessed)
2. Run `/extract-wisdom` pipeline on transcript
3. Write dated signal to `memory/learning/signals/voice_YYYY-MM-DD.md` with `Source: voice`
4. If transcript contains goal/identity content → queue for `/telos-update`
5. Move processed file to `memory/work/inbox/voice/processed/`
6. Log to `history/changes/` that voice session was captured

**Signal format for voice sessions:**
```markdown
Source: voice
Date: YYYY-MM-DD
Context: voice capture, off-desktop session
[standard signal body]
```

This makes voice signals distinguishable in synthesis (can track: are voice sessions producing different insight types than chat sessions?).

## Ideal State Criteria (ISC)

Each line is **eight words**, state-based, binary-testable.

- [ ] Voice transcript lands in inbox within five minutes | Verify: OneDrive sync log or HTTP server receipt timestamp
- [ ] `/voice-capture` processes new inbox files without manual trigger | Verify: file watcher or scheduled job running; processed/ folder populated
- [ ] Voice signals carry `Source: voice` tag in memory | Verify: grep `memory/learning/signals/` for Source: voice
- [ ] Voice sessions feed TELOS pipeline same as chat | Verify: `/telos-update` has been invoked from a voice signal at least once
- [ ] Eric can reach Jarvis terminal from mobile device | Verify: SSH via Tailscale or equivalent confirmed working from iPhone
- [ ] ElevenLabs TTS produces spoken Jarvis responses on mobile | Verify: Layer 3 end-to-end test (STT → response → TTS played back)
- [ ] `/voice-capture` skill registered and invocable in Claude Code | Verify: skill appears in session-start banner; `/voice-capture` runs without error
- [ ] Voice session count tracked in STATE.md or heartbeat | Verify: `memory/work/jarvis/STATE.md` includes voice session metric

Tag confidence: `[E]` where explicitly agreed; `[I]` where implementation detail TBD.

## Build Order

```
3C-1: Create memory/work/inbox/voice/ directory structure          ✅ DONE
3C-2: Build /voice-capture skill (Notion MCP source)               ✅ DONE
3C-3: Voice capture transport (Notion app → Inbox → MCP)           ✅ DONE (iCloud/OneDrive not needed)
3C-4: Register skill + session hook                                ✅ DONE
3C-5: Tailscale + SSH setup (Layer 2 quick-start)                  🔲 Phase 4→5 gate item
3C-6: jarvis_voice_server.py — local HTTP endpoint (Layer 2 full)  🔲 After 3C-5
3C-7: iOS Shortcut for remote invocation                           🔲 After 3C-6
3C-8: Whisper + ElevenLabs loop (Layer 3)                          🔲 Phase 5 era
```

**Gate assignments:**
- Layer 1 (3C-3): required before Phase 5 (Phase 4→5 gate)
- Layer 2 (3C-5): required before Phase 5 (Phase 4→5 gate)
- Layer 3 (3C-8 through 3C-10): Phase 5 era — enables behavioral change feedback loop

**Quick win available today:** Steps 3C-1 through 3C-3 can be done in one session with no new infrastructure. Eric would have voice capture working from iPhone to Jarvis memory within hours.

## Dependencies

- Phase 2: `/extract-wisdom`, `/learning-capture`, `/telos-update` skills — all complete ✓
- Phase 3B Slack: Optional (for voice session completion notifications)
- Phase 3E heartbeat: Optional (voice session count as a tracked metric)
- Tailscale or SSH server: External setup (30 min, not code)
- ElevenLabs API key: Required for Layer 3 TTS only

## Non-goals (Phase 3C)

- Real-time continuous listening (always-on mic)
- Voice control of arbitrary desktop apps
- Replacing chat sessions — voice supplements, doesn't replace
- Processing audio files directly — text transcript is the input to Jarvis (STT happens before the inbox)

## Open decisions

- File watcher vs cron vs manual trigger for inbox processing
- Whisper local vs API (privacy vs convenience tradeoff)
- Whether Layer 2 HTTP server requires auth token (it should — even on local network)
- ntfy notification when voice capture completes (Phase 3B/3E overlap)

## References

- `orchestration/tasklist.md` Phase 3C — task breakdown
- `memory/work/slack-routing.md` — notification routing
- `security/constitutional-rules.md` — voice input is external input, treat as untrusted
- `memory/work/jarvis/PRD.md` — Phase 4 autoresearch (voice sessions feed the same signal pool)

Last updated: 2026-03-26
