# PRD: Jarvis Operational Hub — Data Layer + Dashboard + Autonomous Dispatcher

> **Project:** jarvis-brain-map (dashboard) + epdev (dispatcher, data layer)
> **Status:** planning
> **Companion:** `orchestration/tasklist.md` Phase 4E + new phases; `memory/work/jarvis-dashboard/research_brief.md`
> **Analysis inputs:** /first-principles analysis, /find-logical-fallacies analysis, /research technical brief (2026-03-29)

## OVERVIEW

Evolve the jarvis-brain-map from a graph visualization into the full Jarvis operational hub — a local-first dashboard where Eric can see system health, understand how files influence Jarvis's thinking, edit steering rules and configuration, and monitor autonomous agent activity. Paired with an autonomous task dispatcher that works the backlog continuously using a three-layer architecture (sense/decide/act). The data layer (Phase 4E) must be completed first as the foundation both systems consume.

## PROBLEM AND GOALS

- **Eric can't see Jarvis holistically** — /vitals is CLI-only, heartbeat is Slack alerts, brain-map is a graph with no operational context. No single place shows: what's healthy, what's broken, what happened overnight, what needs human input
- **Jarvis doesn't work the backlog autonomously** — 50+ unchecked tasks sit idle between sessions. The overnight runner improves code quality but doesn't complete tasklist items
- **The data layer has known gaps** — signal lineage is incomplete, heartbeat history grows unbounded, FTS index has path mismatches, no trend detection. Building a dashboard on a broken foundation creates false confidence
- **Jarvis's decision-making is opaque** — Eric can't see which steering rules influenced a decision, how a signal became a synthesis theme, or why a skill was invoked. The "translate" layer that explains causation doesn't exist
- **Configuration requires file editing** — changing heartbeat thresholds, Slack routing, or steering rules means finding and editing raw files. A UI with validation would prevent config corruption and make the system accessible to other users

## NON-GOALS

- No cloud deployment — local-first, localhost only for POC
- No database — file-system backed, reads existing Jarvis JSON/markdown
- No real-time streaming — 30s polling is sufficient for single-user local app
- No auth system for POC — localhost binding provides implicit security
- No mobile dashboard — desktop browser only for now
- No autonomous tasklist writes — agents never check items in tasklist.md (graduated trust, Stage 1 only)
- Not replacing the brain-map graph — the graph remains, dashboard views are added alongside it

## USERS AND PERSONAS

- **Eric (primary)** — Solo developer operating Jarvis. Needs: "show me everything at a glance, let me drill into details, let me edit config without finding files"
- **Future shareable users** — Other developers building personal AI infrastructure. Needs: fork the repo, point at their own file structure, get a working dashboard. Config-driven, no hardcoded paths

## USER JOURNEYS OR SCENARIOS

1. **Morning review (daily, 5 min):** Eric opens dashboard → sees overnight results (dispatcher completed 2 tasks, autoresearch ran scaffolding dimension) → sees 1 item "ready for review" → clicks to see diff → approves merge → checks task in tasklist → sees health is green → done
2. **Deep dive (ad-hoc):** Eric notices signal velocity spiked → clicks into signal timeline chart → sees autonomous producer generated 15 signals in one run → drills into the synthesis that consumed them → sees a proposed steering rule → edits the rule text in the dashboard → saves → rule is live
3. **Configuration change:** Eric wants to adjust heartbeat thresholds → opens config panel → sees current thresholds with explanations → changes `crit_above` for `auth_health` from 1 to 0 → validation warns "value 0 means healthy state triggers CRIT, are you sure?" → Eric corrects to 2 → saves → heartbeat_config.json updated
4. **Understanding causation:** Eric clicks on a steering rule in CLAUDE.md → dashboard shows: "This rule was proposed by synthesis 2026-03-28, which synthesized signals X, Y, Z from sessions on 2026-03-27. The triggering failure was: sed corrupted research skill."

## FUNCTIONAL REQUIREMENTS

### Phase 1: Data Layer Foundation (4E completion — epdev repo)

> Complete Phase 4E items that gate all downstream work. Without these, the dashboard visualizes broken data and the dispatcher produces unbounded output.

