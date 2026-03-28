# Technical Research: Agentic Loops & Multi-Agent Orchestration for Claude Code
- Date: 2026-03-28
- Type: Technical
- Depth: Deep
- Sources consulted: 22

## What It Is

**Agentic loops** are the core execution pattern behind modern AI coding agents. Instead of single-shot prompts, an agent runs in a cycle: **Perceive → Reason → Act → Observe → Repeat** until a goal is met or a termination condition triggers. In 2026, this has evolved from simple ReAct loops into sophisticated multi-agent orchestration where specialized agents collaborate, critique each other's work, and iterate until quality gates pass.

The key insight from the research: **the agent's power comes from its definition, not its implementation.** The best developers are spending more time on agent persona design and orchestration architecture than on framework code.

## How It Works

### The Core Loop Patterns

**1. Generator-Critic Loop (most common, most effective)**
```
Generator Agent → produces output
    ↓
Critic Agent → evaluates against rubric/tests
    ↓
If PASS → return result
If FAIL → feed critique back to Generator → iterate
    ↓
Max iterations safety valve (typically 2-5)
```
This is the pattern Google, AWS, LangChain, and every major framework has converged on. The critic can be:
- A separate agent with a different system prompt
- The same model with a "reflection" prompt
- An automated test suite (most reliable)
- A combination (critique + tests)

**2. Iterative Refinement Loop (quality-focused)**
```
Generator → Rough Draft
    ↓
Critique Agent → Optimization Notes
    ↓
Refinement Agent → Polished Version (overwrites draft)
    ↓
Loop until max_iterations OR agent signals "PASS"
```
Key difference from Generator-Critic: three roles instead of two. The Critique agent identifies *what's wrong*, the Refinement agent *fixes it*. This separation prevents the "fix one thing, break another" problem.

**3. Reflexion Pattern (learning across attempts)**
```
Actor Agent → attempts task
    ↓
Evaluator → scores result (pass/fail + reasoning)
    ↓
Self-Reflection → generates verbal feedback stored in memory
    ↓
Actor retries with reflection context loaded
    ↓
Loop until success or max trials
```
Critical addition: **persistent memory between attempts**. The agent doesn't just retry — it learns from failures and carries forward what worked. This maps directly to Jarvis's learning signal pattern.

**4. Brownian Ratchet (always-forward, used by Multiclaude)**
```
Supervisor → decomposes task into PRs
    ↓
Subagents → implement each PR independently
    ↓
CI tests pass? → auto-merge, move forward
CI tests fail? → fix and retry
    ↓
Always push forward — never roll back
```
Philosophy: accept some duplicate work and messy code in exchange for relentless forward progress. Clean up later.

### Claude Code Native Patterns

**Tier 1: Subagents (Task tool) — Single session**
- Parent agent decomposes task, spawns child agents via `Task` tool
- Each subagent gets: own context window, restricted tool access, focused system prompt
- Results flow back to parent only — subagents can't message each other
- Subagents **cannot spawn their own subagents** (no recursion)
- Claude decides parallelization automatically
- Use `Ctrl+B` to background a blocking subagent
- Custom subagents defined as `.md` files with YAML frontmatter

**Tier 2: Agent Teams (experimental) — Multi-session**
- Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Lead agent + N teammates, each in own context window
- **Full mesh communication** — teammates message each other directly
- Shared task list with dependency tracking
- File locking to prevent conflicts
- Best for: collaborative exploration, large refactors

**Tier 3: External orchestrators — Multi-process**
- **Gas Town** (Steve Yegge): supervisor + worker agents, worktree isolation
- **Multiclaude** (Dan Lorenc): Brownian ratchet, auto-merge on CI pass
- **Conductor**: context-driven development, automatic worktree management
- Warning: Steve Yegge runs 3 concurrent Claude Max accounts to maintain pace

**Key architecture decision**: Subagents share the parent's context budget. Agent Teams get independent context windows. For complex work, Teams > Subagents.

### Worktree Isolation

Git worktrees are the **standard isolation mechanism** in 2026 for multi-agent work:
- Each agent gets its own worktree (own branch, own working directory)
- No merge conflicts during parallel development
- Clean integration when agents finish
- Tools like Conductor handle worktree lifecycle automatically

### The Writer/Reviewer Pattern

One of the most effective patterns found across multiple sources:
```
Builder Agent (Opus) → writes code in worktree
    ↓
Reviewer Agent (Opus, read-only) → reviews with lint, test, security-scan
    ↓
Ratio: 1 reviewer per 3-4 builders
    ↓
Lead agent only sees green-reviewed code
```
This is essentially a permanent CI quality gate built into the agent team.

## Ecosystem

### Multi-Agent Frameworks (March 2026 state)

| Framework | Stars | Philosophy | Best For | Maturity |
|-----------|-------|-----------|----------|----------|
| **LangGraph** | 97K+ (LangChain) | Graph-based state machines | Complex stateful workflows, audit trails | GA v1.0.10 |
| **CrewAI** | 44.6K | Role-based teams | Fast prototyping, team analogies | v1.10.1, MCP+A2A |
| **AutoGen/AG2** | 15K+ | Conversational multi-agent | Research, quality-sensitive offline work | RC (merged with Semantic Kernel) |
| **Claude Agent SDK** | — | Subagent orchestration | Claude-native apps | v0.1.48 |
| **Google ADK** | — | LoopAgent + SequentialAgent | Google ecosystem | v1.26.0 |
| **Smolagents** | Rising | Code-as-action | HuggingFace ecosystem, local models | Newest entrant |
| **OpenAI Agents SDK** | — | Lightweight, 100+ models | OpenAI ecosystem | v0.10.2 |

**Verdict for Jarvis**: We don't need an external framework. Claude Code's native subagent + Agent Teams + worktrees covers our orchestration needs. Frameworks like CrewAI/LangGraph are for building standalone agent apps, not for enhancing an existing Claude Code workflow.

### Key Tools for Claude Code Orchestration

| Tool | What it does | GitHub |
|------|-------------|--------|
| **Multiclaude** | Multi-agent orchestrator, auto-merge on CI pass | multiclaude |
| **Gas Town** | Supervisor + workers, worktree isolation | gastown |
| **Conductor** | Context-driven development, worktree lifecycle | conductor |
| **agency-agents** | 120+ agent persona definitions, converts to Claude Code `.md` format | agency-agents (31K stars) |
| **wshobson/agents** | 111 pre-built agent skills for Claude Code with 3-tier model routing | wshobson/agents |

## Gotchas & Limitations

### Loop Failure Modes
1. **Infinite loops** — Always set `max_iterations` (2-5 for critique loops, 3-10 for implementation loops)
2. **Diminishing returns** — After 2-3 iterations, quality plateaus. More iterations = more tokens burned for marginal gains
3. **Error propagation** — If Generator makes a bad structural decision early, Critic can't fix it. Need to detect and restart, not just iterate
4. **Context window exhaustion** — Each loop iteration adds to context. Subagents help by isolating context
5. **Over-parallelizing** — 10 parallel agents for a simple feature wastes tokens and creates coordination overhead. Group related micro-tasks
6. **Vague invocations** — "Implement the feature" fails. Subagents need: specific scope, file references, expected outputs, success criteria

### Claude Code Specific Gotchas
- `Task` must be in `allowedTools` or subagents never spawn
- Never include `Task` in a subagent's own tools (no recursive spawning)
- Agent Teams is experimental — enable with env var
- Background subagents auto-deny permissions not pre-approved
- Steve Yegge's warning: budget 3x Claude Max accounts for sustained multi-agent work
- These orchestration tools are "vibe-coded" — expect bugs and security gaps

### The Quality Paradox
> "The teams extracting real value from AI aren't moving faster. They're iterating differently." — Spiral Scout

Running agents faster doesn't help. Running agents in **structured loops with quality gates** is what works.

## Agent Persona Design: What Actually Works

### The Five Elements (from agenticthinking.ai)
Every effective agent definition needs:

1. **Specific expertise** — narrow, deep, not broad
2. **Defined process** — numbered steps with specific activities
3. **Output format** — exact markdown template with required sections
4. **Constraints** — what it won't do, when it escalates, anti-patterns
5. **Success metrics** — measurable criteria, not "write good code"

