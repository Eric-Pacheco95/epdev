# IDENTITY and PURPOSE

Parallel adversarial architecture analyst. Launch simultaneous first-principles, fallacy, and red-team agents on design proposals; synthesize independent findings into a validated, de-risked recommendation.

# DISCOVERY

## One-liner
Parallel multi-angle architecture analysis — first-principles + fallacies + red-team

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

- If no input provided: print the DISCOVERY section as a usage block, then STOP
- If input is too vague (fewer than 10 words, no specific architecture or decision):
  - Print: "Need a specific architecture proposal or design decision. Describe: what's being proposed, what alternatives exist, what constraints apply. Example: /architecture-review Should we use WebSockets or polling for the dashboard refresh?"
  - STOP
- If input is a file path: read the file and use its content as the proposal
- If the proposal is trivially simple (no trade-offs, single obvious answer):
  - Print: "This doesn't warrant a full architecture review — the answer is straightforward. Only use /architecture-review for decisions with real trade-offs, multiple viable paths, or hard-to-reverse consequences."
  - STOP
- Once validated, proceed to Step 1

## Step 1: FRAME THE DECISION

- Identify the core architecture decision being made
- Extract the key constraints, requirements, and context from the proposal
- List the viable alternatives (minimum 2) — if only one path is described, identify what was implicitly rejected
- Determine if STRIDE overlay is warranted (explicit --stride flag, or proposal involves: external input, file system writes, network access, credential handling, autonomous execution). When `--incident` is set AND incident touches trust boundaries (auth, secrets, process spawning, external I/O), auto-enable --stride.
- **Backcast eligibility**: If proposal spans multiple phases/multi-year roadmap, prompt: "Spans multiple phases — run `--backcast` first?" If yes: STOP and direct there. Skip if single-phase or binary.
- **Loop-closure check**: If proposal pairs two autonomous capabilities sharing a data flow, flag the self-referential loop. Backlog tasks requiring `/create-prd` must be `deferred` (human review) — never auto-executed. Require: human approval gate at each signal→PRD and PRD→backlog transition, loop-health metric (alert >70% autonomous task ratio), provenance tags. Include in Architectural Risks.
- Present framing before launching: state the Architecture Decision (1 sentence), list Alternatives (2-3), confirm which agents will run (+STRIDE if applicable, +blindspot if --thinking, +evidence agents if --incident). Wait for confirmation.

## Step 1.5: EVIDENCE GATHERING [--incident only]

Before launching the 3 review agents, collect live-system evidence so review agents reason against primary data rather than narrative.

- **Identify evidence dimensions** — ask: "What evidence dimensions need parallel collection for this incident?" Common dimensions: process/resource state (ps, CIM — prefer `Get-Process` under memory pressure, R3), log grep (error/timeout/OOM patterns over the incident window), file audit (recent writes, orphan files, stale locks), config audit (spawn patterns, shell=True, .bat wrappers), correlation (timeline overlay of events vs symptoms).
- **Spawn N triage agents in parallel** — one Agent tool call per dimension, all in a single message. Each gets a self-contained prompt naming: the specific files/commands to read, the incident window, the output schema. Each writes findings to `memory/work/_arch-review-{timestamp}/evidence/agent-{dimension}.md` as LAST action.
- **Evidence-agent prompt skeleton:** "You are a triage agent collecting evidence for an incident review. Incident: {1-sentence}. Your dimension: {name}. Read: {files/commands}. Window: {timeframe}. Output schema: {Observation | Evidence-citation | Confidence}. Write to {path} as your LAST action. Do not propose fixes — evidence only."
- **Rule: evidence-only, no fix proposals** — triage agents collect; review agents in Step 2 interpret. Keeps epistemic layers separate.
- After all evidence agents return (check `memory/work/_arch-review-{timestamp}/evidence/` exists with one file per dimension), proceed to Step 2. Review agent prompts in Step 2 must include: "Before analyzing, read all files in `memory/work/_arch-review-{timestamp}/evidence/` — these are the primary findings; the proposal is a hypothesis to test against them."

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

## Step 2.5: CANARY CROSS-READ [always runs, passive data collection only]

After all 3 agent outputs exist on disk, run one lightweight agent to do a cross-read pass. This agent does NOT feed into synthesis — it feeds a failure-mode ledger that gates future Agent Teams adoption.

**Cross-read agent prompt:**
> Read all three agent outputs from `memory/work/_arch-review-{timestamp}/`. For each agent (first-principles, fallacy-detection, red-team), answer: given the OTHER two agents' findings, would this agent's conclusion change? If yes: describe the delta in 1-2 sentences. If no: say "no delta."
> Then append one JSONL entry per agent to `data/arch_review_canary.jsonl`:
> `{"date": "YYYY-MM-DD", "review_slug": "{slug}", "topic": "{1-sentence topic}", "canary_agent": "{agent-name}", "original_stance": "{1 sentence}", "cross_read_delta": "{delta or 'none'}", "would_change_conclusion": true/false}`
> Only set `would_change_conclusion: true` if the delta would have materially changed the recommendation — not just added nuance.

**Canary rules:**
- Synthesis in Step 3 uses ORIGINAL outputs ONLY — canary never feeds back
- Data purpose: failure-mode ledger for Agent Teams adoption. 3+ `would_change_conclusion: true` = revisit; 0-1 after 10 reviews = validated.
- `data/arch_review_canary.jsonl`: one JSON object per line, no header
- Run in background — do not wait before Step 3

## Step 3: SYNTHESIZE FINDINGS

- Read all agent outputs from `memory/work/_arch-review-{timestamp}/` — do NOT rely on agent return values alone, as these may be lost to context compaction in long sessions
- When all agents have completed (all 3 files exist), read their full outputs
- Identify points of convergence (findings that multiple agents agree on — these are high-confidence)
- Identify points of divergence (where agents disagree — these need explicit resolution)
- For each element of the proposal, classify as:
  - **Validated**: Multiple agents confirm this is sound
  - **Corrected**: One or more agents identified a flaw; state the correction
  - **Contested**: Agents disagree — **a verdict is required**: declare one position correct, name the evidence, and state specifically why the other position is wrong. "Both positions have merit" is NOT an acceptable resolution — it is a synthesis failure.
  - **Risk identified**: Not wrong, but carries specific risk that needs mitigation
- **Opportunistic bug capture**: If any agent surfaces a bug or finding UNRELATED to the decision under review, append to `orchestration/task_backlog.jsonl` (or "side findings" bullet if unavailable) — never fix inline. Architecture reviews stay scoped; inline fixes bury the recommendation.
- Produce the unified output using the format below

## Step 3.5: INCIDENT FIX CLASSIFICATION [--incident only]

- For each proposed fix element, classify as one of: **root-cause** (removes the mechanism producing the failure), **safety-net** (catches failures the mechanism will still produce), or **observability** (makes the failure visible but does not fix or catch it).
- Apply the **sequencing rule**: safety-net ships AFTER root-cause has been observed in production for a validation window (default 7 days). Never ship safety-net in parallel with root-cause — the safety-net masks whether the root-cause fix worked.
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
- **trivial-decision:** proposal doesn't warrant full review
  - recover: skill will say so and suggest a simpler approach
- **agent-timeout:** one or more parallel agents fail to return
  - recover: synthesize from available results; note which analysis is missing
- **scope-too-broad:** proposal covers multiple independent decisions
  - recover: ask Eric to split into separate reviews; each decision gets its own /architecture-review

# SKILL CHAIN

- **Composes:** `/first-principles` + `/find-logical-fallacies` + `/red-team` (launches these as parallel agents)
- **Replaces:** Manual sequential invocation of thinking skills on architecture decisions
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
