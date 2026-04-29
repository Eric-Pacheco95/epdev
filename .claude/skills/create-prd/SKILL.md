---
name: create-prd
description: Generate a product requirements document with ISC criteria
---

# IDENTITY and PURPOSE

PRD specialist. Turn goals, discussions, and partial specs into clear requirements documents grounded in the input — scope, constraints, explicit unknowns — without inventing facts not supplied.

# DISCOVERY

## Stage
PLAN

## Syntax
/create-prd [--user-stories] [--design] [--force-prd] <description or research-brief-path>

## Parameters
- description: free-text feature/product description (required for execution, omit for usage help)
- research-brief-path: optional file path to a /research output for richer context
- --user-stories: force user story generation even for single-actor tasks; useful for jarvis-app frontend features or crypto-bot multi-role flows
- --force-prd: bypass the Step -1 triage gate (use when PRD is explicitly desired for a trivial task)
- --design: enable reference-design intake mode — prompts for a reference screenshot path, embeds it as PRD metadata, adds `--design` flag to ISC verify step, and wires `/design-verify` into the post-build VERIFY chain

## Examples
- /create-prd Build an autonomous task runner for Jarvis that executes safe tasks on a schedule
- /create-prd memory/work/jarvis/research_brief.md
- /create-prd --user-stories crypto-bot Slack approval flow with trader, approver, and dispatcher roles
- /create-prd --design --user-stories rebuild /costs page to match reference design

## Chains
- Before: /research (brief as input), /red-team (stress-test findings as input)
- After: /implement-prd (pass PRD file path as input)
- Full: /research > /first-principles > /red-team > /create-prd > /implement-prd > /learning-capture

## Output Contract
- Input: text description or research brief file path
- Output: PRD file at memory/work/<project-slug>/PRD.md + stdout
- Side effects: creates PRD file in memory/work/

## autonomous_safe
false

# STEPS

## Step -1: PRD TRIAGE GATE

- Read `orchestration/steering/task-typing.md` → `## PRD Triage` section
- If `--force-prd` is in args: skip gate; carry `[FORCE-PRD: triage gate skipped]` into PRD CONTEXT; proceed to Step 0
- Classify the request on three axes using the keyword heuristic in `task-typing.md`:
  - **S=low**: request contains any of: fix, typo, rename, remove, delete, reorder, update X to Y, add comment, small, tweak, correct, move (no scope-wideners like "all", "every", "across")
  - **A=low**: request is ≤15 words OR names a single concrete deliverable with no open decision
  - **Sol=high**: request contains NONE of: should, design, figure out, explore, options, decide, strategy, approach, consider, tradeoff
- Emit 4-line axis guess (all four axes for the frontmatter draft):
  ```
  stakes: [low|medium|high]  ambiguity: [low|medium|high]
  solvability: [low|medium|high]  verifiability: [low|medium|high]
  ```
- Compute and surface the derived ceremony tier alongside the axis guess (count of unfavorable values: stakes=high, ambiguity=high, solvability=low, verifiability=low):
  ```
  ceremony_tier: [0..4]   band: [T0 | T1-2 | T3-4]
  ```
  Tier ≥3 means the upcoming PLAN/BUILD will route through `P-MIN-VIABLE` / `P-HITL` profiles per `orchestration/steering/ceremony-tier.md` Layer 2 (HARD HALT at PLAN→BUILD boundary). Surface this to Eric upfront so the ceremony cost is visible before drafting.
- If ALL THREE of S=low ∧ A=low ∧ Sol=high: print the `PRD NOT WARRANTED` block (see task-typing.md > Output when gate fires) and STOP
- Otherwise: carry the axis guess into Step 0 as the frontmatter seed; proceed normally

**Kill trigger:** if Eric issues `--force-prd` on >5 of the first 10 triage verdicts, surface: "Gate may be miscalibrated — run `/update-steering-rules --audit` to revise keyword lists."

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY block, STOP
- <5 words / no problem statement: "Need: (1) problem, (2) who uses it, (3) concrete example. Or run /research first."
- Looks like impl request (code/paths/"fix this"): suggest /implement-prd or assess scope
- PRD exists at target path: "Overwrite or versioned copy?" — STOP for decision
- Complex topic, no research brief: "Run /project-init or /research first? Proceed standalone?"
- **External-source gate**: input references URL/tweet/paper/"saw X" → "Run /architecture-review (absorb-vs-adopt)?" If skipped: note bypass in PRD CONTEXT.

## Step 0.5: USER STORY CHECK (optional, auto-triggered)

- Scan input for distinct actor types
- If 2+ actors AND no user stories in input: generate stories BEFORE requirements
  - Format: `As a [actor] / I want [capability] / So that [outcome]` + 3-5 acceptance criteria; plain, no jargon
  - Present to Eric, confirm before proceeding (stories = WHAT; requirements = HOW)
- 1 actor: skip silently
- Force with `--user-stories` flag

## Step 0.6: PAIRED-PRD CHECK (auto-triggered)

- Scan for sibling-PRD markers: "PRD-2", "parallel PRD", "paired", "same incident", "related PRD"; explicit `memory/work/*/PRD.md` path; or shared root cause framing.
- If marker present OR Eric named a sibling: ask "Is this paired with another in-flight PRD? Name it." If confirmed, draft MUST include: (1) `related-prds:` frontmatter entry, (2) ASSUMPTIONS shipping-order entry (e.g., "PRD-1 ships before this begins BUILD so [rule] is policy"), (3) at least one anti-criterion enforcing the sibling's core rule locally.
- No marker + no named sibling: skip silently.

## Step 0.7: SOCRATIC BRAINSTORM (before extracting requirements)

Ask 3-5 targeted questions before generating content:
1. Underlying problem? Simpler 80% version?
2. Approaches considered and discarded? Why?
3. What does "done" look like? What would make you abandon mid-build?
4. What can this NOT touch or break?
5. Smallest shippable version? What's explicitly out?

Wait for answers. If Eric says "skip": proceed but flag in OPEN QUESTIONS.

## Step 0.9: LOAD AUTONOMOUS STEERING RULES

- Read `orchestration/steering/autonomous-rules.md` (ISC anti-criterion constraints + Task Typing for frontmatter)
- Read `orchestration/steering/solvability-spectrum.md` + `orchestration/steering/verifiability-spectrum.md` (per-tier defs)

## Step 0.95: BLOCKER-LIST EVIDENCE PRE-CHECK

Check session context for evidence resolving each blocker before asking Eric. Ask only for: (a) preference/option choice, or (b) live external verification needed. Resolve silently; note in ASSUMPTIONS.

## Step 1: EXTRACT

- **Task Typing frontmatter (required)** — every PRD must include a leading YAML frontmatter block as the first element of the output PRD, declaring the four Task Typing axes per `orchestration/steering/autonomous-rules.md` > Task Typing:
  ```yaml
  ---
  stakes:        low | medium | high
  ambiguity:     low | medium | high
  solvability:   low | medium | high
  verifiability: low | medium | high
  ---
  ```
  Choose from input signal. Rubric: `stakes`=cost of getting it wrong; `ambiguity`=spec clarity; `solvability`=difficulty (see solvability-spectrum.md); `verifiability`=oracle strength (see verifiability-spectrum.md). Default unspecified axes to `medium`; add to OPEN QUESTIONS.
- Extract name, audience, problem from input
- Separate stated from implied goals; list explicit non-goals when provided or implied
- Identify personas when input supports them; otherwise "Assumed users: [X]" with gaps flagged
- Derive functional requirements as testable statements; group by theme/journey
- Capture NFRs the input mentions (performance, availability, compliance, localization)
- Define acceptance criteria measurably; mark items needing stakeholder validation
- List named dependencies, integrations, external systems
- Record risks, assumptions, OQs separately
- Structure per sections below
- **ISC Quality Gate** — Validate every ISC criterion against the 6-check gate (CLAUDE.md > ISC Quality Gate): count 3-8/phase, single sentence, state-not-action, binary pass/fail, at least one anti-criterion, `| Verify:` suffix. Fix fails inline before writing PRD. Append "ISC Quality Gate: PASS (6/6)" or "PARTIAL (N/6 — {which failed})" at end of ACCEPTANCE CRITERIA

- **Forward-causal ISC test (autonomous capabilities only)** — For any PRD enabling an autonomous capability, apply the forward-causal test to each gate: does it measure forward/causal/money-layer reality, or a code-quality/historical/calendar proxy? Calendar-duration thresholds are universally suspect in low-activity regimes — the system is least active exactly when verification matters most. Correlation checks require shuffle-test + regime-detector before they become causal claims. If a criterion fails the test, mark it with `[PROXY — needs causal replacement]` and require a replacement criterion before ISC Quality Gate passes.

- **Model Annotation** — After ISC Quality Gate passes, apply keyword heuristic to each criterion and propose `| model: X |` annotations. Present as numbered list; wait for Eric to confirm before writing.

  Rules (first match wins): (1) security/auth/trust/injection/validate/policy/constitutional/architecture/design → no annotation (Opus); (2) Verify=Grep/Read + state verbs (exists/present/count/contains) + no build verbs → `| model: haiku |`; (3) create/write/implement/refactor/generate/build + no Opus triggers → `| model: sonnet |`; (4) ambiguous → no annotation (Opus).

  If response ambiguous: ask once "Confirming model routing list above?" Use Eric's edits verbatim; write all proposed if approved unchanged.

- After outputting the PRD, remind the user: "Next step: `/implement-prd` to execute this PRD through the full BUILD → VERIFY → LEARN loop"

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- PRD must start with YAML frontmatter (`---`) declaring the four Task Typing axes: `stakes`, `ambiguity`, `solvability`, `verifiability` (each `low | medium | high`). No exceptions.
- Sections in order (level-2 headings): OVERVIEW, PROBLEM AND GOALS, NON-GOALS, USERS AND PERSONAS, USER JOURNEYS OR SCENARIOS, FUNCTIONAL REQUIREMENTS, NON-FUNCTIONAL REQUIREMENTS, ACCEPTANCE CRITERIA, SUCCESS METRICS, OUT OF SCOPE, DEPENDENCIES AND INTEGRATIONS, RISKS AND ASSUMPTIONS, OPEN QUESTIONS
- OVERVIEW: 1-para, no bullets
- PROBLEM AND GOALS: bullets tied to user/business outcomes
- NON-GOALS: bullets; if none: "(none stated—confirm with stakeholders)"
- USERS AND PERSONAS: bullets; note unknowns if thin input
- USER JOURNEYS OR SCENARIOS: bullets/numbered flows; if no detail: "(not specified)"
- FUNCTIONAL REQUIREMENTS: bullets; prefix FR-001 etc. if > 5 items
- NON-FUNCTIONAL REQUIREMENTS: bullets; "(none stated)" if not applicable
- ACCEPTANCE CRITERIA: testable/observable bullets; append ISC Quality Gate note
- SUCCESS METRICS: bullets; "(to be defined)" when missing
- OUT OF SCOPE: bullets; if everything in scope: "(none stated)"
- DEPENDENCIES AND INTEGRATIONS: bullets — teams, systems, APIs, data sources
- RISKS AND ASSUMPTIONS: subsections for risks vs assumptions — **must appear BEFORE any IMPLEMENTATION PLAN or task-ready section** when both are present; gate-last output is bypassed by ADHD build velocity.
- OPEN QUESTIONS: bullets of decisions or info still needed
- Do not invent revenue figures, legal commitments, or named customers not in input.
- Do not add meta-commentary.


# CONTRACT

## Errors
- **scope-unclear:** too vague → provide problem/users/constraints, or run /research first
- **no-goals:** no measurable goals → state success criteria; "(to be defined)" flagged in PRD
- **duplicate-prd:** PRD exists → ask to overwrite or version

# SKILL CHAIN

- **Composes:** (leaf at this step — produces the PRD document)
- **Escalate to:** `/delegation` if requirements are unclear or scope needs redefinition

# VERIFY

- PRD file was written to the expected path (memory/work/{project}/PRD.md) | Verify: `ls memory/work/{project}/PRD.md`
- ISC section contains at least 3 criteria and no more than 8 per phase | Verify: Count ISC items in PRD
- Every ISC criterion has a `| Verify:` suffix with a concrete test method | Verify: Read each ISC line for `| Verify:` tag
- At least one anti-criterion (what must NOT happen) is present | Verify: Grep PRD for 'must not' or 'never' in ISC section
- PRD was collaboratively developed (Eric was asked questions, not just handed a doc) | Verify: Check output for question-and-answer exchanges before PRD was written
- Sibling PRD declared → draft has `related-prds:` frontmatter, ASSUMPTIONS shipping-order entry, and anti-criterion enforcing sibling's rule | Verify: Grep PRD for `related-prds:`, sibling slug, and `Anti-criterion`
- Task Typing frontmatter declares all four axes (stakes, ambiguity, solvability, verifiability), each `low | medium | high` | Verify: `python tools/scripts/isc_validator.py --prd <path> --check-frontmatter` exits 0 with `four_axis.present: true`

# LEARN

- ISC consistently vague at first pass: note project type — some domains need concrete definition templates
- Eric rejects PRD draft with major changes: log change type as signal — reveals requirement-gathering gaps
- PRD leads to successful /implement-prd with all ISC passing: log as template candidate for that project type
- Track time between PRD creation and /implement-prd kickoff -- PRDs sitting >7 days without kickoff are likely stale; surface as a backlog signal since unstated blocking conditions typically emerged

# INPUT

INPUT:
