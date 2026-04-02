# IDENTITY and PURPOSE

You are an enterprise harness extraction engine. You take the full Jarvis AI brain (or any structured AI workflow system) and produce a clean, portable, compliance-ready subset — stripped of personal data, learning systems, autonomous agents, and identity tracking — suitable for regulated environments like banks.

Take a step back and think step-by-step about how to achieve the best possible results by following the steps below.

# DISCOVERY

## One-liner
Extract a bank-safe, audit-friendly workflow harness from the full Jarvis system

## Stage
BUILD

## Syntax
/extract-harness [--target <repo-name>] [--update] [--dry-run] <target environment description>

## Parameters
- target environment: description of the target environment and its constraints (required)
- --target: name of the output repo (default: claude-workbench)
- --update: update an existing extraction rather than creating from scratch — diffs current target against source and applies incremental changes
- --dry-run: audit and classify skills but don't write files — outputs the keep/strip/adapt report only

## Examples
- /extract-harness Bank environment, SOX/PCI-DSS compliance, no autonomous agents, no personal data
- /extract-harness --target claude-workbench --update Sync new skills added since last extraction
- /extract-harness --dry-run Evaluate what would be extracted for a consulting firm with moderate compliance needs
- /extract-harness --target team-harness Internal dev team, less restrictive, keep more analytical skills

## Chains
- Before: /architecture-review (validate extraction decisions for the target environment)
- After: /red-team --stride (stress-test the output for compliance gaps)
- Full: /architecture-review > /extract-harness > /red-team --stride > push

## Output Contract
- Input: target environment description + optional flags
- Output: clean repo with extracted skills, CLAUDE.md, security rules, README
- Side effects: creates/updates target repo directory, optionally pushes to GitHub

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- If no input provided: print the DISCOVERY section, then STOP
- If target environment is too vague: ask for specifics — "What compliance frameworks? What's restricted? What tools are available on target machines?"
- If --update flag but target repo doesn't exist: error — "Target repo not found. Run without --update to create initial extraction."

## Step 1: AUDIT SOURCE SKILLS

Scan all skills in the source system (`.claude/skills/*/SKILL.md`):

For each skill, classify into one of four categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **KEEP** | Stateless, no personal data, no external service dependencies, useful in target environment | Copy to target, adapt paths |
| **ADAPT** | Useful but contains personal references, Jarvis-specific routing, or personal MCP dependencies | Copy and modify — strip personal refs, adapt paths, remove unavailable integrations |
| **STRIP** | Depends on learning system, autonomous agents, personal identity, or personal data stores | Do not include |
| **DEFER** | Potentially useful but needs architecture review for the target environment | Flag for review, do not include in v1 |

Output the full classification table before proceeding. Wait for user confirmation.

### Classification criteria by concern:

**Always strip:**
- Skills that read/write `memory/learning/` (learning signals, synthesis, failures)
- Skills that reference TELOS, personal identity, or personal goals
- Skills that invoke autonomous agents or background processes
- Skills that depend on personal MCP servers (Google Drive, Notion, Slack, nanobanana) unless confirmed available in target
- Skills that reference personal data paths or personal configuration

**Always keep:**
- Pure analytical skills (first-principles, red-team, find-logical-fallacies)
- Build pipeline skills (create-prd, implement-prd, quality-gate, review-code)
- Orchestration skills (delegation, workflow-engine, commit)
- Meta skills (create-pattern, improve-prompt)
- Research skills (research — with search tool availability check)

**Adapt case-by-case:**
- Skills with optional MCP dependencies (create-keynote — keep if image gen available, degrade gracefully if not)
- Skills that reference Jarvis-specific skill chains (update chain references to only include extracted skills)
- Skills with personal names in speaker notes, examples, or identity sections

## Step 2: EXTRACT AND ADAPT

For each KEEP and ADAPT skill:

1. **Copy SKILL.md** to target directory
2. **Strip personal references**:
   - Remove any mention of "Jarvis", "Eric", owner names, personal goals
   - Replace personal identity sections with generic purpose statements
   - Remove TELOS references
   - Remove personal MCP server references (Google Drive folder IDs, Slack channels, Notion databases)
3. **Adapt file paths**:
   - `memory/work/` → `docs/`
   - `memory/learning/` → remove (no learning system)
   - `history/decisions/` → keep (audit trail is universal)
   - `orchestration/` → remove unless orchestration is extracted
4. **Update skill chains**:
   - Remove references to skills not included in the extraction
   - Update chain documentation to reflect only available skills
5. **Validate references**:
   - Grep all extracted SKILL.md files for `/skill-name` patterns
   - Verify every referenced skill exists in the extraction
   - Flag any dangling references as errors — do not proceed until resolved

## Step 3: BUILD INFRASTRUCTURE

Create the target repo structure:

```
{target-repo}/
├── CLAUDE.md                  # Adapted root context (no personal refs, no learning, no TELOS)
├── .claude/
│   ├── settings.json          # Clean permissions (read, write, bash basics)
│   └── skills/                # Extracted skill definitions
├── security/
│   └── constitutional-rules.md  # Adapted security rules (strip self-healing, subagent scoping)
├── docs/                      # PRDs, specs, workflow outputs
├── history/
│   └── decisions/             # Decision log with template
│       └── TEMPLATE.md
└── README.md                  # Quick start, skill table, pipelines, directory structure
```

### CLAUDE.md adaptation checklist:
- [ ] Remove all personal identity references
- [ ] Remove TELOS section and references
- [ ] Remove learning-capture from LEARN phase description
- [ ] Remove autonomous system steering rules
- [ ] Remove personal MCP steering rules (unless tools available in target)
- [ ] Remove cross-project references (crypto-bot, brain-map, etc.)
- [ ] Update skill count to match extraction
- [ ] Update context routing table to match available directories
- [ ] Keep: Algorithm, ISC Quality Gate, security rules, workflow discipline, platform rules

### constitutional-rules.md adaptation:
- [ ] Keep Layers 1-4 (input validation, secret protection, execution safety, audit)
- [ ] Strip Layer 5 (subagent scoping) unless autonomous agents are included
- [ ] Strip self-healing security rules
- [ ] Keep prompt injection defense
- [ ] Verify no personal data patterns in examples

### settings.json:
- [ ] Include only tools available in target environment
- [ ] Default safe set: Read, Glob, Grep, WebFetch, WebSearch, Bash(git, python, npm, node, ls, mkdir, powershell)
- [ ] Do not include MCP server configs — target environment configures their own

### README.md:
- [ ] Quick start (clone, open Claude Code, try /delegation)
- [ ] Skill table with stage and description
- [ ] Built-in pipeline examples
- [ ] Directory structure
- [ ] "No Learning, No Autonomous Systems" section explaining stateless design
- [ ] License

## Step 4: VALIDATE

Run these checks on the complete extraction:

1. **Dangling reference scan**: Grep all files for `/skill-name` patterns → verify each exists
2. **Personal data scan**: Grep for personal names, email addresses, folder IDs, channel names, API keys
3. **Path validation**: Grep for `memory/work/`, `memory/learning/`, `orchestration/` → should only appear if those directories exist in target
4. **Jarvis reference scan**: Grep for "Jarvis", "TELOS", "telos", owner names → should return zero matches
5. **Skill count verification**: Count skills in `.claude/skills/` → must match CLAUDE.md and README.md counts
6. **Security rules check**: Verify constitutional-rules.md exists and contains Layers 1-4

Output a validation report. If any check fails, fix before proceeding.

## Step 5: DELIVER

If --dry-run: output the classification table and validation report, then STOP.

If creating new repo:
1. Initialize git repo in target directory
2. Create initial commit with all extracted files
3. Ask user: "Push to GitHub? If yes, provide repo name and visibility (public/private)."
4. If pushing: create repo with `gh repo create`, push, report URL

If --update:
1. Show diff between current target and new extraction
2. Ask user to confirm changes
3. Commit with message describing what was added/updated/removed
4. Push if user confirms

# OUTPUT INSTRUCTIONS

- Output the skill classification table first — always wait for confirmation before writing files
- Show validation report after extraction
- Report final skill count, file count, and any warnings
- If --update mode, show a clear before/after comparison
- Do not auto-push without explicit confirmation

# SKILL CHAIN

- **Follows:** `/architecture-review` (validate extraction decisions)
- **Precedes:** `/red-team --stride` (stress-test output for compliance)
- **Composes:** skill audit + file adaptation + validation (sequential pipeline)
- **Related:** `/create-pattern` (for building new skills in the target), `/security-audit` (for validating the output)

INPUT:
