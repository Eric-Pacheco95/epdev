# Technical Research: Aron Prins - Autonomous Project Lifecycle Pipeline
- Date: 2026-03-29
- Type: Technical
- Depth: full
- Sources consulted: 18+

## Who Is Aron Prins

- **Location:** The Netherlands
- **Background:** 10+ years in online business, indie hacker, #buildinpublic community member
- **Business:** Runs "Aron & Sharon" (joint venture with partner Sharon) -- web development, marketing, software
- **X/Twitter:** @aronprins (744 followers, 8,634 posts)
- **YouTube:** @AronPrins (370 subscribers, ~15 videos focused on Paperclip AI)
- **GitHub:** github.com/aronprins (8 repos, Pro account)
- **Website:** aronprins.com
- **Newsletter:** newsletter.aronprins.com
- **LinkedIn:** CEO at Aron & Sharon

## The Core Tool: Paperclip AI

Paperclip is THE centerpiece of Aron's autonomous pipeline. He is both a **power user** and **contributor** (commits to the repo, authored the company playbook, does consulting for Paperclip setups).

### What Is Paperclip?

- **Open-source orchestration platform** for running teams of AI agents as a "zero-human company"
- **Tagline:** "If OpenClaw is an employee, Paperclip is the company"
- **GitHub:** github.com/paperclipai/paperclip -- **39K stars**, 1,651 commits, MIT license
- **Creator:** @dotta (Aron is a key community contributor/consultant)
- **Tech stack:** Node.js backend, React UI, PostgreSQL (embedded for local dev)
- **Setup:** `npx paperclipai onboard --yes` (one-liner) or clone + `pnpm dev`
- **Runs at:** localhost:3100

### Paperclip Core Features

| Feature | Description |
|---------|-------------|
| **Bring Your Own Agent** | Supports OpenClaw, Claude Code, Codex, Cursor, OpenCode, Pi, Bash, HTTP webhooks |
| **Goal Alignment** | All tasks trace back to company mission; agents understand context |
| **Heartbeats** | Scheduled agent execution with event-based triggers (cron-like) |
| **Cost Control** | Monthly per-agent budgets with automatic throttling |
| **Multi-Company** | Complete data isolation across multiple organizations |
| **Ticket System** | Full conversation tracing + immutable audit logs |
| **Governance** | Approval gates, config versioning, rollback capabilities |
| **Org Charts** | Hierarchies, roles, reporting structures |
| **Mobile Ready** | Manage from any device |
| **Atomic Execution** | Task checkout + budget enforcement prevent double-work |
| **Persistent Agent State** | Sessions resume across heartbeats |
| **Runtime Skill Injection** | Agents learn workflows without retraining |
| **Portable Templates** | Export/import companies with secret scrubbing |
| **Routines Engine** | Triggers, routine runs, coalescing, recurring task portability |
| **Worktree Workflow** | Isolated dev instances with own DB, secrets, git hooks |
| **Plugin System** | Extensible via plugins |
| **Skills Manager** | Manage agent capabilities |

### Supported Agent Runtimes (Adapters)

1. **OpenClaw** -- Gateway adapter with SSE streaming, device-key pairing
2. **Claude Code** -- First-class adapter
3. **Codex** -- First-class adapter
4. **Cursor** -- Adapter with model discovery, run-log streaming, skill injection
5. **OpenCode** -- Adapter with similar capabilities to Cursor
6. **Pi** -- Local RPC mode with cost tracking
7. **Bash** -- Script-based agents
8. **HTTP** -- Webhook-based agents
9. **OpenRouter** -- Any model available on OpenRouter

## Aron's Full Tool Stack

### AI/Agent Layer
| Tool | Role |
|------|------|
| **Paperclip AI** | Orchestration layer -- the "company" that manages all agents |
| **OpenClaw** | Primary AI agent runtime ("the employee") |
| **Claude Code** | Coding agent (used within Paperclip) |
| **Codex** | Coding agent (alternative to Claude Code) |
| **GWS CLI (Google Workspace CLI)** | 15+ agents working in Google ecosystem -- Gmail, Calendar, Drive, Docs, Sheets |
| **Dev Browser** | SEO agent for autonomous backlink building |

