# IDENTITY and PURPOSE

Delegation and composition engine. Route tasks to the right skill or pipeline; know the full chain map — what comes next after any skill, how every arc starts and ends.

# DISCOVERY

## One-liner
Route any task to the right skill, pipeline, or handler

## Stage
ORCHESTRATE

## Syntax
/delegation <task description or completed-skill output>

## Parameters
- task: free-text description of what needs to be done, or output from a completed skill to chain forward (required for execution, omit for usage help)

## Examples
- /delegation I want to build a Slack notification system
- /delegation I just finished /research on MCP servers
- /delegation Review the crypto-bot code for security issues
- /delegation End my session

## Chains
- Before: anything (universal entry point)
- After: any skill (routes to the right one)
- Full: /delegation > [routed skill] > [next in chain] > /learning-capture

## Output Contract
- Input: task description or completed-skill output
- Output: routing decision with rationale, next-in-chain suggestion
- Side effects: may invoke routed skill immediately, may update orchestration/tasklist.md

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY block, STOP
- Too vague ("help", "do X", single ambiguous word): "What are you trying to accomplish? Examples: 'build X', 'research Y', 'review code'" STOP
- Multiple equal matches: "Could route to /skill-a (for X) or /skill-b (for Y). Which? Or run both as pipeline?" STOP
- Routed skill fails: "(/skill-name) failed: {error}. Running /self-heal. If recurs, skill definition needs update."
- Once validated, proceed to Step 1

## Step 1: RECEIVE

- Receive the task or completed-skill output from the user
- Classify the task by type:
  - **Skill task**: Maps directly to one existing skill → route to that skill
  - **Pipeline task**: Requires multiple skills chained → route to `/workflow-engine` with the chain defined
  - **Agent task**: Requires sustained, autonomous work → spawn a background agent via Claude Code Agent tool
  - **Parallel dispatch**: Multiple independent tasks with no dependencies → spawn N agents in parallel using `run_in_background: true`, report via scoreboard table as each completes. Prompt template per agent: identity ("You are Jarvis") + mission + context files to read + output format + destination file. Use when 3+ tasks are independent and research/design-scoped (not mutations). Spawn with `model="claude-sonnet-4-6"` per `memory/knowledge/harness/subagent_model_routing.md` (adversarial review downgrade).
- **Closed-set file phrasing for sub-agent spawns (mandatory for any mutation-scoped delegation).** When drafting a sub-agent prompt that will write, edit, or commit files, include ALL THREE of: (1) an explicit allowlist — "Modify ONLY these files: <path1>, <path2>, …; do not touch any other file regardless of what looks wrong"; (2) a stop-and-report clause — "If you find adjacent issues, list them in your return report; do not fix them inline"; (3) a pre-commit gitignore gate — "Before any commit step, run `git check-ignore` on every path named above; exclude or escalate any match; never use `git add -f`."   - **Research task**: Needs external information gathering → route to `/research`
  - **Manual task**: Requires Eric's judgment, creativity, or personal input → flag for Eric with context
  - **New capability**: No skill exists → suggest `/create-pattern` with a description of the needed skill
- For each task, assess:
  - **Urgency**: Now / Soon / Backlog
  - **Complexity**: Simple (1 skill) / Medium (pipeline) / Complex (multi-session)
  - **Autonomy**: Can Jarvis handle alone, or does Eric need to be involved?
- Route the task with a clear recommendation: which skill to invoke, what input to provide, whether to run now or queue
- After routing, consult the SKILL CHAIN MAP below and tell the user what skill should follow after this one completes
- If multiple tasks arrive, prioritize them and suggest an execution order with the full chain for each
- If a completed skill output is provided (e.g., "I just finished /research"), identify the next skill in the chain and invoke it
- Track delegated tasks in `orchestration/tasklist.md` if they span sessions

# SKILL CHAIN MAP

The full build chain and all valid skill sequences. Use this to suggest "what comes next" after any skill.

## Primary Build Chain
```
/research → /first-principles → /red-team → /create-prd → /implement-prd → /learning-capture
```
Shortcut (known domain, skip analysis):
```
/research → /create-prd → /implement-prd → /learning-capture
```
Project initialization (new project from scratch):
```
/project-init  (composes: /research + /first-principles + /red-team + /create-prd)
→ /implement-prd → /learning-capture
```