- FR-001: **Signal lineage index** — After each `/synthesize-signals` run, append JSONL records to `memory/learning/signal_lineage.jsonl` mapping signal filenames to synthesis docs. Enables reverse-lookup for the "translate" layer
- FR-002: **Heartbeat trend detection** — Implement 3-5 run moving average in `diff_snapshots()`. New severity level: `TREND_WARN` when metric is within thresholds but consistently degrading. Dashboard charts depend on this for meaningful time-series
- FR-003: **Heartbeat history rotation** — Implement `raw_days` retention from config. Rotate `heartbeat_history.jsonl` entries older than threshold to gzipped monthly archives. Dashboard loads history; unbounded file = slow/broken dashboard
- FR-004: **Reporting dashboard data contract** — Define JSON schema emitted by heartbeat for dashboard consumption: signal velocity, synthesis frequency, event volume, FTS index size, retention status, trend data. Write schema to `data/dashboard_contract.json`
- FR-005: **FTS index path fix** — Fix `jarvis_index.py` heartbeat path constant (`data/logs/` → `memory/work/isce/`). Validate indexes all signal sources. Dashboard search depends on FTS
- FR-006: **Delta thresholds in config** — Support `delta_above`/`delta_below` in heartbeat threshold dict for ramp detection. Enables trend alerting in dashboard
- FR-007: **Autonomous signal volume monitoring** — `autonomous_signal_rate` collector in heartbeat. Alert if `Source: autonomous` signals exceed daily cap. Gates the dispatcher — without this, autonomous agents could flood the pipeline

### Phase 2: Dashboard Core (jarvis-brain-map repo)

> Add operational panels alongside the existing graph. The brain-map becomes the "Understand" layer; the dashboard panels become the "Operate" layer.

- FR-100: **Navigation shell** — Add sidebar navigation to brain-map: Graph (existing) | Dashboard | Tasks | Agents | Settings. Uses shadcn/ui sidebar component
- FR-101: **System health panel** — KPI cards showing: ISC pass ratio, signal count, test health, auth health, heartbeat status (last run time, severity). Source: `/api/heartbeat` reading `heartbeat_latest.json`
- FR-102: **Health timeline chart** — Line/area chart showing metric trends over time. Source: `/api/heartbeat/history` reading `heartbeat_history.jsonl`. Tremor chart components. Uses trend data from FR-002
- FR-103: **Task progress panel** — Parses `orchestration/tasklist.md`, shows phase completion percentages, unchecked items grouped by tier, progress bars. Source: existing tasklist parser (already built in brain-map)
- FR-104: **Signal velocity panel** — Chart showing signals written over time, synthesis runs, signal-to-synthesis ratio. Source: `/api/signals` reading `_signal_meta.json` + lineage index from FR-001
- FR-105: **Skill usage panel** — Table showing invocation counts per skill, tier classification, zero-invocation highlights. Source: `/api/skills` reading `data/skill_usage.json`
- FR-106: **Overnight results panel** — Shows last overnight runner result: dimension, baseline→final, kept/discarded, branch name, quality gate status. Source: `/api/overnight` reading `data/overnight_state.json` + run reports
- FR-107: **Morning feed viewer** — Renders latest morning feed markdown. Source: `/api/feed` reading `memory/work/jarvis/morning_feed/*.md`
- FR-108: **New parsers for brain-map** — Add parsers for: heartbeat config, steering rules (CLAUDE.md AI Steering Rules section), hooks (.claude/settings.json), slack routing, overnight state. These appear as new node types in the graph AND power dashboard panels

### Phase 3: Translate and Edit Layer (jarvis-brain-map repo)

> The layer that explains "what does this file do and how does it influence Jarvis?" and lets users edit configuration through the UI.

- FR-200: **Node annotations** — Each node type in the brain-map gets a human-readable explanation panel: "This is a steering rule. It was added on [date] from [synthesis]. It tells Jarvis to [behavior]. It applies when [context]." Driven by metadata in the node + lineage index
- FR-201: **Causation chains** — Click any node → see its upstream/downstream chain. Example: Failure → Synthesis Theme → Proposed Steering Rule → CLAUDE.md entry. Uses edge types already defined in brain-map (triggers, aggregates, produces)
- FR-202: **Steering rule editor** — View all AI Steering Rules from CLAUDE.md in a list. Each rule shows: text, origin (manual/synthesis), date added. Click to edit in a textarea with markdown preview. Save writes back to CLAUDE.md at the correct location. Validation: rule must be non-empty, must not duplicate existing rules
- FR-203: **Heartbeat config editor** — Form UI for `heartbeat_config.json`. Each collector shows: name, type, thresholds, ISC reference. Edit thresholds with validation (e.g., "crit_above must be > 0 for auth_health"). Save writes JSON
- FR-204: **Skill prompt viewer/editor** — View SKILL.md content for any skill. Edit mode allows plain-text changes. Save writes back to the SKILL.md file. Read-only view shows: discovery metadata, chain relationships, invocation count
- FR-205: **Slack routing editor** — View/edit `slack-routing.md` as a structured table. Add/remove routing rules. Validation ensures channel IDs are present
- FR-206: **Overnight program editor** — View/edit `autoresearch_program.md` dimensions. Toggle enable/disable, adjust iterations, edit metric commands (validated against safe-prefix list from overnight_runner.py)

