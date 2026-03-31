# Technical Research: Autonomous Agent Orchestration for Phase 5
- Date: 2026-03-30
- Type: Technical
- Depth: deep
- Sources consulted: 25+
- Prior research: `memory/work/aron-prins-research/research_brief.md` (2026-03-29)

## Executive Summary

Three orchestration approaches exist in the wild. Each solves a different problem. Jarvis needs to pick the right one — or synthesize from all three.

| Approach | Representative | Core Abstraction | Best For |
|----------|---------------|-----------------|----------|
| **Company-as-OS** | Paperclip (Aron Prins) | Org chart: CEO -> managers -> workers | Multi-agent businesses with many independent agents |
| **Visual workflow** | n8n (AI Automators) | DAG: nodes connected by edges | Multi-step pipelines with external integrations |
| **Skill-first brain** | Jarvis (epdev) | Single brain + skills + dispatcher | Solo operator with deep project context |

**Bottom line: Don't adopt Paperclip. Don't adopt n8n. Absorb specific patterns from both into Phase 5's existing SENSE/DECIDE/ACT architecture.**

## Source 1: Paperclip AI (Aron Prins / @dotta)

### What It Is
Open-source agent orchestration platform (39K GitHub stars, launched March 2, 2026). Node.js + React + PostgreSQL. MIT licensed. `npx paperclipai` to start.

### Architecture: Company-as-OS
```
Company Goal
  └── CEO Agent (strategic decisions, quality gate)
        ├── Manager Agent (engineering)
        │     ├── Worker (developer)
        │     └── Worker (QA)
        ├── Manager Agent (marketing)
        │     └── Worker (content strategist)
        └── Manager Agent (operations)
```

**Key concept:** "Control plane, not execution plane." Paperclip orchestrates — agents run wherever they run (Claude Code, Codex, OpenClaw, Python scripts, HTTP webhooks) and phone home.

### Patterns Worth Studying

**1. Task Parentage (Goal Alignment)**
Every task traces back to the company goal through a chain of parents:
```
Current: researching Facebook ads Granola uses
  because → need to create Facebook ads (parent)
    because → need to grow signups by 100 users (parent)
      because → need revenue to $2,000 this week (parent)
        because → building #1 AI note-taking app to $1M MRR
```
**Jarvis relevance:** Our Phase 5 PRD has flat task backlog. Adding goal ancestry (`parent_id` field) would let workers understand "why am I doing this?" — directly addresses the task granularity hard problem.

**2. Heartbeat-Driven Execution**
Agents don't run continuously. They wake on scheduled heartbeats or notifications (assigned task, @-mentioned). Each heartbeat: read memory → check queue → work → report → sleep.
**Jarvis relevance:** Already doing this! Our overnight runner + heartbeat collector = same pattern. Validated.

**3. Routines Engine**
Recurring tasks that re-enter the backlog on schedule. Example: "Every day at 10 AM, read GitHub changes for 24h, craft Discord message." Each routine execution logs tokens spent and output.
**Jarvis relevance:** Our Phase 5C ISC already calls for this. Paperclip confirms the pattern works. Implementation: `routines.jsonl` with schedule + template → dispatcher creates task from template on schedule.

**4. "Memento Man" Mental Model**
Agents wake capable but with zero memory. Need heartbeat checklists, persona prompts, and written context. "If it's not written down, it doesn't exist."
**Jarvis relevance:** Directly maps to our "context profiles" need. Each task type needs a minimal written context package.

**5. Iterative Prompt Refinement as Quality Control**
When an agent does something wrong, you add a rule to its persona prompt. "When it does something you don't like, come in here and say 'rule: make sure you remember to set a success condition for every task.'" This is the current state of the art.
**Jarvis relevance:** Our steering rules system IS this, but automated via /update-steering-rules. We're ahead here.

**6. Budget Enforcement**
Per-agent monthly spend caps. Auto-pause at 100%, soft warning at 80%.
**Jarvis relevance:** Phase 5C ISC already has budget cap. Good to validate this matters in practice — Aron hit $130 in one session with nothing working.

**7. Atomic Task Checkout**
Prevents double-work by ensuring tasks complete fully or not at all. Only one agent works a task at a time.
**Jarvis relevance:** Our lockfile protocol + status state machine already covers this. Validated.

