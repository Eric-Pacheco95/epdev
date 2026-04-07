---
topic: Current State of AI Agent Frameworks -- LangGraph, CrewAI, AutoGen, Agentless Patterns
type: technical
date: 2026-04-06
depth: default
researcher: Jarvis (autonomous)
task_id: task-1775458801621840
---

# Research Brief: AI Agent Frameworks 2026

## What It Is

AI agent frameworks provide orchestration primitives -- state management, tool routing, multi-agent coordination -- on top of LLM APIs.
The four main patterns in 2026: **LangGraph** (state graph), **CrewAI** (role crew), **AutoGen** (conversational), **Agentless** (pipeline-only, no LLM agency).

---

## How It Works

### LangGraph

- **Architecture**: DAG (directed acyclic graph) of nodes + edges. Each node = agent, function, or decision point. Central `StateGraph` persists shared context across all nodes.
- **State model**: Immutable state snapshots -- each update creates a new version. Prevents race conditions but increases memory usage at scale.
- **Killer feature**: Built-in checkpoints for human-in-the-loop. Execution can pause at any node, serialize state, await approval, and resume. Essential for regulated workflows with audit trails.
- **Current version**: LangGraph 2.0 (2026). LangChain monorepo has 126K+ GitHub stars.
- **Durable execution**: Agents persist through failures; automatically resume from last checkpoint.

### CrewAI

- **Architecture**: Role-based multi-agent teams ("crews"). Each agent has a `role`, `backstory`, and `goal`. Tasks are delegated across the crew.
- **Strength**: Fastest time-to-production -- 40% faster than LangGraph for standard workflows. Can ship a multi-agent team in an afternoon.
- **Use case fit**: Content generation, workflow automation, business process automation.
- **Weakness**: Less control over exact execution flow; hard to debug when role definitions conflict.
- **Status**: Actively maintained; 280K downloads/month in late 2025, growing 3-4x year-over-year.

### AutoGen

- **Architecture**: Conversational multi-agent teams. Agents interact through multi-turn dialogue -- they debate, critique, and refine outputs conversationally.
- **Strength**: Built-in code execution; strong for technical tasks requiring complex reasoning chains.
- **Critical update**: Microsoft has moved AutoGen to **maintenance mode** (no new features, only bug/security fixes). AutoGen v0.4 released January 2026.
- **Replacement**: Microsoft Agent Framework (MAF) -- consolidates AutoGen + Semantic Kernel into a unified enterprise SDK. GA target: Q1 2026.
- **Migration note**: Teams on AutoGen should plan migration to MAF. Existing projects still work, but no new orchestration patterns are coming.
- **Downloads**: 450K/month in late 2025 (higher than CrewAI but declining as migration begins).

### Agentless Pattern

- **Architecture**: No agentic decision-making. The LLM does not autonomously choose next steps or operate complex tools. Instead, the workflow is a **fixed pipeline**: localize, repair, validate -- each step is deterministic code, LLM invoked as a function call.
- **Origin**: OpenAutoCoder/Agentless (arXiv 2407.01489) -- designed for software engineering tasks (SWE-bench).
- **Performance**: 32% on SWE-bench Lite at $0.70/task; with Claude 3.5 Sonnet: 40.7% (Lite) / 50.8% (Verified).
- **Key insight**: Complexity of agent frameworks + limited LLM reliability = compounding error rates. Agentless avoids this by removing LLM agency from control flow.
- **Trade-off**: High performance for well-defined task shapes (bug fixing, code repair). Fails for tasks requiring genuine open-ended reasoning across unknown problem shapes.
- **Jarvis parallel**: This is essentially how Jarvis tasks work -- fixed ISC + deterministic steps + LLM as a function call at each step.

---

## Ecosystem

| Framework | Stars | Monthly Downloads | Status | Primary Org |
|-----------|-------|-------------------|--------|-------------|
| LangGraph | 126K (monorepo) | N/A (embedded) | Active | LangChain AI |
| CrewAI | ~25K | 280K/mo | Active | CrewAI Inc |
| AutoGen | ~42K | 450K/mo | Maintenance | Microsoft |
| Agentless | ~5K | N/A | Research/stable | OpenAutoCoder |

**New entrants (2026):**
- OpenAI Agents SDK -- first-party, tightly integrated with GPT-4o function calling
- Google ADK (Agent Development Kit) -- for Gemini agents
- Anthropic Agent SDK -- Claude-native, matches how Claude Code works internally
- HuggingFace Smolagents -- lightweight, framework-agnostic
- Microsoft Agent Framework -- replaces AutoGen + Semantic Kernel

---

## Gotchas

