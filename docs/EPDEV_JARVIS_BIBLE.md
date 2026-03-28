# 📖 EPDEV JARVIS BIBLE

> Your living guide to building and using the Jarvis AI brain.
> **Pin this to your desktop. It updates as the project evolves.**
> Last updated: 2026-03-27 | Phase: 3E (ISC engine live); Phase 3B ideal state captured

---

## 📖 GLOSSARY — Terms You’ll See Everywhere

### What is a **PRD**?
**PRD** = **Product Requirements Document**. In this repo it is a **project brief**: goal, scope, deliverables, constraints, and (when using TheAlgorithm) **Ideal State Criteria** so you know when you’re done. Warm memory stores PRDs under `memory/work/{project-slug}/PRD.md`.

### What are **hooks**?
**Hooks** (in **Claude Code**) are **event scripts** the CLI runs at fixed points in a session—for example **before a tool runs** (PreToolUse) or **when a session starts/ends**. They are **not** “the model remembering”; they are **your code** (e.g. Python) that prints a briefing, validates a Bash command, or reminds you to capture learning. They only run when you use **Claude Code in the repo** with hooks configured—not in Claude Desktop by default.

### Claude **Desktop** vs Claude **Code** (important)
| Surface | What it is | Session / hooks / epdev scripts |
|--------|------------|----------------------------------|
| **Claude Desktop** (app) | General chat: voice, projects, attachments | **No** automatic link to `epdev/` hooks or `hook_learning_capture.py`. Each chat is just a chat unless **you** paste or save into the repo. |
| **Claude Code** (CLI in `epdev/`) | Agent in your codebase | **Can** run hooks and use repo tools; this is where “session start” and “learning capture” **can** be wired. |
| **Cursor** (IDE) | Code + Composer | **No** Claude Code hooks unless you run them yourself or use Claude Code separately. |

**Bottom line:** Nothing “starts a Jarvis session” or “ends with learning” **unless you set up that habit** (or automate it in Claude Code). The bible’s daily habits are **intentional rituals**, not defaults in every Claude product.

---

## 🔄 LIVING BIBLE — Micro-learnings (how this file stays useful)

**Goal:** This document should **accumulate tiny, actionable tips** about *how you actually use* Jarvis (workflows that worked, mistakes avoided, best prompts). Big synthesis still lives in `memory/learning/synthesis/`; **this section is the quick, personal operator’s manual.**

### Rules (keep it lightweight)
1. **Add one micro-learning when** something clicked: a prompt pattern, a tool combo, a failure mode, or a “I’ll always do X from now on.”
2. **Format:** one bullet under **Micro-learnings log** using the template below (copy-paste).
3. **Keep it short** — one to three sentences per entry. Link a file path if it helps.
4. **Optional:** mirror the same idea into `memory/learning/signals/` if it’s worth compounding (rating + observation).
5. **Monthly:** skim the log; merge duplicates; promote 2–3 items into **TIPS & TRICKS** if they’re timeless.

### Template (copy when adding an entry)
```text
- **YYYY-MM-DD** — [tool: Claude Code | Cursor | Desktop | Fabric | other] — One sentence: what you learned. Optional: second sentence on when to use it.
```

### Micro-learnings log
- **2026-03-26** — [meta] — The bible is the **running UI guide**; signals/synthesis are the **compounding memory**. Update this file when you learn *how to operate* the assistant, not for every raw observation.

---

## 🔑 QUICK REFERENCE — What To Do Right Now

### Daily Habits (5-10 min)
1. **Open Claude Code** in `epdev/` → session start hook will brief you
2. **Rate your last session** (1-10) → learning capture compounds over time
3. **Check the tasklist** → `orchestration/tasklist.md` — what's active, what's blocked?
4. **Log anything interesting** → even a one-liner to `memory/learning/signals/`

### Weekly Habits (30 min)
1. **Review signals** → read `memory/learning/signals/` from the week
2. **Run synthesis** → cluster signals into themes in `memory/learning/synthesis/`
3. **Update TELOS** → has anything changed? New goals? New challenges?
4. **Review security log** → any events in `history/security/`?
5. **Update this bible** → add anything you learned about the system

