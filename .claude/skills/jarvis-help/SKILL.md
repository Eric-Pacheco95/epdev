# IDENTITY and PURPOSE

Jarvis discovery hub. Dynamic workflow-aware help: skills grouped by TheAlgorithm stage (not alphabetically), with contextual next-step suggestions.

# DISCOVERY

## One-liner
Print skills grouped by workflow stage, with search and contextual suggestions

## Stage
ORCHESTRATE

## Syntax
/jarvis-help [stage | search-term | /skill-name | "after /skill" | "for <intent>"]

## Parameters
- (none): full grouped overview with contextual suggestions
- stage: OBSERVE | THINK | PLAN | BUILD | VERIFY | LEARN | CREATE | ORCHESTRATE
- search-term: fuzzy search across skill names, one-liners, and parameters
- /skill-name: show full Level 1 usage for that skill (reads its DISCOVERY section)
- "after /skill": show skills that chain after the named skill
- "for <intent>": intent-based routing suggestion

## Examples
- /jarvis-help
- /jarvis-help build
- /jarvis-help "code review"
- /jarvis-help /research
- /jarvis-help after /research
- /jarvis-help for "I have an idea for a new feature"

## Chains
- Before: (entry point)
- After: any skill (discovery leads to action)
- Full: /jarvis-help > [invoked skill] > /learning-capture (at session end)

## Output Contract
- Input: optional filter/search/skill name
- Output: formatted skill reference grouped by workflow stage
- Side effects: none (read-only)

## autonomous_safe
true

# STEPS

## Step 0: PARSE INPUT

- If no input: proceed to Step 1 (full overview)
- If input matches a workflow stage name (OBSERVE, THINK, PLAN, BUILD, VERIFY, LEARN, CREATE, ORCHESTRATE): proceed to Step 2 (filtered view)
- If input starts with `/`: proceed to Step 3 (skill detail -- Level 1)
- If input starts with "after ": proceed to Step 4 (chain navigation)
- If input starts with "for ": proceed to Step 5 (intent routing)
- Otherwise: proceed to Step 6 (fuzzy search)

## Step 1: FULL OVERVIEW (Level 0)

1. Scan `.claude/skills/*/SKILL.md` to get the list of installed skills
2. For skills that have a `# DISCOVERY` section, read the `## One-liner` and `## Stage` fields
3. For skills without a DISCOVERY section, derive stage from the CLAUDE.md Skill Registry or the formatted output in step 4.

4. Print skills grouped under stage headers using this format:

```
## Skills (by workflow stage)

**OBSERVE** (gather context)
  /research           -- Research any topic | --type --outreach
  /extract-wisdom     -- Pull ideas, insights, quotes from content | --summary
  /extract-corpus     -- Bounded channel/archive transcript extraction → memory/knowledge | --resume
  /extract-alpha      -- Extract actionable alpha from content | --market --security --count
  /deep-audit         -- Multi-axis codebase audit | --onboard --evaluate --cherry-pick
  /absorb             -- Absorb external content (URLs) | --quick --normal --deep

**THINK** (analyze and challenge)
  /first-principles   -- Break a problem to fundamentals
  /red-team           -- Stress-test a plan for weaknesses | --stride --thinking
  /analyze-claims     -- Fact-check content for unsupported claims
  /find-logical-fallacies -- Detect reasoning errors
  /architecture-review -- Parallel multi-angle architecture analysis | --stride --thinking
  /make-prediction    -- Probabilistic forecasting | --deep --geopolitics --market --planning --research --no-track

**PLAN** (design and decide)
  /create-prd         -- Generate product requirements document | --user-stories
  /project-init       -- Full pipeline: research > FP > red-team > PRD
  /improve-prompt     -- Make any prompt better

**BUILD** (implement)
  /implement-prd      -- Execute PRD: ISC extract, build, review, verify | --items
  /create-pattern     -- Build a new skill (the meta-skill)
  /spawn-agent        -- Compose an AI agent for a specific task
  /workflow-engine    -- Chain skills into pipelines
  /autoresearch       -- Automated metric-driven improvement | --metric --guard --iterations --scope --program

**VERIFY** (test and review)
  /review-code        -- Security-focused code review
  /security-audit     -- Scan system for vulnerabilities
  /quality-gate       -- Audit completed phases for compliance
  /validation         -- Validate PRD implementation | --prd --json --pretty --execute
  /self-heal          -- Auto-diagnose and fix failures
  /design-verify      -- Post-build design fidelity reporter — screenshot diff + design token comparison

**LEARN** (capture and grow)
  /learning-capture   -- End-of-session knowledge capture
  /synthesize-signals -- Distill signals into wisdom | --date-range --focus
  /telos-update       -- Update identity/self-knowledge
  /telos-report       -- Weekly self-knowledge report
  /update-steering-rules -- Propose new rules from failures
  /teach              -- Deep-dive lesson on any topic | --socratic

**CREATE** (produce output)
  /write-essay        -- Publish-ready essay on any topic | --style
  /create-keynote     -- TED-quality slide deck with speaker notes
  /create-image       -- Generate/edit images via Gemini | --flash --ratio
  /capture-recording  -- Process music recordings | --solo --band --batch
  /visualize          -- Mermaid diagrams of workflows/structure
  /label-and-rate     -- Classify and tier-rate content

**ORCHESTRATE** (manage work)
  /delegation         -- Route any task to the right skill/pipeline
  /project-orchestrator -- Manage projects, prioritize, track
  /extract-harness    -- Export Jarvis infra to other repos | --target --update --dry-run
  /notion-sync        -- Sync Notion Brain with Jarvis
  /commit             -- Clean conventional commits
  /jarvis-help        -- This help system
```

