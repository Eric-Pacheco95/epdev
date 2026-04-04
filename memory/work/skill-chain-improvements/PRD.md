# PRD: Skill Chain Quality Improvements

**Project:** Jarvis AI Brain — Skill Chain Improvements
**Status:** READY FOR IMPLEMENTATION
**Last updated:** 2026-04-04
**Architecture review:** Completed (first-principles + fallacy + red-team, 2026-04-04)

---

## OVERVIEW

Four targeted improvements to the Jarvis core skill chain (`/implement-prd`, `/create-prd`, `/review-code`) derived from analysis of external AI coding workflow patterns and validated through parallel architecture review. T5 (`/quality-gate --phase`) was found already implemented and is excluded from scope. Changes ship in two phases: Phase 1 establishes the OWNERSHIP CHECK discipline and phase-scoped build filtering (foundation); Phase 2 adds automated model routing annotation and cross-model review enforcement (routing).

---

## PROBLEM AND GOALS

- **Same-model self-evaluation on every build:** `/implement-prd`'s REVIEW GATE uses the same model instance that wrote the code, violating the existing steering rule and systematically missing generator blind spots
- **No ownership enforcement:** AI-generated code is being merged without Eric demonstrating he understands it — eroding the "AI-augmented not AI-dependent" TELOS mission
- **No phase scoping:** Large PRDs (8+ ISC items, 3+ phases) run full-scope on every build, causing context pollution and cross-phase scope bleed despite `--items` existing as a workaround
- **Model annotation friction:** `/create-prd` outputs ISC items without `model:` annotations, causing `/implement-prd` to interrupt every build asking Eric to classify items he has no context to evaluate at that moment

---

## NON-GOALS

- Changes to the ISC format (no new inline `| Phase: N |` tags — use existing section headers already supported by `detect_phases()`)
- T5 (`/quality-gate --phase N`) — already fully implemented end-to-end
- Changes to overnight autonomous runner or dispatcher model routing
- Any change to `security/validators/validate_tool_use.py`

---

## USERS AND PERSONAS

- **Eric (primary):** ADHD build velocity, build-first learner, tunnel-vision risk in flow state; needs low-friction gates that still enforce discipline
- **Jarvis (execution context):** Claude Code CLI, interactive sessions, Windows platform

---

## USER JOURNEYS OR SCENARIOS

1. Eric runs `/implement-prd memory/work/crypto-bot/PRD.md --phase 1` — only Phase 1 ISC items are built; Phase 2+ remain visible as read-only context but excluded from the build loop
2. Eric runs `/create-prd` on a new feature — ISC items are generated, keyword heuristic proposes `model:` annotations, Eric reviews and confirms the annotation list before it's written to the PRD file
3. Eric completes an implement-prd run — VERIFY RESULTS OWNERSHIP CHECK prompts Eric to write one sentence per ISC item before COMPLETION STATUS is set; the model provides a scaffold sentence, Eric edits or approves it
4. Eric completes an implement-prd run — the REVIEW GATE spawns a fresh Sonnet subagent with explicit adversarial review framing (no build-session context), replacing the same-model LLM step in `/review-code`; the deterministic prescan still runs first

---

## FUNCTIONAL REQUIREMENTS

**Phase 1: Foundation**

- FR-001: `isc_validator.py` exposes a `--phase N` CLI flag that returns only the ISC items under the matching phase section header, using the existing `detect_phases()` function
- FR-002: `/implement-prd` accepts a `--phase N` parameter that calls `isc_validator.py --phase N` to extract the scoped item list before the MODEL ANNOTATION CHECK step; out-of-scope phase sections remain in the PRD context window as read-only text but are excluded from the BUILD loop
- FR-003: OWNERSHIP CHECK in `/implement-prd` VERIFY RESULTS requires Eric to provide one self-attestation sentence per completed ISC item before COMPLETION STATUS is written; the model scaffolds a proposed sentence per item and Eric edits or confirms each one explicitly

**Phase 2: Model Routing**

- FR-004: `/create-prd` applies a deterministic keyword heuristic to each ISC item's criterion text and `| Verify:` method during ISC generation, producing proposed `| model: X |` annotations
- FR-005: Proposed model annotations are presented to Eric in a numbered review list before being written to the PRD file; Eric confirms, edits, or rejects each annotation
- FR-006: The keyword heuristic routes to Opus (no annotation) for any item containing: `security`, `auth`, `trust`, `injection`, `validate`, `policy`, `constitutional`, `architecture`, `design`, or mixed-concern items; routes to `model: haiku` only for pure extraction/existence checks (`| Verify: Grep` or `| Verify: Read` with state verbs `exists`, `present`, `count`); routes to `model: sonnet` for bulk code/file creation items
- FR-007: `/implement-prd` REVIEW GATE spawns a Sonnet subagent with adversarial review framing and passes it the changed file list and PRD ISC context; the subagent has no build-session history, providing fresh-eyes review; the deterministic prescan (ruff + security scan) still runs in the main thread first
- FR-008: The review subagent stdout is checked for rate-limit messages before treating exit code 0 as PASS; empty output blocks the REVIEW GATE with an explicit error; true Codex API integration is deferred to a future sprint

---

## NON-FUNCTIONAL REQUIREMENTS

