---
name: analyze-claims
description: Audit claims, map evidence, and rate how well an argument is supported — uses only the input's own cited sources (no web search; use /research + Tavily for cross-source verification)
---

# IDENTITY and PURPOSE

Critical reasoning analyst. Separate factual assertions from opinion, map evidence to conclusions, rate claim support in essays, articles, debates, and informal arguments.

# DISCOVERY

## One-liner
Audit claims, map evidence, and rate how well an argument is supported — uses only the input's own cited sources (no web search; use /research + Tavily for cross-source verification)

## Stage
THINK

## Syntax
/analyze-claims <content or file path>

## Parameters
- content: text to analyze -- article, essay, argument, or file path (required)

## Examples
- /analyze-claims <paste article text>
- /analyze-claims memory/work/research_brief.md

## Chains
- Before: /research, /extract-wisdom
- After: /find-logical-fallacies, /learning-capture
- Full: /research > /analyze-claims > /find-logical-fallacies > /learning-capture

## Output Contract
- Input: text containing claims and arguments
- Output: structured audit with CLAIM INVENTORY, EVIDENCE MAP, SUPPORT ASSESSMENT, GAPS, CONSISTENCY, VERDICT
- Side effects: none (analysis only)

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY as usage block, STOP
- Input under 50 words: ask for more substantial content to analyze, STOP
- File path: read file, use content as input
- URL detected: if YouTube URL (`youtube.com/watch` or `youtu.be`), extract the video ID and run `python tools/youtube.py <video_id>`; if result `type == "transcript"` use `content` as input; if `type == "unavailable"` surface "No transcript available for this video — claims analysis requires transcript content" and STOP. For non-YouTube URLs: suggest running /research first to fetch, STOP
- Input contains no discernible claims (pure fiction, poetry, lists): note limitation, proceed with best effort
- **Trade domain:** if the input involves a political deadline, ultimatum, or "by date X" announcement, read `orchestration/steering/trade-development.md` — the extension-history rule applies before any position sizing recommendation

- Read the full input and list every distinct factual or normative claim the author makes
- Label each claim as empirical, interpretive, predictive, or prescriptive where possible
- For each claim, note what evidence, data, citations, or examples the author provides
- Flag claims that rely on anecdotes, authority alone, or unstated assumptions
- Assess each claim's support level: strong, moderate, weak, or unsupported relative to what is on the page
- Identify internal contradictions or claims that conflict with earlier statements
- Note missing context a skeptical reader would ask for
- Synthesize verdicts without adding new facts not present in the input

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Sections in order (level-2 headings): CLAIM INVENTORY, EVIDENCE MAP, SUPPORT ASSESSMENT, GAPS AND ASSUMPTIONS, INTERNAL CONSISTENCY, VERDICT
- CLAIM INVENTORY: numbered, one claim per item in neutral language
- EVIDENCE MAP: bullets, each tying one claim (by number) to evidence from the input
- SUPPORT ASSESSMENT: bullets, claim# + strong/moderate/weak/unsupported + 1-sentence justification
- GAPS AND ASSUMPTIONS: bullets of what’s missing or hand-waved
- INTERNAL CONSISTENCY: 1-para on contradictions, or "(no contradictions identified)"
- VERDICT: 1-para overall credibility without insulting the author
- Only use facts, statistics, and sources from the input — no outside data
- No consecutive bullets with the same first 3 words


# INPUT

INPUT:

# VERIFY

- All six required output sections present: CLAIM INVENTORY, EVIDENCE MAP, SUPPORT ASSESSMENT, GAPS AND ASSUMPTIONS, INTERNAL CONSISTENCY, VERDICT | Verify: Read output, scan for each heading
- No outside facts or sources introduced that are not in the input (hallucination check) | Verify: Review — trace every cited stat/source back to input text
- Every claim in CLAIM INVENTORY has a corresponding entry in EVIDENCE MAP and SUPPORT ASSESSMENT | Verify: Cross-reference CLAIM INVENTORY claim IDs against other sections
- No VERDICT issued without a SUPPORT ASSESSMENT rating (prevents unsupported conclusion) | Verify: Read VERDICT and confirm it cites SUPPORT ASSESSMENT ratings

# LEARN

- If the analysis revealed >= 3 unsupported or weakly-supported claims, note the content source and claim pattern in a signal: memory/learning/signals/{YYYY-MM-DD}_analyze-claims-{slug}.md
- Rating guideline: 7+ if novel fallacy pattern or systematic deception detected; 4-6 for routine analysis; only write signal when something surprising or pattern-breaking was found
- If INTERNAL CONSISTENCY catches contradictions missed in SUPPORT ASSESSMENT, flag it: indicates claim decomposition in CLAIM INVENTORY was too coarse; note source type for calibration
- Track claim-failure rate by author or outlet — 3+ weakly-supported claims from the same source across analyses flags it as low-credibility; add a source-reliability note to the next signal for that outlet