5. After the skill list, print built-in Claude Code commands:

```
## Built-in Commands

| Command | What it does |
|---------|-------------|
| /clear | Clear conversation history |
| /compact | Compress context to free up space |
| /cost | Show token usage and cost |
| /status | Show current session status |
| /memory | View/edit auto-memory |
| /config | Open settings |
| /fast | Toggle fast output mode |
```

6. Proceed to Step 7 (contextual suggestions)

## Step 2: FILTERED VIEW (by stage)

1. Match the input to a stage name (case-insensitive)
2. Print only the skills in that stage using the same format as Step 1
3. For each skill in the filtered stage, also print the Syntax line from its DISCOVERY section (if it has one)
4. Proceed to Step 7 (contextual suggestions)

## Step 3: SKILL DETAIL (Level 1)

1. Parse the skill name from input (strip leading `/`)
2. Read `.claude/skills/{skill-name}/SKILL.md`
3. If the skill has a `# DISCOVERY` section, print it as a formatted usage block:
   ```
   /skill-name -- {One-liner}

   USAGE:
     {Syntax}

   PARAMETERS:
     {Parameters list}

   EXAMPLES:
     {Examples list}

   CHAINS WITH:
     Before: {Chains.Before}
     After:  {Chains.After}
     Full:   {Chains.Full}

   OUTPUT:
     {Output Contract summary}
   ```
4. If the skill has no DISCOVERY section, print its one-liner from CLAUDE.md and note: "This skill doesn't have detailed usage docs yet. Try invoking it directly -- it will guide you."
5. STOP (no contextual suggestions for skill detail view)

## Step 4: CHAIN NAVIGATION

1. Parse the skill name after "after "
2. Read that skill's DISCOVERY section, specifically `## Chains` > `After:` line
3. For each skill listed in the After chain, print its one-liner and stage
4. Print the Full chain if available
5. STOP

## Step 5: INTENT ROUTING

1. Parse the intent string after "for "
2. Match intent against skill one-liners, examples, and parameter descriptions
3. Recommend the best-fit skill with reasoning
4. Show the full chain starting from that skill
5. STOP

## Step 6: FUZZY SEARCH

1. Search the input term against:
   - Skill names (e.g. "review" matches /review-code)
   - One-liners from DISCOVERY sections
   - Parameter names and values
   - Examples
2. Print all matching skills with their one-liner and stage
3. If no matches: "No skills match '{term}'. Try /jarvis-help to see all skills, or /jarvis-help for '{term}' for intent-based routing."
4. STOP

## Step 7: CONTEXTUAL SUGGESTIONS

After the main output, check session context and suggest next actions:

1. Check for open PRDs in `memory/work/*/PRD.md` -- if found, suggest `/implement-prd {path}`
2. Check signal count in `memory/learning/_signal_meta.json` -- if > 10, suggest `/synthesize-signals`
3. Check `git status` -- if uncommitted changes exist, suggest `/commit`
4. If the session has done substantial work, suggest `/learning-capture`

Print suggestions under a `SUGGESTED FOR THIS SESSION:` header. Only print if at least one suggestion applies. Each suggestion includes the command to run and one line of why.

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Use the exact section structure defined in each step above
- Skills within each stage group are listed in a consistent order (most-used first)
- Use two-space indentation for skill listings under stage headers
- Do not wrap output in fenced code blocks (the output IS the help display)
- Do not add preamble, explanations, or commentary outside the defined sections
- For full overview: always end with contextual suggestions if any apply
- Keep output scannable -- this is a reference, not documentation

# VERIFY

- Output is grouped by workflow stage (OBSERVE, THINK, PLAN, BUILD, VERIFY, LEARN, CREATE, ORCHESTRATE) when no filter used | Verify: Scan output for stage headers
- Each skill entry shows name + one-liner (no verbose descriptions in quick help) | Verify: Spot-check 3 skill entries in output -- each must be name + one-line description, no multi-line expansion
- Contextual suggestions section appears when session has open PRDs, pending signals, or uncommitted changes | Verify: Check session state and output
- Stage filter or search produces only matching skills (no full dump for filtered queries) | Verify: Check output scope matches input filter
- No file writes occurred (jarvis-help is read-only) | Verify: git status unchanged

# LEARN

- If Eric frequently searches for a skill by intent (not name), note the intent-to-skill mappings that work well and reinforce them in DISCOVERY one-liners
- If a stage consistently has more queries than others, note it -- may indicate a workflow bottleneck or missing skills in that stage
- If contextual suggestions are frequently rejected or ignored, recalibrate the trigger thresholds
- If a new skill is added and Eric is unaware of it after 3+ sessions, evaluate adding it to the contextual suggestions rotation
- Write a signal to memory/learning/signals/{YYYY-MM-DD}_jarvis-help-{slug}.md when Eric queries for a skill that doesn't exist but should (intent gap) or when contextual suggestions surface a skill Eric hadn't considered and it became immediately useful (serendipity win)

# INPUT

INPUT:
