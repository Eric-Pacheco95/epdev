# EPDEV Jarvis — Complete Project Roadmap

> Master plan to reach Daniel Miessler Kai-level personal AI infrastructure.
> Last updated: 2026-03-25

---

## Architecture: How epdev Relates to Your Other Projects

```
C:\Users\ericp\Github\
│
├── epdev/                  ← THE BRAIN (orchestration, memory, learning, security)
│   ├── CLAUDE.md           ← Global AI context + steering rules
│   ├── memory/             ← Cross-project learning + signals
│   ├── orchestration/      ← Tracks ALL projects
│   └── ...
│
├── crypto-bot/             ← SEPARATE PROJECT (own repo, own git history)
├── guitar-practice-app/    ← SEPARATE PROJECT
├── bank-automation/        ← SEPARATE PROJECT
├── side-hustle-xyz/        ← SEPARATE PROJECT
└── ...
```

### Key Principle: epdev is the BRAIN, not a monorepo

- Each project gets its own Github repo in `C:\Users\ericp\Github\`
- epdev **tracks** all projects via `orchestration/tasklist.md`
- epdev **learns** from all projects via `memory/learning/`
- Individual projects get their own `CLAUDE.md` that references epdev

### How AI Gets Context Across Repos

```
┌─ Your Project Repo ──────────────────────────┐
│  CLAUDE.md:                                   │
│    "This project is tracked by epdev.         │
│     See C:\Users\ericp\Github\epdev\          │
│     for global context, steering rules,       │
│     and memory."                              │
│                                               │
│  .claude/settings.local.json:                 │
│    MCP servers: [epdev-context-server]         │
│    env: { EPDEV_DIR: "C:\Users\ericp\..." }   │
└───────────────────────────────────────────────┘
         │
         │ reads context from
         ▼
┌─ epdev/ (the brain) ─────────────────────────┐
│  memory/work/{project-slug}/PRD.md            │
│  orchestration/tasklist.md                     │
│  config/steering-rules.yaml                    │
│  security/constitutional-rules.md              │
└───────────────────────────────────────────────┘
```

### Your Workflow In Any Project

```bash
# 1. Open terminal in your project repo
cd C:\Users\ericp\Github\crypto-bot

# 2. Start Claude Code (it reads that project's CLAUDE.md)
claude

# 3. Claude has context about:
#    - This project (from local CLAUDE.md)
#    - Your global identity (from epdev reference)
#    - Your steering rules (from epdev)
#    - Your learning history (from epdev memory)

# 4. Work naturally. Rate when done.
#    "That was a 7 — crypto bot now handles limit orders"

