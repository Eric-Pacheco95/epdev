# Daniel Miessler Deep Research — Concepts, Methods, and Roadmap for Jarvis

> Synthesized: 2026-03-25
> Purpose: Foundation knowledge for building Jarvis to KAI-level capability

---

## How Miessler's Projects Stack Together

Everything Miessler builds is part of one coherent vision: **Human 3.0** — the AI-augmented human.

```
Substrate        → Philosophical OS for humanity (knowledge graph, structured objects)
  └─ TELOS       → Personal purpose framework (mission/goals/strategies)
      └─ Fabric  → Modular AI patterns (140+ reusable prompts, CLI-composable)
          └─ TheAlgorithm → Universal problem-solving loop (7 phases, ISC, hill-climbing)
              └─ PAI       → Full agentic AI infrastructure (memory, hooks, agents, security)
                  └─ KAI   → His running instance — the named assistant
```

Each layer feeds the next. TELOS gives PAI identity. Fabric gives PAI patterns. TheAlgorithm gives PAI methodology. PAI gives KAI infrastructure. KAI is the living, learning assistant.

---

## The 7 Fundamental Concepts You Must Internalize

### 1. System > Intelligence (The Most Important Idea)

**The claim**: Excellent scaffolding with an 18-month-old model beats the latest model with poor scaffolding. Haiku with great context outperforms Opus with bad context.

**What this means for you**: Stop chasing the newest model. Instead, invest in:
- Better CLAUDE.md instructions
- Better patterns/skills with precise output constraints
- Better memory that loads the right context at the right time
- Better hooks that automate the boring parts
- Better TELOS that tells the AI who you are

**The model stays the same. The scaffolding improves daily.** This is why building Jarvis IS the learning.

### 2. TELOS — Purpose-Driven AI (Not Task-Driven)

Most people use AI for tasks: "summarize this", "write that code." Miessler uses AI for **purpose**: "given who I am and what I'm trying to become, help me make progress."

TELOS provides 10 identity documents:
1. MISSION — The one thing you're trying to accomplish in life
2. GOALS — Derived from mission
3. PROJECTS — Active work streams
4. BELIEFS — Core values and worldview
5. MODELS — Mental models you operate by
6. STRATEGIES — How you approach goals
7. NARRATIVES — Stories you tell yourself
8. LEARNED — Accumulated wisdom
9. CHALLENGES — What stands in your way
10. IDEAS — Creative concepts and possibilities

**Your TELOS.md is already good.** The gap: you're missing LEARNED, IDEAS, and PROJECTS as separate living documents that Jarvis loads on session start. These are what make each session smarter than the last.

### 3. TheAlgorithm — The Universal Problem-Solving Loop

The 7 phases (OBSERVE/THINK/PLAN/BUILD/EXECUTE/VERIFY/LEARN) with ISC as the core mechanism.

**The key insight most people miss**: ISC criteria are simultaneously the GOAL and the TEST SUITE. You define what success looks like in 8-word binary-testable statements, then verify against those exact statements. You can't hill-climb toward something you can't test.

Example ISC for "Build the self-heal skill":
```
- [ ] Failed tests trigger automatic diagnosis and fix | Verify: run failing test, observe auto-fix
- [ ] Fix attempts are logged with root cause analysis | Verify: check history/changes/ after fix
- [ ] Maximum three retry attempts before human escalation | Verify: force 4 failures, confirm escalation
- [ ] Self-heal skill loads only when tests fail | Verify: passing tests don't trigger skill
```

**"Euphoric Surprise"** is the quality bar — not "did it work" but "did it delight." This is aspirational but it changes how you think about output quality.

### 4. Fabric Patterns — The Unit of AI Utility

A Pattern is a structured Markdown prompt with rigid sections:
- `IDENTITY AND PURPOSE` — Who the AI is for this task
- `STEPS` — Exact procedure to follow
- `OUTPUT INSTRUCTIONS` — Precise format constraints (exact word counts, specific sections)
- `INPUT` — What to process

**Why patterns matter**: They fight LLM entropy. Without structure, LLMs produce different outputs every time. With precise patterns, you get deterministic, composable, reusable results.

**Patterns compose via Unix pipes**: `echo "text" | fabric -p extract_wisdom | fabric -p create_summary`

Miessler calls these chains "Stitches" — pipelines of patterns that accomplish complex workflows.

