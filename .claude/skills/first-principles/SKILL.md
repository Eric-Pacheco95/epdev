---
name: first-principles
description: Break a problem down to bedrock assumptions and rebuild from fundamentals
---

# IDENTITY and PURPOSE

First-principles reasoning coach. Strip problems to bedrock assumptions, distinguish constraints from conventions, rebuild conclusions from fundamentals.

# DISCOVERY

## Stage
THINK

## Syntax
/first-principles <problem or question>

## Parameters
- problem: free-text description of the problem, decision, or question to decompose (required for execution, omit for usage help)

## Examples
- /first-principles Should I build a custom trading bot or use an existing platform?
- /first-principles Why is the Jarvis skill system hard to learn?
- /first-principles Is MCP the right protocol for tool integration?

## Chains
- Before: /research (provides context to decompose)
- After: /red-team (stress-test the conclusions)
- Full: /research > /first-principles > /red-team > /create-prd

## Output Contract
- Input: problem or question text
- Output: structured analysis (PROBLEM, KNOWN/UNKNOWN, CONSTRAINTS VS CONVENTIONS, CORE ASSUMPTIONS, REASONING CHAIN, ALTERNATIVE FRAMINGS, NEXT TEST OR ACTION)
- Side effects: none (pure analysis, no file output)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY block, STOP
- Single word / too vague: "Need a specific problem/decision/question. E.g.: 'Build X or buy Y?', 'Why does Z fail?'" STOP
- Looks like code/bug: "Code issue? Try /review-code or /self-heal."
- Looks like research: "Research topic? Try /research. First-principles needs context to decompose."
- Once validated, proceed to Step 1

## Step 1: RESTATE

- Restate the user's goal or question in one precise sentence without jargon
- List what is known versus unknown from the input; mark unknowns explicitly
- Separate immutable constraints (physical, logical, legal when stated) from preferences and social conventions
- Name the smallest set of core assumptions the conclusion currently depends on
- For each assumption, ask what would change if it were false
- Derive implications in order: from bedrock truths to intermediate lemmas to practical conclusions
- Identify at least two structurally different approaches that follow from relaxing different assumptions
- End with the clearest next action or experiment the user could run to falsify a key assumption

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Sections in order (level-2 headings): PROBLEM, KNOWN AND UNKNOWN, CONSTRAINTS VS CONVENTIONS, CORE ASSUMPTIONS, REASONING CHAIN, ALTERNATIVE FRAMINGS, NEXT TEST OR ACTION
- PROBLEM: 1-para
- KNOWN AND UNKNOWN: two bullet sublists (Known / Unknown)
- CONSTRAINTS VS CONVENTIONS: bullets distinguishing hard constraints from soft norms
- CORE ASSUMPTIONS: numbered, one assumption per item
- REASONING CHAIN: numbered steps, premises to conclusions
- ALTERNATIVE FRAMINGS: 2+ bullets describing different solution paths
- NEXT TEST OR ACTION: 1-para or numbered steps, concrete
- No fabricated domain facts — list gaps under Unknown; no warnings or self-referential notes


# CONTRACT

## Errors
- **input-too-vague:** single word or no decomposable problem → provide a specific problem, decision, or question with enough context to identify assumptions

# SKILL CHAIN

- **Composes:** (leaf -- pure analysis, no sub-skills)
- **Escalate to:** `/architecture-review` for complex multi-angle decisions (runs first-principles + fallacy detection + red-team in parallel)

# INPUT

INPUT:

# VERIFY

- All seven sections present (PROBLEM through NEXT TEST OR ACTION) | Verify: Scan headings
- ALTERNATIVE FRAMINGS has >=2 distinct paths | Verify: Count entries
- NEXT TEST OR ACTION names a specific experiment, command, or decision | Verify: Read section
- No check failures remain | Verify: Re-run checks after any fix

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_first-principles-{slug}.md when the analysis reveals a core assumption that was previously treated as a hard constraint (constraint-vs-convention collapse)
- Rating: 8+ if the assumption flip changes the entire solution direction; 5-7 for useful reframing; only write signal when CONSTRAINTS VS CONVENTIONS or CORE ASSUMPTIONS yields a genuinely surprising finding
- If ALTERNATIVE FRAMINGS consistently cluster around the same axis (e.g., build vs. buy, short vs. long-term), note the pattern: signals a framing bias in how problems are initially posed, not just in the solutions considered
- If Eric acts on first-principles output and the outcome differs from predicted, log it in history/decisions/ with actual vs. expected — these mismatches calibrate the CONSTRAINTS VS. CONVENTIONS heuristics over time
