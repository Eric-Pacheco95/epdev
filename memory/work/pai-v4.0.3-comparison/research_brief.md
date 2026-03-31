# Technical Research: PAI v4.0.3 vs Jarvis Architecture Comparison
- Date: 2026-03-30
- Type: Technical
- Depth: deep
- Sources consulted: 16 (GitHub repo pages, documentation files)

## What PAI v4.0.3 Is

Daniel Miessler's Personal AI Infrastructure — a community-maintained Claude Code scaffolding system. v4.0.3 is a patch release (4 bug fixes, no new features) on the v4.0 architecture. The real comparison target is PAI v4.0.x overall.

**Scale**: 63 skills across 13 categories, 21 hooks, 338 workflows, 202 tips, Algorithm v3.6.0

## Architecture Comparison

### Shared DNA (What Jarvis Already Has)

| Concept | PAI | Jarvis | Notes |
|---------|-----|--------|-------|
| Algorithm loop | v3.6.0 (7-phase) | TheAlgorithm 7-phase | Same lineage, Jarvis customized |
| TELOS identity | Full TELOS system | Full TELOS system | Equivalent |
| ISC criteria | Ideal State Criteria | ISC with quality gate | Jarvis has stricter gate (6 checks) |
| Skill-first routing | 63 skills, intent-match | 38+ skills, slash-command | Different activation model |
| Memory system | WORK/LEARNING/STATE hierarchy | work/learning/signals/synthesis | Similar 3-tier approach |
| Hook lifecycle | 21 hooks across 7 events | Custom hooks via settings.json | Both use all Claude Code hook events |
| Security layer | Constitutional rules + validator | constitutional-rules.md + validators/ | Equivalent |
| Agent delegation | Named agents + dynamic compose | Named agents + /spawn-agent | PAI has richer composition |
| Steering rules | AISTEERINGRULES.md | CLAUDE.md steering section | Equivalent concept |
| Learning signals | Ratings + failure capture | Signals + synthesis + auto-signals | Jarvis more mature here |
| Self-healing | Not emphasized | Core principle + self-heal tests | Jarvis stronger |
| Decision logging | In PRD/work files | history/decisions/ dedicated | Jarvis more explicit |

### What PAI Has That Jarvis Doesn't

#### 1. CLI-First Architecture (HIGH VALUE)
PAI's biggest philosophical differentiator. Pattern: build deterministic CLI tools first, then wrap with AI prompting. Every repeated operation should be a CLI command with `--flags`, not ad-hoc prompt execution.

**Jarvis gap**: Our skills are prompt-first. When a skill could be a Python script with flags (e.g., signal counting, synthesis triggering, tasklist validation), we still route through LLM. The steering rule "does this step require intelligence? No -> Python script" exists but isn't consistently applied.

**Action**: Audit skills for deterministic steps that should be CLI tools. Priority targets: `/vitals`, `/synthesize-signals`, `/security-audit` scan steps.

#### 2. Actions/Pipelines/Flows System (MEDIUM VALUE)
Three-tier execution model:
- **Actions** (`A_*`): Single-step, typed, with `action.json` manifests. Like microservices for AI ops.
- **Pipelines** (`P_*`): Chain actions sequentially (output -> input).  
- **Flows** (`F_*`): Connect external sources to pipelines on cron schedules.

**Jarvis gap**: We have `/workflow-engine` and scheduled tasks but no formal action/pipeline abstraction. Our autonomous loop (heartbeat -> ISC engine -> auto-signals) is functionally a flow but isn't formalized.

**Action**: Consider formalizing our autonomous components into a pipeline model during Phase 5. Not urgent — current approach works, but the abstraction would improve composability.

#### 3. Cloud Execution Layer ("Arbol") (LOW VALUE for Jarvis)
Cloudflare Workers deployment with two tiers: V8 Isolates (lightweight LLM actions) and Sandbox (Docker containers). Enables running PAI actions in the cloud.

**Jarvis gap**: We're local-first by design. Cloud triggers via Claude Remote exist but are limited. Task Scheduler handles our scheduling needs.

**Action**: Not a gap to close. Jarvis's local-first architecture is a deliberate choice. The MCPorter evaluation (5-pre) is our equivalent path for moving deterministic work off the LLM path.