### What NOT to Adopt from Paperclip

| Pattern | Why Skip |
|---------|----------|
| **CEO -> Manager -> Worker hierarchy** | Solves team coordination. Jarvis is one brain, not a team. The hierarchy adds latency and token cost for no benefit in a solo-operator system |
| **Org chart / role / reporting lines** | Same — team abstraction for a personal AI brain is overhead |
| **Multi-company isolation** | We have multi-project, but it's simpler (repo_path per task) |
| **Paperclip as dependency** | Node.js + React + PostgreSQL runtime for something we can build in 200 lines of Python dispatcher. Violates steering rule: "absorb ideas over adopt dependencies" |
| **"Zero-human company" framing** | Jarvis is human-approved autonomous execution, not zero-human. The approval layer is a feature, not a limitation |

## Source 2: The AI Automators (Alan & Daniel) + n8n Patterns

### What They Teach
Production-grade AI agent systems using n8n as the visual orchestration layer. Focus on "real systems that survive production."

### Architecture: DAG-Based Visual Workflows
```
Trigger (webhook/schedule/chat)
  → Orchestrator Agent (routes to sub-agents)
      → Calendar Agent (specialized tools)
      → Email Agent (specialized tools)
      → Expense Agent (specialized tools)
  → Aggregation → Response
```

**Key concept:** The orchestrator agent decides WHICH sub-agent to invoke based on intent. Sub-agents have their own tools, memory, and chat model.

### Patterns Worth Studying

**1. Three Execution Patterns**
| Pattern | When | How |
|---------|------|-----|
| **Sequential** | Each step depends on previous | Agent A → Agent B → Agent C |
| **Parallel** | Independent work streams | Map-Reduce with Execute Workflow nodes |
| **Hierarchical** | Mixed complexity | Gatekeeper routes to specialists |

**Jarvis relevance:** Phase 5 PRD's Tier 0-1 is sequential (dispatcher → worker). Tier 2 adds chains. Worth encoding these as first-class dispatch modes.

**2. Self-Healing Workflows**
When a workflow throws an error, it triggers an error workflow that calls Claude Code. Claude audits the broken workflow, understands what went wrong, and fixes it. "I just get a notification that the error was caught and resolved."
**Jarvis relevance:** We have `self_diagnose_wrapper.py` that does this for runners. The n8n pattern confirms: error → diagnosis → fix → notify is the right loop. Consider extending self-heal to cover dispatcher failures.

**3. Reflection Loops with Bounded Retries**
If a tool fails, the agent re-plans instead of crashing. Limit retries to 3-4 with exponential backoff. Loop counters on ALL retry loops.
**Jarvis relevance:** Our Phase 5 PRD says "Failed tasks don't retry automatically → manual_review queue." This is correct for code changes (Tier 1), but for Tier 0 read-only tasks, bounded retry (max 2) before failing is safer than immediate escalation.

**4. Structured Logging for Post-Mortem**
Every agent action logged to a DB. Full trace: what happened, why, what tools called, what output.
**Jarvis relevance:** Our `manifest_db.py` + `producer_runs` table already does this. Validated and ahead of curve.

**5. Health Check Webhooks**
Monitoring endpoint that reports: agents running, last success, error rate, queue depth.
**Jarvis relevance:** Our heartbeat system is this. Could add dispatcher-specific health metrics in Phase 5B.

**6. Error Compounding Math**
"If each step is 95% accurate and you chain 10 steps, end-to-end accuracy drops to ~60%. QA loops act as error correction checkpoints." This is why ISC verification at every step matters more than one final check.
**Jarvis relevance:** Validates our ISC-per-task design. Each task verifies independently. Don't batch verification.

### What NOT to Adopt from n8n/AI Automators

| Pattern | Why Skip |
|---------|----------|
| **n8n as orchestration layer** | Visual DAG builder solves integration problems. Jarvis's dispatcher is code-first — simpler, more controllable, no new runtime |
| **Redis + Qdrant hybrid memory** | Solves multi-user/multi-session memory at scale. Jarvis is single-operator with file-based memory that works |
| **Map-Reduce 50-100 parallel agents** | Enterprise pattern. Jarvis runs one task at a time by design (lockfile) |
| **Webhook triggers** | We use Task Scheduler. Webhooks add network surface for no benefit |

