# PRD: Autonomous Research & Task Loop (Phase 5C)

> **Project:** epdev Jarvis
> **Status:** PLAN
> **Parent:** Phase 5 — Autonomous Execution
> **Depends on:** Phase 5B (dispatcher, worktree lib, backlog format) — SHIPPED
> **Companion:** `orchestration/tasklist.md`, `orchestration/task_backlog.jsonl`
> **Design principle:** Everything connects. One pipeline, one backlog, reusable across future projects.

## OVERVIEW

The Autonomous Research & Task Loop closes the gap between Jarvis's monitoring infrastructure and its ability to act on what it discovers. Today, multiple systems sense the environment (heartbeat, overnight runner, morning feed, source registry) but nothing automatically converts findings into validated, dispatchable tasks. This PRD defines the full closed loop: producers discover work, a validation gate triages cheaply, research deepens understanding where warranted, architecture review gates task creation, the dispatcher executes, and feedback flows back into the learning system. The pattern is designed to be project-agnostic so it can be lifted into crypto-bot, jarvis-app, or future projects.

## PROBLEM AND GOALS

- **No automated backlog producers** — The dispatcher has 12 hand-seeded tasks. Once consumed, the pipeline stalls. Producers must continuously discover work worth doing.
- **Source monitoring is shallow** — `morning_feed.py` checks GitHub commit metadata only. No pipeline reads, understands, or extracts learnings from Tier 1/2 source content (blogs, release notes, security advisories).
- **Research findings don't become tasks** — `/research` and `/absorb` produce artifacts but require Eric to manually convert insights into backlog items.
- **No deep research capability** — Large sources (YouTube channels with 50+ videos, Substack archives, GitHub repo histories) can't be processed in a single pass. Need iterative chunked processing.
- **Eric can't defer work to the pipeline** — When Eric is in a session and identifies work he doesn't want to do right now, there's no quick way to inject it into the autonomous loop.
- **No feedback loop** — Completed/failed tasks don't automatically generate signals, trigger self-heal, or tune validation thresholds.
- **Goal:** A self-sustaining loop where Jarvis discovers, validates, researches, executes, and learns — with Eric as approver and steering authority, not bottleneck.

## NON-GOALS

- **Replacing Eric's judgment** — Producers propose, Eric (or validation gate) decides. No autonomous action on S-rated items without explicit opt-in per producer type.
- **Real-time streaming** — All producers run on scheduled cadence (minutes to daily), not event-driven websockets.
- **Multi-project orchestration in Sprint 1** — The pattern will be reusable, but Sprint 1 targets epdev only. Cross-project wiring is Sprint 3+.
- **Brain-map dashboard** — Kanban task view is a separate jarvis-app phase (scoped after this pipeline stabilizes).
- **Dispatcher model routing redesign** — Separate PRD. This PRD uses the existing `model` field in task schema; the routing intelligence improvement is tracked independently.

## USERS AND PERSONAS

- **Eric (operator)** — Reviews morning feed proposals, kicks off deep research, uses `/defer` to inject tasks, reviews completed work. Needs visibility without reading JSONL files.
- **Jarvis (autonomous)** — Runs producers, validates proposals, dispatches tasks, captures feedback. Must be conservative (false negatives > false positives for task creation).
- **Future project instances** — crypto-bot, jarvis-app, or new repos that adopt the same producer → gate → dispatcher → feedback pattern.

## USER JOURNEYS OR SCENARIOS

### Journey 1: Source Monitor discovers a relevant Claude Code release
1. Source monitor crawls Anthropic blog (Tier 1, daily cadence)
2. Extracts release notes content via Tavily
3. Validation gate scores relevance vs TELOS goals → rated A (directly enables active project)
4. Auto-promotes to research: `/absorb --quick` on the release URL
5. Absorb output includes actionable finding ("new hook type available")
6. `/architecture-review` confirms it's worth a task (not just a signal)
7. Writes task to `task_backlog.jsonl`: "Evaluate and integrate new hook type"
8. Dispatcher picks up task next cycle, runs in worktree
9. Completed task → learning signal auto-generated
10. Morning feed surfaces the result to Eric

