# Verifiability spectrum (task difficulty: checking a candidate)

> **Phase:** Verifiability is an **eval-phase** property. It routes evaluator tier and whether an oracle exists. It is consumed after BUILD at the REVIEW GATE.
>
> **Pair:** Use with `orchestration/steering/solvability-spectrum.md`. The 2D view is consumed by the Task Typing section of `orchestration/steering/autonomous-rules.md`.

## What this measures

**Verifiability** = how cheap and reliable a **check** is **after** a candidate exists: tests, lints, schemas, diffs to golden, CI, or a **weaker** proxy (similarity, spot-checks). *Not* "feels right to the same model that wrote it."

| Tier | Indicators | Evaluator tier + oracle kind |
|------|-------------|------------------------------|
| **high** | Binary/structured oracles: unit tests, exit codes, `pytest`, schema validation, golden file diff, reproducible script verification | **Script is the verifier.** Skip Sonnet subagent review when the verify method IS the oracle; LLM subagent is backup/spot-check only. Log `evaluator: "script-oracle"`. |
| **medium** | Heuristic checks, linters, spot human review, pairwise compare to priors, statistical checks with known limits | **Sonnet subagent review + detector.** Heuristic qualifies as `medium` iff it has a **positive-control test** (inject known-bad state, assert detector fires) per `isc-governance.md` §ISC Quality Gate check 7. Without the positive control, demote to `low`. |
| **low** | No stable ground truth: strategy, taste, "correct" narrative, or verification only in production / court / late feedback | **Opus subagent OR `/second-opinion` OR Codex adversarial OR HITL.** Forbid "generator self-grades in a loop" as the only gate. Scale evaluator **difficulty** and **independence** to match low V. |

**Label values** in PRD frontmatter: `verifiability: low | medium | high`.

**low is not "unsolvable"** — it is **expensive to know if we won**. The harness must **not** treat one-pass **self-evaluation** as sufficient.

## 2D snapshot (Solvability × Verifiability)

|                | **V = high** | **V = medium** | **V = low** |
|----------------|--------------|----------------|-------------|
| **S = high**   | **Sweet spot** — automate; cheap eval loops | Strong candidate + bounded review | Plausible, fluent output **not** provably right -> **highest** eval and/or HITL (Legora contract cell) |
| **S = medium** | Iterate with clear checks | Mixed — split subtasks to raise V where possible | Default **decision under uncertainty** (log + escalate / proxy + strong eval) |
| **S = low**    | Rare combo — may be V=high for toy slice only | Tread carefully | **Fluent-bluff danger cell** — force HITL; no tournament-until-converged without an oracle |

**Fluent-bluff danger cell:** `solvability: low` × `verifiability: low` — the one place Solvability crosses into eval. Always force HITL or an evaluator strictly stronger than the generator. See `solvability-spectrum.md` for the generate-side framing.

## V = high oracle-drift guard

A V=high oracle that never flags anything can silently drift from reality (tests pinned to old behavior; exit-code-0 masking empty-output bugs). If the high-tier oracle hasn't flagged N consecutive runs (suggest N=20), re-validate with an **injected failure**: deliberately break the invariant the oracle claims to check; if the oracle does not fire, the oracle is broken and the V tier is wrong.

This mirrors `isc-governance.md` §ISC Quality Gate check 7 (positive-control tests for medium-tier heuristics) and the `autonomous-rules.md` capability-gap kill switch (catch-rate monitoring at 20-sample windows).

## Proxy verification

When true low-V (late truth), you may add medium-tier **proxies**: golden style, "similar to last good," **lint**-like consistency rules, or **RAG** on trusted chunks — **mark proxies as such** in the task spec so no one confuses them with full truth.

## Subagent eval routing (with `autonomous-rules.md`)

- **V = high** -> subagent / automated eval can be **lighter** if checks are **already** the oracle (CI, tests) — the **script** is the **verifier**; the LLM subagent is backup or **spot**
- **V = medium** -> **stronger** subagent (Sonnet+), multi-check, **never** same model as generator; track `data/review_gate_log.jsonl`
- **V = low** -> **strongest** eval (Opus / **Codex adversarial**), **or** **human batch**; forbid generator-self-grading as the only gate

## Stakes override

If `stakes: high`, require HITL regardless of V. The stakes eval-depth multiplier supersedes the V-tier default evaluator choice (see Task Typing in `autonomous-rules.md`).

## Loaded by

- `orchestration/steering/autonomous-rules.md` — **Task Typing** section (eval-phase routing) + model pairing and eval
- `.claude/skills/implement-prd/SKILL.md` — REVIEW GATE Step 2 (evaluator tier selection)
- `.claude/skills/create-prd/SKILL.md` — PRD frontmatter labeling at Step 1
- PRD/ISC design, trace grader / overnight review, `memory/knowledge/ai-infra/2026-04-22_legora-complex-agents-beyond-chat.md` (concepts)
- `orchestration/steering/research-patterns.md` — **oracle check** (when convergence machinery is disallowed)
