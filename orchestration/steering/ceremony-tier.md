# Ceremony Tier — Composite Routing from the 4 Task Typing Axes

> Single source of truth for routing ceremony intensity across all 7 ALGORITHM phases. Replaces scattered axis-cascade logic in `model-effort-routing.md`, `autonomous-rules.md`, `task-typing.md`, and per-skill prose.

**Authority chain:**
1. Frontmatter is authoritative (set per PRD, validated by `isc_validator.py --check-frontmatter`).
2. Tier is **derived**, never stored — single source of truth is `tools/scripts/ceremony_tier.py`.
3. This file maps tier → enforceable per-phase action checklists. Skills cite the table; they do not re-derive logic.

## Layer 1 — Tier Function

**Formula:** count of unfavorable axes.

| Axis          | Unfavorable value | Why unfavorable                               |
|---------------|-------------------|------------------------------------------------|
| stakes        | `high`            | irreversible blast radius if wrong             |
| ambiguity     | `high`            | requirements unstable, scope likely to drift   |
| solvability   | `low`             | no known recipe; novel design or research load |
| verifiability | `low`             | hard to detect failure post-build              |

```
tier = sum(axis matches its unfavorable value)
range: 0 .. 4
```

Reference implementation: `tools/scripts/ceremony_tier.py:compute_tier()`.

### Bands

| Band  | Tier values | Meaning                                                  |
|-------|-------------|----------------------------------------------------------|
| T0    | 0           | All axes favorable. Inline execution, no checkpoints.    |
| T1-2  | 1, 2        | Standard ceremony: checkpoint, advisor, single confirm.  |
| T3-4  | 3, 4        | High-ceremony: hard halts at phase boundaries; tier-3-4 is by definition NOT autonomous-overnight work. |

The exact tier (0-4) is logged in `data/review_gate_log.jsonl` for calibration; the band drives behavior.

### Missing-axis policy

| Condition                                  | Behavior                                                   |
|--------------------------------------------|------------------------------------------------------------|
| Frontmatter block entirely absent          | `MissingFrontmatterError` — caller surfaces, refuses to guess |
| Frontmatter present, axis missing          | Default `medium` (favorable). Logged as `axis_default_used`.  |
| Invalid value (e.g. `stakes: critical`)    | `InvalidAxisValueError` — fail loud, no canonicalization      |

### Examples

| Axes profile                                          | Tier | Band  |
|-------------------------------------------------------|------|-------|
| stakes:low, ambiguity:low, solvability:high, verifiability:high   | 0 | T0    |
| stakes:high, ambiguity:low, solvability:high, verifiability:high  | 1 | T1-2  |
| stakes:medium, ambiguity:low, solvability:low, verifiability:medium | 1 | T1-2 |
| stakes:high, ambiguity:high, solvability:high, verifiability:medium | 2 | T1-2 |
| stakes:high, ambiguity:high, solvability:low, verifiability:medium  | 3 | T3-4 |
| stakes:high, ambiguity:high, solvability:low, verifiability:low     | 4 | T3-4 |

### Callers

- `tools/scripts/isc_validator.py --check-frontmatter --print-tier` — emits axes + derived tier
- `.claude/skills/create-prd/SKILL.md` Step -1 — surfaces tier alongside axis verdict during triage
- `.claude/skills/implement-prd/SKILL.md` Step 1 — extracts tier from PRD; routes phase actions per the table below
- `data/review_gate_log.jsonl` — `ceremony_tier_used` field captures the tier at task close

## Layer 2 — Per-Phase × Tier Action Table

**To be added in Step 3.** The 21 cells (7 phases × 3 bands) compress to the 7 action profiles below; each phase × band cell references one profile.

### Action profile catalogue

Profiles are defined here once, referenced by name in the phase × tier map.

