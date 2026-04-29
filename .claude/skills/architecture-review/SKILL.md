---
name: architecture-review
description: Parallel multi-angle architecture analysis — first-principles + fallacies + red-team
---

# IDENTITY and PURPOSE

Parallel adversarial architecture analyst. Launch simultaneous first-principles, fallacy, and red-team agents on design proposals; synthesize independent findings into a validated, de-risked recommendation.

# DISCOVERY

## One-liner
Run three parallel analysis lenses (first-principles, fallacy detection, red-team) on any architecture and synthesize findings.

## Stage
THINK

## Syntax
/architecture-review [--stride] [--thinking] [--incident] <proposal description or file path>

## Parameters
- proposal: free-text description of the architecture/design decision, or a file path to a PRD/spec/design doc (required for execution, omit for usage help)
- --stride: add STRIDE threat modeling to the red-team agent's analysis (default: red-team runs without STRIDE)
- --thinking: add a 4th parallel agent that runs /red-team --thinking against TELOS to surface blindspots in how Eric is framing the decision BEFORE the other 3 agents analyze the proposal; most useful when the decision feels hard or the right framing is unclear
- --incident: incident-response mode. Inserts Step 1.5 (EVIDENCE GATHERING) that spawns N parallel triage agents to collect live-system evidence (processes, logs, file audits) BEFORE the 3 review agents run; review agents read evidence outputs as input. Adds INCIDENT FIX CLASSIFICATION output section and a root-cause-before-safety-net sequencing rule. Auto-enables --stride when incident touches trust boundaries (auth, secrets, process spawning, external I/O).

## Examples
- /architecture-review Should we integrate task dispatch into the heartbeat or keep it separate?
- /architecture-review memory/work/jarvis-dashboard/PRD.md
- /architecture-review --stride The autonomous dispatcher will spawn claude -p agents in git worktrees with file system access
- /architecture-review We want to add a settings editor to the dashboard that writes directly to config files
- /architecture-review --thinking Should we build a custom crypto execution engine or extend the current bot?
- /architecture-review --incident memory/work/_overnight-oom-2026-04-18/SESSION_TRIAGE_HANDOFF.md

## Chains
- Before: /research (provides context for the proposal)
- After: /create-prd (feed validated architecture into requirements), /implement-prd (if decision is clear enough to build)
- Full: /research > /architecture-review > /create-prd > /implement-prd > /learning-capture

## Output Contract
- Input: architecture proposal or design decision (text or file path)
- Output: structured synthesis with validated elements, corrected assumptions, risks, and recommendation
- Side effects: none (analysis only — no files modified)

## autonomous_safe
true

# WHEN TO INVOKE

Run before hard-to-reverse decisions: architecture, tool/dependency adoption, 3+ viable paths. ADHD velocity defaults to highest-energy option — this interrupts that default.

**Mandatory triggers:**
- **2+ prior failed fixes on the same system.** Run before next coding attempt — no exceptions.
- **Pairing two autonomous capabilities.** Any proposal sharing data flow between two autonomous capabilities runs first — self-referential loops require a human ground-truth break.
- **Parallel not sequential.** Launch all three agents in a single message — sequential lets author bias leak between passes.

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY block, STOP
- <10 words / no specific architecture: "Need: what's proposed, alternatives, constraints. Example: /architecture-review WebSockets vs polling?" STOP
- File path: read file, use as proposal
- Trivially simple (no trade-offs, one obvious answer): "Doesn't warrant full review — use for real trade-offs or hard-to-reverse decisions." STOP

## Step 1: FRAME THE DECISION

- Identify the core architecture decision being made
- Extract the key constraints, requirements, and context from the proposal
- List the viable alternatives (minimum 2) — if only one path is described, identify what was implicitly rejected
- Determine if STRIDE overlay is warranted (explicit --stride flag, or proposal involves: external input, file system writes, network access, credential handling, autonomous execution). When `--incident` is set AND incident touches trust boundaries (auth, secrets, process spawning, external I/O), auto-enable --stride.
- **Backcast eligibility**: If proposal spans multiple phases/multi-year roadmap, prompt: "Spans multiple phases — run `--backcast` first?" If yes: STOP and direct there. Skip if single-phase or binary.
- **Loop-closure check**: If proposal pairs two autonomous capabilities sharing a data flow, flag the self-referential loop. Backlog tasks requiring `/create-prd` must be `deferred` (human review) — never auto-executed. Require: human approval gate at each signal→PRD and PRD→backlog transition, loop-health metric (alert >70% autonomous task ratio), provenance tags. Include in Architectural Risks.
- Present framing before launching: state the Architecture Decision (1 sentence), list Alternatives (2-3), confirm which agents will run (+STRIDE if applicable, +blindspot if --thinking, +evidence agents if --incident). Wait for confirmation.