### When Starting a New Project
1. Create `memory/work/{project-slug}/PRD.md` using ISC format
2. Add it to `orchestration/tasklist.md`
3. Define inflows/outflows in the PRD
4. Use TheAlgorithm loop: Observe → Think → Plan → Build → Execute → Verify → Learn

---

## 🏗️ ARCHITECTURE AT A GLANCE

```
YOU (Eric/epdev)
 │
 ├── Claude Code (CLI) ──── brain, planning, orchestration, memory
 │     │
 │     ├── CLAUDE.md ────── identity, steering rules, context routing
 │     ├── Hooks ────────── lifecycle automation (session start, security, learning)
 │     ├── Skills ───────── modular capabilities (security audit, self-heal, etc.)
 │     └── Agents ───────── named workers (Architect, Engineer, SecurityAnalyst, QA)
 │
 ├── Cursor Pro (IDE) ──── implementation, fast code iteration
 │     └── .cursorrules ── reads project context automatically
 │
 ├── Fabric (CLI) ──────── 200+ AI prompt patterns (summarize, analyze, threat model)
 │
 └── Memory/History ────── persistent brain state across sessions
       ├── Session (hot) ── current working memory
       ├── Work (warm) ──── active project PRDs and state
       ├── Learning (cold) ─ accumulated wisdom, failures, signals
       └── History ──────── immutable audit trail
```

---

## 📚 THE LEARNING PATH

### Level 1: Foundation (You Are Here)
- [x] Understand what PAI is and why scaffolding > model
- [x] Set up the repo scaffold (directories, CLAUDE.md, configs)
- [x] Define your TELOS identity (mission, goals, beliefs)
- [ ] Get hooks working (session start, security validator, learning capture)
- [ ] Get defensive tests passing
- [ ] Make your first git commit
- [ ] Practice the daily habits for 1 week

### Level 2: Fluency
- [ ] Create your first custom skill (a repeatable workflow)
- [ ] Build 3+ project PRDs and run them through TheAlgorithm
- [ ] Accumulate 50+ learning signals and do your first synthesis
- [ ] Install Fabric and use 10+ patterns regularly
- [ ] Customize AI Steering Rules based on your own failure analysis
- [ ] Create your first multi-agent workflow

### Level 3: Mastery (Miessler-Level)
- [ ] 67+ skills with dedicated workflows
- [ ] Voice system (ElevenLabs TTS for agent announcements)
- [ ] Notification system (ntfy mobile push)
- [ ] Self-upgrading system (monitors for new AI capabilities)
- [ ] Meta-prompting (template-based agent generation)
- [ ] Full UOCS (Universal Output Capture System)
- [ ] Dashboard UI for monitoring everything
- [ ] Side hustles running through Jarvis orchestration

---

## 🧠 KEY CONCEPTS TO INTERNALIZE

### TheAlgorithm (The Brain's Operating System)
**Every non-trivial task follows this loop:**
```
OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN
   │                                                    │
   └────────────────────────────────────────────────────┘
                    (loop until done)
```

**Ideal State Criteria (ISC)** — the secret weapon:
- Write exactly what "done" looks like as binary checkboxes
- 8 words, state-based, testable: `"All defensive tests pass without false negatives"`
- Tag confidence: [E]xplicit, [I]nferred, [R]everse-engineered

### Memory Tiers (How Jarvis Remembers)
| Tier | What | Lifespan | Example |
|------|------|----------|---------|
| Session | Current conversation | Hours | "We're building the hook system" |
| Work | Active project state | Weeks/months | PRD.md, ISC.json, artifacts |
| Learning | Accumulated wisdom | Permanent | "Python subprocess needs shell=True on Windows" |

### Signal Capture (How Jarvis Gets Smarter)
After every session, capture:
- **Rating** (1-10): How'd it go?
- **Signals**: What did you notice? What surprised you?
- **Failures**: What went wrong? Root cause? How to prevent?
- Signals compound → synthesis → steering rule updates → system improves