### Journey 2: Eric kicks off deep research on a YouTube channel
1. Eric in session: `/deep-research https://youtube.com/@AndrejKarpathy --plan`
2. Jarvis fetches channel index, identifies 15 relevant videos (filtered by topic/date)
3. Presents plan: "15 videos, estimated 5 autonomous chunks of 3 videos each, ~2 hours total"
4. Eric approves: "go"
5. Jarvis processes chunk 1 in-session: `/extract-wisdom` + `/learning-capture` per video
6. Writes remaining 4 chunks as autonomous tasks to backlog (tier 1, model: sonnet)
7. Dispatcher processes chunks overnight in worktrees
8. Each chunk produces signals + wisdom extracts
9. Final consolidation task auto-queued: synthesize all chunks into a coherence report
10. Morning feed: "Deep research complete: Karpathy channel — 15 videos processed, 7 signals, 3 TELOS proposals"

### Journey 3: Eric defers a fix from interactive session
1. Eric is building a feature, notices a test is flaky
2. Types: `/defer Fix flaky test in test_heartbeat.py — intermittent timeout on Windows`
3. Jarvis writes a task to backlog with auto-generated ISC and tier 1 classification
4. Eric continues building without context-switching
5. Dispatcher picks up the fix task in next cycle

### Journey 4: Heartbeat detects metric degradation
1. Heartbeat collector detects `isc_ratio` dropped below threshold (3 consecutive readings)
2. Heartbeat producer emits a proposal: "ISC ratio degraded — investigate"
3. Validation gate: auto-promote (metric degradation is always S-tier)
4. Task written: "Diagnose ISC ratio drop — read recent changes, identify regression"
5. Dispatcher runs diagnostic task (tier 0, read-only, model: opus)
6. Output: signal with root cause analysis + optional follow-up fix task

### Journey 5: Feedback loop tunes thresholds
1. Over 30 days, Eric has reviewed 20 proposals from source monitor
2. 15 were rated B by the gate, Eric acted on 3 (15% act-on rate for B)
3. Threshold tuner proposes: "Lower B auto-promote to B+ only (require source-type match to active project)"
4. Eric approves threshold change
5. Next cycle uses tighter filter

## FUNCTIONAL REQUIREMENTS

### FR-001: Producer Framework

- FR-001a: A `Producer` base interface that all producers implement: `discover() → list[Proposal]`
- FR-001b: Each producer has: `id`, `cadence` (cron expression), `tier_ceiling` (max task tier it can create), `enabled` flag
- FR-001c: Producer registry in `orchestration/producers.yaml` — single file listing all active producers with their config
- FR-001d: Producer runner script (`tools/scripts/run_producers.py`) that loads registry, runs due producers, feeds proposals to validation gate
- FR-001e: Each producer run logged to `data/producer_runs/` with timestamp, proposal count, and outcome

### FR-002: Source Monitor Producer

- FR-002a: Reads `sources.yaml` for Tier 1 (daily), Tier 2 (weekly), Tier 3 (monthly) sources
- FR-002b: Fetches actual content via Tavily extract/crawl (not just GitHub API metadata)
- FR-002c: Extracts key findings using a focused prompt (Haiku for extraction, not full absorb)
- FR-002d: Each finding becomes a `Proposal` with: source, title, summary, relevance_hint, url
- FR-002e: Tracks `last_checked` per source in `sources.yaml` to respect frequency cadence
- FR-002f: Rate-limits external requests (1 per 10 seconds, per existing constraint)

### FR-003: Heartbeat Producer

- FR-003a: Reads `heartbeat_latest.json` and `heartbeat_history.jsonl`
- FR-003b: Detects metric degradation (value below threshold for N consecutive readings)
- FR-003c: Detects metric staleness (no update in >48 hours)
- FR-003d: Emits proposals for degraded/stale metrics with severity context
- FR-003e: Requires non-zero delta (per existing steering rule — no WARN/CRIT on unchanged values)

### FR-004: Signal Accumulator Producer

- FR-004a: Counts unprocessed signals in `memory/learning/signals/`
- FR-004b: When count >= threshold (20 default, 30 when auto-signal producers active), emits synthesis proposal
- FR-004c: Threshold is configurable in `producers.yaml`

### FR-005: Self-Heal Producer

