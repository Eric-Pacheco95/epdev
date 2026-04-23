# Solvability spectrum (task difficulty: producing a *good* candidate)

> **Phase:** Solvability is a **generate-phase** property. It routes *attempt-vs-escalate* and *retry depth* before code is written. It does **not** directly route eval — that is Verifiability's job. The one cross-phase interaction is the fluent-bluff danger cell (see below).
>
> **Pair:** Use with `orchestration/steering/verifiability-spectrum.md`. The 2D view is consumed by the Task Typing section of `orchestration/steering/autonomous-rules.md`.
>
> **Attribution:** Vertical-AI / agent talks pair "easy to **solve** (generate)" with "easy to **verify**" (Legora-style **verifier** framing). This file is the **solvability** half: how hard is it to produce a **useful** output, not merely *some* output.

## What this measures

**Solvability** = difficulty of going from spec + context -> a **high-quality** artifact **before** a separate check. High solvability means the task is **well-shaped**, has **clear success cues**, and **decomposes** into steps the model/tools can execute reliably.

| Tier | Indicators | Generate-time action |
|------|-------------|----------------------|
| **high** | Narrow scope, crisp ISC, good precedents, tools/APIs that narrow search space, objective partial scores | Attempt directly at stakes-level model tier |
| **medium** | Some ambiguity, needs judgment calls, or messy inputs but expert can still name "done" | Attempt; chunk into smaller sub-ISC if first pass fails; budget 2-3 retries |
| **low** | Fuzzy goal, no stable reference, adversarial or shifting requirements, or output shape unclear until late | **Escalate** — move to next model tier (Sonnet -> Opus), or pause and route to human. Do not self-loop. |

**Label values** in PRD frontmatter: `solvability: low | medium | high`.

## Cross-phase interaction (the one place Solvability touches eval)

**Fluent-bluff danger cell:** `solvability: low` combined with `verifiability: low` produces candidates that *look* convincing but cannot be cheaply checked — the Legora **contract-review** failure mode. When this pair occurs:

- Force HITL — no autonomous sign-off
- OR require an evaluator strictly stronger than the generator (see `autonomous-rules.md` Model Routing)
- Never allow "generator self-grades in a loop" as the only gate

This is the only case where Solvability influences eval routing; everywhere else Verifiability owns eval.

## Anti-patterns

- Confusing "model produced text" with "task was solvable" — always hold **V** in the other hand
- Running **more** agent self-loops on low-solvability × low-verifiability to "get convergence" without an oracle (see `research-patterns` **oracle check** — converged wrong can be **worse** than single wrong)
- Using `defer` (the PreToolUse permission state) to describe Solvability escalation — **use "escalate"** for the model-tier bump, reserve `defer` strictly for the permission state in `security/validators/validate_tool_use.py`

## Loaded by

- `orchestration/steering/autonomous-rules.md` — **Task Typing** section (generate-phase routing)
- `.claude/skills/create-prd/SKILL.md` — PRD frontmatter labeling at Step 1
- `.claude/skills/implement-prd/SKILL.md` — pre-BUILD routing decision
- Dispatcher / autonomous task definitions when scoping subagent **generation**