### Security Layers (Defense in Depth)
```
Layer 1: Input Validation ─── block injections, validate inputs
Layer 2: Secret Protection ── never expose credentials
Layer 3: Execution Safety ─── prefer reversible, sandbox untrusted
Layer 4: Audit Trail ──────── log everything to history/
```

---

## 🔧 TOOL REFERENCE

### Claude Code (CLI)
```bash
# Start a session in the project
cd epdev && claude

# Ask Claude to do something
"Read the tasklist and tell me what's next"
"Create a PRD for my new side hustle idea"
"Run the security audit on the codebase"
"Capture this learning signal: rating 8, discovered that..."
```

### Cursor Pro (IDE)
```
1. Open epdev/ folder in Cursor
2. It auto-reads .cursorrules for project context
3. Point it at PRDs: "Read memory/work/{project}/PRD.md and implement"
4. Use for: code writing, debugging, fast iteration
5. Come back to Claude Code for: review, integration, learning
```

### Fabric (when installed)
```bash
# Summarize a YouTube video
fabric -y https://youtube.com/watch?v=xxx | fabric --pattern extract_wisdom

# Analyze a document
cat document.txt | fabric --pattern analyze_claims

# Threat model something
echo "my app architecture" | fabric --pattern create_threat_model

# List all available patterns
fabric --list
```

### Key File Locations
| File | Purpose | Edit Frequency |
|------|---------|----------------|
| `CLAUDE.md` | Root brain context | Rarely (stable) |
| `memory/work/TELOS.md` | Your identity | Weekly |
| `orchestration/tasklist.md` | Active work tracker | Daily |
| `config/personality.yaml` | Jarvis personality | Occasionally |
| `config/steering-rules.yaml` | Behavioral rules | After failures |
| `security/constitutional-rules.md` | Security rules | Rarely (stable) |

---

## 🤖 WHAT'S AUTONOMOUS vs 👤 WHAT NEEDS YOU

### Fully Autonomous (Jarvis handles it)
- ✅ Session start context loading (hook)
- ✅ Security validation on every command (hook)
- ✅ Defensive testing (runs automatically)
- ✅ Self-healing when tests fail (diagnose → fix → verify)
- ✅ Memory/history file management (structured writes)
- ✅ Code implementation from PRDs (Cursor executes)
- ✅ Secret scanning before commits
- ✅ Change logging to history/
- ✅ Agent coordination for multi-step tasks

### Semi-Autonomous (Jarvis does it, you review)
- 🔄 Learning signal capture (Jarvis prompts, you rate)
- 🔄 Steering rule updates (Jarvis proposes from failure analysis, you approve)
- 🔄 Project prioritization (Jarvis suggests, you decide)
- 🔄 Synthesis generation (Jarvis drafts, you validate insights)
- 🔄 New skill creation (Jarvis scaffolds, you refine)

### Requires You (Human-in-the-loop)
- 👤 **TELOS updates** — only you know if your goals changed
- 👤 **Session ratings** (1-10) — your subjective assessment drives learning
- 👤 **New project ideas** — Jarvis can brainstorm but you decide what matters
- 👤 **Side hustle validation** — market sense, customer conversations, real-world testing
- 👤 **Guitar practice** — Jarvis can structure it, but your fingers do the work
- 👤 **Gym/health execution** — Jarvis can build the system, you have to show up
- 👤 **Security decisions** — what level of privacy/risk you're comfortable with
- 👤 **Irreversible decisions** — Jarvis escalates these to you by design

---

## 🔌 Phase 3B — External integrations (ideal state)

