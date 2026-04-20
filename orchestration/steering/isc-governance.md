# ISC Governance — Steering Rules

> Ideal State Criteria authoring rules and the PLAN→BUILD quality gate. Loaded contextually by ISC-authoring skills (`/create-prd`, `/quality-gate`, `/implement-prd`) rather than universally via `CLAUDE.md`. Extracted from `CLAUDE.md` 2026-04-19 during steering audit to free root context budget.

## ISC Rules

- Each criterion: concise, state-based, binary-testable
- Format: `- [ ] Criterion text here | Verify: method`
- Tag confidence: `[E]`xplicit, `[I]`nferred, `[R]`everse-engineered
- Tag verification type: `[M]`easurable (tested by collectors/metrics) or `[A]`rchitectural (enforced by code structure, verified by review) — prevents building unnecessary monitoring for invariants
- **RUNTIME-GATED verify** — Any ISC verify method containing `curl`, `http://localhost`, or a reference to a running external service must be tagged `RUNTIME-GATED` in the PRD and left `[ ]` until a live environment is confirmed. Code-review confidence is not evidence; the checkbox is a truth claim.

## PRD Evaluation Phase Rules

- **Pre-Registered Decision Matrix** — Any PRD that includes an evaluation phase (A/B test, pilot, migration decision, tool comparison) must commit a decision matrix BEFORE testing begins: win condition (specific numeric threshold), tie rule, sample size with power analysis. Post-hoc threshold setting with uncommitted criteria = confirmation bias. Format: "X wins iff metric_A >= baseline + Y pp AND metric_B <= Z; tie rule: prefer status quo; N ≥ 60 (sign test α=0.05)."
- **Falsification window for "absence of evidence" or "volume" justifications** — Any PRD phase justified by "we have no logs proving X isn't a problem" or "incoming data volume requires Y" must include: (a) a falsification window (explicit start + end date during which evidence is collected), (b) a pre-committed STOP condition that cancels downstream phases if the threshold is unmet, (c) for volume-based claims: enumerate first-20 expected queries and categorize by type — if >70% are structured filters, the correct investment is indexing/tagging, not vector retrieval. Arguments without a stop condition are unfalsifiable and rationalize any build.

## ISC Quality Gate (blocks PLAN → BUILD)

Before BUILD begins, every ISC set must pass these 7 checks. If any check fails, fix the criteria before proceeding — do not build against weak ISC:

1. **Count** — At least 3 criteria for any non-trivial task; no more than 8 for a single phase (split if larger)
2. **Conciseness** — Each criterion is one sentence; no compound criteria joined by "and"
3. **State-not-action** — Criteria describe what IS true when done, not what to DO ("Auth tokens expire after 24h", not "Implement token expiry")
4. **Binary-testable** — Each criterion has a clear pass/fail evaluation with no subjective judgment
5. **Anti-criteria** — At least one criterion states what must NOT happen (prevents regressions, security violations)
6. **Verify method** — Every criterion has a `| Verify:` suffix specifying how to test it (CLI, Test, Grep, Read, Review, Custom)
7. **Vacuous-truth audit** — For every verify method, ask: does it exit 0 on empty output? Pass when its data source is absent? Count non-executable items toward the gate? Grep an artifact that stores its own verify string? Does the verify command reference the **same primary data source** named in the ISC criterion text (if ISC says "producers.json", verify must load producers.json — not a secondary DB)? Any "yes" requires a guard — "exit 0" is not confirmation of the target state. Additionally, any verify using `-newer {ref}`, `stat -c {ref}`, or `diff {ref}` must include a file-existence guard (`test -f {ref} || exit 1`) — a missing reference file must not produce the same exit code as a missing output file. Additionally, for any gate/filter/detection ISC criterion, the verify method must include a **positive-control test** — inject a known-bad state and assert the gate fires. Rule-presence check alone (grep for a pattern, confirm file exists) is insufficient.

## Loaded by

- `.claude/skills/create-prd/SKILL.md` — Step 0.9 ISC drafting and quality gate
- `.claude/skills/implement-prd/SKILL.md` — ISC_QUALITY_GATE step (PLAN→BUILD blocker)
- `.claude/skills/quality-gate/SKILL.md` — Step 0 ISC re-verification
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