#### 4. Voice Server (MEDIUM VALUE)
Full local TTS server with ElevenLabs integration, per-agent voice IDs, pronunciations.json, menubar control. Hooks fire voice notifications on task start/complete.

**Jarvis gap**: We have voice capture (3C) but no voice OUTPUT. PAI's voice server provides ambient awareness — you hear when tasks complete without watching the terminal.

**Action**: Consider for Phase 5+ as an ergonomics feature. Low priority vs core autonomous capabilities.

#### 5. Notification System (MEDIUM-HIGH VALUE)
Multi-channel: Voice (primary), ntfy.sh (push), Discord (webhooks), Desktop (native). Smart routing based on event type and duration. Fire-and-forget, non-blocking.

**Jarvis gap**: We have Slack notifications (crypto-bot, #jarvis-inbox) but no unified notification routing. No duration-aware escalation (e.g., "push to phone if task > 5min").

**Action**: This would pair well with Phase 5 autonomous execution. When background agents complete, Eric needs to know. ntfy.sh is zero-friction to add.

#### 6. Agent Composition System (MEDIUM VALUE)
`ComposeAgent` dynamically creates agents from trait combinations (expertise x personality x approach). Each combination maps to a voice and system prompt. Spotcheck pattern: always verify multi-agent output with a separate agent.

**Jarvis gap**: `/spawn-agent` exists but is simpler — it uses predefined agent definitions, not dynamic trait composition. We don't have the spotcheck-after-parallel pattern formalized.

**Action**: The spotcheck pattern is worth adopting immediately. Trait composition is interesting but may be overengineered for solo use — our 5 named agents cover our needs. Revisit if we find agent variety is limiting.

#### 7. Rating System (LOW-MEDIUM VALUE)
Hook-based capture of explicit ratings (1-5) and implicit sentiment inference via Haiku. Low ratings (1-3) trigger automatic failure analysis with full context dumps to LEARNING/FAILURES/.

**Jarvis gap**: We have `/learning-capture` with manual signals but no per-response rating system. No automatic failure context dump on bad interactions.

**Action**: The automatic failure dump pattern is valuable — when a session goes badly, capturing full context before it's compacted is smart. Could integrate into our existing `/learning-capture` flow.

#### 8. Dynamic Context Loading for Skills (MEDIUM VALUE)
Skills keep SKILL.md minimal (30-50 lines) with routing table. Heavy context lives in sibling .md files, loaded on-demand via `SkillSearch()`. Claims ~70% token reduction per invocation.

**Jarvis gap**: Our skills are monolithic — each SKILL.md contains everything. This works but costs tokens, especially for complex skills like `/research` or `/implement-prd`.

**Action**: Worth adopting for our largest skills. Split context-heavy skills into routing SKILL.md + context files. Priority: `/implement-prd`, `/research`, `/delegation`.

#### 9. PRD as Single Source of Truth (SHARED - DIFFERENT IMPL)
PAI: PRD.md with YAML frontmatter is THE work file — metadata, ISC, decisions, changes all in one. PostToolUse hook syncs frontmatter to work.json.

**Jarvis**: PRDs live in memory/work/ but are separate from ISC files, decision logs, and tasklist. More distributed approach.

**Action**: Not necessarily a gap. Our distributed approach has benefits (dedicated decision log, separate tasklist). But the frontmatter-sync hook pattern is interesting for keeping metadata current.

#### 10. Multi-Model Research Agents (LOW VALUE)
PAI has 5 researcher agents: Claude, Codex, Gemini, Grok, Perplexity. Each queries a different model/service for the same research topic, then results are synthesized.

**Jarvis gap**: We use external models for review-only (steering rule). Our `/research` uses Tavily + WebSearch.

**Action**: Aligns with our existing steering rule that external models are review-only. We could add Gemini/Codex as research verification, but this is complexity for marginal gain on solo use.

#### 11. Skill Customization System (LOW VALUE for solo)
`USER/SKILLCUSTOMIZATIONS/{SkillName}/EXTEND.yaml` — merge strategies (append, override, deep_merge) for personalizing shared skills. Enables skill sharing without forking.

**Jarvis gap**: Our skills are already personal. No sharing/distribution model.

**Action**: Only relevant if we ever distribute Jarvis skills. Skip for now.

#### 12. Session Auto-Naming & Tab Management (LOW VALUE)
Hooks auto-name sessions from first prompt, color-code terminal tabs by state (question pending, algorithm phase, completed).

**Jarvis gap**: No terminal UI enhancement. We work in Windows Terminal / VS Code.

**Action**: Nice-to-have ergonomics. Very low priority.

### What Jarvis Has That PAI Doesn't

| Feature | Jarvis | PAI Equivalent |
|---------|--------|---------------|
| **Autonomous background loop** | Heartbeat + ISC engine + auto-signals | No autonomous execution |
| **Auto-synthesis** | Periodic signal synthesis at threshold | Manual synthesis only |
| **Self-healing tests** | Dedicated test suite + auto-fix | Not formalized |
| **Defensive testing** | Security test suite | Security skills but no continuous testing |
| **Steering rule lifecycle** | `/update-steering-rules --audit` + pruning | Static AISTEERINGRULES.md |
| **Phase-gated development** | Phased roadmap with explicit gates | No visible project phasing |
| **Brain-map visualization** | jarvis-app (Next.js dashboard) | No visualization layer |
| **Cross-project orchestration** | `/project-orchestrator` + external health sources | Single-project focus |
| **Learning loop maturity** | 156 signals, 6 synthesis runs, auto-signals | Rating capture only |
| **Crypto-bot integration** | Live trading bot with Jarvis governance | No domain-specific integration |

## Top 5 Gaps to Close (Priority-Ranked)

### 1. CLI-First Tool Migration (Phase 5 candidate)
Audit deterministic skill steps -> extract to Python CLI tools. Biggest bang for the buck on cost and reliability.

### 2. Notification Routing Layer (Phase 5 candidate)
Add ntfy.sh for push notifications. Route by event type + duration. Essential for autonomous execution awareness.

### 3. Spotcheck Pattern for Multi-Agent Work (Quick win)
After any parallel agent delegation, auto-launch a verification agent. Add to `/delegation` and `/spawn-agent`.

### 4. Dynamic Skill Context Loading (Quick win)
Split 3-5 largest skills into routing SKILL.md + context files. Reduce token cost per invocation.

### 5. Automatic Failure Context Dump (Quick win)
When `/learning-capture` records a low-rated session, auto-dump full context to failures/ before compaction loses it.

## Open Questions

1. PAI's Algorithm is at v3.7.0 — what specific improvements exist vs our implementation?
2. How effective is the ComposeAgent trait system in practice for solo users?
3. Is the Actions/Pipelines/Flows abstraction worth the overhead vs our direct scheduling approach?
4. PAI's `doc-dependencies.json` tracks cross-references — would this help prevent our doc drift?

## Sources

1. https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Releases/v4.0.3
2. PAI README.md (release notes, installation, metrics)
3. PAISYSTEMARCHITECTURE.md (16 founding principles, full architecture)
4. SKILLSYSTEM.md (skill anatomy, lifecycle, customization)
5. THEDELEGATIONSYSTEM.md (agent routing, timing scopes)
6. MEMORYSYSTEM.md (memory hierarchy, data flow)
7. THEHOOKSYSTEM.md (7 lifecycle events, 21 hooks)
8. THENOTIFICATIONSYSTEM.md (multi-channel routing)
9. CLIFIRSTARCHITECTURE.md (CLI-first pattern, migration strategy)
10. PAIAGENTSYSTEM.md (3 agent types, composition model)
11. Skills directory (11 categories: Agents, ContentAnalysis, Investigation, Media, Research, Scraping, Security, Telos, Thinking, USMetrics, Utilities)
12. Hooks directory (21 hooks across all lifecycle events)
13. Agents directory (14 agents including multi-model researchers)
14. VoiceServer directory (local TTS with ElevenLabs)
15. ACTIONS/PIPELINES/FLOWS directories (cloud execution primitives)

## Recommended Next Steps

1. `/first-principles` on the CLI-First Architecture pattern — challenge whether it applies to Jarvis or if our prompt-first approach is actually better for solo use
2. `/architecture-review` on adding ntfy.sh notification routing — evaluate blast radius and integration points
3. `/create-prd` for "Phase 5A: CLI-First Tool Migration" if the first-principles analysis supports it
4. Quick wins (spotcheck pattern, skill splitting, failure dump) can be implemented in current sprint without a PRD

Some sources contain verifiable claims (63 skills, 338 workflows, Algorithm v3.7.0). Run `/analyze-claims` to fact-check?