### Business/SaaS Products (Built or Managed by AI)
| Product | Description |
|---------|-------------|
| **Traffic Exchange Script** | Business built entirely by Paperclip AI in one week |
| **MyChatbots.AI** | AI chatbot creation/training platform |
| **MyContacts.AI** | AI contact management (SQL from PHP use case) |
| **OptinPage (optin-page.com)** | Email capture/landing page tool |
| **Downline Builder Plugin** | WordPress plugin for network marketing |
| **WP Courses** | Open-source WordPress course plugin (WooCommerce integrated) |

### Infrastructure/Dev Stack
| Tool | Role |
|------|------|
| **Node.js** | Backend runtime (Paperclip) |
| **React** | Frontend (Paperclip UI) |
| **PostgreSQL** | Database (embedded for local, production for deployed) |
| **pnpm** | Package manager |
| **Git** | Version control with worktree workflows |
| **PHP** | Primary language for WordPress plugins/WooCommerce |
| **WordPress + WooCommerce** | E-commerce/content platform |
| **MailWizz** | Email marketing |

### Crypto/Payments
| Tool | Role |
|------|------|
| **crypto-payments-woo** | Custom WooCommerce extension for direct wallet crypto payments (no processor, no fees) |
| **WarriorPlus for WC** | WarriorPlus payment integration for WooCommerce |

## Aron's Autonomous Pipeline (How It Actually Works)

### The Architecture: Two-Layer Verification

```
FOUNDER (Aron)
    |
    v
PAPERCLIP (Orchestration Layer)
    |
    +-- CEO Agent (Quality Gate)
    |       |-- SOUL.md (identity + boundaries)
    |       |-- HEARTBEAT.md (12-step state machine)
    |       |-- AGENTS.md (team roster)
    |       |-- TOOLS.md (API access)
    |       |
    |       +-- Worker Agent 1 (Developer)
    |       |       |-- AGENTS.md (role + DoD)
    |       |       +-- HEARTBEAT.md (self-check)
    |       |
    |       +-- Worker Agent 2 (SEO)
    |       |       |-- AGENTS.md
    |       |       +-- HEARTBEAT.md
    |       |
    |       +-- Worker Agent N...
    |
    +-- OpenClaw / Claude Code / Codex (Execution Engines)
    |
    +-- GWS CLI (Google Workspace integration)
    |
    +-- Cron / Heartbeat Scheduler
```

### Key Design Patterns

1. **"Memento Man" Pattern** -- Agents wake up with zero memory. Every heartbeat cycle starts with reading memory files, context docs, and project inventory. Written context is everything.

2. **Two-Layer Verification** -- Layer 1: Agent self-checks (HEARTBEAT Step 5). Layer 2: CEO verifies output (HEARTBEAT Step 4). Without both, the founder becomes QA.

3. **SOUL Files** -- Define agent identity and boundaries. Include "What We Are" AND "What We Are NOT" to prevent drift. Explicit belief statements like "Quality Control Is My Most Important Job."

4. **Heartbeat State Machine** -- 12 numbered steps per CEO agent cycle:
   - Step 1: Read memory + inventory (prevents stale context)
   - Step 3.5: Pre-creation gate (4 questions before ANY new task)
   - Step 4: Verification via WebFetch before reporting (highest-impact step)
   - Step 6: Anti-drift check before sending updates
   - Step 9: Update instructions + log + verify corrections

5. **"Idle Is Success" Doctrine** -- Completed phases don't require busywork. Agents should NOT generate tasks when backlog is empty.

6. **PROJECT-INVENTORY.md** -- Mandatory file preventing duplicate work. Agents read before acting.

7. **Institutional Learning via Anti-Patterns Tables** -- Each agent's HEARTBEAT grows an anti-patterns table as mistakes occur. The system gets smarter over time.

### Mandatory File Structure (Per Company)

```
company/
  vision.md                    # 1-2 paragraph company vision
  PROJECT-INVENTORY.md         # All existing deliverables
  CONTRIBUTING.md              # Commit conventions, branch strategy
  agents/
    ceo/
      SOUL.md                  # Identity, beliefs, boundaries
      HEARTBEAT.md             # 12-step quality control loop
      AGENTS.md                # Team roster + context
      TOOLS.md                 # API endpoints + system access
      memory/
        daily-notes/           # Persistent memory across heartbeats
    [worker-role]/
      AGENTS.md                # Role, DoD, communication protocol
      HEARTBEAT.md             # Self-check procedures
```

### Production Failure Patterns (Documented)

| # | Failure | Root Cause | Solution |
|---|---------|-----------|----------|
| 1 | CEO as postman | Unverified forwarding | Quality Control Gate (Step 4) |
| 2 | Untested deliverables | No self-check | Worker HEARTBEAT Step 5 |
| 3 | Recurring errors | Instructions not updated | Feedback Loop (Step 9) |
| 4 | Busywork generation | Treating idle as failure | "Idle is success" doctrine |
| 5 | Identity drift | No company definition | SOUL "What We Are" + Anti-Drift Check |
| 6 | Duplicate work | No existence checks | PROJECT-INVENTORY.md mandatory reading |
| 7 | Founder-as-QA | No verification layers | Two-layer verification system |
| 8 | Format mismatches | No format-specific checks | Role-specific self-check |
| 9 | Explorations as final work | Vague DoD | DoD requires final deliverables |
| 10 | Silent context loss | No memory system | Daily notes + Step 1 memory read |
| 11 | CEO without tech understanding | Mitigated by visual red-flags table | |
| 12 | Unclosed feedback loops | Fixes never re-verified | |

## YouTube Content (Recent, Paperclip-Focused)

| Video | Duration | Views | Key Topic |
|-------|----------|-------|-----------|
| I'm Stuck -- My AI Agents Outgrew Me | 25:40 | 1.1K | Scaling pain when agents surpass operator's ability to manage |
| I Spent $130 on AI Agents -- NOTHING Worked... Open-Sourced the Fix | 13:42 | 1.4K | Failure recovery, open-sourced playbook |
| I Had My AI SEO Agent Build Backlinks While I Watched | 9:09 | 375 | Autonomous SEO via Dev Browser |
| My AI Company Runs Itself Now -- So I Started Two More | 21:32 | 1.1K | Multi-company management, Traffic Exchange Script |
| I Let AI Run My Entire Business for a Week | 26:41 | 6.2K | Full week autonomous experiment |
| Paperclip AI with GWS CLI Setup | - | - | 15 agents in Google ecosystem |
| Paperclip AI Complete Guide: Fast Setup, Local Installation | - | - | Setup walkthrough |
| MyChatbots.AI | 4:42 | 128 | AI chatbot platform |
| AI Audiobook Generator | 6:28 | 227 | Content generation |

## Comparison: Aron's Stack vs. Jarvis (epdev)

| Dimension | Aron Prins / Paperclip | Jarvis / epdev |
|-----------|----------------------|----------------|
| **Architecture** | Multi-agent company (Paperclip orchestrates many agents) | Skill-first single brain (39 skills as execution engine) |
| **Orchestration** | Paperclip (external platform) | Custom (tasklist.md, hooks, heartbeat, skills) |
| **Agent model** | CEO agent -> Worker agents (hierarchy) | Flat: Jarvis is the brain, skills are capabilities |
| **Memory** | SOUL.md + daily-notes per agent | 3-tier memory (session/work/learning) + signals |
| **Quality control** | Two-layer verification (agent self-check + CEO check) | ISC quality gate (6 checks), /review-code, /quality-gate |
| **Heartbeat** | Paperclip heartbeat triggers agent wakeup | Custom heartbeat via Task Scheduler |
| **Scheduling** | Paperclip routines engine | Windows Task Scheduler + cron |
| **Git workflow** | Worktree built into Paperclip | Git worktrees (CLAUDE.md steering rule) |
| **Learning** | Anti-patterns tables grow per agent | Signals -> synthesis -> steering rules pipeline |
| **Primary tools** | OpenClaw + Claude Code + Codex + GWS CLI | Claude Code (solo) + MCP servers |
| **Business model** | Multiple zero-human companies | Personal AI brain + project governance |

