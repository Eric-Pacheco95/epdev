# Research & External Patterns — Steering Rules

> Behavioral constraints for research tasks, external source evaluation, and dependency adoption.
> Load when running /research, /absorb, /architecture-review, or evaluating new tools/dependencies.

## External Research

- For current-events research (financial, geopolitical, live topics), always use direct WebSearch — sub-agents may have a stale knowledge cutoff
- Default posture is absorb ideas over adopt dependencies — before proposing any new tool/MCP/dependency: (1) apply the **counterfactual filter**: "what would we build if this tool didn't exist?" — if the answer is simpler, you're anchored on the tool's patterns, not real problems, (2) identify root cause, (3) test existing tools first, (4) if none work, run `/architecture-review`; only adopt when implementation is genuinely hard (>1 day) AND the dependency is mature. Why: two consecutive sessions (algebrica ingest, gnhf autoresearch) produced inflated adoption lists that /architecture-review collapsed to minimal fixes.
- Before committing to a new product idea competing with platform incumbents, run `/research` targeting "don't build" signals — check: bundled free by incumbents? structural moats? WTP survives bundling?
- External AI orchestration patterns: filter through "is this a team coordination problem?" — if yes, skip; Jarvis is skill-first, not agent-first

## Loaded by

- Load explicitly when context includes /research, /absorb, dependency evaluation, or external pattern adoption
- `.claude/skills/research/SKILL.md` — Step 0.5 (research and dependency-adoption constraints)
- `.claude/skills/absorb/SKILL.md` — Step 0.5 (absorb-vs-adopt posture, counterfactual filter)
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