| Profile         | Used at                                              | Action checklist (each cell is enforceable) |
|-----------------|-------------------------------------------------------|---------------------------------------------|
| `P-EXEC`        | OBSERVE/T0, BUILD/T0, EXECUTE/T0                      | inline action; no checkpoints, no halts |
| `P-CHECKPOINT`  | OBSERVE/T1-2, BUILD/T1-2, EXECUTE/T1-2                | checkpoint per FR; surface state in run summary; no halts |
| `P-ADVISOR`     | THINK/T1-2                                            | call `advisor()` before next phase; surface advisor verdict |
| `P-ARCH-REVIEW` | THINK/T3-4                                            | run `/architecture-review` (3 parallel agents); HARD HALT after |
| `P-CONFIRM`     | PLAN/T1-2                                             | draft + single explicit confirm before BUILD |
| `P-MIN-VIABLE`  | PLAN/T3-4                                             | min-viable design ≤3 sentences; HARD HALT; full draft after confirm |
| `P-HITL`        | EXECUTE/T3-4 (irreversible), VERIFY/T3-4 with criticals | HARD HALT before action; require explicit unblock |

## Layer 5 — Eric-Interrupt Protocol (HARD HALT mechanism)

A `HARD HALT:` line emitted by a skill is a literal pause point — process stops, awaits explicit unblock keyword from Eric.

### Unblock keywords (canonical)

Any of: `approved`, `proceed`, `go ahead`, `unblock`, `confirm`, `yes proceed`. Skill-specific keywords allowed (e.g., `/implement-prd` accepts `build`).

**Ambiguous responses do NOT clear halts:** `ok`, `sounds good`, `looks good`, `sure`, `fine` — the skill re-surfaces the halt verbatim.

### State persistence (sentinel files)

`data/halt_state/<task_slug>.json` is written when a halt fires, deleted when an unblock keyword clears it. Survives compaction and session boundaries (per CLAUDE.md "Durable files survive compaction" rule).

Sentinel schema:
```json
{
  "task_slug": "deploy-ready-verifier-gate",
  "halt_type": "PLAN_BOUNDARY",
  "halt_text": "min-viable design + axis profile awaiting confirm",
  "phase": "PLAN",
  "tier": 3,
  "fired_at": "2026-04-25T14:32:00Z",
  "expires_at": "2026-04-26T14:32:00Z"
}
```

Cleanup: `/quality-gate` removes sentinels past `expires_at` (24h default).

### Enforcement layers

1. **Convention (SKILL.md):** any skill writing a line starting with `HARD HALT:` stops emitting and exits the current step.
2. **Sentinel check:** at the start of any tier-3-4 phase, the skill checks `data/halt_state/<task_slug>.json`; if present, refuse to proceed and re-surface the pending halt.
3. **Refusal in autonomous mode:** the overnight runner refuses-and-defers tier-3-4 tasks to the next interactive session — they never run unattended.

### Halt points (tier ≥3 only)

- After PLAN phase: surface min-viable design ≤3 sentences + axis profile, await explicit confirm
- Before BUILD phase: surface plan diff + ISC validator output, await explicit confirm
- Before EXECUTE on irreversible action (commit, push, network call, file delete outside `_archive/`): HITL gate
- After VERIFY if any critical REVIEW FINDING: halt, surface findings verbatim, do not auto-fix

Tier 0: no halts. Tier 1-2: standard checkpoints (advisor, single confirm) but no hard halts.

## Layer 4 — Adaptive Verify Routing (DEFERRED)

Gated on 15-30 logged tasks with the extended `review_gate_log.jsonl` schema (Layer 3). At that point `tools/scripts/calibration_rollup.py` will emit `data/ceremony_calibration.json` with profile-keyed suggestions surfaced in REVIEW FINDINGS as **advisory only** — never auto-applied.

If a calibration suggestion proves reliable enough to auto-apply, it should be promoted to a hard rule in this file rather than stay as silent calibration.

## Why this exists

Before this file, ceremony intensity was scattered across: `task-typing.md` (axis triage), `model-effort-routing.md` (advisor/arch-review triggers), `autonomous-rules.md` (write-protect rules), per-skill SKILL.md prose (per-phase behavior), and `isc-governance.md` (verifiability cascade). Each consumed axes independently; rules drifted; the same input produced different ceremony in different skills.

This file collapses those into **one rubric + one action table** so a single edit propagates everywhere.
