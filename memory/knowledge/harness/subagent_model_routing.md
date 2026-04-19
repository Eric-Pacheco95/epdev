# Subagent Model Routing

> Load before spawning any Agent subagent. Claude Code's built-in default (Opus/Sonnet depending on harness) stays in force — this file is an **allowlist of safe DOWNGRADES**, not an escalation guide.

## How to use

- Leave the harness default in place when in doubt. The default fails-safe (expensive but correct); downgrading fails-cheap (thin output) and is recoverable only if you notice, which is the hard part.
- On every `Agent` tool call, decide: does this task match a DOWNGRADE row below? If yes, pass `model: "<target>"` in the call.
- **If uncertain, do NOT downgrade.** The cost of an unnecessary Opus/Sonnet call is small and observable in billing. The cost of a thin Haiku subagent output is invisible and can steer downstream decisions wrong.
- If a downgraded subagent returns thin/wrong output, log in "Observed misclassifications" below, REMOVE the row from the allowlist, and respawn at the harness default.

## Allowlist (safe downgrades only)

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

## Enforcement posture (v1 of this rubric)

- No harness hook. Skill authors read this file and add `model:` explicitly where the allowlist applies.
- The allowlist defaults SAFE: a skill author who never reads this file produces correct-but-expensive output. That is the intended failure mode.
- Next enforcement tier (v2, deferred): PreToolUse hook reads the allowlist and injects `model:` for matching shapes. Only ship once the allowlist has stabilized and evidence supports the rows.

## Observed misclassifications

(Append `- YYYY-MM-DD: <task shape> downgraded to <model>, <what went wrong>, row removed` as they occur.)