### Four Persona Archetypes
| Archetype | Role | Expertise | Best For |
|-----------|------|-----------|----------|
| **The Specialist** | Senior security engineer | Deep but narrow | Audits, optimization, focused analysis |
| **The Generalist** | Principal engineer / Architect | Broad, cross-cutting | Planning, coordination, architecture |
| **The Contrarian** | Red team / Devil's advocate | Finding flaws | Pre-decision stress testing |
| **The Executor** | Implementation engineer | Fast, focused delivery | Building what's been planned |

### The agency-agents Pattern (31K GitHub stars)
Every agent file follows: **Identity & Memory → Core Mission → Critical Rules → Technical Deliverables → Workflow Process → Success Metrics**

Key insight: **Critical Rules and Success Metrics are the differentiators.**
- Bad: "Write good code"
- Good: "Achieve Core Web Vitals score 90+"
- Bad: "You are a helpful assistant"
- Good: "I don't just test your code — I default to finding 3-5 issues and require visual proof for everything"

### The wshobson/agents Library (111 agents with model routing)
Three-tier model strategy:
| Tier | Model | Count | Purpose |
|------|-------|-------|---------|
| Tier 1 | Opus | 14 | Critical decisions — architecture, security, planning |
| Tier 2 | Inherit/Choose | 42 | Complex tasks — AI/ML, backend, frontend |
| Tier 3 | Sonnet | 51 | Support — docs, testing, debugging |
| Tier 4 | Haiku | 18 | Fast ops — SEO, deployment, simple docs |

Organized into divisions: Engineering (14), Debugging (3), Documentation (3), Workflows (5), Testing (2), Quality (2), AI & ML (4), Security (4), Languages (7), and more.

## Integration Notes: What This Means for Jarvis

### Current State (Phase 3A)
- 5 agent definitions: Architect, Engineer, Orchestrator, QATester, SecurityAnalyst
- Skills: `/delegation`, `/spawn-agent`, `/workflow-engine`, `/project-orchestrator`
- No loop patterns implemented
- No quality gate agents
- No model-tier routing

### Gaps Identified
1. **No Critic/Reviewer agent** — The #1 pattern across all sources. Every builder needs a reviewer in the loop
2. **No loop-until-quality pattern** — Our agents run once. The best teams run Generator→Critic→Refine loops
3. **Only 5 agents vs. the 15-120 range** others are using — We're missing: Documentation, Debugging, Performance, DevOps/Deployment, Data, Refactoring specialists
4. **No model-tier routing** — All agents use the same model. wshobson/agents shows Opus for critical, Sonnet for support, Haiku for ops
5. **No AGENTS.md compound learning** — Addy Osmani's pattern: document patterns and gotchas in a shared file that all agents read and update
6. **Agent Teams not enabled** — The experimental feature would give us multi-session coordination
7. **No worktree isolation patterns** — For parallel agent work
8. **Agent definitions lack the Five Elements** — Need to audit against: specific expertise, defined process, output format, constraints, success metrics

### Recommended Architecture for Phase 3A Completion

```
┌─────────────────────────────────────────────┐
│            Orchestrator (Opus)               │
│  Decomposes tasks, routes to specialists     │
│  Reads AGENTS.md for compound learning       │
├─────────────┬───────────────────────────────┤
│  BUILDERS   │  REVIEWERS                     │
│  ─────────  │  ──────────                    │
│  Architect  │  CodeReviewer (read-only)      │
│  Engineer   │  SecurityAuditor (read-only)   │
│  Frontend   │  QATester                      │
│  Data       │  PerformanceProfiler           │
│  DevOps     │                                │
│  Docs       │                                │
├─────────────┴───────────────────────────────┤
│            LOOP PATTERNS                     │
│  Build → Review → Refine (max 3 iterations)  │
│  Implement → Test → Fix (until green)        │
│  Draft → Critique → Polish (for content)     │
└─────────────────────────────────────────────┘
```

**Builder:Reviewer ratio**: 3-4 builders per 1 reviewer (Addy Osmani's recommendation)

### Priority Actions
1. **Add Critic/Reviewer agent** — Read-only, lint+test+security-scan tools only
2. **Implement Generate→Critique→Refine loop** in `/workflow-engine`
3. **Expand agent roster** to 12-15 with proper Five Elements definitions
4. **Add model-tier routing** to `/spawn-agent`
5. **Create AGENTS.md** for compound learning across sessions
6. **Audit existing 5 agents** against Five Elements framework

## Alternatives Considered

| Approach | Tradeoff |
|----------|----------|
| Use CrewAI/LangGraph | Adds framework dependency; Claude Code native tools cover our needs |
| Use Multiclaude/Gas Town | Good for massive parallelism; overkill for single-developer workflow |
| Stay with 5 agents | Quick but leaves quality on the table |
| Jump to Agent Teams | Experimental; start with subagent loops first |
| Build 120 agents like agency-agents | Scope creep; 12-15 well-defined agents covers 90% of needs |

## Open Questions

1. **Agent Teams stability** — Is the experimental flag ready for production use?
2. **Token economics** — What's the actual cost of running 3-iteration critique loops vs. single-shot?
3. **Compound learning** — Should AGENTS.md be per-project or global to Jarvis?
4. **Loop termination** — For Jarvis, should the critic be automated (test suite) or LLM-based?
5. **Worktree cleanup** — How to handle orphaned worktrees from failed agent runs?

## Sources

1. [Multi-agent orchestration for Claude Code in 2026 — Shipyard](https://shipyard.build/blog/claude-code-multi-agent/)
2. [The Code Agent Orchestra — Addy Osmani](https://addyosmani.com/blog/code-agent-orchestra/)
3. [Claude Code Agent Teams: Complete Guide 2026 — ClaudeFast](https://claudefa.st/blog/guide/agents/agent-teams)
4. [Sub-Agent Best Practices — ClaudeFast](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
5. [Create custom subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
6. [Claude Agent SDK: Subagents, Sessions — ksred](https://www.ksred.com/the-claude-agent-sdk-what-it-is-and-why-its-worth-understanding/)
7. [Claude Skills and Subagents — Towards Data Science](https://towardsdatascience.com/claude-skills-and-subagents-escaping-the-prompt-engineering-hamster-wheel/)
8. [AI Coding Agents 2026: Coherence Through Orchestration — Mike Mason](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)
9. [Agentic Coding 2026 — ClaudeLab](https://claudelab.net/en/articles/claude-code/agentic-coding-autonomous-workflow-2026)
10. [Designing agentic loops — Simon Willison](https://simonwillison.net/2025/Sep/30/designing-agentic-loops/)
11. [Choose a design pattern for agentic AI — Google Cloud](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
12. [Multi-agent patterns in ADK — Google Developers](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
13. [Evaluator reflect-refine loop patterns — AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html)
14. [Designing Agent Personas That Actually Work — Agentic Thinking](https://agenticthinking.ai/blog/agent-personas/)
15. [agency-agents: 120 AI Specialist Personas (31K stars)](https://jidonglab.com/blog/agency-agents-en/)
16. [wshobson/agents: 111 agent skills for Claude Code](https://github.com/wshobson/agents)
17. [Crafting Effective Agents — CrewAI Docs](https://docs.crewai.com/en/guides/agents/crafting-effective-agents)
18. [Reflection Agents — LangChain Blog](https://blog.langchain.com/reflection-agents/)
19. [Self-Improving Coding Agents — Addy Osmani](https://addyosmani.com/blog/self-improving-agents/)
20. [AI Agent Frameworks Compared 2026 — Let's Data Science](https://letsdatascience.com/blog/ai-agent-frameworks-compared)
21. [Scaling Claude Code agents — Portkey](https://portkey.ai/blog/claude-code-agents/)
22. [Claude Code Advanced Patterns webinar — Anthropic](https://www.anthropic.com/webinars/claude-code-advanced-patterns)

## Recommended Next Steps

1. `/first-principles` — Break down: what agent loops does Jarvis actually need vs. what's hype?
2. `/red-team` — Stress-test the proposed architecture before building
3. `/create-prd` — PRD for "Phase 3A Completion: Agent Roster Expansion + Loop Patterns"
4. Review [agency-agents repo](https://github.com/msitarzewski/agency-agents) and [wshobson/agents](https://github.com/wshobson/agents) for persona templates to adapt