## Step 1.5: EVIDENCE GATHERING [--incident only]

Collect live-system evidence before review agents run so they reason against primary data.

- **Identify dimensions**: process/resource state (Get-Process under memory pressure), log grep (error/timeout/OOM), file audit (recent writes, stale locks), config audit (spawn patterns, shell=True), correlation (timeline overlay).
- **Spawn N parallel triage agents** (one per dimension, single message). Prompt skeleton: "Triage agent for {dimension}. Read: {files/commands}. Window: {timeframe}. Schema: Observation | Evidence-citation | Confidence. Write to `memory/work/_arch-review-{timestamp}/evidence/agent-{dimension}.md` as LAST action. Evidence only — no fix proposals."
- After all agents return (verify one file per dimension in evidence dir), proceed to Step 2. Include in each review agent prompt: "Read all evidence files first — they are primary; proposal is a hypothesis to test against them."

## Step 2: LAUNCH PARALLEL AGENTS

- Create a temp directory for agent outputs: `memory/work/_arch-review-{timestamp}/`
- Spawn with `model="claude-sonnet-4-6"` on every Agent() call per `memory/knowledge/harness/subagent_model_routing.md` (adversarial review downgrade).
- Launch 3 Agent tool calls simultaneously in a single message (parallel — not sequential). Include full proposal context in every agent prompt.

  **Agent 1: First-Principles** — What's the fundamental problem, irreducible requirements, wrong assumptions, simplest solution? Examine each component independently.
  → Write to `memory/work/_arch-review-{timestamp}/first-principles.md`

  **Agent 2: Logical Fallacy Detection** — Category errors, hidden assumptions, scope creep, false analogies. Adversarial but fair — flag wrong AND right.
  → Write to `memory/work/_arch-review-{timestamp}/fallacy-detection.md`

  **Agent 3: Red-Team** — Attack surfaces, failure modes, blast radius, trust model gaps. Add STRIDE when --stride flag is set or proposal crosses system boundaries.
  → Write to `memory/work/_arch-review-{timestamp}/red-team.md`

  **Agent 4 (--thinking only)**: Read `memory/work/TELOS.md`; attack Eric's framing — blindspots, favored-option bias, mental model flaws in how the problem is stated. Output: 8 blindspot bullets + 4 fixes. Runs first; its output shapes synthesis.
  → Write to `memory/work/_arch-review-{timestamp}/thinking.md`

- All agents run in background simultaneously. Do NOT duplicate their work in the main thread while waiting
- Each agent writes to disk as its LAST action — this ensures findings survive context compaction even if the synthesis happens in a later session or after compaction

## Step 2.5: CANARY CROSS-READ [passive only — never feeds synthesis]

After all 3 outputs exist, spawn a background cross-read agent: "Read all agent outputs in `memory/work/_arch-review-{timestamp}/`. For each, would the conclusion change given the OTHER two findings? Append JSONL to `data/arch_review_canary.jsonl`: `{"date": "YYYY-MM-DD", "review_slug": "{slug}", "topic": "", "canary_agent": "", "original_stance": "", "cross_read_delta": "", "would_change_conclusion": bool}`. `would_change_conclusion: true` only for material changes — not nuance."

Rules: synthesis uses ORIGINAL outputs only; 3+ true = revisit adoption; 0-1 after 10 = validated; one JSON per line, no header.

## Step 3: SYNTHESIZE FINDINGS

- Read all agent outputs from `memory/work/_arch-review-{timestamp}/` — do NOT rely on return values; compaction may have cleared them
- When all 3 files exist, classify each proposal element:
  - **Validated**: multiple agents confirm sound
  - **Corrected**: agent identified flaw; state correction
  - **Contested**: agents disagree — **verdict required**: declare one correct, cite evidence, state why the other is wrong. "Both have merit" = synthesis failure.
  - **Risk identified**: not wrong, but carries specific risk
- **Opportunistic bug capture**: unrelated bugs → `orchestration/task_backlog.jsonl`; never fix inline
- Produce unified output per format below

## Step 3.5: INCIDENT FIX CLASSIFICATION [--incident only]