- FR-005a: Reads `memory/learning/failures/` for recent failures (last 7 days)
- FR-005b: Cross-references against existing backlog to avoid duplicate fix tasks
- FR-005c: Emits fix proposals with failure context and suggested ISC

### FR-006: Cross-Project Producer

- FR-006a: Reads CLAUDE.md and key state files from registered external repos
- FR-006b: Detects drift: naming inconsistencies, pattern divergence, stale references
- FR-006c: Emits coherence proposals (report-only tier 0 tasks)
- FR-006d: External repos registered in `producers.yaml` with their paths

### FR-007: Validation Gate

- FR-007a: Receives proposals from all producers
- FR-007b: Runs deterministic pre-filter first: deduplication (fuzzy match against last 30 days of proposals + existing backlog), recency check, source tier weight
- FR-007c: Proposals passing pre-filter get LLM scoring (Haiku for cost efficiency): relevance to TELOS goals (0-100), novelty (0-100), effort estimate (XS/S/M/L/XL)
- FR-007d: Combined score maps to S/A/B/C/D rating
- FR-007e: S/A proposals auto-promote to research or direct task creation (configurable per producer)
- FR-007f: B proposals queued for morning feed — Eric decides
- FR-007g: C/D proposals dropped (logged to `data/gate_log.jsonl` for audit and threshold tuning)
- FR-007h: Gate results include reasoning trace for Eric's review
- FR-007i: Anti-gaming: gate prompt is hardcoded, not dynamically constructed from proposal content (prompt injection defense)

### FR-008: Research Execution

- FR-008a: S/A proposals marked `needs_research: true` get a research pass before task creation
- FR-008b: Standard research: single `/absorb --quick` or `/research quick` call via `claude -p`
- FR-008c: Research output goes through `/architecture-review` (lightweight: "is this worth a task, or just a signal?")
- FR-008d: If architecture review says "task": write to backlog with auto-generated ISC
- FR-008e: If architecture review says "signal only": write learning signal, no task created
- FR-008f: Research artifacts saved to `memory/work/jarvis/research_pipeline/YYYY-MM-DD/`

### FR-009: Deep Research Agent

- FR-009a: New `/deep-research` skill — interactive kickoff, autonomous execution
- FR-009b: `--plan` mode: fetch source index (YouTube playlist, Substack archive, GitHub releases), present chunk plan to Eric
- FR-009c: Eric approves plan → first chunk processed in-session
- FR-009d: Remaining chunks written as autonomous tasks to backlog (tier 1, linked by `parent_id`)
- FR-009e: Each chunk task runs `/extract-wisdom` + `/learning-capture` in a worktree
- FR-009f: After all chunks complete, a consolidation task auto-queues: synthesize findings across all chunks
- FR-009g: Chunk size configurable (default: 3 items per chunk for videos, 5 for articles)
- FR-009h: Source type handlers: YouTube (via transcript extraction), Substack (via Tavily crawl), GitHub (via API + README/changelog)
- FR-009i: Progress tracking: each chunk task references the deep-research session ID for lineage

### FR-010: `/defer` Skill

- FR-010a: Syntax: `/defer <description>` or `/defer <description> --tier <0|1|2> --model <model>`
- FR-010b: Auto-generates ISC from description using in-session LLM (2-3 criteria, quality gate applied)
- FR-010c: Before writing, presents reasoning to Eric: generated ISC, suggested tier/model, and asks "Does this capture your intent? Can the dispatcher handle this autonomously?" Eric confirms, adjusts, or cancels.
- FR-010d: Only writes to `task_backlog.jsonl` after Eric confirms (status `pending`)
- FR-010e: Default tier: 1 (code change). Eric can override with `--tier 0` (read-only) or `--tier 2` (architecture)
- FR-010f: Confirms to Eric: "Queued task `{id}`: {description} — will be picked up by dispatcher"
- FR-010g: No validation gate — Eric's judgment (via the reasoning step) is the gate for deferred tasks

### FR-011: Feedback Loops

