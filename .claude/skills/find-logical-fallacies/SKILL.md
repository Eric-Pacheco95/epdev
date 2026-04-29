---
name: find-logical-fallacies
description: Spot logical fallacies and rhetorical tricks in any argument
---

# IDENTITY and PURPOSE

Logic and rhetoric analyst. Identify informal fallacies, rhetorical shortcuts, and persuasive tricks in speeches, essays, marketing, and debates. Map to named fallacy types with plain-language explanations.

# DISCOVERY

## One-liner
Spot logical fallacies and rhetorical tricks in any argument

## Stage
THINK

## Syntax
/find-logical-fallacies <content or file path>

## Parameters
- content: text to analyze -- speech, essay, debate, or file path (required)

## Examples
- /find-logical-fallacies <paste article text>
- /find-logical-fallacies memory/work/research_brief.md

## Chains
- Before: /research, /analyze-claims
- After: /learning-capture
- Full: /research > /analyze-claims > /find-logical-fallacies > /learning-capture

## Output Contract
- Input: text containing arguments or rhetoric
- Output: OVERVIEW, FALLACY FINDINGS, NON-FALLACIOUS STRENGTHS, RECOMMENDED FIXES
- Side effects: none (analysis only)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY as usage block, STOP
- Input under 50 words: ask for more substantial content to analyze, STOP
- File path: read file, use content as input
- No arguments or rhetoric detected (pure data, lists): note limitation, proceed with best effort

- Read the input and divide it into claim units or short passages you can refer to by paraphrase
- For each unit, ask whether the reasoning moves validly from premises to conclusion
- Match problematic moves to standard fallacy names only when the fit is strong; avoid forced labels
- When the text is vague, name the ambiguity before labeling
- Distinguish rhetorical flair from faulty logic when no fallacy applies
- Note any good arguments or valid patterns to balance the critique
- Order findings by how much they affect the overall conclusion
- Prefer precise names (e.g. false dilemma, hasty generalization) over vague criticism

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Sections in order (level-2 headings): OVERVIEW, FALLACY FINDINGS, NON-FALLACIOUS STRENGTHS, RECOMMENDED FIXES
- OVERVIEW: 1-para on the argument’s goal
- FALLACY FINDINGS: numbered (max 12, merge duplicates); each item: fallacy name | quote/paraphrase | ≤3-sentence explanation why it’s flawed
- NON-FALLACIOUS STRENGTHS: bullets of valid moves; "(none identified)" if clean
- RECOMMENDED FIXES: bullets repairing/strengthening each numbered finding in order
- "Insufficient support" ≠ fallacy; label it appropriately without a fallacy name
- Critique reasoning only, not the author


# INPUT

INPUT:

# VERIFY

- All four sections present (OVERVIEW through RECOMMENDED FIXES) | Verify: `grep -E "## (OVERVIEW|FALLACY FINDINGS|CONTEXT AND IMPACT|RECOMMENDED FIXES)" <output>` returns 4 matches
- Every FALLACY FINDINGS item has matching RECOMMENDED FIX | Verify: `grep -c "^[0-9]\+\." <FALLACY_section>` equals `grep -c "^[0-9]\+\." <FIXES_section>` (item counts match)
- FALLACY FINDINGS has at most 12 items | Verify: `grep -c "^[0-9]\+\." <FALLACY_section>` ≤ 12
- No missing sections or FALLACY FINDINGS >12 after fixes | Verify: Re-run section header grep — all 4 must be present after any revision
- RECOMMENDED FIXES are actionable replacements for the flawed reasoning (not generic "avoid X") | Verify: Each fix begins with an alternative claim or reframed argument, not just "avoid" or "do not use"

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_fallacies-{slug}.md when >= 3 distinct fallacy types are found or a high-stakes document (policy, research, investment thesis) contains >= 2 High-severity logical flaws
- Rating: 7+ if the fallacies fundamentally undermine the argument; 4-6 for routine style/support issues; only write signal when the analysis changes how Eric should act on the source material
- Track which fallacy types appear most frequently across documents Eric brings - if one type (e.g., appeal-to-authority) appears in >30% of analyses, add it as a pre-scan heuristic in STEPS
- If same source is re-analyzed and fallacy count drops significantly: note that framing/context changed, not logic improved -- flag for signal
- When /absorb feeds this skill: compare fallacy findings to /extract-wisdom's key claims -- fallacy in a key claim = HIGH severity regardless of fallacy count