- For each proposed fix element, classify as one of: **root-cause** (removes the mechanism producing the failure), **safety-net** (catches failures the mechanism will still produce), or **observability** (makes the failure visible but does not fix or catch it).
- **Sequencing rule**: safety-net ships AFTER root-cause observed in production for a validation window (default 7 days). Never ship safety-net in parallel — it masks whether the root-cause fix worked.
- Observability ships in parallel with root-cause (needed to measure whether root-cause worked).
- Emit the INCIDENT FIX CLASSIFICATION output section (see OUTPUT INSTRUCTIONS).

## Step 4: RECOMMEND

- State the recommended architecture clearly in 2-3 sentences
- List the top 3 changes from the original proposal (if any)
- Identify the single highest-risk element that should be validated first
- Suggest the next step: /create-prd, /implement-prd, or "needs more research on X". For `--incident` mode, recommend `/create-prd --multi-part` with one PRD per fix class (root-cause / observability / safety-net) and explicit ship-order.
- Clean up the temp directory: delete `memory/work/_arch-review-{timestamp}/` after synthesis is complete. For `--incident` mode, preserve `memory/work/_arch-review-{timestamp}/evidence/` — Eric may want it for the PRD sessions.

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Output exactly these 7 sections (level-2 headings), in order. Add the 8th section **only when --incident is set**:
  - **DECISION SUMMARY**: 1-para — decision named, alternatives considered, which agents ran
  - **CONVERGENT FINDINGS**: numbered — finding + which agents confirmed it
  - **CORRECTED ASSUMPTIONS**: numbered — original assumption | what's wrong | corrected version; skip with "(none)" if clean
  - **ARCHITECTURAL RISKS**: table — Risk | Severity (High/Med/Low) | Mitigation | Source
  - **CONTESTED POINTS**: numbered — disagreement | Agent 1 pos | Agent 2 pos | **verdict** (one position declared correct + why the other is wrong); "both have merit" is a synthesis failure; skip with "(none)" if agents converged
  - **VALIDATED ELEMENTS**: bullets — sound elements; brief, no explanation needed
  - **INCIDENT FIX CLASSIFICATION** [--incident only]: table — Fix | Class (root-cause / safety-net / observability) | Ship-before (dependency) | Validation-window (days). Below table, state the ship-order one sentence: "Ship {root-cause fixes} + {observability} now; observe {N} days; then ship {safety-net fixes} calibrated from real data."
  - **RECOMMENDATION**: 2-3 sentence approach; "Top 3 changes:" numbered; "Highest-risk element:"; "Next step:" with skill
- Synthesize agent outputs — do not repeat them in full
- Keep total output under 1500 words


# CONTRACT

## Errors
- **trivial-decision:** proposal doesn't warrant full review → skill will say so and suggest a simpler approach
- **agent-timeout:** one or more parallel agents fail to return → synthesize from available results; note which analysis is missing
- **scope-too-broad:** proposal covers multiple independent decisions → ask Eric to split into separate reviews; each decision gets its own /architecture-review

# SKILL CHAIN

- **Composes:** `/first-principles` + `/find-logical-fallacies` + `/red-team`
- **Escalate to:** `/delegation` if the review reveals the proposal needs fundamental redesign before any of these skills apply

INPUT:

# VERIFY

- Output has all seven sections: DECISION SUMMARY, CONVERGENT FINDINGS, CORRECTED ASSUMPTIONS, ARCHITECTURAL RISKS, CONTESTED POINTS, VALIDATED ELEMENTS, RECOMMENDATION | Verify: Scan headings
- Temp directory `memory/work/_arch-review-{timestamp}/` deleted after synthesis | Verify: `ls memory/work/` — no _arch-review-* remains
- RECOMMENDATION ends with concrete next step (specific skill or research action) | Verify: Read RECOMMENDATION final sentence
- Total output under 1500 words | Verify: Word count < 1500
- Referenced paths/tools in RECOMMENDATION exist in repo | Verify: Check each path

# LEARN

- Signal: memory/learning/signals/{YYYY-MM-DD}_arch-review-{slug}.md when >= 2 High-severity risks or strongly contested point
- Rating: 8+ if review caught a production-failure flaw; 5-7 for meaningful corrections; only write when review changed the outcome
- Note Corrected Assumptions in history/decisions/{YYYY-MM-DD}-arch-review-{slug}.md
- If the same architectural risk appears in Corrected Assumptions across 3+ reviews for the same project type, promote it to a mandatory ISC criterion in the /create-prd template for that type