- FR-011a: Completed tasks auto-generate a learning signal (`Source: autonomous`, rating based on ISC pass rate)
- FR-011b: Failed tasks (ISC not met after retries) auto-generate a failure log + emit self-heal proposal
- FR-011c: Eric's act-on rate for proposals tracked in `data/gate_metrics.jsonl` (proposal_id, rating, acted_on, date)
- FR-011d: Monthly threshold tuner: reads gate_metrics, proposes S/A/B threshold adjustments if act-on rates drift
- FR-011e: Dispatcher run reports (`data/dispatcher_runs/`) feed into morning feed summary

### FR-012: Backlog Task Schema Extension

- FR-012a: New fields on task schema: `source_producer` (which producer created it), `proposal_id` (link to gate log), `research_artifacts` (list of file paths), `parent_id` (for deep-research chunk linking — already exists), `feedback` (post-completion: `{signal_id, acted_on}`)
- FR-012b: New task type field: `research`, `fix`, `audit`, `synthesis`, `deep-research-chunk`, `deferred`
- FR-012c: Backward compatible — existing seed tasks continue to work without new fields

## NON-FUNCTIONAL REQUIREMENTS

- NFR-001: Producer runner completes all due producers in < 5 minutes (excluding deep research)
- NFR-002: Validation gate processes a batch of 20 proposals in < 60 seconds (Haiku call)
- NFR-003: Source monitor rate-limits to 1 external request per 10 seconds
- NFR-004: All producer scripts use ASCII-only terminal output (Windows cp1252 safe)
- NFR-005: No producer may modify files outside its designated output directories
- NFR-006: Gate log and metrics files use append-only JSONL (no rewrite on each run)
- NFR-007: Deep research chunks are independently resumable — if a chunk fails, remaining chunks still execute
- NFR-008: Pattern must be extractable: producer framework, gate, and feedback loop should work with only `task_backlog.jsonl` + `producers.yaml` as the integration surface (no epdev-specific imports required)
- NFR-009: Source monitor tracks Tavily credit usage per request in `data/tavily_usage.jsonl` (date, source, credits_used). Alerts Eric via morning feed when 80% of monthly budget (1,000 credits) consumed. Surfaces upgrade recommendation when usage exceeds 800 credits for 2+ consecutive months.
- NFR-010: Gemini API usage tracked in `data/gemini_usage.jsonl` for any producers or research passes that use Gemini. Both usage logs feed into jarvis-app usage dashboard (future phase).

## ACCEPTANCE CRITERIA

### Sprint 1: Producers + Validation Gate + Backlog Writer

- [ ] Producer runner reads `producers.yaml` and executes only producers whose cadence is due | Verify: `python tools/scripts/run_producers.py --dry-run` shows selected producers
- [ ] Source monitor fetches Tier 1 content via Tavily and produces >= 1 proposal per source with content | Verify: `python tools/scripts/run_producers.py --producer source_monitor --dry-run`
- [ ] Validation gate deduplicates proposals against existing backlog (no duplicate task descriptions within 14 days) | Verify: feed duplicate proposal, confirm it's dropped with reason in gate_log.jsonl
- [ ] Validation gate rates proposals S/A/B/C/D with reasoning trace | Verify: gate_log.jsonl entries contain `rating` and `reasoning` fields
- [ ] S/A proposals auto-write tasks to `task_backlog.jsonl` with valid schema | Verify: `python tools/scripts/isc_validator.py` passes on new tasks
- [ ] No producer writes to directories outside its designated output paths | Verify: grep producer scripts for write operations; all target `data/` or `memory/work/jarvis/research_pipeline/`
- [ ] Heartbeat and signal accumulator producers emit proposals when thresholds are met | Verify: mock threshold breach, confirm proposal in dry-run output
- [ ] `/defer` skill writes a valid task to backlog with auto-generated ISC | Verify: `/defer "test task"` then read last line of task_backlog.jsonl

ISC Quality Gate: PASS (6/6)

### Sprint 2: Deep Research + Research Execution

