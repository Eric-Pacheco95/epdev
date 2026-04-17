# EPDEV JARVIS BIBLE

> Your operator's handbook for the Jarvis AI brain.
> **Keep this on your desktop. Reference it when you're unsure what Jarvis can do.**
> Last updated: 2026-03-27 | Phase: 4A (autonomous loop live) | Skills: 33

---

## HOW TO START A SESSION

```bash
cd C:\Users\ericp\Github\epdev
claude
```

That's it. The session-start hook auto-loads: TELOS status, active tasks, signal counts, security alerts.

### What to say first

| Your mood / goal | Say this |
|-----------------|----------|
| Continue yesterday's work | "What was I working on last session?" (or check open terminals) |
| Build something | "Read the PRD at memory/work/{project}/PRD.md and implement" |
| Research a topic | `/research <topic>` |
| Learn something | `/teach <topic>` |
| Check system health | `/vitals` |
| Just vibing / exploring | Start talking -- Jarvis routes to the right skill |

### Search past sessions

```bash
python tools/scripts/jarvis_index.py search "whatever you're looking for"
python tools/scripts/jarvis_index.py search "slack oauth" --source failure
python tools/scripts/jarvis_index.py stats
```

This searches across ALL your past sessions, signals, failures, decisions, and security events. 236+ documents indexed. Auto-updates every 60 minutes via heartbeat.

---

## SKILLS QUICK REFERENCE

This is the most important section. These are your tools -- use them by name.

### The Build Chain (most common flow)

```
/research  -->  /create-prd  -->  /implement-prd  -->  /learning-capture
```

### By Situation

| You want to... | Use this | Example |
|----------------|----------|---------|
| **Research** a topic before building | `/research <topic>` | `/research EV batteries Canada` |
| **Plan** a new project from scratch | `/project-init <idea>` | `/project-init crypto alerts bot` |
| **Write requirements** | `/create-prd` | After /research gives you context |
| **Build from requirements** | `/implement-prd` | Reads PRD, extracts ISC, builds, verifies |
| **Review code** for security | `/review-code` | Auto-called by /implement-prd at VERIFY gate |
| **Break down** a hard problem | `/first-principles <problem>` | `/first-principles why Slack webhooks fail` |
| **Stress-test** a plan | `/red-team <plan>` | `/red-team my crypto bot strategy` |
| **Learn** something deeply | `/teach <topic>` | `/teach how MCP servers work` |
| **Fact-check** content | `/analyze-claims <content>` | Paste an article, check its claims |
| **Find logic errors** | `/find-logical-fallacies` | In arguments, plans, proposals |
| **Improve a prompt** | `/improve-prompt` | Before running an important query |
| **Write an essay** | `/write-essay <topic>` | Publish-ready, optional author style |
| **Create a presentation** | `/create-keynote` | TED-quality slides with speaker notes |
| **Summarize** content for memory | `/create-summary` | Compress before storing |
| **Extract insights** from content | `/extract-wisdom` | Ideas, quotes, habits from any content |
| **Rate/classify** content | `/label-and-rate` | S/A/B/C/D tier + JSON metadata |
| **Visualize** system structure | `/visualize` | Mermaid diagrams of workflows, projects |

### System & Meta Skills

| You want to... | Use this |
|----------------|----------|
| **Check system health** | `/vitals` |
| **Capture learning** at end of session | `/learning-capture` |
| **Synthesize** accumulated signals | `/synthesize-signals` |
| **Update identity** from session input | `/telos-update` |
| **Weekly identity report** | `/telos-report` |
| **Propose new steering rules** | `/update-steering-rules` |
| **Run security scan** | `/security-audit` |
| **Diagnose and fix** a failure | `/self-heal` |
| **Model threats** | `/threat-model` |
| **Route a task** to the right skill | `/delegation` |
| **Chain skills** into pipelines | `/workflow-engine` |
| **Manage projects** | `/project-orchestrator` |
| **Compose an AI agent** | `/spawn-agent` |
| **Sync with Notion** | `/notion-sync` |
| **Process voice transcripts** | `/voice-capture` |
| **Create a new skill** | `/create-pattern` |
| **Commit changes** | `/commit` |

### Key Rule

**You don't need to remember all of these.** Just describe what you want and Jarvis will route to the right skill. But knowing the names helps you go faster.

---

## GLOSSARY

| Term | What it means |
|------|--------------|
| **PRD** | Product Requirements Document -- project brief with ISC (what "done" looks like) |
| **ISC** | Ideal State Criteria -- 8-word binary-testable checkboxes defining completion |
| **TheAlgorithm** | 7-phase loop: OBSERVE > THINK > PLAN > BUILD > EXECUTE > VERIFY > LEARN |
| **TELOS** | Your identity profile -- mission, goals, beliefs, challenges. Lives at `memory/work/telos/` |
| **Signal** | A learning observation rated 1-10. Accumulates in `memory/learning/signals/` |
| **Synthesis** | Periodic distillation of signals into themes and steering rules |
| **Steering rule** | A behavioral directive in CLAUDE.md that shapes how Jarvis works |
| **Hook** | A script that runs automatically at session events (start, tool use, stop) |
| **MCP** | Model Context Protocol -- how Jarvis connects to Slack, Notion, Calendar, Gmail |
| **Heartbeat** | Automated 60-min health check: 19 metrics, auto-signals on regressions |
| **Knowledge Index** | SQLite search engine across all sessions, signals, decisions, failures |

---

## ARCHITECTURE (Current)

```
YOU (Eric)
 |
 |-- Claude Code CLI (epdev/) ---- brain, planning, orchestration, memory
 |     |
 |     |-- CLAUDE.md ------------- identity, 33 skills, steering rules
 |     |-- Hooks ------------------ session start, security validator, events, learning
 |     |-- Skills (.claude/skills/) - modular capabilities in Fabric format
 |     |-- MCP Servers ------------ Slack, Notion, Calendar, Gmail, Tavily
 |     +-- Knowledge Index -------- full-text search across all Jarvis data
 |
 |-- Heartbeat (Task Scheduler) --- 60-min autonomous health loop
 |     |-- 19 metric collectors
 |     |-- ISC gap detection
 |     |-- Auto-signal writing
 |     +-- Slack alerts on regressions
 |
 |-- Slack ----------------------- mobile hub + notifications
 |     |-- #epdev (routine)
 |     |-- #general (critical only)
 |     |-- #jarvis-inbox (mobile prompts -> claude -p -> thread reply)
 |     +-- #jarvis-voice (voice transcripts -> signals)
 |
 |-- jarvis-app (separate repo) -- visual system of record
 |     +-- React Flow dashboard, ISC tracking, 23/25 passing
 |
 +-- Memory / History ------------ persistent brain state
       |-- session/ (hot) --------- current session
       |-- work/ (warm) ----------- active PRDs, TELOS, project state
       |-- learning/ (cold) ------- signals, failures, synthesis
       +-- history/ --------------- decisions, changes, security events
```

---

## MEMORY TIERS

| Tier | What | Where | Lifespan |
|------|------|-------|----------|
| **Session** | Current conversation | `memory/session/` | Hours |
| **Work** | Active project PRDs, TELOS, state | `memory/work/` | Weeks-months |
| **Learning** | Signals, failures, synthesis | `memory/learning/` | Permanent |
| **History** | Decisions, changes, security | `history/` | Permanent (audit trail) |
| **Knowledge Index** | Full-text search of everything | `data/jarvis_index.db` | Rebuilt on demand |

---

## DAILY HABITS (5 min)