### Phase 4: Autonomous Dispatcher (epdev repo)

> Three-layer architecture: SENSE (heartbeat, unchanged) → DECIDE (dispatcher.py) → ACT (worker agents in worktrees). Graduated trust model.

- FR-300: **Dispatcher script** — `tools/scripts/dispatcher.py`. Runs every 30-60 min via Task Scheduler. Reads heartbeat state + tasklist. Classifies autonomous-eligible items. Respects budget (daily cap, quiet hours, active-session detection). Writes to dispatch log
- FR-301: **Task taxonomy** — Define autonomous eligibility criteria per task type. Tasks must be tagged `[auto]` by Eric to be eligible. Taxonomy includes: unblocked (no dependencies on unchecked items), well-defined (has verification command), no human judgment needed (not architecture/design decisions), small scope (estimatable as single-agent work)
- FR-302: **Agent prompt template** — Self-contained prompt with embedded guardrails for worker agents. Includes: task description, worktree path, branch name, security constraints, directory map, verification commands. No CLAUDE.md dependency — quality comes from narrow scope + external gate
- FR-303: **Worker agent execution** — Dispatcher spawns `claude -p` in a git worktree. One agent at a time (MAX_CONCURRENT=1). 10-minute timeout. Agent writes AGENT_RESULT.md on completion
- FR-304: **Quality gate on agent output** — Dispatcher runs quality checks post-agent: diff size check, test execution, file-existence verification. Pass → mark READY in dispatch log. Fail → mark FAILED, log reason, discard worktree
- FR-305: **Dispatch log** — `orchestration/autonomous/dispatch_log.jsonl`. One entry per dispatch: task, agent branch, status (dispatched/completed/failed/ready/merged/rejected), timestamps, quality gate result. Dashboard reads this for the agent activity panel
- FR-306: **Budget controls** — MAX_DAILY_DISPATCHES=5, QUIET_HOURS=(9,23) (don't compete with Eric's sessions), active-session detection (check for running claude processes). Start conservative, tune based on real data
- FR-307: **Morning feed integration** — Enhance `morning_feed.py` to read dispatch log and add "Autonomous Work" section: items completed, items ready for review, items failed

### Phase 5: Dashboard Agent Activity Panel (jarvis-brain-map repo)

> Connect the dispatcher output to the dashboard UI.

- FR-400: **Agent activity panel** — Shows dispatch log: recent dispatches with status badges (dispatched/completed/failed/ready/merged). Click to expand: see agent branch, diff summary, quality gate result, AGENT_RESULT.md content
- FR-401: **Review and merge UI** — For READY items: show diff, allow Eric to approve (merge branch to main) or reject (discard). On approve: update dispatch log status, prompt tasklist checkbox update
- FR-402: **Compute budget display** — Shows: daily dispatches used/remaining, quiet hours schedule, last dispatch time, success/failure rate over 7 days

## NON-FUNCTIONAL REQUIREMENTS

- NFR-001: **File-system only** — No database, no external services. All data from existing Jarvis JSON/markdown files
- NFR-002: **Config-driven paths** — All file paths read from `brain-map.config.json`. No hardcoded paths. Other users can point to their own directory structure
- NFR-003: **Dashboard loads in <2s** — API routes should respond within 500ms. Use SWR with stale-while-revalidate for perceived instant loads
- NFR-004: **Security: never expose secrets** — API routes must filter .env content, API keys, tokens before sending to frontend. Apply redaction layer
- NFR-005: **Windows compatible** — All file paths use `path.join()`. No Unix-only assumptions. Task Scheduler for dispatcher
- NFR-006: **Shareable template** — Another developer can: clone repo, edit config.json to point at their directory, run `npm run dev`, see their own dashboard. Include `.example` config and setup docs
- NFR-007: **Dispatcher compute budget** — Never exhaust Claude Max quota such that Eric can't use Claude Code interactively. Interactive sessions have absolute priority