- [ ] `/deep-research --plan <url>` fetches source index and presents chunk plan without executing | Verify: run with YouTube channel URL, confirm plan output with chunk count
- [ ] Approved deep-research plan processes chunk 1 in-session and writes remaining chunks as backlog tasks | Verify: task_backlog.jsonl contains chunk tasks with matching `parent_id`
- [ ] Each chunk task produces `/extract-wisdom` output and a learning signal | Verify: after dispatcher runs chunk, signal file exists with `Source: autonomous`
- [ ] Consolidation task auto-queues after all chunks complete | Verify: when last chunk status=done, new consolidation task appears in backlog
- [ ] S/A proposals from source monitor trigger `/absorb --quick` research pass before task creation | Verify: research artifact exists in `memory/work/jarvis/research_pipeline/` for auto-promoted proposal
- [ ] Research artifacts that fail architecture review become signals, not tasks | Verify: mock a "signal only" review result, confirm no task written but signal file created
- [ ] No anti-criterion: deep research chunks never modify files outside their worktree | Verify: diff of main branch shows zero changes during chunk execution

ISC Quality Gate: PASS (6/6)

### Sprint 3: Feedback Loops + Cross-Project + Threshold Tuning

- [ ] Completed dispatcher tasks auto-generate learning signals with ISC pass rate context | Verify: after task completion, new signal in `memory/learning/signals/` with `Source: autonomous`
- [ ] Failed tasks generate failure log entries and emit self-heal proposals | Verify: after task failure (max retries), entry in `memory/learning/failures/` and proposal in next producer run
- [ ] Eric's act-on rate tracked per proposal rating tier | Verify: `data/gate_metrics.jsonl` contains entries with `rating` and `acted_on` fields
- [ ] Monthly threshold tuner reads metrics and proposes adjustments when B act-on rate < 20% | Verify: mock 30 days of low-B-act-on data, confirm tuner proposal
- [ ] Cross-project producer detects naming drift between epdev and registered repos | Verify: introduce deliberate drift in test fixture, confirm coherence proposal
- [ ] No anti-criterion: feedback loops never modify the validation gate's scoring prompt or thresholds without Eric's approval | Verify: threshold tuner writes proposals only, not config changes
- [ ] Producer framework is extractable to a new repo with only `task_backlog.jsonl` + `producers.yaml` as integration surface | Verify: copy framework files to temp directory, run with mock backlog, confirm it works

ISC Quality Gate: PASS (6/6)

## SUCCESS METRICS

- Backlog never reaches zero pending tasks for more than 48 hours (producers are generating work)
- >= 60% of auto-created tasks pass ISC on first dispatcher run (validation gate quality)
- Eric's act-on rate for S/A proposals >= 50% (relevance is high)
- Eric's act-on rate for B proposals >= 20% (not spamming noise)
- Deep research sessions produce >= 3 learning signals per source (extracting value)
- `/defer` used >= 2x per week (Eric trusts the pipeline enough to delegate)
- Zero tasks created from C/D proposals (gate is working)
- Feedback loop generates >= 1 threshold adjustment proposal per month (system is self-tuning)

## OUT OF SCOPE

- Brain-map kanban dashboard (separate jarvis-app phase — PRD to follow after pipeline stabilizes)
- Dispatcher model routing intelligence redesign (separate PRD — uses existing `model` field for now)
- Slack Bot Socket Mode integration (Phase 3E-Slack — separate track)
- Multi-project backlog federation (Sprint 3 enables the pattern; actual federation is Phase 6+)
- Cost tracking per autonomous run (useful but not blocking — add when token counting is available)

## DEPENDENCIES AND INTEGRATIONS

- **Tavily MCP** — Source monitor uses `tavily_extract` and `tavily_crawl` for content fetching. Already configured in `.mcp.json`.
- **Dispatcher (Phase 5B)** — `jarvis_dispatcher.py` reads `task_backlog.jsonl` and executes tasks. This PRD adds producers that write to the same backlog.
- **Worktree lib** — `tools/scripts/lib/worktree.py` provides isolated execution for code-change tasks.
- **`/absorb` skill** — Research execution uses `/absorb --quick` for standard research passes.
- **`/extract-wisdom` skill** — Deep research chunks use this for content extraction.
- **`/architecture-review` skill** — Gates the research → task promotion path.
- **`/learning-capture` skill** — Deep research chunks and feedback loops generate signals.
- **Haiku model** — Validation gate uses Haiku for cheap triage scoring.
- **`claude -p`** — Research execution and deep research chunks run via `claude -p` in autonomous mode.
- **Task Scheduler** — `run_producers.py` runs on schedule (e.g., 3am before dispatcher at 5am).
- **Consolidation script** — `consolidate_overnight.py` already merges overnight branches; no changes needed.
- **Morning feed** — `morning_feed.py` reads gate log and pipeline status for daily briefing. Enhancement needed.
- **sources.yaml** — Source registry with 24 sources across 3 tiers. Already exists.