## Source 3: Broader Ecosystem Patterns

### Ralph Wiggum Loops (Nx/Community Pattern)
Agent keeps working on a task until completion without intervention. When CI fails, self-healing kicks in: classify failure → propose fix → apply → push → repeat until green. Human reviews the final PR.
**Jarvis relevance:** This IS our Phase 5B worker design. Agent works in worktree, runs ISC verify, commits. If ISC fails → task marked failed (we don't auto-retry code changes). For CI-style tasks, the ralph loop pattern could apply.

### Five Levels of Agent Autonomy (Swarmia)
| Level | Description | Jarvis Phase |
|-------|-------------|-------------|
| 0 | Autocomplete | N/A |
| 1 | Chat assistant | Phase 1-2 (skills) |
| 2 | Interactive agent | Phase 3-4 (current) |
| 3 | Task agent (PR from phone) | **Phase 5 target** |
| 4 | Fully autonomous | Phase 6+ (future) |

Phase 5 aims for Level 3: "Can you create a PR from your phone without opening your laptop?"

### GitHub AI Agent Best Practices
- One agent = one responsibility (matches our dispatcher+worker separation)
- Shared context via ADRs + architecture docs (matches our context_files per task)
- Never allow AI to design auth flows unsupervised (matches our protected paths list)
- Multi-agent setups get chaotic fast unless scoped (validates lockfile + one-task-at-a-time)

## Synthesis: What This Means for Phase 5

### Validated Decisions (Our PRD is Already Correct)
1. **SENSE/DECIDE/ACT three-layer** — Paperclip uses the same split (they call it "control plane, not execution plane")
2. **Worktree isolation** — Paperclip has it built in. Community consensus confirms this is non-negotiable
3. **Lockfile / one-at-a-time** — Paperclip's atomic task checkout. Simple is better than parallel for solo operator
4. **ISC as machine-executable verification** — Error compounding math proves per-task verification is essential
5. **Human-approved, not zero-human** — Paperclip's own docs recommend human checkpoints. "Full autonomy is a direction, not where you start"
6. **Budget caps** — Validated by Aron's $130 failure and Paperclip's auto-throttle
7. **Routines engine** — Confirmed as Paperclip's latest shipped feature. Works as designed in our 5C ISC
8. **"Idle Is Success"** — Already a steering rule. Paperclip independently converged on same principle

### Patterns to Absorb into Phase 5 PRD

| # | Pattern | Source | Where to Apply | Effort |
|---|---------|--------|---------------|--------|
| 1 | **Task parentage (goal ancestry)** | Paperclip | Add `parent_id` + `goal_context` to task_backlog.jsonl schema | Low |
| 2 | **Context profiles as "persona prompts"** | Paperclip/Memento Man | Formalize as `context_profiles.md` — what each task type loads | Medium (5A) |
| 3 | **Dispatch modes (sequential/parallel/hierarchical)** | AI Automators | Add `dispatch_mode` field to task schema for Tier 2 chains | Low (5C) |
| 4 | **Bounded retry for Tier 0** | AI Automators | Tier 0 read-only tasks get max 2 retries before failing | Low (5B) |
| 5 | **Self-heal for dispatcher failures** | AI Automators | Extend `self_diagnose_wrapper.py` to cover dispatcher | Medium (5B) |
| 6 | **Anti-patterns table per task type** | Aron Prins | Worker prompt includes growing anti-patterns from failures | Low (5D) |
| 7 | **Pre-creation gate (4 questions)** | Aron Prins | Dispatcher validates before claiming: exists? duplicate? in-scope? serves goal? | Low (5B) |

### What We Should NOT Build

| Anti-pattern | Why | Who Got Burned |
|-------------|-----|---------------|
| CEO agent managing worker agents | Token cost + latency for a single-operator system | Aron hit $130 with this pattern |
| Multi-agent chat threads | Hard to insert quality gates into flowing conversations | AutoGen users per Paperclip analysis |
| Parallel agent swarms | Coordination overhead exceeds benefit for scoped tasks | n8n users warn about state management |
| External orchestration runtime (Paperclip/n8n) | New dependency with its own failure modes; 200-line Python dispatcher does the same | Steering rule: absorb ideas > adopt dependencies |
| Dynamic model routing optimizer | Over-engineering; tier-based defaults + override is sufficient | Paperclip's own docs say start simple |

## The Three Hard Problems (Updated After Research)

### 1. Task Granularity → SOLVED by goal ancestry
Paperclip's task parentage gives workers the "why." ISC gives the "what." Together: worker knows both scope and purpose. Add `goal_context` string to task schema — 1-2 sentences of why this task matters.

### 2. Context Loading → SOLVED by persona profiles
"Memento Man" pattern: write everything down, load only what's needed. Create 3-4 context profiles:
- **Tier 0 (analysis):** CLAUDE.md summary (2K tokens) + relevant file paths + ISC
- **Tier 1 (code change):** Above + project conventions + test commands + anti-patterns for task type
- **Tier 2 (chain):** Tier 1 + chain state + previous step output

### 3. Quality without CEO → SOLVED by ISC + error math
The error compounding insight confirms: verify at every step, not once at the end. Our ISC verify commands ARE the quality gate. Paperclip's CEO agent is overhead we don't need because our verification is machine-executable, not judgment-based.

**New hard problem identified:** **Institutional learning at the task level.** When a task type fails repeatedly, how does the system get smarter? Paperclip uses growing anti-patterns tables. We should add a `task_failures.jsonl` that the worker prompt template reads for its task type. Each failure adds a "Never X because Y" entry.

## Open Questions

1. How does Paperclip handle cross-agent context sharing when tasks depend on each other? (Relevant for our Tier 2 chains)
2. What's Aron's actual autonomous success rate? He documented 12 failure patterns but no success metrics
3. Does the AI Automators' n8n self-healing pattern work for code-level failures or just workflow-level?

## Sources

### Paperclip / Aron Prins
- https://github.com/paperclipai/paperclip (39K stars, core platform)
- https://github.com/paperclipai/paperclip/blob/master/doc/PRODUCT.md
- https://github.com/paperclipai/companies (pre-built company templates)
- https://paperclip.ing/ (official site)
- https://websearchapi.ai/blog/paperclip-ai-agent-orchestrator (detailed interview with Dotta)
- https://www.mindstudio.ai/blog/what-is-paperclip-zero-human-ai-company-framework-2/
- https://flowtivity.ai/blog/zero-human-company-paperclip-ai-agent-orchestration/
- https://www.youtube.com/watch?v=C3-4llQYT8o (Greg Isenberg x Dotta live demo)
- https://www.youtube.com/watch?v=gPbDxMS_x9s (Aron: zero employees using Paperclip)
- https://www.youtube.com/watch?v=2K-_gRZ2ZKw (Aron: agents outgrew me)
- https://x.com/aronprins/status/2032430903566217472

### AI Automators / n8n Patterns
- https://www.theaiautomators.com/blog/
- https://www.youtube.com/watch?v=EV2gqgdmcqs (AI Agent Army tutorial)
- https://blog.n8n.io/best-practices-for-deploying-ai-agents-in-production/
- https://www.reddit.com/r/n8n/comments/1r96rio/ (autonomous agent system architecture)
- https://hatchworks.com/blog/ai-agents/multi-agent-solutions-in-n8n/
- https://stackademic.com/blog/agentic-qa-building-a-self-healing-test-automation-system-using-n8n-and-ai

### Broader Ecosystem
- https://nx.dev/blog/autonomous-ai-workflows-with-nx (Ralph Wiggum loops)
- https://www.swarmia.com/blog/five-levels-ai-agent-autonomy/ (autonomy levels)
- https://github.com/orgs/community/discussions/182197 (GitHub agent best practices)
- https://www.augmentcode.com/learn/how-do-autonomous-ai-agents-transform-development-workflows
- https://c3.ai/blog/autonomous-coding-agents-beyond-developer-productivity/
- https://ericmjl.github.io/blog/2025/11/8/safe-ways-to-let-your-coding-agent-work-autonomously/

## Recommended Next Steps

1. **Update Phase 5 PRD** — Absorb the 7 patterns above into the PRD (task parentage, context profiles, dispatch modes, etc.)
2. `/first-principles` on "Should Jarvis use multi-agent hierarchy or stay skill-first?" — the research says stay skill-first, but worth formally challenging
3. `/architecture-review` on the 7 absorption patterns — confirm none violates existing constraints
4. Start 5A remaining items: skill safety audit, seed backlog, context profiles doc