| Surface | Role |
|---------|------|
| **Notion (MCP)** | **Read-heavy:** context for TELOS and sessions. **Selective write** only when approved. **`memory/work/telos/*.md` in-repo stays canonical**; Jarvis merges Notion + chat/session into markdown updates. |
| **Slack** | **Enforced:** `memory/work/slack-routing.md`. [**`#epdev`**](https://ericpdev.slack.com/archives/C0ANZKK12CD) (`C0ANZKK12CD`) = routine default; [**`#general`**](https://ericpdev.slack.com/archives/C0AKR43PDA4) (`C0AKR43PDA4`) = must-see only. ClaudeActivities + MCP route A. |
| **ntfy** | Push to **iPhone** via ntfy iOS app; topic URL = secret; tie to heartbeat/regression (Phase 3E). |
| **Observability** | **Miessler / PAI-shaped:** hooks + structured events; optional PAI observability pack patterns. **Langfuse** (or similar) optional if you want hosted LLM traces. |

---

## 📊 GAP TRACKER: Kai vs Jarvis

Features from Daniel Miessler's Kai that we still need:

| Feature | Kai Has | Jarvis Status | Priority |
|---------|---------|---------------|----------|
| TheAlgorithm 7-phase loop | v1.6.0 | ✅ Embedded in CLAUDE.md | — |
| TELOS 10-file identity | 10 files | ✅ Single TELOS.md (simpler) | — |
| 3-tier memory | v7.0 | ✅ session/work/learning | — |
| Signal capture (explicit ratings) | 3,540+ signals | 🔧 Hook in progress (Cursor) | High |
| Implicit sentiment analysis | Automatic | ❌ Not yet | Medium |
| 12 quantified personality traits | 0-100 scale | ✅ personality.yaml (1-10) | — |
| 17 hooks across 7 events | <50ms each | 🔧 3 hooks in progress | High |
| 4-layer security | Full | ✅ Constitutional rules written | — |
| SecurityValidator PreToolUse | <50ms | 🔧 In progress (Cursor) | High |
| 67 skills / 333 workflows | Massive | ❌ Skills dir exists, none built | Medium |
| Skill assembly pipeline | Auto-rebuild | ❌ Not yet | Medium |
| Named agents with voices | 15+ agents | ✅ 5 agents defined (no voice) | Low |
| ElevenLabs voice system | Full TTS | ❌ Not yet | Low |
| ntfy push notifications | Mobile | ❌ Not yet | Medium |
| Discord integration | Team | ❌ Not yet | Low |
| Fabric integration | 200+ patterns | ❌ Needs Go install | Medium |
| Self-upgrade system | Monitors blogs/GitHub | ❌ Not yet | Medium |
| Meta-prompting templates | 65% token savings | ❌ Not yet | Medium |
| UOCS (output capture) | Full history | ⚡ Partial (history/ exists) | Medium |
| USER/SYSTEM separation | Upgrade-safe | ⚡ Partial (.cursorrules + CLAUDE.md) | Low |
| MCP servers | 4+ servers | ❌ Phase 3B — ideal state in tasklist + bible | Medium |
| PAI-style observability (hooks / event capture) | pai-observability-server etc. | ❌ Prefer over raw Langfuse unless you choose SaaS traces | Medium |
| Dashboard UI | Planned | ❌ Placeholder exists | Low |
| GitHub-centric orchestration | Issues as tasks | ❌ Using tasklist.md instead | Low |
| AI Steering Rules from failures | 84 failures analyzed | ❌ Need failures first | Auto |

**Legend**: ✅ Done | 🔧 In Progress | ⚡ Partial | ❌ Not Yet

---

## 💡 TIPS & TRICKS (Updated as discovered)

1. **"Read the PRD and implement"** — this one sentence in Cursor does 80% of the work
2. **Rate every session** — even a quick "7" builds the signal database that makes Jarvis smarter
3. **TELOS is alive** — update it whenever your thinking shifts, even slightly
4. **ISC before code** — writing "what done looks like" before writing code saves massive rework
5. **Failures are gold** — a well-documented failure is worth more than a success you can't explain
6. **Desktop vs Code** — use Desktop for open-ended thinking; use Claude Code in `epdev/` when you want hooks and repo-grounded behavior. Learning files are updated by **you or your scripts**, not by every chat automatically.

---

## Scheduled Heartbeat (Windows Task Scheduler)

The ISC engine heartbeat runs every 60 minutes via Windows Task Scheduler to monitor Jarvis health between sessions. It collects 19 metrics, diffs against the previous snapshot, auto-writes learning signals when thresholds are crossed, and routes alerts to Slack/ntfy.

### How it works

1. Task Scheduler calls `tools\scripts\run_heartbeat.bat` every 60 min
2. The .bat wrapper sets working directory to repo root, logs to `data\logs\heartbeat_YYYY-MM-DD.log`
3. Heartbeat runs all collectors, diffs vs previous snapshot, writes auto-signals on WARN/CRIT
4. Env vars (`SLACK_BOT_TOKEN`, `NTFY_TOPIC`) inherit from user environment (confirmed via smoke test)

### Task Scheduler commands

```powershell
# Create (already done — task name: JarvisHeartbeat)
schtasks /create /tn "JarvisHeartbeat" /tr "C:\Users\ericp\Github\epdev\tools\scripts\run_heartbeat.bat" /sc minute /mo 60 /f

# Verify
schtasks /query /tn "JarvisHeartbeat" /v /fo list

# Manual test run
schtasks /run /tn "JarvisHeartbeat"

# Remove if needed
schtasks /delete /tn "JarvisHeartbeat" /f
```

### Key files

| File | Purpose |
|------|---------|
| `tools/scripts/run_heartbeat.bat` | Task Scheduler wrapper (sets cwd, logs output) |
| `tools/scripts/jarvis_heartbeat.py` | Heartbeat engine (19 collectors, diff, signals, alerts) |
| `heartbeat_config.json` | Thresholds, collectors, alert routing, cooldown |
| `memory/work/isce/heartbeat_latest.json` | Latest snapshot |
| `memory/work/isce/heartbeat_history.jsonl` | Append-only history |
| `data/logs/heartbeat_YYYY-MM-DD.log` | Daily run logs |

### Notes

- The Stop hook also fires heartbeat with `--session-end` at the end of every Claude Code session
- Auto-signals include `isc_ref` field linking to PRD ISC lines (Phase 4A addition)
- Cooldown: 60 min per metric (configurable in `heartbeat_config.json`)
- Daily alert caps: Slack 20, ntfy 5
- Log rotation: use `tools/scripts/rotate_events.py` or manual cleanup of `data/logs/` and `heartbeat_history.jsonl`

---

## CHANGELOG

### 2026-03-27 — Phase 3B ideal state
- Captured **Notion** (read-heavy, selective write; repo TELOS canonical), **Slack** (`#epdev` routine, `#general` critical-only), **ntfy** (iPhone), **PAI-aligned observability** vs optional Langfuse — see table above and `orchestration/tasklist.md`

### 2026-03-27 — Slack channels locked + enforcement
- **`memory/work/slack-routing.md`** — channel IDs, links, **enforced** rules; **ClaudeActivities** reuse; **MCP route A**. Decision: `history/decisions/2026-03-27_slack-epdev-routing.md`

### 2026-03-26 — Living bible + glossary
- Added glossary (PRD, hooks, Desktop vs Code) and clarified that Desktop chats do not auto-run Jarvis hooks or learning
- Added **Micro-learnings log** protocol for continuous small updates to this doc
- Tip #6: explicit split Desktop vs Claude Code for learning

### 2026-03-24 — Project Initialized
- Created full scaffold: 36 files across 10 directories
- TELOS identity populated with mission, goals, beliefs, challenges
- Constitutional security rules (4-layer defense)
- 5 agents defined (Architect, Engineer, SecurityAnalyst, QATester, Orchestrator)
- Personality configured: casual, verbose, autonomous, high security
- Cursor integration (.cursorrules) for parallel development
- Phase 1 PRD sent to Cursor for hook/test implementation
- Decision logged: hybrid approach (PAI concepts, custom scaffold, Windows-compatible)

---

*Canonical copy in-repo: `docs/EPDEV_JARVIS_BIBLE.md` (commit this version).*
*If you keep a desktop copy, sync from the repo so micro-learnings don’t diverge.*
*Open in any markdown viewer for formatted reading (Cursor, VS Code, Obsidian, etc.)*