### LangGraph
- **Security**: CVE-2025-67644 (CVSS 7.3) -- SQL injection in SQLite checkpoint implementation via metadata filter keys. Patched; pin versions.
- **Breaking changes**: `langgraph-prebuilt==1.0.2` (Oct 2025) introduced breaking change to `ToolNode.afunc` signature with no deprecation warning.
- **Learning curve**: State machine mental model is unfamiliar to most devs. Complex async debugging.
- **Silent failures**: Agents don't obviously fail -- a tool error may not surface, agent continues with broken state.
- **Overhead**: Too much ceremony for simple single-agent workflows.
- **MCP/A2A mismatches**: Protocol version mismatches cause subtle bugs -- pin explicitly in production.

### CrewAI
- Loss of deterministic control when agent roles conflict or tasks are ambiguous.
- Role-based model leaks into task output quality -- a poorly written backstory tanks results.

### AutoGen
- **Maintenance mode** -- strategic liability for any new project adopting it now.
- Conversation-based coordination is verbose and token-expensive for simple tasks.

### Agentless
- Only fits structured task shapes. Useless for open-ended exploration.
- Pipeline rigidity -- adding a new task type requires new pipeline code, not just a new prompt.

---

## Examples / Reference Implementations

- **LangGraph production**: Replit, Elastic, LinkedIn -- all use LangGraph for human-in-the-loop code review and approval workflows.
- **Agentless SWE**: OpenAutoCoder/Agentless repo on GitHub -- full implementation in Python, no external deps beyond LLM API.
- **Jarvis parallel**: Jarvis's dispatcher + ISC tasks + skill routing is structurally identical to the Agentless pattern -- deterministic phases, LLM as executor, not planner.

---

## Integration Notes (Jarvis)

- **Adopt nothing** -- Jarvis is already implementing the Agentless pattern correctly. Fixed ISC, deterministic phase gates, LLM as function call.
- **LangGraph's checkpoint pattern** is worth studying for Phase 6 human-in-the-loop design. The pause/serialize/resume model is exactly what backtest review approval gates need.
- **CrewAI's role abstraction** has no Jarvis fit -- single-brain architecture does not benefit from role crews.
- **AutoGen**: maintenance mode -- do not adopt.
- **MAF (Microsoft Agent Framework)**: enterprise-only value prop. No Jarvis fit.
- **Anthropic Agent SDK**: monitor. If Claude Code integrates natively, this becomes relevant to how Jarvis spawns subagents.

---

## Alternatives

| Pattern | Fit |
|---------|-----|
| Direct API calls (no framework) | Best for solo devs; full control; Jarvis already uses this |
| Agentless pipeline | Already Jarvis's pattern -- validated |
| LangGraph checkpoints | Worth studying for human-in-the-loop gates |
| OpenAI Agents SDK | Locked to OpenAI; skip |
| Anthropic Agent SDK | Monitor for native Claude Code integration |
| Smolagents | Lightweight; worth evaluating if Jarvis needs a non-Claude executor path |

---

## Open Questions

1. Does Anthropic's Agent SDK change how Claude Code subagents are invoked -- would it replace current `Task` tool patterns?
2. Is there a production case where LangGraph's state checkpoint pattern is worth backporting into Jarvis's dispatcher (e.g., long-running overnight tasks that partially fail)?
3. As models improve, does the Agentless vs. Agentic tradeoff shift -- does stronger self-evaluation close the gap?

---

## Sources

- [LangGraph official](https://www.langchain.com/langgraph)
- [Fordel Studios: State of AI Agent Frameworks 2026](https://fordelstudios.com/research/state-of-ai-agent-frameworks-2026)
- [LangGraph in 2026 -- DEV Community](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5)
- [LangGraph vs CrewAI vs AutoGen 2026 -- Medium](https://medium.com/data-science-collective/langgraph-vs-crewai-vs-autogen-which-agent-framework-should-you-actually-use-in-2026-b8b2c84f1229)
- [Microsoft retires AutoGen -- VentureBeat](https://venturebeat.com/ai/microsoft-retires-autogen-and-debuts-agent-framework-to-unify-and-govern)
- [AutoGen vs CrewAI 2026 -- is4.ai](https://is4.ai/blog/our-blog-1/autogen-vs-crewai-comparison-2026-332)
- [Agentless: arXiv 2407.01489](https://arxiv.org/abs/2407.01489)
- [Agentless GitHub repo](https://github.com/OpenAutoCoder/Agentless)
- [LangChain/LangGraph CVE -- The Hacker News](https://thehackernews.com/2026/03/langchain-langgraph-flaws-expose-files.html)
- [LangGraph limitations 2025 -- Latenode Community](https://community.latenode.com/t/current-limitations-of-langchain-and-langgraph-frameworks-in-2025/30994)
- [AI Agent Frameworks 2026 -- Apify](https://use-apify.com/blog/ai-agent-frameworks-2026-langgraph-autogen-crewai)

---

## Next Steps

- `/first-principles` -- test Agentless vs. Agentful tradeoff against Jarvis's actual failure modes
- `/make-prediction` -- will Anthropic Agent SDK displace Claude Code's `Task` tool pattern within 12 months?
- Monitor MAF GA release for any patterns applicable to Jarvis's overnight runner
