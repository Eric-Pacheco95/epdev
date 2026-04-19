# Research & External Patterns — Steering Rules

> Behavioral constraints for research tasks, external source evaluation, and dependency adoption.
> Load when running /research, /absorb, /architecture-review, or evaluating new tools/dependencies.

## Dependency Verification

- Before claiming a dependency is "installed" or "available," verify the actual package manifest (package.json, requirements.txt, pyproject.toml, go.mod). PRDs and documentation describe intent, not current state — trust the lockfile. Why: /research subagent inferred Tremor + shadcn/ui were installed because the jarvis-app PRD named them as the intended stack; package.json had neither. All downstream recommendations in that session were wrong.

## URL Tool Routing

- **Never call `WebFetch` directly on x.com, twitter.com, or linkedin.com URLs** — these return 402. Always use `mcp__tavily__tavily_extract` with `extract_depth: "advanced"` first. This applies in ALL contexts (inside or outside `/research`), including ad-hoc URL lookups mid-session.
- **Domain routing quick-ref**: x.com/twitter → `tavily_extract` (advanced); linkedin.com → `tavily_extract` (advanced); medium.com → `tavily_extract` (advanced, may hit paywall); github.com/docs/blogs → `WebFetch`; JS-heavy SPAs → Firecrawl; Reddit → `WebSearch` metadata only (Firecrawl blocks Reddit)
- **WebFetch is the wrong first instinct for unknown URLs** — check domain against the difficult-domains list before picking the tool

## External Research

- For current-events research (financial, geopolitical, live topics), always use direct WebSearch — sub-agents may have a stale knowledge cutoff
- Default posture is absorb ideas over adopt dependencies — before proposing any new tool/MCP/dependency: (1) apply the **counterfactual filter**: "what would we build if this tool didn't exist?" — if the answer is simpler, you're anchored on the tool's patterns, not real problems, (2) identify root cause, (3) test existing tools first, (4) if none work, run `/architecture-review`; only adopt when implementation is genuinely hard (>1 day) AND the dependency is mature. Why: two consecutive sessions (algebrica ingest, gnhf autoresearch) produced inflated adoption lists that /architecture-review collapsed to minimal fixes.
- Before committing to a new product idea competing with platform incumbents, run `/research` targeting "don't build" signals — check: bundled free by incumbents? structural moats? WTP survives bundling?
- External AI orchestration patterns: filter through "is this a team coordination problem?" — if yes, skip; Jarvis is skill-first, not agent-first
- When evaluating external iterative-refinement or evaluation techniques from research/papers, run an **oracle check** before adopting the convergence apparatus — "does the benchmark task have a binary correctness oracle (test suite, score, ground truth), and does Jarvis's target task have an equivalent?" If no: extract structural insights only (e.g., "do nothing as first-class option") and reject the tournament/convergence mechanism — a converged wrong output enters downstream pipelines with higher authority than a single-pass wrong output. Why: 2026-04-16 autoreason arch-review — CodeContests gains (binary oracle) don't transfer to Jarvis synthesis/PRD (no oracle); all 3 parallel review agents flagged this independently.
- When extracting patterns from external case studies, teardowns, or architectural post-mortems, run an **analogy-break test** before carrying the pattern into `/create-prd`: (a) name the specific constraint that made the pattern load-bearing in the source system, and (b) show that same constraint exists in Jarvis. If (b) fails, extract the pattern for reference only — do not promote it to a P1/P2 PRD recommendation. Why: 2026-04-18 Cortex teardown — /research extracted P1 cold-boot handoff from shujunliang/svpino; the source constraint ("sessions die with no operator memory") doesn't exist in Jarvis (Eric is the persistent operator). /architecture-review rejected the P1 and surfaced 7 High-severity risks that would never have been raised if the analogy-break test ran at brief-write time.

## Loaded by

- Load explicitly when context includes /research, /absorb, dependency evaluation, or external pattern adoption
- `.claude/skills/research/SKILL.md` — Step 0.5 (research and dependency-adoption constraints)
- `.claude/skills/absorb/SKILL.md` — Step 0.5 (absorb-vs-adopt posture, counterfactual filter)
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