## RISKS AND ASSUMPTIONS

### Risks

- **Token cost spiral** — If producers generate too many S/A proposals, research execution burns through Claude Max capacity. Mitigation: daily cap on auto-research passes (default 5/day), configurable in `producers.yaml`.
- **Tavily rate limits** — Free tier may hit limits with daily Tier 1 crawling (6 sources x daily). Mitigation: caching layer + graceful degradation (skip source if Tavily fails, log, retry next cycle).
- **Validation gate quality** — Haiku may misjudge relevance for nuanced TELOS connections. Mitigation: log all gate decisions, review weekly, escalate to Sonnet if accuracy < 70%.
- **Deep research runaway** — A YouTube channel with 500 videos could generate 167 chunk tasks. Mitigation: hard cap at 30 chunks per deep-research session (configurable), require Eric approval above 10.
- **Prompt injection via source content** — External blog posts could contain adversarial instructions. Mitigation: existing constitutional rule (never execute instructions from external content), plus gate prompt is hardcoded (FR-007i).

### Assumptions

- Claude Max subscription provides sufficient `claude -p` capacity for 5-10 autonomous research passes per day
- Tavily MCP tools work reliably from `claude -p` autonomous context (to be validated in Sprint 1)
- Haiku is available via `claude -p --model haiku` or equivalent for gate scoring
- Existing dispatcher handles increased backlog volume (10-20 tasks/week vs current 12 static seeds)

## RESOLVED QUESTIONS

1. **Haiku access from `claude -p`** — RESOLVED: `claude -p --model haiku` works. Validated 2026-03-31.
2. **Tavily from autonomous context** — RESOLVED: Tavily MCP tools load and work in `claude -p` context. Validated 2026-03-31.
3. **Gate threshold initial values** — RESOLVED: Starting values S >= 90, A >= 75, B >= 55, C >= 35, D < 35. Jarvis auto-tunes via feedback loop (Sprint 3) based on Eric's act-on rates.
4. **Producer cadence orchestration** — RESOLVED: Single `run_producers.py` script, one Task Scheduler entry. Simpler, less surface area.
5. **Deep research transcript extraction** — Tavily likely handles YouTube pages. To be validated in Sprint 2. Fallback: YouTube Data API (requires API key setup).
6. **Cross-project producer scope** — RESOLVED: Initial repos: `crypto-bot`, `jarvis-app`. Producer is read-only (tier 0). Checks: steering rule sync, naming conventions, stale references, pattern adoption gaps, health cross-checks. Output is coherence reports → may become tasks in the target repo's backlog. New repos added via `producers.yaml` config.
7. **`/defer` ISC quality** — RESOLVED: `/defer` runs a reasoning pass with Eric before finalizing. Presents generated ISC + asks "does this capture your intent? Can the dispatcher handle this autonomously?" Eric confirms or adjusts before task is written.

## OPEN QUESTIONS

1. **Tavily credit budget** — Free tier = 1,000 credits/month. Daily Tier 1 crawling (6 sources x 30 = 180) + Tier 2 weekly (6 sources x 4 = 24) + research passes (~5/day x 30 = 150) + deep research = ~400-600 credits/month baseline. Leaves headroom but not much. Jarvis should track usage in `data/tavily_usage.jsonl` and alert when 80% consumed. Upgrade trigger: when monthly usage consistently exceeds 800 credits for 2+ months, surface recommendation to Eric.
2. **Tavily + Gemini usage dashboard** — Usage metrics should be surfaced in jarvis-app (new tab or section in vitals). Scoped as part of the brain-map kanban phase, not this PRD. For now, JSONL tracking + morning feed mention when approaching limits.

---

Next step: `/implement-prd memory/work/jarvis/PRD_autonomous_loop.md` to execute Sprint 1 through the full BUILD > VERIFY > LEARN loop.