## ACCEPTANCE CRITERIA

### Phase 1: Data Layer
- [ ] Signal lineage JSONL appended after each synthesis run | Verify: `jq` query returns synthesis doc for any given signal filename [E] [M]
- [ ] Heartbeat trend detection shows TREND_WARN for 3+ consecutive degrading runs | Verify: unit test with synthetic history [E] [M]
- [ ] Heartbeat history rotates entries >90 days | Verify: run rotation, confirm old entries archived [E] [M]
- [ ] Dashboard data contract JSON schema exists and heartbeat emits it | Verify: schema file exists, heartbeat output matches schema [E] [M]
- [ ] FTS index returns results for signals in all source directories | Verify: `jarvis_index.py search` finds content from processed/ [E] [M]
- [ ] Delta thresholds trigger on ramp detection | Verify: unit test with increasing metric values [E] [M]
- [ ] Autonomous signal rate collector alerts above daily cap | Verify: unit test with high signal count [E] [M]

### Phase 2: Dashboard Core
- [ ] Brain-map has sidebar navigation with Graph/Dashboard/Tasks/Agents/Settings | Verify: navigate between views [E] [A]
- [ ] Health panel shows live heartbeat data with KPI cards | Verify: change heartbeat_latest.json, refresh, see update [E] [M]
- [ ] Health timeline chart renders 7 days of history | Verify: visual inspection with real data [E] [M]
- [ ] Task panel shows phase completion percentages matching tasklist.md | Verify: cross-reference with manual count [E] [M]
- [ ] Signal velocity chart shows signals over time | Verify: matches _signal_meta.json counts [E] [M]
- [ ] Skill usage table matches /vitals output | Verify: compare side-by-side [E] [M]

### Phase 3: Translate and Edit
- [ ] Clicking any node shows human-readable explanation of its role | Verify: 3 different node types tested [E] [A]
- [ ] Causation chain navigable from failure → synthesis → steering rule | Verify: trace one real chain end-to-end [E] [A]
- [ ] Steering rule edits persist to CLAUDE.md correctly | Verify: edit rule in UI, read CLAUDE.md, confirm change [E] [M]
- [ ] Heartbeat config edits validate before saving | Verify: try invalid value (crit_above: 0 for auth), get warning [E] [M]
- [ ] Skill prompt edits persist to SKILL.md | Verify: edit in UI, read file, confirm [E] [M]

### Phase 4: Autonomous Dispatcher
- [ ] Dispatcher runs on schedule, identifies eligible tasks | Verify: dry-run mode shows what it would dispatch [E] [M]
- [ ] Worker agent completes a task in worktree without touching main tree | Verify: git status on main shows no changes during agent run [E] [M]
- [ ] Quality gate rejects a bad agent output | Verify: intentionally bad diff is caught [E] [M]
- [ ] Dispatch log records all dispatches with correct status transitions | Verify: `jq` query on dispatch_log.jsonl [E] [M]
- [ ] Budget controls prevent dispatch during quiet hours and over daily cap | Verify: run during quiet hours, confirm skip [E] [M]
- [ ] Morning feed includes autonomous work section | Verify: check Slack after dispatcher has completed work [E] [M]

### Phase 5: Agent Activity Panel
- [ ] Dashboard shows dispatch log with status badges | Verify: visual inspection with real dispatch data [E] [M]
- [ ] Review UI shows diff for READY items | Verify: approve one item, confirm branch merged [E] [M]
- [ ] Compute budget display matches dispatcher state | Verify: compare UI with dispatch_log.jsonl [E] [M]

## SUCCESS METRICS

- Eric's morning review takes <5 minutes using dashboard instead of checking Slack + CLI + files separately
- Autonomous dispatcher completes 2-3 tasks/week with zero rollbacks after first month
- At least one other developer can fork the repo and get a working dashboard for their own setup within 30 minutes
- Signal-to-steering-rule causation chain is navigable for 80%+ of steering rules (those that originated from synthesis)
- Config changes via dashboard UI produce zero file corruption incidents

## OUT OF SCOPE

- Cloud hosting / deployment (local only)
- Mobile-responsive dashboard (desktop browser)
- Multi-user collaboration / auth
- Autonomous dispatcher Stage 2/3 (auto-merge, tasklist writes) — Stage 1 only in this PRD
- Tauri desktop app wrapper (future, after web dashboard is solid)
- Obsidian integration (evaluated, deferred — dashboard serves the same need with more control)

## DEPENDENCIES AND INTEGRATIONS

- **jarvis-brain-map repo** — Phases 2, 3, 5 build here. Existing: 7 parsers, 11 node types, React Flow, Next.js 15, Tailwind, zustand, dagre
- **epdev repo** — Phases 1, 4 build here. Existing: heartbeat, overnight runner, morning feed, tasklist, all data files
- **shadcn/ui** — New dependency for dashboard components (sidebar, cards, tables, forms). Add to brain-map repo
- **Tremor** — New dependency for chart components (line charts, area charts, KPI cards). Add to brain-map repo
- **brain-map.config.json** — Must be extended with paths to all new data sources (heartbeat, dispatch log, overnight state, etc.)
- **Claude Max** — Dispatcher uses `claude -p` for worker agents. Compute budget is a hard constraint

## RISKS AND ASSUMPTIONS

### Risks
- **Claude Max compute budget unknown** — No empirical data on daily `claude -p` capacity. Dispatcher caps at 5/day but the real limit may be lower. Mitigation: measure before increasing caps
- **File write races** — Dashboard editing config files while heartbeat reads them. Mitigation: atomic writes (write to .tmp, rename) + file locking for critical configs
- **Tasklist parser fragility** — The brain-map tasklist parser depends on exact markdown format. If someone changes tasklist structure, parser breaks. Mitigation: parser tests with snapshot fixtures
- **Scope creep into Phase 5** — Dashboard + dispatcher could expand into full behavioral change system. Mitigation: strict non-goals, Phase 5 is explicitly out of scope
- **Agent quality without skills/hooks** — Worker agents have no CLAUDE.md, no hooks. Mitigation: self-contained prompts with embedded guardrails + external quality gate

### Assumptions
- Eric has Claude Max subscription for the duration of development and autonomous operation
- The existing brain-map architecture (React Flow + Next.js) can accommodate dashboard panels without major refactoring
- 30-second polling provides sufficient "real-time feel" for a single-user local dashboard
- The existing 13 Jarvis data files cover the dashboard's initial data needs without new collection mechanisms

## OPEN QUESTIONS

1. **Phase 1 → 2 sequencing**: Can some Phase 2 panels be built in parallel with Phase 1, using whatever data exists? (e.g., task panel doesn't depend on 4E items)
2. **shadcn/ui version**: Brain-map currently uses Tailwind 4. Need to verify shadcn/ui v4 compatibility or pin to Tailwind 3
3. **Config editing safety**: Should edits require a "confirm" step that shows the diff before writing? Or is inline validation sufficient?
4. **Dispatcher Task Scheduler slot**: Which time slot? Between heartbeat runs (every 30 min) or on its own cadence?
5. **Cross-repo data access**: Brain-map reads epdev files via `brain-map.config.json` rootDir. Will this work cleanly for dispatch_log.jsonl and other new files?
6. **Compute budget measurement**: Before enabling the dispatcher, should we run a 1-week measurement of Claude Max capacity under current usage (heartbeat + overnight + morning feed + interactive sessions)?

---

## Phase Summary

| Phase | Location | Dependency | Estimated ISC Count |
|-------|----------|------------|-------------------|
| 1: Data Layer | epdev | None (existing 4E items) | 7 |
| 2: Dashboard Core | jarvis-brain-map | Phase 1 (partially) | 6 |
| 3: Translate & Edit | jarvis-brain-map | Phase 2 + Phase 1 (lineage) | 5 |
| 4: Dispatcher | epdev | Phase 1 (signal monitoring) | 6 |
| 5: Agent Activity Panel | jarvis-brain-map | Phase 4 | 3 |

**Implementation order:** Phase 1 first (data foundation). Phases 2 and 4 can partially overlap. Phase 3 after Phase 2 shell exists. Phase 5 after Phase 4 has real dispatch data.

---

Next step: `/implement-prd` to execute this PRD through the full BUILD → VERIFY → LEARN loop. Recommend starting with Phase 1 (data layer) since it unblocks everything else and maps directly to existing 4E tasklist items.