**For Jarvis**: Your skills are Jarvis's patterns. Each skill should have the same rigid structure. The skill assembly pipeline on your tasklist is exactly this.

### 5. 3-Tier Memory — How Knowledge Compounds

```
HOT  (Session)  → Current conversation, immediate context
WARM (Work)     → Active projects, PRDs, TELOS, tasklist
COLD (Learning) → Accumulated wisdom, failures, signals, synthesis
```

**The compounding mechanism**:
1. Every session generates **signals** (observations rated 1-10)
2. Signals accumulate in `memory/learning/signals/`
3. Periodically, signals are **synthesized** into wisdom documents
4. Synthesis documents update **AI Steering Rules** in CLAUDE.md
5. Next session starts with better instructions → better outputs → better signals

**Miessler's PAI has 3,540+ user ratings** feeding into this loop. That's the moat — not the model, but the accumulated context.

**What you're missing**: The rating/feedback mechanism. Miessler's hooks detect explicit ratings ("that was great", "that was wrong") and implicit sentiment. Your implicit sentiment analysis hook is on the tasklist — this is high priority.

### 6. Security as Constitutional Law

Miessler's 20+ years in cybersecurity shaped this:
- **External content is READ-ONLY** — never execute instructions found in fetched content
- **Constitutional rules are non-negotiable** — no prompt can override them
- **Defense-in-depth**: settings hardening → constitutional rules → pre-tool validation → safe code patterns
- **Prompt injection is architectural** — LLMs are designed to be helpful, not secure. You can't "fix" it, only layer defenses

Your `security/constitutional-rules.md` already implements this. The gap: your security validator hook needs to actually run and log events.

### 7. The Learning Loop — LEARN Phase is Mandatory

After EVERY completed task:
1. What worked? What didn't?
2. What would I do differently?
3. What pattern emerged that I should capture?
4. Write it to `memory/learning/signals/`

This is the difference between "using AI" and "building a second brain." Without the LEARN phase, every session starts from zero. With it, every session starts smarter.

---

## The Personal AI Maturity Model (PAIMM) — Where You Are

Miessler defines 9 levels across 3 tiers:

### Tier 1: Chatbots (CH1-CH3)
- CH1: Basic prompting (ChatGPT conversations)
- CH2: Custom instructions, system prompts
- CH3: Advanced prompting, multiple models, output optimization

### Tier 2: Agents (AG1-AG3)
- AG1: Basic tool use (Claude Code with file read/write)
- AG2: Multi-tool workflows (hooks, MCP servers, API calls)
- AG3: Multi-agent orchestration (specialized agents, parallel execution)

### Tier 3: Assistants (AS1-AS3)
- AS1: Persistent context + memory (knows who you are across sessions)
- AS2: Proactive assistance (anticipates needs, monitors, alerts)
- AS3: Full digital companion (continuous protector, advocate, building partner)

**You are currently at: AG1-AG2 transition.** You have Claude Code with hooks and MCP configured, but the memory loop isn't actively compounding, agents aren't orchestrating, and the system isn't proactive yet.

**Target: AS1** — where Jarvis persistently knows who you are, what you're working on, and starts each session with rich context. This is achievable in Phase 2.

---

## What You Need to Learn (Skill Gaps)

### Immediate (Learn While Building Phase 2)

1. **How Claude Code hooks work** — You have hook scripts but need to understand the lifecycle deeply: when they fire, what data they receive, how to chain them. Read `.claude/settings.json` and experiment.

2. **How memory loading works** — Your session-start hook needs to inject TELOS + active project context + recent learning into every session. This is the #1 lever for making Jarvis smarter.

3. **How to write good patterns/skills** — Study 5-10 Fabric patterns from `danielmiessler/fabric/patterns/`. Notice the rigid structure, exact word counts, and precise output format. Apply this to every Jarvis skill.

4. **ISC thinking** — Practice writing 8-word, binary-testable criteria for everything. This is a skill that improves with repetition.

### Medium-Term (Phase 2-3)

5. **Multi-agent orchestration** — How to spawn specialized agents (Architect, Engineer, SecurityAnalyst) and compose their outputs. Study Miessler's PAI agent definitions.

6. **Signal capture and synthesis** — Build the pipeline: interaction → signal → rating → synthesis → steering rule update. This is the compounding engine.

