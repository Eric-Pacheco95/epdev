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

The 21 cells (7 phases × 3 bands) compress to 7 action profiles. Each phase × band cell references a profile; profile checklists are the enforcement contract.

### Phase × Tier map

| Phase    | T0          | T1-2          | T3-4            |
|----------|-------------|---------------|-----------------|
| OBSERVE  | `P-EXEC`    | `P-CHECKPOINT`| `P-CHECKPOINT`  |
| THINK    | `P-EXEC`    | `P-ADVISOR`   | `P-ARCH-REVIEW` |
| PLAN     | `P-EXEC`    | `P-CONFIRM`   | `P-MIN-VIABLE`  |
| BUILD    | `P-EXEC`    | `P-CHECKPOINT`| `P-CHECKPOINT`  |
| EXECUTE  | `P-EXEC`    | `P-CHECKPOINT`| `P-HITL`        |
| VERIFY   | `P-EXEC`    | `P-CHECKPOINT`| `P-HITL`        |
| LEARN    | `P-EXEC`    | `P-CHECKPOINT`| `P-CHECKPOINT`  |

OBSERVE, BUILD, and LEARN never carry hard halts — exploration and post-action capture are cheap. The **boundary halts** (after PLAN, before EXECUTE on irreversible, after VERIFY on criticals) live inside their respective profiles (`P-MIN-VIABLE` and `P-HITL`).

### Action profile catalogue

Each profile below is the enforcement contract for cells that reference it. Skills and validators read these checklists verbatim; do not paraphrase them in skill prose.

#### `P-EXEC` — inline execution

- [ ] Run the action; no checkpoints, no advisor call, no halts
- [ ] Emit one-line outcome to run log

#### `P-CHECKPOINT` — checkpoint per functional requirement

- [ ] Identify the FR/sub-step before starting
- [ ] At each FR boundary: write a one-line status update (what completed, what is next)
- [ ] On failure of any FR: surface error, do not auto-retry more than once, ask before changing approach
- [ ] At phase end: emit run-summary block (FRs completed, FRs skipped, anomalies)

#### `P-ADVISOR` — pre-phase advisor consultation

- [ ] Before exiting THINK: call `advisor()` with current interpretation + plan summary
- [ ] Surface advisor verdict verbatim in run log
- [ ] If advisor flags a concrete issue: address it inline before exiting THINK
- [ ] If advisor's recommendation conflicts with retrieved primary-source evidence: file a reconcile call before proceeding

#### `P-ARCH-REVIEW` — multi-agent architecture review (T3-4 only)

- [ ] Draft a one-paragraph proposal (≤120 words) before any sub-PRD or decision rule
- [ ] Run `/architecture-review` with 3 parallel agents (first-principles, fallacy, red-team)
- [ ] Wait for all 3 results; reconcile divergences into a verdict block
- [ ] HARD HALT: surface the verdict block + axis profile to Eric, await explicit confirm
- [ ] Do not advance to PLAN until halt is cleared

#### `P-CONFIRM` — draft + single explicit confirm (T1-2)

- [ ] Draft full PRD/plan with 4-axis frontmatter
- [ ] Run `python tools/scripts/isc_validator.py --check-frontmatter --print-tier`; surface output verbatim
- [ ] Run full `isc_validator.py` quality gate; address hard-fails inline
- [ ] Surface plan summary (≤200 words) + tier + axis profile to Eric, await explicit confirm
- [ ] On confirm: advance to BUILD. On change request: re-draft, do not patch around it

#### `P-MIN-VIABLE` — min-viable then full draft (T3-4 only)

- [ ] State minimum-viable design in ≤3 sentences before drafting any artifact
- [ ] HARD HALT: surface min-viable design + axis profile to Eric, await explicit confirm
- [ ] After confirm, draft full PRD with 4-axis frontmatter and `ceremony_tier` field
- [ ] Run `python tools/scripts/isc_validator.py --check-frontmatter --print-tier`; surface ALL hard-fails verbatim (no inline fixes)
- [ ] HARD HALT: surface validator output + ISC count + plan diff to Eric, await explicit confirm
- [ ] Do not proceed to BUILD until both halts cleared
- [ ] Write `data/halt_state/<task_slug>.json` sentinel at each halt; delete on unblock keyword

#### `P-HITL` — human in the loop on irreversible/critical (T3-4 only)

- [ ] Before any irreversible action (commit, push, network call, file delete outside `_archive/`): emit action description + reversibility classification
- [ ] HARD HALT: surface the action + reversibility classification to Eric, await explicit unblock keyword
- [ ] Ambiguous responses (`ok`, `sure`, `looks good`) do NOT clear the halt; re-surface verbatim
- [ ] On unblock: execute the action, log to run log
- [ ] If VERIFY phase produced any critical REVIEW FINDING: HARD HALT, surface findings verbatim, do NOT auto-fix
- [ ] Sentinel at `data/halt_state/<task_slug>.json`; cleared only on canonical unblock keyword

## Halt clearance — canonical unblock keywords

Listed in Layer 5 above. Reproduced here for grep visibility:

```
approved | proceed | go ahead | unblock | confirm | yes proceed
```

Skill-specific keywords allowed when documented in the skill (e.g. `/implement-prd` accepts `build`).

**Ambiguous responses NEVER clear a halt:** `ok`, `sounds good`, `looks good`, `sure`, `fine`, `cool`, `yep`, `yeah`. The skill re-surfaces the halt verbatim.

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