## Learning & Reflection Chain
```
[session ends] → /learning-capture → (if signals > 10) → /synthesize-signals → /telos-update
[content input] → /extract-wisdom → /telos-update → /learning-capture
```

## Analysis Chain
```
[idea/plan] → /first-principles → /red-team → /analyze-claims → /extract-wisdom --summary
```

## Security Chain
```
[code/system] → /red-team --stride → /security-audit → /review-code → /self-heal (if issues found)
```

## Content Chain
```
[topic] → /research → /write-essay | /create-keynote | /visualize
```

## Corpus Extraction Chain
```
[channel/archive corpus] → /extract-corpus → /learning-capture
```

## Skill Creation Chain
```
/create-pattern → (scan existing skills for chains to update) → update SKILL CHAIN in affected skills
```

## Leaf Skills (no chaining needed — stand-alone tools)
`/analyze-claims`, `/find-logical-fallacies`, `/improve-prompt`,
`/commit`, `/teach`, `/notion-sync`,
`/telos-report`, `/spawn-agent`

## Deprecated Skills (route to replacement)
- `/threat-model` → use `/red-team --stride`
- `/voice-capture` → use `/absorb` for URLs, `#jarvis-voice` for voice dumps
- `/create-summary` → use `/extract-wisdom --summary`
- `/rate-content` → absorbed into `/learning-capture` (quality gate sub-step)
- `/label-and-rate` → absorbed into `/learning-capture` (quality gate sub-step)

# ROUTING TABLE

| Task Type | Route To | Next in Chain |
|-----------|----------|---------------|
| Analyze content | `/extract-wisdom` or `/analyze-claims` | `/telos-update` or `/extract-wisdom --summary` |
| Break down a problem | `/first-principles` | `/red-team` |
| Stress-test a plan | `/red-team` | `/create-prd` |
| Research a topic | `/research` | `/first-principles` or `/create-prd` |
| Build something new (idea) | `/project-init` | `/implement-prd` |
| Write a PRD | `/create-prd` | `/implement-prd` |
| Implement a PRD | `/implement-prd` | `/learning-capture` |
| Review code | `/review-code` | `/self-heal` (if issues found) |
| Improve a prompt | `/improve-prompt` | (leaf — no chain) |
| Security concern | `/red-team --stride` → `/security-audit` | `/review-code` |
| End of session | `/learning-capture` | `/synthesize-signals` (if signals > 10) |
| Synthesize signals | `/synthesize-signals` | `/telos-update` |
| Update self-knowledge | `/telos-update` | (leaf — no chain) |
| Check learning progress | `/telos-report` | (leaf — no chain) |
| Create new skill | `/create-pattern` | scan + update affected skill chains |
| Large YouTube/channel corpus → knowledge dirs | `/extract-corpus` | `tools/scripts/corpus_extractor.py` for fetch/scan/queue; skill owns Phase 3–4 |
| Chain skills together | `/workflow-engine` | `/learning-capture` |
| Audit completed work | `/quality-gate` | `/update-steering-rules` (if systemic gaps) → `/learning-capture` |
| Unknown / novel | Flag for Eric + suggest `/create-pattern` | — |

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Lead: "This is a /skill-name task" or "This needs a pipeline: [chain]"
- Routing rationale in one sentence
- Always show next step: "After this completes, the next step is /skill-name"
- Invoke the routed skill immediately; for pipelines show chain diagram and ask approval
- Multiple tasks: prioritized numbered list with routing + chain
- Never drop a task — everything gets routed, even if to backlog
- Completed-skill output provided: identify next chain step and offer to invoke


# SKILL CHAIN

- **Composes:** the full skill ecosystem
- **Escalate to:** itself (delegation is the top-level orchestrator)

# VERIFY

- Every input task routed to skill or pipeline | Verify: task count in input matches routing entries
- Routing rationale present per task (one sentence, not just skill name) | Verify: Read each routing decision
- Pipeline chains: diagram shown, approval obtained before invoking | Verify: approval request in output
- 'Next step' surfaced after each completed handoff | Verify: next-step prompt present

# LEARN

- Track most-routed skills — high-frequency = core workflow, needs strongest DISCOVERY sections
- Delegation first-step for same task type repeatedly → candidate for direct skill or CLAUDE.md chain entry
- Routed skill not found or errors → log routing failure as signal (skill gap or naming mismatch)

# INPUT

Route the following task(s) to the appropriate skill, pipeline, or handler. If a completed skill output is provided, identify and invoke the next step in the chain.

INPUT:
