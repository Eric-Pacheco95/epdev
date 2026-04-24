# Task Typing — Four-Axis Rubric

> Behavioral constraints for PRD triage and evaluator routing. Loaded by create-prd, implement-prd, quality-gate, and the PRD triage gate (Step -1).

The four axes classify every build request before a PRD is drafted and route evaluators after BUILD. Each axis is labeled `low | medium | high` and recorded as YAML frontmatter at the top of every PRD.

## Axes

| Axis | Phase | Question | Spectrum doc |
|------|-------|----------|--------------|
| **stakes** | both | Cost of getting this wrong (reversibility, blast radius) | — |
| **ambiguity** | generate | How clear is the spec? | — |
| **solvability** | generate | How hard is it to produce a high-quality artifact? | `solvability-spectrum.md` |
| **verifiability** | eval | How reliable is the check after a candidate exists? | `verifiability-spectrum.md` |

For per-tier definitions and routing rules, read the linked spectrum docs — this file does not duplicate them.

## PRD Triage

**Step -1 gate on `/create-prd`** — runs before Step 0. Prevents ceremony waste on trivially solvable, reversible, unambiguous requests.

### Heuristic

Classify the incoming request on all three generate-phase axes using keyword signals. If ALL three conditions below are simultaneously true, print `PRD NOT WARRANTED` and STOP. Otherwise carry the axis guess into Step 0 as the frontmatter draft seed.

**S = low** — request contains any of:
`fix`, `typo`, `rename`, `remove`, `delete`, `reorder`, `update X to Y`, `add comment`, `small`, `tweak`, `correct`, `move`
(and no scope markers like "all", "every", "across the codebase")

**A = low** — request is ≤15 words OR names a single concrete deliverable with no decision left to Jarvis.

**Sol = high** — request contains NONE of:
`should`, `design`, `figure out`, `explore`, `options`, `decide`, `strategy`, `approach`, `consider`, `tradeoff`

### Canonical examples

| Request | Verdict | Reason |
|---------|---------|--------|
| "fix typo in README" | NOT WARRANTED | S=low, A=low, Sol=high |
| "rename `get_data` to `fetch_data`" | NOT WARRANTED | S=low, A=low, Sol=high |
| "remove unused import in producers.py" | NOT WARRANTED | S=low, A=low, Sol=high |
| "design new crypto exit-strategy layer" | WARRANTED | S=medium, Sol=medium (design ambiguity) |
| "add overnight monitoring for Moralis CU" | WARRANTED | A=medium (scope undefined), Sol=medium |
| "fix the bug causing calibration rollup to crash" | WARRANTED | Sol=medium (root cause unknown) |

### `--force-prd` override

When `--force-prd` is passed: skip the gate on every invocation, carry a note `[FORCE-PRD: triage gate skipped]` into the PRD's CONTEXT section, and proceed directly to Step 0. No session memory of the override.

### Output when gate fires

```
PRD NOT WARRANTED
Request: "fix typo in README"
S=low | A=low | Sol=high → inline fix; no PRD needed
If this assessment is wrong, re-invoke with --force-prd
```

### Kill trigger

If Eric issues `--force-prd` on >50% of the first 10 triage verdicts, the gate heuristic is miscalibrated. Flag and run `/update-steering-rules --audit` to revise keyword lists before continuing.

## Frontmatter contract

Every PRD must open with:

```yaml
---
stakes:        low | medium | high
ambiguity:     low | medium | high
solvability:   low | medium | high
verifiability: low | medium | high
---
```

PRDs without this block are **grandfathered** (pre-rubric): they pass quality gates with a note rather than failing, until Phase 2 stamper retrofits them.

## Loaded by

- `.claude/skills/create-prd/SKILL.md` — Step -1 triage gate + Step 1 frontmatter labeling
- `.claude/skills/implement-prd/SKILL.md` — REVIEW GATE evaluator routing (via verifiability tier)
- `.claude/skills/quality-gate/SKILL.md` — Step 0 frontmatter axis check
- `orchestration/steering/autonomous-rules.md` — Task Typing section (generate + eval routing)