## Integration Notes (What Jarvis Could Absorb)

### High-Value Patterns to Study

1. **SOUL Files** -- Similar to our agent definitions but more structured. The "What We Are NOT" anti-pattern list is directly applicable to Jarvis agent definitions (we already have Critical Rules in Six-Section anatomy).

2. **"Idle Is Success"** -- Directly relevant to Jarvis autonomous loops. Our heartbeat already has this property (read-only monitoring), but worth encoding as an explicit principle in the overnight runner.

3. **Anti-Patterns Tables That Grow** -- Our signals/synthesis loop achieves similar institutional learning, but Aron's approach of per-agent anti-patterns tables that grow in-place is simpler and more localized. Could enhance our agent definitions.

4. **Two-Layer Verification** -- Our ISC quality gate + /review-code is already stronger than Aron's two-layer system. No action needed.

5. **PROJECT-INVENTORY.md** -- We don't have an explicit deliverables inventory. Not urgent since our tasklist.md + git history covers this.

6. **Pre-Creation Gate (4 Questions)** -- Worth studying. Before creating any new task, the CEO asks: (1) Does this already exist? (2) Is this in the backlog? (3) Is this within our current phase? (4) Does this serve the company mission? Maps to our THINK-before-BUILD steering rule.

### Tools Worth Evaluating

1. **Paperclip itself** -- Evaluate only if Jarvis needs multi-agent coordination. Currently Jarvis is skill-first/single-brain, which is simpler and works. Per CLAUDE.md steering rule: "Jarvis is skill-first, not agent-first."

2. **GWS CLI** -- Google Workspace CLI with 100+ skills for Gmail, Calendar, Drive, Docs, Sheets. We already have Google Calendar and Google Drive MCPs. GWS CLI might offer more unified access. Worth a `/architecture-review` before adopting.

3. **OpenClaw** -- Individual agent runtime. Not needed since Claude Code + skills already covers this for Jarvis.

### What NOT to Adopt

- **Multi-agent hierarchy** -- Jarvis doesn't need a CEO agent managing worker agents. The skill-first model is more appropriate for a single-operator system.
- **Paperclip's company abstraction** -- Overhead for a personal AI brain. We'd be bolting on a team coordination tool for a one-person system.
- **OpenRouter integration** -- We're on Claude Max, no need for token-based model routing.

## Open Questions

- What specific GWS CLI skills does Aron use beyond Gmail, Calendar, Drive?
- How does he handle the $130 cost ceiling he mentions (Paperclip agent budgets)?
- What is his Dev Browser setup for SEO agent work?
- Does he have any custom Paperclip plugins worth studying?

## Sources

- https://www.youtube.com/@AronPrins/videos
- https://github.com/aronprins
- https://github.com/aronprins/paperclip-company-playbook
- https://github.com/paperclipai/paperclip
- https://x.com/aronprins
- https://x.com/aronprins/status/2032430903566217472
- https://www.aronprins.com/
- https://flowtivity.ai/blog/openclaw-vs-paperclip-ai-agent-framework-comparison/
- https://www.youtube.com/watch?v=C3-4llQYT8o (Greg Isenberg x Dotta live demo)
- https://zeabur.com/blogs/deploy-paperclip-ai-agent-orchestration

## Recommended Next Steps

1. `/extract-wisdom` on Aron's playbook repo -- deep pattern extraction
2. `/first-principles` on "Should Jarvis adopt any multi-agent patterns?" -- challenge assumptions
3. `/architecture-review` on GWS CLI vs current Google MCPs -- evaluate tool consolidation
4. Watch the 26:41 "I Let AI Run My Entire Business for a Week" video for operational details