- All Python changes to `isc_validator.py` must be ASCII-safe (no Unicode in print/logging output) for Windows cp1252
- The `--phase N` flag in `isc_validator.py` must be composable with existing flags (`--prd`, `--json`, `--pretty`)
- `/implement-prd --phase N` on a PRD with no phase section headers must not silently exclude all items — must fall back to full-scope with a printed warning
- Cross-model review subagent must not block the REVIEW GATE for more than one retry cycle; if the subagent fails twice, escalate to manual review prompt, do not silently pass

---

## ACCEPTANCE CRITERIA

### Phase 1: Foundation

- [x] `python tools/scripts/isc_validator.py --prd <path> --phase 1 --json` returns only ISC items under the Phase 1 section header | Verify: CLI | [E] | [M] | model: sonnet
- [x] `/implement-prd memory/work/skill-chain-improvements/PRD.md --phase 1` builds only Phase 1 ISC items while Phase 2 section text is visible but excluded from the build loop | Verify: Review [A]
- [x] OWNERSHIP CHECK in `/implement-prd` VERIFY RESULTS outputs a scaffold sentence per ISC item and requires Eric to confirm or edit before COMPLETION STATUS is written | Verify: Review [A]
- [x] `/implement-prd --phase 1` on a PRD with no phase section headers prints a warning and falls back to full-scope rather than silently building nothing | Verify: CLI | [E] | [M] | model: sonnet
- [x] No ISC item in Phase 1 is marked PASS in OWNERSHIP CHECK without an Eric-authored sentence in the VERIFY RESULTS table | Verify: Review [A] | anti-criterion

ISC Quality Gate: PASS (6/6)

### Phase 2: Model Routing

- [x] `/create-prd` proposes `model:` annotations for ISC items using the keyword heuristic and presents a numbered review list before writing to the PRD file | Verify: Review [A]
- [x] Any ISC item containing `security`, `auth`, `trust`, or `injection` is annotated with no model tag (Opus default) by the heuristic | Verify: Grep | [E] | [M]
- [x] `/implement-prd` REVIEW GATE spawns a Sonnet subagent with adversarial framing and PRD context, replacing the same-model `/review-code` LLM step while keeping the deterministic prescan | Verify: Review [A]
- [x] Empty or rate-limited subagent stdout (exit 0, no content) causes the REVIEW GATE to surface an explicit error rather than silently passing | Verify: Review [A]
- [x] No `model: haiku` annotation is proposed for an ISC item whose criterion text contains code generation verbs (`create`, `write`, `implement`, `refactor`) | Verify: Review [A] | anti-criterion

ISC Quality Gate: PASS (6/6)

---

## SUCCESS METRICS

- Phase-scoped builds (`--phase N`) used on at least 50% of multi-phase PRD runs within 30 days
- OWNERSHIP CHECK produces at least one Eric-authored sentence per completed ISC item (verifiable in VERIFY RESULTS table)
- Codex review catch rate tracked over 10+ implement-prd runs (per existing steering rule); if Codex catches zero additional issues across 20+ tasks, revisit routing
- Zero silent REVIEW GATE passes from rate-limited subagents (tracked via history/decisions audit)

---

## OUT OF SCOPE

- T5 (`/quality-gate --phase`) — already implemented
- New inline `| Phase: N |` tags on individual ISC lines — section headers are sufficient
- Autonomous session model routing changes
- Changes to overnight dispatcher or heartbeat scripts

---

## DEPENDENCIES AND INTEGRATIONS

- `tools/scripts/isc_validator.py` — needs `--phase N` CLI flag (Phase 1)
- `.claude/skills/implement-prd/SKILL.md` — needs `--phase N` parameter, OWNERSHIP CHECK prompt, Codex REVIEW GATE wiring (Phase 1 + 2)
- `.claude/skills/create-prd/SKILL.md` — needs keyword heuristic + review-before-write step (Phase 2)
- Steering rules in `CLAUDE.md` — needs subagent-as-interactive-reviewer rule + note that true Codex API integration is future work (Phase 2)

---

## RISKS AND ASSUMPTIONS

**Risks:**
- Phase section header matching in `detect_phases()` uses regex `Phase|Sprint \d+` — PRDs using non-standard headers (e.g., `### Build Stage 1`) will not match; must validate format before relying on `--phase`
- "Codex adversarial mode" in steering rules is not an implemented API call — `/validation --execute` runs deterministic verify methods only, no LLM; fresh Sonnet subagent is the viable near-term cross-model boundary; real Codex API integration is future work
- OWNERSHIP CHECK scaffold sentence may become a rubber-stamp if Eric confirms without editing; no mechanical enforcement, relies on session discipline

**Assumptions:**
- PRDs using section headers for phases are the standard format; single-phase PRDs (no headers) are common and must degrade gracefully
- `/validation --execute` Codex path is available in interactive sessions (not just overnight runner)
- `detect_phases()` is stable and does not need changes for Phase 1 CLI exposure

---

## OPEN QUESTIONS

- ~~Confirm `/validation --execute` Codex path~~ — confirmed NOT a real API call; deterministic verify methods only; Codex integration is future work
- ~~`detect_phases()` phase label format~~ — confirmed working: `Phase 0 ISC:`, `Phase 1 ISC:` labels all parse correctly; 4 phases, correct item counts