# 5. Learning flows back to epdev/memory/learning/signals/
```

---

## Complete Phase Breakdown

### Phase 1: Foundation ✅ COMPLETE

| Task | Status | Commit |
|------|--------|--------|
| Git repo initialized | ✅ | 44db410 |
| Directory scaffold (memory, history, orchestration, security, tests) | ✅ | 44db410 |
| CLAUDE.md root context with TheAlgorithm + ISC | ✅ | 44db410 |
| TELOS identity (mission, goals, beliefs, challenges) | ✅ | 44db410 |
| Constitutional security rules (4-layer defense) | ✅ | 44db410 |
| Security validator hook (PreToolUse) | ✅ | 44db410 |
| Secret scanner (credential pattern detection) | ✅ | 44db410 |
| Session start hook (banner, tasks, signals, security) | ✅ | 44db410 |
| Learning capture hook (ratings, signals, failures) | ✅ | 44db410 |
| Defensive test suite (injection + secrets — all passing) | ✅ | 44db410 |
| 5 agent definitions | ✅ | 44db410 |
| Personality config + steering rules | ✅ | 44db410 |
| Cursor integration (.cursorrules) | ✅ | 44db410 |
| EPDEV Bible (desktop) | ✅ | 44db410 |
| Repos moved off OneDrive | ✅ | 44db410 |

---

### Phase 2: Hook Wiring & Cross-Project Context

**Goal**: Make hooks actually fire in Claude Code sessions. Enable cross-project context.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 2.1 | Wire hooks into `.claude/settings.json` (PreToolUse, SessionStart) | Claude Code | 30 min | — |
| 2.2 | Build UserPromptSubmit rating detection hook (auto-detect "7/10" in messages) | Cursor | 2 hr | — |
| 2.3 | Build Stop hook (session end learning capture, tasklist refresh) | Cursor | 2 hr | — |
| 2.4 | Create project CLAUDE.md template (for new project repos to reference epdev) | Claude Code | 30 min | — |
| 2.5 | Create `tools/scripts/new_project.py` scaffold generator | Cursor | 1 hr | 2.4 |
| 2.6 | Test hooks end-to-end in a real session | Claude Code | 30 min | 2.1-2.3 |
| 2.7 | Wire crypto-bot as first cross-project integration | Claude Code | 30 min | 2.4 |

---

### Phase 3: Skills System

**Goal**: Build reusable skills (markdown + workflow + tools) like Kai's 67 skills.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 3.1 | Create SKILL.md template + skill assembly pipeline | Cursor | 3 hr | — |
| 3.2 | Build `SelfHeal` skill (detect failure → diagnose → fix → verify → learn) | Cursor | 4 hr | 3.1 |
| 3.3 | Build `SecurityAudit` skill (scan repo, run defensive tests, report) | Cursor | 3 hr | 3.1 |
| 3.4 | Build `LearningCapture` skill (Claude Code skill wrapping the hook) | Claude Code | 1 hr | 3.1 |
| 3.5 | Build `ProjectOrchestrator` skill (manage tasklist, track inflows/outflows) | Cursor | 3 hr | 3.1 |
| 3.6 | Build `Research` skill (web search → summarize → store in memory) | Cursor | 2 hr | 3.1 |
| 3.7 | Build `GuitarPractice` skill (structure practice, track progress, theory) | Cursor | 3 hr | 3.1 |
| 3.8 | Build `SideHustle` skill (idea validation, market research, MVP planning) | Cursor | 3 hr | 3.1 |
| 3.9 | AI Steering Rules auto-generation from failure analysis | Cursor | 4 hr | 3.2 |

---

### Phase 4: Fabric Integration

**Goal**: Install Fabric CLI and integrate 200+ patterns as callable tools.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 4.1 | Install Go runtime | Manual | 15 min | — |
| 4.2 | Install Fabric CLI (`go install github.com/danielmiessler/fabric@latest`) | Terminal | 15 min | 4.1 |
| 4.3 | Configure Fabric with API keys | Manual | 15 min | 4.2 |
| 4.4 | Create Fabric skill in epdev (wraps `fabric --pattern X`) | Cursor | 2 hr | 4.2, 3.1 |
| 4.5 | Create 5 custom Fabric patterns for personal use | Claude Code | 2 hr | 4.2 |
| 4.6 | Integrate Fabric into research + analysis workflows | Claude Code | 1 hr | 4.4 |

---

### Phase 5: Memory & Learning Maturity

**Goal**: Reach Kai-level signal capture (3,500+ signals) and self-improving steering rules.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 5.1 | Build implicit sentiment analysis hook (detect frustration/excitement from tone) | Cursor | 4 hr | Phase 2 |
| 5.2 | Build PostToolUse output capture (UOCS — Universal Output Capture System) | Cursor | 3 hr | Phase 2 |
| 5.3 | Build weekly synthesis automation (cluster signals → themes → rules) | Cursor | 4 hr | Phase 3 |
| 5.4 | Build steering rule proposal system (analyze failures → suggest new rules) | Cursor | 4 hr | 5.3 |
| 5.5 | Hit 50 signals milestone → first real synthesis | Usage | Ongoing | — |
| 5.6 | Hit 100 signals → first steering rule update from data | Usage | Ongoing | 5.3 |

---

### Phase 6: Mobile & Remote Access

**Goal**: Access Jarvis from phone, dispatch tasks remotely.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 6.1 | Set up Claude Remote Control (`claude remote-control`) | Terminal | 15 min | — |
| 6.2 | Test QR code scan from Claude mobile app | Phone | 15 min | 6.1 |
| 6.3 | Set up Claude Dispatch (mobile → desktop task delegation) | Desktop + Phone | 30 min | — |
| 6.4 | Set up Telegram Channel (chat-based task dispatch) | Terminal | 1 hr | — |
| 6.5 | Test full mobile workflow: dispatch task → monitor → get result | Phone | 30 min | 6.1-6.4 |

---

### Phase 7: Notifications & Monitoring

**Goal**: Know what's happening without staring at a terminal.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 7.1 | Set up ntfy server (free, self-hosted push notifications) | Terminal | 1 hr | — |
| 7.2 | Build notification hook (long-running task → push to phone) | Cursor | 2 hr | 7.1 |
| 7.3 | Build daily health report (auto-generate, push to phone) | Cursor | 2 hr | 7.1 |
| 7.4 | Discord integration for team/logging channel | Terminal | 1 hr | — |

---

### Phase 8: Voice System

**Goal**: Agents speak out loud, announce phases, narrate completions.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 8.1 | Get ElevenLabs API key | Manual | 15 min | — |
| 8.2 | Build voice server (TTS endpoint, local) | Cursor | 4 hr | 8.1 |
| 8.3 | Add voice to session start/stop hooks | Cursor | 2 hr | 8.2 |
| 8.4 | Assign unique voices to agents | Claude Code | 1 hr | 8.2 |
| 8.5 | Algorithm phase announcements (voice says "OBSERVE", "PLAN", etc.) | Cursor | 2 hr | 8.2 |

---

### Phase 9: Dashboard UI

**Goal**: Visual monitoring of memory, projects, signals, security.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 9.1 | Choose UI framework (React/Next.js or Astro) | Claude Code | 30 min | — |
| 9.2 | Build memory browser (view signals, failures, synthesis) | Cursor | 6 hr | 9.1 |
| 9.3 | Build project dashboard (tasklist, health, inflows/outflows) | Cursor | 6 hr | 9.1 |
| 9.4 | Build security event viewer | Cursor | 4 hr | 9.1 |
| 9.5 | Build learning analytics (signal trends, rating distribution) | Cursor | 4 hr | 9.1 |

---

### Phase 10: Self-Upgrade & Meta System

**Goal**: System monitors for new capabilities and proposes its own improvements.

| # | Task | Tool | Effort | Depends On |
|---|------|------|--------|------------|
| 10.1 | Build Anthropic blog/changelog monitor | Cursor | 3 hr | — |
| 10.2 | Build capability integration recommender | Cursor | 4 hr | 10.1 |
| 10.3 | Build PAI version tracker (monitor Miessler's releases) | Cursor | 2 hr | — |
| 10.4 | Build scheduled self-audit (am I meeting TELOS goals?) | Cursor | 3 hr | Phase 5 |
| 10.5 | Meta-prompting system (template-based agent generation) | Cursor | 6 hr | Phase 3 |

---

## Milestone Targets

| Milestone | What It Means | Target |
|-----------|---------------|--------|
| **M1: First Blood** | Hooks firing, first 10 signals captured | Week 1 |
| **M2: Skill Builder** | 5+ skills working, Fabric installed | Week 3 |
| **M3: Cross-Project** | 3+ repos connected to epdev brain | Week 4 |
| **M4: Mobile Jarvis** | Dispatch tasks from phone, get results | Week 5 |
| **M5: Self-Improving** | 100+ signals, first auto-generated steering rule | Week 8 |
| **M6: Full Stack** | Voice, notifications, dashboard, 20+ skills | Week 12 |
| **M7: Kai Parity** | 60+ skills, 300+ workflows, self-upgrading | Week 20 |

---

## Phone Access: How To Use Kai From Mobile

### Option 1: Remote Control (Easiest — Start Here)
```bash
# On your PC, in any project:
claude remote-control --name "Jarvis"

# Displays a QR code → scan with Claude mobile app
# Full two-way session control from your phone
# Your local files, MCP servers, hooks all available
```

### Option 2: Dispatch (Fire and Forget)
- Pair Claude mobile app with Claude Desktop
- Send a message from phone: "Run the security audit on crypto-bot"
- Desktop processes it in background
- Check results later

### Option 3: Channels (Chat Integration)
- Set up Telegram bot → Claude listens for messages
- Text your bot from phone: "What's the status of my projects?"
- Claude responds in Telegram with tasklist summary

### Requirements
- Claude Pro or Max plan
- Claude Desktop installed and running on PC
- Claude mobile app (iOS/Android)
- PC must be on and terminal open for Remote Control / Channels