1. **Open Claude Code in epdev/** -- session hook briefs you automatically
2. **Check the tasklist** -- `orchestration/tasklist.md` or ask "what's active?"
3. **Build, research, or learn** -- follow your energy (this is by design)
4. **Run `/learning-capture` before closing** -- don't rely on the stop hook alone

## WEEKLY HABITS (30 min)

1. **Run `/synthesize-signals`** -- cluster the week's signals into themes
2. **Run `/telos-report`** -- "What has Jarvis learned about me?"
3. **Review `history/security/`** -- any events this week?
4. **Update this bible** -- add any micro-learning from the week
5. **Check jarvis-app** -- node growth = brain growth

---

## WHAT'S AUTONOMOUS vs WHAT NEEDS YOU

### Fully Autonomous (runs without you)

- Heartbeat: 19 metrics every 60 min, auto-signals on regressions
- Knowledge Index: re-indexes all data every 60 min
- Security validator: blocks destructive commands on every tool use
- Event capture: logs all tool use to `history/events/`
- Slack poller: `#jarvis-inbox` messages get processed when `start_jarvis.bat` is running

### Semi-Autonomous (Jarvis does it, you review)

- Learning capture at session end (Jarvis prompts, you confirm)
- Steering rule proposals from synthesis (Jarvis drafts, you approve in CLAUDE.md)
- Signal synthesis (Jarvis clusters, you validate themes)
- Skill suggestions ("This looks like a /research task")

### Requires You

- **TELOS updates** -- only you know if your goals changed
- **New project ideas** -- Jarvis can research but you decide what matters
- **Session direction** -- Jarvis adapts to your energy/mood
- **Irreversible decisions** -- Jarvis always escalates these
- **Mobile voice capture** -- speak into Slack #jarvis-voice from iPhone
- **Life priorities** -- family, work, gym, music -- Jarvis coaches but you execute

---

## EXTERNAL INTEGRATIONS

| Service | How | Status |
|---------|-----|--------|
| **Slack** | MCP (claude.ai Slack) + bot token for posting | Live. 4 channels: #epdev, #general, #jarvis-inbox, #jarvis-voice |
| **Notion** | MCP (claude.ai Notion) | Live. Jarvis Brain: Inbox, Journal, Goals, Ideas, Music, Reports, TELOS Mirror |
| **Google Calendar** | MCP (@cocal/google-calendar-mcp) | Live. 3 calendars. |
| **Gmail** | MCP (@gongrzhe/server-gmail-autoauth-mcp) | Live. Requires new session to load tools. |
| **Tavily** | MCP (npx tavily-mcp, stdio) | Live. Powers `/research` skill. |

---

## SCHEDULED HEARTBEAT

Runs every 60 minutes via Windows Task Scheduler.

### What it does

1. Collects 19 metrics (file counts, signal velocity, ISC ratios, disk usage, etc.)
2. Diffs against previous snapshot
3. Writes auto-signals when WARN/CRIT thresholds crossed
4. Updates Knowledge Index (incremental)
5. Routes alerts to Slack

### Key commands

```powershell
# Verify it's running
schtasks /query /tn "JarvisHeartbeat" /v /fo list

# Manual run
schtasks /run /tn "JarvisHeartbeat"

# Check today's log
type data\logs\heartbeat_2026-03-27.log
```

### Key files

| File | Purpose |
|------|---------|
| `tools/scripts/run_heartbeat.bat` | Task Scheduler wrapper |
| `tools/scripts/jarvis_heartbeat.py` | Heartbeat engine |
| `tools/scripts/jarvis_index.py` | Knowledge Index (build/update/search/stats) |
| `tools/scripts/rotate_events.py` | Log rotation (gzip, retention) |
| `heartbeat_config.json` | Thresholds, collectors, alert routing |
| `memory/work/isce/heartbeat_latest.json` | Latest snapshot |

### Log rotation

Runs automatically at end of each heartbeat cycle. Managed by `rotate_events.py`:
- **Rollup**: daily JSONL files aggregated into monthly summaries after 30 days
- **Gzip**: raw files compressed after 180 days
- **Retention**: files deleted after 90 days (raw) per `heartbeat_config.json`

Dry-run: `python tools/scripts/rotate_events.py`
Execute: `python tools/scripts/rotate_events.py --execute`

### Troubleshooting

**Heartbeat not running:**
```powershell
# Check task status
schtasks /query /tn "JarvisHeartbeat" /v /fo list
# Look for "Status: Ready" and "Last Run Time" within the last 60 min

# Check today's log for errors
type data\logs\heartbeat_%date:~0,4%-%date:~5,2%-%date:~8,2%.log

# Manual test run
cd C:\Users\ericp\Github\epdev
python tools/scripts/jarvis_heartbeat.py
```

**No Slack alerts firing:**
- Verify `SLACK_BOT_TOKEN` is set in user environment variables (not just terminal)
- Check `heartbeat_config.json` alert routing section
- Confirm daily cap (20/channel) hasn't been hit

**Snapshot not updating:**
- Check `memory/work/isce/heartbeat_latest.json` timestamp
- If stale, run heartbeat manually and check for Python errors in log

---

## SECURITY

### What's enforced automatically

- **PreToolUse hook** blocks: fork bombs, rm -rf, git push --force main, disk format, protected paths (.ssh, .aws, .env, .pem, .key), path traversal, prompt injection patterns, secret-like patterns in commands, git reset --hard, git checkout --, git clean -f, inline script destructive commands
- **Constitutional rules** at `security/constitutional-rules.md` -- non-negotiable
- **Secret scanning** before commits
- **Layer 5 subagent scoping** -- background agents have restricted tool access

### What you should watch for

- `history/security/` events (surfaced in session-start hook)
- Heartbeat CRIT alerts in Slack #epdev
- Any prompt injection attempts in external content (Jarvis flags these)

---

## MICRO-LEARNINGS LOG

**Add one line when something clicks.** Monthly: merge duplicates, promote timeless tips.

```
- YYYY-MM-DD -- [tool] -- What you learned.
```

- **2026-03-26** -- [meta] -- The bible is the running UI guide; signals/synthesis are the compounding memory.
- **2026-03-27** -- [knowledge-index] -- `python tools/scripts/jarvis_index.py search "topic"` finds answers from any past session, signal, failure, or decision. Use it before asking Jarvis to re-research something.
- **2026-03-27** -- [workflow] -- Session direction is mood/energy-driven by design. Follow your interest -- Jarvis adapts. Don't force a task order.
- **2026-03-27** -- [meta] -- If you don't know which skill to use, just describe what you want. Jarvis will suggest the right slash command.
- **2026-03-27** -- [algorithm] -- Always check: did we THINK before we BUILD? The jarvis-app shipped without the workflow spec. Building feels productive but specs prevent rework.

---

## TIPS

1. **"Read the PRD and implement"** -- this one sentence does 80% of the work
2. **Rate every session** -- even a quick "7" builds the signal database
3. **TELOS is alive** -- update when your thinking shifts, even slightly
4. **ISC before code** -- writing "what done looks like" saves massive rework
5. **Failures are gold** -- a documented failure is worth more than an unexplained success
6. **Search before re-researching** -- `jarvis_index.py search` may already have the answer
7. **Describe, don't memorize** -- tell Jarvis what you need, it routes to the right skill
8. **THINK before BUILD** -- if there's no spec/document, write one before coding
9. **Mobile capture** -- dictate to Slack #jarvis-voice from iPhone, Jarvis processes it
10. **Trust the heartbeat** -- if something regresses, you'll get a Slack alert

---

## CHANGELOG

### 2026-03-27 -- Major rewrite (Phase 4A)
- Rewrote entire bible to reflect current state (Phase 4A, 33 skills, Knowledge Index)
- Removed Cursor references (retired), ntfy (retired), stale gap tracker
- Added Skills Quick Reference -- addresses #1 pain point (operator familiarity)
- Added Knowledge Index usage
- Updated architecture diagram, integrations, autonomous/human-in-loop
- Added micro-learnings from 3D workflow spec session

### 2026-03-27 -- Phase 3E heartbeat docs
- Added Task Scheduler section, key files, commands

### 2026-03-26 -- Living bible + glossary
- Added glossary, micro-learnings protocol, Desktop vs Code distinction

### 2026-03-24 -- Project initialized
- Created full scaffold, TELOS identity, constitutional security rules

---

*Canonical copy: `docs/EPDEV_JARVIS_BIBLE.md` (in repo).*
*Desktop shortcut should point here. If they diverge, repo wins.*
