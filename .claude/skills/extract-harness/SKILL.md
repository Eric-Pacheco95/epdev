# IDENTITY and PURPOSE

Harness extraction engine. Produces a clean, portable subset of the Jarvis system for target audiences. `--enterprise`: compliance-ready subset (personal data/agents/tracking stripped; for banks). `--personal`: starter kit (learning loop + dispatcher + steering rules; personal content stripped; for solo builders).

# DISCOVERY

## One-liner
Extract a portable workflow harness from the full Jarvis system (--enterprise for compliance, --personal for solo builders)

## Stage
BUILD

## Syntax
/extract-harness [--target <repo-name>] [--update] [--dry-run] [--enterprise | --personal] <target environment description>

## Parameters
- target environment: description of the target environment and its constraints (required)
- --target: name of the output repo (default: claude-workbench)
- --update: update an existing extraction — diffs skills, templates, knowledge, and CLAUDE.md against source and applies incremental changes
- --dry-run: audit and classify skills but don't write files — outputs the keep/strip/adapt report only
- --enterprise: after extraction/update, run a gap analysis for regulated/team environments: what NEW skills, templates, or knowledge would improve the target environment for its users? Proposes improvements without building them
- --personal: extract a starter kit for individual builders — keeps learning loop (simplified), dispatcher scaffold, steering rules architecture, and content pipeline while stripping personal TELOS content, personal memories, and personal MCP configs. Generates a "Getting Started" onboarding README instead of compliance docs

## Examples
- /extract-harness Bank environment, SOX/PCI-DSS compliance, no autonomous agents, no personal data
- /extract-harness --target claude-workbench --update Sync new skills added since last extraction
- /extract-harness --dry-run Evaluate what would be extracted for a consulting firm with moderate compliance needs
- /extract-harness --target team-harness Internal dev team, less restrictive, keep more analytical skills
- /extract-harness --target claude-workbench --update --enterprise Sync + propose new workflows for bank BA/BSAs
- /extract-harness --target jarvis-starter --personal Solo dev building a personal AI brain — keep learning, dispatcher, steering rules

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

## Step 0.5: LOAD PLATFORM STEERING RULES

- Read `orchestration/steering/platform-specific.md` — load Windows/Scheduling/MCP/Hooks constraints before evaluating what to extract for the target environment

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
- `/absorb` — personal knowledge intake pipeline; no enterprise equivalent (absorbing external content into a personal brain model is not a regulated-team workflow)
- `/make-prediction` — personal forecasting and calibration; no enterprise analogue; creates compliance risk if prediction outputs are used in regulated decisions

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
4. **Adapt examples for target audience**:
   - Replace personal/project examples with target-environment examples
   - For bank environments: use KYC, AML, regulatory change, requirements writing, API design review examples
   - For dev environments: use code review, architecture, sprint planning examples
   - Examples should speak the target user's language — this is what makes the tool feel built for them
5. **Update skill chains**:
   - Remove references to skills not included in the extraction
   - Update chain documentation to reflect only available skills
6. **Validate references**:
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
├── templates/                 # Reusable artifact formats (Claude loads before generating)
│   ├── requirements.md        # Requirements document
│   ├── adr.md                 # Architecture Decision Record
│   ├── meeting-notes.md       # Meeting notes
│   └── status-update.md       # Status update / sprint report
├── context/                   # Session context — Claude actively populates
│   ├── glossary.md            # Terms, acronyms, system names (Claude appends new terms)
│   ├── stakeholders/          # Per-project stakeholder maps
│   └── sprint-log/            # Lightweight delivery history per project
├── knowledge/                 # Domain reference — Claude reads when generating artifacts
│   ├── regulatory/            # Regulatory summaries (OSFI, PIPEDA, etc.)
│   └── standards/             # Story format, DoR/DoD, review checklists
├── docs/                      # PRDs, specs, workflow outputs
│   ├── projects/              # One subdirectory per project
│   └── absorbed/              # Content absorbed via /absorb
├── history/
│   ├── decisions/             # Decision log with ADR template
│   └── lessons-learned/       # Sprint/milestone retrospectives
└── README.md                  # Quick start, skill table, pipelines, directory structure
```

### Active Context Population rules (add to CLAUDE.md):

Target CLAUDE.md must include rules for: glossary auto-append to `context/glossary.md`; template loading from `templates/` before generating artifacts; ADR logging to `history/decisions/`; regulatory NFR injection from `knowledge/regulatory/`; stakeholder map creation at `context/stakeholders/{project}.md`; sprint log append to `context/sprint-log/{project}.md`; lessons-learned prompt after milestones.

### CLAUDE.md: Remove personal identity, TELOS, learning-capture, autonomous steering rules, personal MCP rules, cross-project references. Update skill count + context routing. Keep: Algorithm, ISC Quality Gate, security rules, workflow discipline, platform rules.

### constitutional-rules.md: Keep Layers 1-4 (input validation, secrets, execution, audit). Strip Layer 5 (subagent scoping) unless autonomous agents included. Strip self-healing rules. Keep prompt injection defense. Verify no personal data in examples.

### settings.json: Include only available tools. Default safe set: Read, Glob, Grep, WebFetch, WebSearch, Bash(git, python, npm, node, ls, mkdir, powershell). No MCP server configs.

### README.md: Quick start, skill table with stage+description, pipeline examples, directory structure, "No Learning, No Autonomous Systems" section, license.

## Step 3.5: ENTERPRISE (only if --enterprise flag)

Gap analysis for regulated/team environments. Evaluate: (1) **Workflow gaps** — repetitive tasks with no skill (meeting → actions, email → requirements, regulatory update → impact analysis); (2) **Knowledge gaps** — missing `knowledge/` domain reference; (3) **Template gaps** — artifacts with no template; (4) **LLM compliance** — CLAUDE.md data send/don't-send, audit trail, disclaimers, model logging; (5) **Strategic assessment** — internal adoption vs. external revenue play.

Output: numbered list with effort (S/M/L) and priority. Do NOT build — present proposal, add approved to `docs/backlog.md`.

## Step 3.6: PERSONAL (only if --personal flag)

**Classification overrides:**
- **KEEP**: learning scaffold (strip existing data), dispatcher scaffold (strip personal paths), steering rules + `/update-steering-rules`, content pipeline (`/extract-wisdom` > `/synthesize-signals` > `/write-essay`), security layer
- **STRIP**: personal TELOS content, memories, MCP configs, predictions, project-specific orchestration
- **ADAPT**: `/learning-capture`, `/synthesize-signals` — remove personal signal categories, keep generic structure

**Repo structure overrides:**
- Replace bank artifacts (`templates/`) with personal builder artifacts (daily log, weekly review, project kickoff)
- Replace `knowledge/regulatory/` with `knowledge/examples/` (2-3 sample research briefs)
- Generate `README.md` as "Getting Started": first 5 sessions, learning loop, adding skills, dispatcher
- Include `QUICKSTART.md`: clone → API key → `/extract-wisdom` → `/learning-capture` → check `memory/learning/signals/`

**Gap analysis:**
1. Daily workflows a solo dev/creator wants automated (journal → signal, research → brief, content → publish)
2. Minimum viable skill set to feel the learning loop (extract-wisdom, learning-capture, synthesize-signals, research)
3. Onboarding friction (too many skills, unclear starting point, no example data)

Output: onboarding friction report + proposed starter skill set. Do NOT build — present for approval.

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
1. **Skill diff**: Compare source `.claude/skills/` against target — report: new skills to add, existing skills with source changes, skills in target but not in source (manual additions — preserve)
2. **Infrastructure diff**: Compare templates/, context/, knowledge/, history/ — report: new templates, updated knowledge files, new directories in source not in target
3. **CLAUDE.md diff**: Check if source CLAUDE.md steering rules have been updated — apply relevant changes to target CLAUDE.md (preserving target-specific customizations)
4. Show full diff report: "Adding N skills, updating M files, N new templates/knowledge files"
5. Ask user to confirm changes
6. Commit with message describing what was added/updated/removed
7. Push if user confirms

# OUTPUT INSTRUCTIONS

- Output the skill classification table first — always wait for confirmation before writing files
- Show validation report after extraction
- Report final skill count, file count, and any warnings
- If --update mode, show a clear before/after comparison
- Do not auto-push without explicit confirmation

# SKILL CHAIN

- **Composes:** skill audit + file adaptation + validation (sequential pipeline)
- **Related:** `/create-pattern` (for building new skills in the target), `/security-audit` (for validating the output)

INPUT:

# VERIFY

- Step 4 VALIDATE ran all six checks: dangling references, personal data, path validation, Jarvis references, skill count, security rules | Verify: Read validation report — all six check names must appear
- Validation report was output before any files were written to disk | Verify: Check session timeline — validate output must precede any write confirmation
- Extraction did not auto-push to remote without explicit user confirmation | Verify: Check session output for push confirmation prompt — must not be absent
- All six validation checks returned PASS, or failures were documented with resolution | Verify: Read validation report — each check shows PASS or FIXED
- If personal data or Jarvis references were found, delivery was blocked and specific matches were surfaced | Verify: Read output — delivery confirmation absent if any match was found

# LEARN

- Signal: `{YYYY-MM-DD}_extract-harness-{slug}.md` when >20% of skills blocked by Jarvis-specificity. Rating: 7-8 for architectural reusability insights, 5-6 for minor-adaptation extractions, skip for clean runs.
- If --enterprise or --personal produced harness improvements: capture in history/decisions/.
