# Subagent Model Routing

> Load before spawning any Agent subagent. v2 rubric: Stakes × Ambiguity → model + effort.  
> Two layers: Layer 1 (interactive Eric+Jarvis session), Layer 2 (Agent tool spawns).  
> Allowlist posture: defaults fail-safe (expensive but correct); downgrades are explicit and evidence-gated.

## How to use

- Leave the harness default in place when in doubt. The default fails-safe (expensive but correct); downgrading fails-cheap (thin output) and is recoverable only if you notice, which is the hard part.
- On every `Agent` tool call, decide: does this task match a DOWNGRADE row below? If yes, pass `model: "<target>"` in the call.
- **If uncertain, do NOT downgrade.** The cost of an unnecessary Opus/Sonnet call is small and observable in billing. The cost of a thin Haiku subagent output is invisible and can steer downstream decisions wrong.
- If a downgraded subagent returns thin/wrong output, log in "Observed misclassifications" below, REMOVE the row from the allowlist, and respawn at the harness default.

## Stakes × Ambiguity Rubric

Stakes and Ambiguity are **orthogonal axes** — not weights summing to 100%.

- **Stakes → model selection** (what's the cost of being wrong?)
- **Ambiguity → effort level** (how much does the model need to fill in?)

### Stakes definitions

| Level | Criteria |
|-------|----------|
| Low | Reversible, draft, read-only, Eric will review before anything acts on output |
| Medium | Structured adversarial, analysis, output accumulates downstream |
| High | Irreversible (commit, deploy, external write), security-adjacent, TELOS-level |

### Ambiguity definitions

| Level | Criteria |
|-------|----------|
| Low | Schema-constrained output, clear unambiguous instructions, known domain |
| Medium | Some inference needed, partially specified, familiar domain with novel aspect |
| High | Vague task, novel domain, multiple valid interpretations, first-principles required |

### Failure polarity

- Context axis: fail-safe = lean LOW (less context = less noise)
- Model axis: fail-safe = lean LOW (Sonnet not Opus when uncertain)
- Effort axis: fail-safe = lean HIGH (more thinking catches errors; galaxy-brain risk is asymmetrically less costly than missed errors)

Default effort posture: **high**, not medium. Drop to medium only when task is demonstrably mechanical (schema-constrained, Glob/Grep/Read only).

---

## Layer 1 — Interactive (Eric + Jarvis session)

Model is set at session start. Effort is variable per prompt via `/effort`.

| Stakes | Ambiguity | Model | Effort | Example tasks |
|--------|-----------|-------|--------|---------------|
| Low | Low | Haiku | medium | File reads, status checks, mechanical ops |
| Low | Medium | Haiku | high | Brainstorm with vague prompt, low-stakes explore |
| Low | High | Sonnet | high | Low-stakes but high ambiguity (Haiku can't fill gaps) |
| Medium | Low | Sonnet | medium | Adversarial review with clear schema |
| Medium | Medium | Sonnet | high | Standard build/implement tasks |
| Medium | High | Sonnet | max | Debugging unknown root cause, novel domain analysis |
| High | Low | Sonnet | high | Security review with clear spec |
| High | Medium | Opus | high | PRD for irreversible system change |
| High | High | Opus | max | TELOS decisions, novel architecture under uncertainty |

Note: Haiku and Opus are session-start choices in Claude Code; mid-session model switching is not supported. Layer 1 Haiku usage requires Eric to start the session with Haiku selected.

---

## Layer 2 — Subagent spawns (Agent tool)

Agent tool has `model:` but NO `effort:` parameter. Effort is inherited from the session level.

**D4 resolution — effort constraint for Layer 2:**
- **Low-stakes + high ambiguity → Strategy B**: sharpen the spawn prompt to reduce ambiguity before spawning; keep model at stakes-level choice (Haiku for low-stakes). Prompt sharpening is free and preferred.
- **High-stakes + high ambiguity → Strategy A**: escalate model one tier (e.g., Sonnet → Opus) to compensate for the missing effort lever.

| Stakes | Ambiguity | Model | Effort resolution |
|--------|-----------|-------|-------------------|
| Low | Low | Haiku | inherited from session |
| Low | Medium | Haiku | sharpen prompt (Strategy B) |
| Low | High | Haiku | sharpen prompt aggressively (Strategy B) |
| Medium | Low | Sonnet | inherited |
| Medium | Medium | Sonnet | inherited |
| Medium | High | Sonnet | sharpen prompt (Strategy B) |
| High | Low | Sonnet | inherited |
| High | Medium | Opus | model escalation (Strategy A) |
| High | High | Opus | model escalation (Strategy A); sharpen prompt too |

---

## Allowlist (evidence-gated downgrades — v1 rows, now subsumed by rubric above)

> These rows are preserved as evidence seeds for the Layer 2 table above. The rubric supersedes them — use the routing tables, not the allowlist directly.

| Task shape | Downgrade to | Rationale | Evidence-seed |
|---|---|---|---|
| File-read exploration (Glob/Grep/Read only, ≤15 files, single repo) | `claude-haiku-4-5` | Mechanical retrieval; no synthesis; no comparison/ranking | v1 arch-review class (a) allowlist |
| Adversarial review — arch-review, deep-audit, synthesize-signals, delegation classification, second-opinion, pai-cli-demo | `claude-sonnet-4-6` | Sonnet is sufficient for structured adversarial shapes with clear schemas; Opus reserved for open-ended synthesis across ≥10 sources | v2 arch-review convergence; current default is already Opus-or-Sonnet |

## NOT on the allowlist (keep harness default)

Explicitly NOT downgraded — if you see these shapes, do NOT pass `model:`:
- Single-file code edit / refactor (security-adjacent or architectural)
- Research across 3+ sources or novel domains
- Synthesis across 10+ sources or multi-step causal reasoning
- ISC drafting / PRD creation
- Dispatcher autonomous execution (no-human-in-loop)

## Enforcement posture (v2 of this rubric)

- No harness hook. Skill authors read this file and choose model + effort at spawn time per the routing tables.
- **6 pinned skills** (architecture-review, deep-audit, synthesize-signals, second-opinion, delegation, pai-cli-demo) use Sonnet for Layer 2 per the Medium/Low allowlist row — this is consistent with the v2 rubric.
- The allowlist defaults SAFE: a skill author who never reads this file produces correct-but-expensive output. Intended failure mode.
- **v3 (deferred)**: PreToolUse hook reads the rubric and injects `model:` for matching shapes. Ship only once allowlist has stabilized and misclassification log has ≥10 entries with no regressions.
- Open question (D7.2): which pinned skills should call `/effort high` at skill start? Default: "Eric sets effort before invoking skill." Revisit if misclassifications cluster around low-effort Sonnet calls.

## Observed misclassifications

(Append `- YYYY-MM-DD: <task shape> downgraded to <model>, <what went wrong>, row removed` as they occur.)
