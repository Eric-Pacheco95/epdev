# IDENTITY and PURPOSE

Fabric/Jarvis skill author. Turn informal agent behavior descriptions into complete SKILL.md documents (IDENTITY, STEPS, OUTPUT INSTRUCTIONS, VERIFY, LEARN sections) ready to use.

# DISCOVERY

## One-liner
Build a new Fabric-format skill (the meta-skill)

## Stage
BUILD

## Syntax
/create-pattern <skill description>

## Parameters
- description: natural language description of what the new skill should do (required)

## Examples
- /create-pattern a skill that generates changelog entries from git history
- /create-pattern a skill that converts voice notes to structured action items
- /create-pattern a skill that audits npm dependencies for security issues

## Chains
- Before: (entry point -- triggered when a repeatable workflow is identified)
- After: /improve-prompt (auto-fires to refine the generated skill prompt)
- Full: (standalone -- creates new skill files)

## Output Contract
- Input: natural language description of desired skill behavior
- Output: complete SKILL.md file in Fabric format (IDENTITY, DISCOVERY, STEPS, OUTPUT INSTRUCTIONS, INPUT)
- Side effects: writes new skill to .claude/skills/{name}/SKILL.md, updates /jarvis-help and CLAUDE.md registry

## autonomous_safe
false

# DESIGN PRINCIPLES

- **Script-vs-SKILL split**: for each step in the new skill, evaluate whether it requires intelligence (judgment, synthesis, NLG). If not, emit a deterministic Python script under `tools/scripts/` and have the SKILL.md call it. Only keep steps in SKILL.md that genuinely need the model.
- **Corpus extraction is its own skill**: bounded channel/archive transcript workflows use `/extract-corpus` plus `tools/scripts/corpus_extractor.py` — not a `--corpus` flag on `/create-pattern` (different inputs, outputs, and promotion gates; see `history/decisions/2026-04-22-second-opinion-extract-corpus-vs-flag.md`).

# STEPS

## Step 0: INPUT VALIDATION (Level 2 Discovery)

- No input: print DISCOVERY block, STOP
- <10 words: "Need: who it's for, what it does, what it outputs. E.g.: /create-pattern skill generating changelog from git diff" STOP
- Similar name exists: "/{existing} already exists. Update it, or genuinely different?"
- Narrow sub-step of /{parent}: "Add there instead?"

### Skill Lifecycle Gate

1. **Flag first**: scan for overlapping skill; propose `--flag` mode if new behavior is a mode of an existing skill. Create standalone only when genuinely independent. (Exception: `/extract-corpus` for channel corpora.)

2. **Architecture-review run?** Required if skill touches external data, sends to real people, or has security implications. If not: recommend it first.

3. **Recurrence vs recency**: "How many times in 12 months?" If < 4, `--flag` or ad-hoc may suffice. Guard availability bias.

4. **Promotion trigger defined?** `--flag` modes: promote at N uses × M contexts. Standalone: archive if unused 6+ months.

5. **Manual validation first?** Don't scaffold from hypothetical — steps freeze before real friction surfaces. Default: "do manually this session, extract next time." Only proceed with at least one completed manual run or explicit override.

Proceed to Step 1 only if all 5 pass or user explicitly overrides.

## Step 1: PARSE AND GENERATE

- Parse the user’s description of the desired skill: audience, domain, trigger situations, and desired output shape
- Infer a specific professional role and 2–4 sentences for IDENTITY and PURPOSE that state expertise and the single-sentence task
- Include the exact line: Take a step back and think step-by-step about how to achieve the best possible results by following the steps below.
- Draft 5–15 STEPS as imperative bullets; each step one action; no code or shell commands
- Draft OUTPUT INSTRUCTIONS that fix the output format (headings, bullets, word limits, ordering rules, and exclusion rules)
- Require “Only output Markdown.” and forbid meta-commentary, warnings, and repeated openings across bullets
- End the generated skill with a final line that is only: INPUT: (the runtime placeholder; nothing after it)
- **Prompt refinement pass**: Before finalizing, run `/improve-prompt` logic on the generated IDENTITY + STEPS + OUTPUT INSTRUCTIONS — diagnose ambiguity, missing constraints, weak verbs, unstated success criteria; apply fixes inline; note refinements in a brief "Refinements applied:" comment (max 5 items) in your output
- Self-check: IDENTITY length fits 2–4 sentences; STEPS use strong verbs; no code blocks or executable snippets in the skill body
- Derive a kebab-case skill name from the purpose (e.g., "analyze-claims", "extract-wisdom")
- Save the generated skill to `.claude/skills/{skill-name}/SKILL.md` using the Write tool — Claude Code auto-discovers skills in this location
- After saving, confirm the skill is registered by noting its `/skill-name` invocation command
- Update the `/jarvis-help` skill: open `.claude/skills/jarvis-help/SKILL.md` and add the new skill's one-liner to the correct category group in the STEPS section so `/jarvis-help` stays current
- Update `CLAUDE.md` skill registry: increment the skill count and add the new skill's one-liner row to the table
- Scan existing chain-aware skills for chain relationships: read `/delegation`, `/workflow-engine`, `/project-init`, `/implement-prd`, `/research`, `/create-prd`, `/learning-capture` and determine if the new skill fits into any existing chain (as a precedes, follows, or composes step)
- Update the SKILL CHAIN section of any affected skills to reference the new skill
- Update the SKILL CHAIN MAP in `/delegation` routing table if the new skill creates a new route
- Output the new skill markdown document

# OUTPUT INSTRUCTIONS

- Only output Markdown.
- Output one complete skill starting with `# IDENTITY and PURPOSE`, ending with `INPUT:` (no trailing text)
- Exact section order: `# IDENTITY and PURPOSE`, `# STEPS`, `# OUTPUT INSTRUCTIONS`, `# INPUT`
- `# INPUT` contains only the line `INPUT:` — no additional content
- The skill’s OUTPUT INSTRUCTIONS must prescribe Markdown-only output
- No fenced code blocks wrapping the result; no title above IDENTITY; no YAML frontmatter unless requested; no commentary before/after


# INPUT

INPUT:

# VERIFY

- Generated SKILL.md starts with `# IDENTITY and PURPOSE` as line 1 | Verify: first line of SKILL.md
- Four sections in order: IDENTITY and PURPOSE, STEPS, OUTPUT INSTRUCTIONS, INPUT | Verify: scan headings in generated SKILL.md
- Ends with `INPUT:` alone on last line | Verify: last line of SKILL.md
- Not wrapped in fenced code blocks | Verify: file does not start/end with triple-backtick fences
- OUTPUT INSTRUCTIONS section prescribes Markdown-only output | Verify: Read OUTPUT INSTRUCTIONS -- must contain 'Only use Markdown' or equivalent
- No structural check failures remain in final generated skill | Verify: Re-run all five checks after any regeneration

# LEARN

- After generating the skill, evaluate: would this pattern apply to >= 3 future recurring tasks?
- If yes: note the pattern name in memory/learning/signals/{YYYY-MM-DD}_new-pattern-{slug}.md
- Rating: 7-8 for high-reuse patterns that fill a clear skill gap; 4-6 for narrow single-purpose skills; skip signal for one-off tasks that were forced into skill format