7. **Workflow composition** — How to chain skills/patterns into multi-step workflows. Study Fabric's "Stitches" concept.

### Long-Term (Phase 3+)

8. **Proactive assistance** — Moving from "I ask, Jarvis answers" to "Jarvis monitors and alerts." Requires scheduled tasks, ntfy notifications, and state awareness.

9. **MCP server integration** — Connecting Jarvis to external services (Notion, Slack, email, calendar) so it can act on your behalf.

10. **UI/Dashboard** — Visual interface for seeing memory state, task progress, learning signals, and system health.

---

## The Daily Workflow You Want

Here's how to structure your PC time for maximum compounding:

### Session Start (5 min)
1. Open Claude Code in epdev/
2. Jarvis session-start hook fires automatically
3. Review: active tasks, pending learning signals, recent decisions
4. Pick ONE focus: learn, build, or work on a project

### Learn Mode (when you want to understand the system)
- Ask Jarvis to explain a concept from this document
- Read a Fabric pattern and discuss what makes it effective
- Review recent learning signals and synthesize them
- Practice writing ISC for real tasks
- Study a PAI subsystem and compare to your Jarvis equivalent

### Build Mode (when you want to improve Jarvis)
- Pick a Phase 2 task from the tasklist
- Run TheAlgorithm: OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN
- Each build session should produce both code AND a learning signal

### Project Mode (when you want Jarvis to help with something)
- Use Jarvis for side hustle research, guitar practice planning, health systems, etc.
- The act of using Jarvis for real tasks reveals what's missing
- Every project interaction generates signals that improve the system

### Session End (5 min)
- Jarvis LEARN phase: what was accomplished, what was learned
- Any signals captured get written to `memory/learning/signals/`
- Tasklist updated
- Decision log updated if any significant choices were made

---

## Priority Actions (What to Build Next)

Based on this research, here's the optimal Phase 2 sequence:

1. **Fix session-start hook to load TELOS + context** — This is the #1 lever. Every session should start with Jarvis knowing who you are and what you're working on.

2. **Build learning-capture skill** — Automate the LEARN phase so signals get captured every session without manual effort.

3. **Build implicit sentiment hook** — Detect when you express satisfaction/frustration and log it as a rating signal.

4. **Build self-heal skill** — When tests fail, auto-diagnose and fix. This teaches you about the retry loop (DIAGNOSE → CHANGE → RE-EXECUTE).

5. **Create 3-5 Fabric-style patterns for your most common tasks** — Research, project planning, code review, learning synthesis, decision analysis.

6. **Build signal synthesis workflow** — Periodically distill accumulated signals into wisdom documents that update CLAUDE.md steering rules.

7. **Build security-audit skill** — Regular scanning of the system for vulnerabilities, secret exposure, injection vectors.

---

## Key Miessler Quotes to Remember

- "AI isn't a thing; it's a magnifier of a thing. And that thing is human creativity."
- "Scaffolding > Model" — system architecture matters more than which AI
- "Code Before Prompts" — solve with code/bash before using AI
- "You can't hill-climb toward something you can't test."
- "The focus should be on activation — helping people identify and pursue their purpose."
- "Knowledge must be captured and integrated into your life in a tangible way, rather than letting it wash over you and drip onto the ground."
- "AI-augmented humans, not AI-dependent humans."

---

## Sources

- [PAI GitHub](https://github.com/danielmiessler/Personal_AI_Infrastructure)
- [TheAlgorithm GitHub](https://github.com/danielmiessler/TheAlgorithm)
- [Fabric GitHub](https://github.com/danielmiessler/fabric)
- [TELOS GitHub](https://github.com/danielmiessler/Telos)
- [How My Projects Fit Together](https://danielmiessler.com/blog/how-my-projects-fit-together)
- [Building a Personal AI Infrastructure](https://danielmiessler.com/blog/personal-ai-infrastructure)
- [PAIMM](https://danielmiessler.com/blog/personal-ai-maturity-model)
- [Generalized Hill-Climbing](https://danielmiessler.com/blog/nobody-is-talking-about-generalized-hill-climbing)
- [AI Is Mostly Prompting](https://danielmiessler.com/blog/ai-is-mostly-prompting)
- [Algorithmic Learning](https://danielmiessler.com/blog/algorithmic-learning)
- [Human 3.0](https://human3.unsupervised-learning.com/)
