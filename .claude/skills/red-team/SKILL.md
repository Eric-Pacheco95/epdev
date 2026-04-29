---
name: red-team
description: Stress-test a plan, product, or idea for weaknesses and failure modes
---

# IDENTITY and PURPOSE

Red-team reviewer. Adversarial analysis of plans, prompts, products, policies. Stress-test as a motivated critic, competitor, or attacker to surface failure modes, abuse cases, and blind spots.

# DISCOVERY

## Stage
THINK

## Syntax
/red-team [--stride] [--thinking] <plan, product description, or file path>

## Parameters
- input: free-text description of the plan/product/policy to attack, or a file path to review (required for execution, omit for usage help)
- --stride: activate STRIDE threat modeling mode (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) -- produces a structured threat model alongside the adversarial analysis
- --thinking: activate TELOS-aware personal reasoning attack mode -- reads memory/work/TELOS.md and attacks Eric's mental models, frames, and reasoning patterns rather than a system; produces BLINDSPOTS (8 bullets) and RED-TEAM THINKING (4 bullets + fixes); input is optional (defaults to TELOS + any question provided)

## Examples
- /red-team memory/work/jarvis/PRD.md
- /red-team Our crypto bot uses a simple moving average crossover strategy
- /red-team The new auth flow stores session tokens in localStorage
- /red-team --stride The Jarvis heartbeat system runs as a scheduled task with file-based state
- /red-team --thinking Am I building the right things in Phase 5?
- /red-team --thinking (no input -- attacks general reasoning patterns from TELOS)

## Chains
- Before: /first-principles (decompose assumptions first)
- After: /create-prd (incorporate mitigations into requirements)
- Full: /research > /first-principles > /red-team > /create-prd

## Output Contract
- Input: plan, product description, or file path
- Output: adversarial analysis (SUMMARY, THREAT MODEL, FAILURE MODES, MISUSE/ABUSE, DATA/TRUST RISKS, RANKED FINDINGS, MITIGATIONS, OPEN QUESTIONS)
- Multi-candidate proposal mode: when input is a list of N adoption candidates, design alternatives, or scope decisions (≥2 distinct items), each RANKED FINDINGS item must carry an explicit VERDICT TIER from {HARD REJECT, SOFT REJECT, COLLAPSES TO ONE-LINER, ACCEPT-AS-SCOPED, ACCEPT}. Single-system attack mode (one artifact) skips verdict tiers.
- Side effects: none (pure analysis, no file output)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY block, STOP
- <10 words / no plan: "Provide a plan, product, or system. E.g.: /red-team memory/work/jarvis/PRD.md" STOP
- Content analysis (article/essay/claims): "Try /analyze-claims (fact-check) or /find-logical-fallacies. /red-team is for plans/systems."
- Code review: "/review-code for code security; /red-team for architecture. Need both? /review-code first."
- Once validated, proceed to Step 1

## Step 0.5a: THINKING MODE CHECK

- If `--thinking` flag is present:
  - Read `memory/work/TELOS.md` fully; this is the primary context
  - If input (beyond the flag) is provided, treat it as the specific question or domain to focus on
  - If no input beyond the flag, attack general reasoning patterns across the full TELOS
  - Output two sections only:
    - **BLINDSPOTS**: 8 bullets (max 16 words each) naming frames or models in Eric's thinking that could leave him exposed to error or risk — derived from patterns, assumptions, and stated beliefs in TELOS
    - **RED-TEAM THINKING**: 4 bullets (max 16 words each) adversarially attacking specific reasoning patterns or conclusions visible in TELOS, followed by **FIXES**: numbered recommendations addressing each bullet
  - Use plain markdown only; no bold/italic emphasis within bullets
  - STOP after outputting these two sections; do not run Steps 1+ (system red-team)
- If `--thinking` is NOT present, continue to Step 0.5b

## Step 0.5b: STRIDE MODE CHECK

- If `--stride` flag is present, activate STRIDE overlay:
  - After completing the standard red-team analysis (Steps 1+), add STRIDE-specific sections
  - Identify trust boundaries: where data crosses privilege levels, networks, or organizational boundaries
  - List relevant actors with intent notes (users, admins, external services, anonymous internet, insiders)
  - For each STRIDE category (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege):
    - Brainstorm plausible threats specific to the described architecture
    - Tie threats to affected assets or data flows
    - Note preconditions and attacker capabilities
  - If a category has no plausible threats: "(no distinct threats identified for this category given current description)"
  - Map STRIDE findings into the MITIGATIONS section alongside the standard red-team mitigations
  - Add TRUST BOUNDARIES AND DATA FLOWS and STRIDE ANALYSIS sections to the output (after DATA AND TRUST RISKS)
- If `--stride` flag is NOT present, skip directly to Step 1
- If `--thinking` and `--stride` are both present: run `--thinking` mode first, then append STRIDE analysis of Eric's reasoning frameworks as a bonus section

## Step 1: SUMMARIZE

- Summarize the artifact under review in one neutral sentence
- Identify the stated goals and success criteria implied by the input
- Brainstorm ways the system or plan fails under edge cases, overload, or ambiguity
- Brainstorm misuse: deception, gaming metrics, social engineering, and trust exploitation relevant to the domain
- Consider data, privacy, and authorization angles when the input touches people or sensitive information
- Rank issues by severity and likelihood using the input only; flag where severity depends on unstated context
- Propose concrete mitigations tied to each major issue class
- Note what additional information would sharpen the red-team findings

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Sections in order (level-2 headings): SUMMARY, THREAT MODEL, FAILURE MODES, MISUSE AND ABUSE CASES, DATA AND TRUST RISKS, [if --stride: TRUST BOUNDARIES AND DATA FLOWS, STRIDE ANALYSIS], RANKED FINDINGS, MITIGATIONS, OPEN QUESTIONS
- SUMMARY: 1-para describing what is being red-teamed
- THREAT MODEL: bullets of actor types + incentives
- FAILURE MODES: bullets of ways it breaks/behaves badly
- MISUSE AND ABUSE CASES: bullets of adversarial/gaming behaviors
- DATA AND TRUST RISKS: bullets; "(not applicable)" if none
- STRIDE ANALYSIS: subsections for Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege
- RANKED FINDINGS: numbered high-to-low; each item: severity + 1-line rationale. Multi-candidate proposal mode: append a VERDICT TIER per item using the set below; single-system mode omits the tier. Empty-section rule (per scope-inflation guardrail): do not pad findings to fill structure — fewer high-quality findings beat exhaustive low-signal ones.
- VERDICT TIERS (multi-candidate mode only):
  - **HARD REJECT** — pattern is structurally wrong; no salvage; cite the failure mode that breaks it
  - **SOFT REJECT** — wrong as proposed but salvageable in a smaller form (note the salvage path)
  - **COLLAPSES TO ONE-LINER** — core idea is right but doesn't need a new artifact; specify the exact one-line steering edit, frontmatter field, or SKILL.md flag that captures it
  - **ACCEPT-AS-SCOPED** — adopt with explicit scope constraints (state the constraint)
  - **ACCEPT** — adopt as proposed
- MITIGATIONS: bullets mapped to numbered findings
- OPEN QUESTIONS: what the red team still needs to know
- Describe defenses and risks abstractly — no illegal instructions, no moralizing.


# INPUT

INPUT:

# VERIFY

- All required output sections present (SUMMARY, THREAT MODEL, FAILURE MODES, MISUSE AND ABUSE CASES, DATA AND TRUST RISKS, RANKED FINDINGS, MITIGATIONS, OPEN QUESTIONS; plus STRIDE sections if --stride was used) | Verify: Read output, scan for each heading
- Every item in RANKED FINDINGS has a corresponding MITIGATIONS entry (or explicit 'no mitigation' note) | Verify: Cross-reference RANKED FINDINGS item IDs against MITIGATIONS
- Severity ratings in RANKED FINDINGS span at least two distinct levels (uniform ratings = insufficient discrimination) | Verify: Count distinct severity values in RANKED FINDINGS
- Multi-candidate proposal mode only: every RANKED FINDINGS item carries a verdict tier from the allowed set | Verify: Each numbered item ends with one of {HARD REJECT, SOFT REJECT, COLLAPSES TO ONE-LINER, ACCEPT-AS-SCOPED, ACCEPT}
- No required sections missing after any generation pass | Verify: Re-scan output headings after generation

# LEARN

- >= 2 High-severity findings: signal at memory/learning/signals/{YYYY-MM-DD}_red-team-{slug}.md
- Rating: 8-9 unknown critical surfaces; 5-7 familiar risk with new context; only when findings change design decisions
- Highest-severity recurring pattern: promote to relevant agent/skill Critical Rules
- Track which target types (MCP tools, hooks, skill chains, data pipeline) produce the most High-severity findings -- concentrate future pre-build red-team gates on those types
