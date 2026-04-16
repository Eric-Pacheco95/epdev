# PRD: Jarvis App (formerly jarvis-brain-map)

- Status: draft
- Created: 2026-03-30
- Owner: Eric P
- Repo: `jarvis-app` at `C:\Users\ericp\Github\jarvis-app` (GitHub: Eric-Pacheco95/jarvis-app)
- Stack: Next.js 15 + React 19 + TypeScript + React Flow + Tailwind + Zustand
- Depends on: epdev `vitals_collector.py` JSON contract (schema v1.0.0, already shipped)
- Supersedes: `memory/work/jarvis_brain_map/PRD.md` (Phases 1-3 complete, Phase 4+ continues here)

## OVERVIEW

Jarvis App is the unified browser-based interface for the Jarvis AI system. It evolved from jarvis-brain-map (a graph visualization tool) into a multi-view application that surfaces system health, project state, and learning progress. This PRD covers the next phase: completing the Phase 4 drill-down panel, adding a vitals dashboard route that consumes the epdev vitals_collector.py JSON contract, renaming the app identity, and establishing the architecture for future views. The graph canvas remains the primary view; the vitals dashboard is a parallel route, not a replacement.

## PROBLEM AND GOALS

- **No browser-based health view**: Eric checks system health via `/vitals` in the CLI, which requires an active Claude Code session. A persistent browser dashboard provides at-a-glance monitoring without consuming LLM turns.
- **Incomplete drill-down**: Phase 4 (detail panel on node click) is partially built with uncommitted work. Completing it makes the graph interactive rather than view-only.
- **Identity mismatch**: The app is still named `jarvis-brain-map` in package.json, page titles, and config. It needs to reflect the broader "Jarvis App" vision.
- **No unified app shell**: The current app renders a single full-page graph. Multiple views (graph, vitals, future: observability, data layer) need shared navigation and layout.

## NON-GOALS

- Real-time data streaming or WebSocket connections (file reads are sufficient for MVP)
- API server or backend beyond Next.js server-side rendering
- Authentication, multi-user, or cloud deployment
- Full Three.js renderer replacement (Phase 4.5 is progressive CSS enhancement only)
- Editing capabilities (write-back to markdown files) -- read-only through this PRD
- Phase 5 Gap Co-pilot (Jarvis chat panel) -- future PRD
- Phase 6 Packaging (npx distribution) -- future PRD

## USERS AND PERSONAS

- **Eric P (sole user)**: ADHD working style, build-first. Opens the app in a browser tab alongside Claude Code. Wants instant visual feedback on system state. Checks vitals frequently, uses the graph to understand project relationships and find gaps.

## USER JOURNEYS OR SCENARIOS

1. **Morning health check**: Eric opens `localhost:3000/vitals` in his browser. The dashboard shows ISC status, signal velocity, overnight results, threshold crossings, and skill evolution — all from the latest `vitals_latest.json`. No CLI session required.
2. **Graph exploration**: Eric opens `localhost:3000` (graph view). Zooms in on a project, clicks a red ISC node. The detail panel slides open showing the ISC text, source file, and met/open status.
3. **Quick navigation**: Eric uses the top nav bar to switch between Graph and Vitals views. Both load instantly from local data.

## FUNCTIONAL REQUIREMENTS

### App Shell + Identity

- FR-001: App renamed from `jarvis-brain-map` to `jarvis-app` in package.json, page titles, and all user-visible text
- FR-002: Shared layout with top navigation bar providing links between views (Graph, Vitals)
- FR-003: Root route (`/`) renders the existing graph canvas (no behavior change)
- FR-004: Navigation visually indicates the active route

### Phase 4 Completion: Drill-Down Panel

- FR-005: Clicking any node on the graph canvas opens a right sidebar detail panel
- FR-006: Sidebar displays node metadata (type, status, owner, weight) based on node type
- FR-007: Sidebar fetches and displays raw markdown source from the original file via `/api/source`
- FR-008: ISC nodes show met/open status indicator in sidebar

### Vitals Dashboard Route

- FR-009: New route at `/vitals` renders a dashboard consuming `vitals_latest.json`
- FR-010: Dashboard reads JSON from the epdev repo path configured in `brain-map.config.json` (same config pattern used by the parser — add a `vitalsPath` field pointing to `C:\Users\ericp\Github\epdev\data\vitals_latest.json`)
- FR-011: Dashboard displays: system status (HEALTHY/WARN/CRITICAL), ISC met/total/ratio, signal count and velocity, session count, storage size
- FR-012: Dashboard displays: autonomous value rate, TELOS introspection status, skill evolution (active/deprecated/upgrade candidates), unmerged branches
- FR-013: Dashboard displays: threshold crossings with severity badges, collector errors with [DEGRADED] markers
- FR-014: Dashboard shows data freshness indicator (time since `collected_at` timestamp)
- FR-015: Dashboard gracefully handles missing, stale (>24h), or malformed JSON (shows "no data" / "stale data" state, not a crash)

### Config Update

- FR-016: `brain-map.config.json` renamed to `jarvis-app.config.json` with backward-compatible field additions (`vitalsPath`, `securityScanPath` for future use)

## NON-FUNCTIONAL REQUIREMENTS

- Dashboard page load under 500ms (local file read, no network)
- All UI text is ASCII-safe (consistent with epdev convention)
- Responsive layout works at 1280px+ width (Eric's primary monitor)
- No new runtime dependencies beyond what's already in package.json (Tailwind, React, Next.js are sufficient for the dashboard)
- Schema version check: dashboard validates `_schema_version` matches expected version before rendering; mismatch shows warning banner

## ACCEPTANCE CRITERIA

### Sprint 1: App Shell + Vitals Dashboard

- [ ] [E] Package.json name is `jarvis-app` and page title shows "Jarvis App" | Verify: `grep '"name": "jarvis-app"' package.json` and check browser tab title [M]
- [ ] [E] Top navigation bar renders on all routes with Graph and Vitals links | Verify: `npm run dev`, both links visible and clickable on `/` and `/vitals` [M]
- [ ] [E] `/vitals` route renders dashboard with ISC status, signals, storage, autonomous value from JSON | Verify: run `vitals_collector.py --file`, then load `/vitals` in browser, confirm data displays [M]
- [ ] [E] Dashboard shows "No data" state when `vitals_latest.json` is missing | Verify: delete/rename the JSON file, reload `/vitals`, page renders without error [M]
- [ ] [E] Dashboard validates `_schema_version` and shows warning on mismatch | Verify: edit JSON to change version, reload, warning banner appears [M]
- [ ] [R] Existing graph view at `/` is not broken by layout changes | Verify: navigate to `/`, graph renders with zoom and pan working [A]

### Sprint 2: Phase 4 Drill-Down Panel

- [ ] [E] Clicking a node on the graph opens the detail panel sidebar | Verify: click any node, sidebar slides in from right [M]
- [ ] [E] Detail panel shows node metadata matching the node type | Verify: click TELOS node → shows TELOS fields; click ISC → shows met/open status [M]
- [ ] [E] Detail panel displays source markdown from original file | Verify: click node, source text matches actual file content [M]
- [ ] [R] Detail panel does not break zoom-layer behavior | Verify: open panel, zoom in/out, layers still toggle correctly [A]

ISC Quality Gate: PASS (6/6) -- count 6/4 per sprint (within range), single sentence each, state-not-action, binary-testable, anti-criteria present (no regression on graph view, no regression on zoom layers), verify methods specified.

## SUCCESS METRICS

- Vitals dashboard loads and displays current data within 500ms of page open
- Eric uses `/vitals` browser view instead of CLI `/vitals` for daily health checks (qualitative)
- Graph detail panel reduces need to manually open source files (qualitative)
- (to be defined) Time-on-page and view-switch frequency once basic analytics are added

## OUT OF SCOPE

- Write-back to markdown files (edit ISC status, create tasks) -- future PRD
- Three.js particle animations (Phase 4.5) -- separate effort, progressive CSS enhancement first
- Gap Co-pilot chat panel (Phase 5) -- future PRD
- npx packaging (Phase 6) -- future PRD
- Security scan dashboard (future -- `securityScanPath` config reserved but not implemented)
- Observability traces view, data layer view, md file management -- future phases
- Mobile/responsive below 1280px

## DEPENDENCIES AND INTEGRATIONS

- **epdev `vitals_collector.py`**: Produces `data/vitals_latest.json` consumed by the dashboard. Schema contract at `tools/schemas/vitals_collector.v1.json`. Already shipped and stable (Harness Foundation Sprint 1).
- **epdev `security_scan.py`**: Future data source (config field reserved). Already shipped (Harness Foundation Sprint 2).
- **brain-map.config.json** (renamed to jarvis-app.config.json): Config-driven path resolution for both parser (epdev markdown) and vitals (JSON file). Existing pattern, extended with `vitalsPath`.
- **React Flow (@xyflow/react)**: Graph canvas library. Already in dependencies.
- **Tailwind CSS**: Styling. Already in dependencies.

## RISKS AND ASSUMPTIONS

### Risks

- **Config path brittleness**: The app reads files from absolute paths in `jarvis-app.config.json`. If Eric moves the epdev repo, both the graph parser and vitals dashboard break. Mitigated by: config file is the single place to update.
- **Stale data**: `vitals_latest.json` is only updated when `vitals_collector.py --file` runs (manually via `/vitals` or scheduled). The dashboard shows a freshness indicator, but data could be hours old. Future mitigation: add a "refresh" button that shells out to the collector.
- **Phase 4 uncommitted work**: Partially built drill-down panel exists as uncommitted changes. These may need reconciliation with the new layout/nav changes.

### Assumptions

- Eric will run `vitals_collector.py --file` regularly (via `/vitals` skill or scheduled task) to keep the JSON current
- `localhost:3000` is the development URL (no custom port or hosting setup needed)
- The existing parser and graph canvas code is stable and doesn't need refactoring for the nav addition
- Tailwind + React components are sufficient for the dashboard (no chart library needed for MVP)

## OPEN QUESTIONS

- **Chart library**: Should the vitals dashboard include trend charts (heartbeat_trend data)? If yes, need a lightweight chart library (recharts, chart.js). MVP can skip charts and show numeric values only.
- **Auto-refresh**: Should the dashboard poll for file changes, or is manual browser refresh sufficient for MVP?
- **Phase 4 reconciliation**: How much of the existing uncommitted Phase 4 work is usable vs needs reworking for the new layout?

---

# Sprint 3: Dashboard Tab Restructure

- Status: draft
- Created: 2026-03-31
- Depends on: Sprint 1+2 COMPLETE
- Architecture review: PASSED (2026-03-31) -- first-principles + fallacy + red-team + STRIDE
- Design references: `epdev/data/vitals_images/01-09_*.png` (inspiration, not spec)

## OVERVIEW

Restructure the existing flat `/vitals` page into a 4-tab dashboard: Vitals (system health at a glance), Overnight Review (what happened while you slept), Next Steps (prioritized action cards from morning_feed), and Usage (Claude session counts + Gemini API cost tracking). All data pipelines are in place -- `vitals_latest.json` now includes `morning_feed`, `session_usage` (claude/gemini breakdowns), `overnight_deep_dive`, `telos_introspection`, and `external_monitoring`. The existing page's components (StatCard, SectionHead, SparkBars, ProgressBar) are reused and extended with new visualizations.

## PROBLEM AND GOALS

- **Information density without hierarchy**: The current flat page dumps ~15 card groups linearly. With ADHD, scanning a long page to find the 2-3 things that matter produces decision fatigue.
- **No morning review surface**: Overnight results, TELOS contradictions, and external monitoring data exist in vitals_latest.json but are not rendered or are buried at the bottom.
- **No action recommendations**: morning_feed generates prioritized proposals daily, but they only appear in Slack -- not in the dashboard Eric has open all day.
- **No usage visibility**: Eric has no view of how many Claude sessions he runs or how much Gemini API usage costs. Session counts and Gemini token data now flow through the pipeline but have no UI.
- **Goal**: Reduce Eric's morning cognitive load to under 60 seconds by organizing information into purpose-driven tabs that answer: (1) is anything broken? (2) what happened overnight? (3) what should I do? (4) how much am I using?

## NON-GOALS

- Chart library adoption (recharts, chart.js) -- use CSS/Tailwind for all visualizations in this sprint; evaluate chart library need after
- Mobile responsive below 1280px
- Write-back / edit capabilities
- Gemini image generation at runtime (the mockup images are design inspiration only)
- Real-time WebSocket connections
- TELOS radar chart (requires scoring rubric that does not exist yet)

## USERS AND PERSONAS

- **Eric P (sole user)**: ADHD, build-first. Opens `localhost:3000/vitals` as a persistent browser tab. Checks it first thing in the morning and throughout the day. Needs the most important information at the top of whatever tab he's on.

## USER JOURNEYS OR SCENARIOS

1. **Morning check-in**: Eric opens the dashboard. The Vitals tab shows system health ring (green/yellow/red), ISC progress, and key numbers. He clicks "Overnight Review" tab to see what the overnight runner did, any TELOS contradictions, and external news. He clicks "Next Steps" to see 2-3 prioritized actions with context. Total time: under 60 seconds.
2. **Mid-day usage check**: Eric clicks the "Usage" tab to see how many Claude sessions he's run today (27 unique, avg 177 min), Gemini API calls this week (0 calls, $0), and a 7-day session trend sparkline.
3. **Stale data awareness**: If vitals_collector.py hasn't run in >5 minutes, a staleness badge appears on the Vitals tab header. If no overnight run occurred, the Overnight tab shows an informative empty state ("No overnight run detected. Last run: 2 days ago.").

## FUNCTIONAL REQUIREMENTS

### Tab Infrastructure

- FR-100: Tab bar renders at the top of the `/vitals` page with 4 tabs: Next Steps (default), Vitals, Overnight Review, Usage
- FR-101: Active tab is visually indicated; clicking a tab switches content without page reload (client-side state)
- FR-102: Tab selection persists across polls (30s refresh does not reset the active tab)
- FR-103: Tabs are focusable via standard keyboard navigation (semantic HTML buttons provide Tab/Enter/Space for free)

### Tab 1: Next Steps (default landing tab)

- FR-130: Top action cards (max 3) rendered as numbered priority cards with: rank number, title, TELOS alignment tag, description excerpt -- sourced from `morning_feed.proposals`. If more than 3 proposals exist, show top 3 with a "+ N more" badge
- FR-131: Each card uses visual priority indicator: #1 = green accent, #2 = yellow accent, #3 = blue accent (matching mockup image 09)
- FR-132: Morning feed date shown at top ("Proposals for 2026-03-31")
- FR-133: Empty state distinguishes three cases: (a) `morning_feed === null` -> "No morning briefing found." (b) `morning_feed.proposals` is empty -> "Morning feed ran but generated no proposals." (c) proposals exist -> render cards

### Tab 2: Vitals

- FR-110: System health status badge at top (HEALTHY/WARN/CRITICAL/DEGRADED) derived from ISC ratio + error count -- reuses existing colored pill badge (no ring/donut chart)
- FR-111: Primary metrics row: ISC progress (percentage + met/total), signal count with sparkline, open tasks with sparkline, sessions/day
- FR-112: "Days since" staleness badges with documented field mappings: last synthesis = `heartbeat.learning_loop_health.value` (days_since), last security audit = `heartbeat.cloud_audit_recency.value` (days_since), last overnight run = derived from last `overnight_streak[]` entry where status == "ran"
- FR-113: Skill usage horizontal bar chart showing top 10 skills over 30 days (already built, relocate to this tab). Skill evolution (active/deprecated/upgrade_candidates) renders alongside
- FR-114: Autonomous systems section: auto signal rate, producer health, signal volume, learning loop status, autonomous value (rate_pct, acted_on, total, status) -- all already built, relocate
- FR-115: Storage metrics row (already built, relocate)
- FR-116: Collapsed "Details" section for trend averages, health indicators (failure count, security events, tool failure rate, scheduled tasks unhealthy, auth health) -- click to expand
- FR-117: Data freshness badge in tab header showing time since last collection with color coding (green <5min, yellow <30min, red >30min)

### Tab 3: Overnight Review

- FR-120: Overnight run summary card: commit count, files changed, lines added/removed, quality badge, security badge -- sourced from `overnight_deep_dive.branch_stats` and `overnight_deep_dive.log_summary`. Quality/security badges parsed from `log_summary.dimensions` strings (split on ": " to get label and PASS/FAIL status)
- FR-121: Overnight run streak indicator: 7-dot row (green = ran, gray = skipped, red = failed) -- sourced from `overnight_streak` array. Dashboard renders exactly 7 dots: pad with "unknown" if fewer entries, truncate to last 7 if more
- FR-122: Contradictions displayed as alert cards with severity coloring (HIGH=red border, MEDIUM=yellow border) -- sourced from `contradictions_structured` (top-level key, pre-parsed array of `{claim, evidence, severity}`)
- FR-123: Proposals section: numbered list of update proposals ready for review -- sourced from `proposals_structured` (top-level key, pre-parsed array of `{file, change, evidence}`)
- FR-124: External monitoring grid: flexible layout adapting to N categories (currently 5: Anthropic, Claude Code, OpenAI, Krebs, Hacker News) -- sourced from `external_monitoring_structured` (top-level key, pre-parsed array of `{category, items[]}`)
- FR-125: Unmerged branches list with count badge -- sourced from `unmerged_branches`
- FR-126: Empty state when no overnight run occurred: "No overnight run detected. Last run: {date}." with last known run date derived from `overnight_streak`
- FR-127: TELOS introspection summary: coverage_score, staleness_flags, insight_count, contradiction_count -- sourced from `telos_introspection`. Displayed as compact stat row at bottom of tab
- FR-128: "Last overnight run" timestamp shown at top of tab content ("Last run: 7h ago") -- derived from last `overnight_streak[]` entry where status == "ran"

### Tab 4: Usage

- FR-140: Claude session metrics: events today / this week / this month (labeled as "events", not "sessions"), unique sessions, average session duration (minutes) -- sourced from `session_usage.claude` fields `events_today`, `events_week`, `events_month`, `unique_sessions`, `avg_duration_min`
- FR-141: Claude 7-day session trend sparkline -- sourced from `session_usage.claude.daily_trend` (array of `{date, sessions}`)
- FR-142: Gemini API metrics: total calls, total tokens, today/week/month breakdowns -- sourced from `session_usage.gemini`. Note: Gemini sub-object shape differs from Claude (nested `{calls, tokens}` per period)
- FR-143: Empty state for Gemini: "No Gemini API calls tracked yet. Usage will appear after the next analyze_recording.py run."
- FR-144: Days tracked count shown for context ("Tracking since: 2 days ago")
- FR-145: Top tools histogram: ranked horizontal bar chart of tool usage counts (Bash, Read, Edit, etc.) -- sourced from `heartbeat.top_tools`

## NON-FUNCTIONAL REQUIREMENTS

- Tab switching is perceptually instant (no visible loading state or flash) -- client-side state, no re-fetch
- Tab selection persists in `localStorage` to survive browser refresh (cheap alternative to URL routing)
- Polling cadence: Vitals tab polls every 30s (existing behavior); data is shared across all tabs from a single fetch
- All text is ASCII-safe (Windows cp1252 compatibility)
- Works at 1280px+ width
- No new npm dependencies for this sprint

## ACCEPTANCE CRITERIA

### Sprint 3: Tab Restructure

- [x] [E] Tab bar with 4 labeled tabs renders at top of `/vitals` route, switching content on click without page reload | Verify: load `/vitals`, click through all 4 tabs, content changes, no network request fires [M]
- [x] [E] Active tab selection survives 30s poll refresh | Verify: select "Usage" tab, wait 35s, tab remains on "Usage" with updated data [M]
- [x] [E] Morning feed proposals render as numbered priority cards on Next Steps tab | Verify: confirm `morning_feed` exists in vitals JSON, cards display with rank, title, TELOS tag [M]
- [x] [E] Claude session metrics (today/week/month/unique/avg_duration) display on Usage tab | Verify: confirm `session_usage.claude` in JSON, all 5 metrics render with values [M]
- [x] [E] Overnight deep dive data renders on Overnight Review tab with branch stats and quality/security badges parsed from `log_summary.dimensions` strings | Verify: confirm `overnight_deep_dive` in JSON, commit count and PASS/FAIL badges display [M]
- [x] [E] When `morning_feed` is absent from JSON, Next Steps tab shows informative empty state message | Verify: serve JSON without `morning_feed` key, empty state renders [M]
- [x] [R] Existing graph view at `/` is unaffected by tab restructure | Verify: navigate to `/`, graph renders and interacts normally [A]
- [x] [R] No new npm dependencies introduced | Verify: `git diff package.json` shows no dependency additions [M]

ISC Quality Gate: PASS (6/6) -- count 8 (at ceiling), single sentence each, state-not-action, binary-testable, anti-criteria present (graph unaffected, no new deps), verify methods specified.

## SUCCESS METRICS

- Eric uses tab-based dashboard instead of CLI `/vitals` for morning check-in (qualitative)
- Morning review time under 60 seconds (start to "I know what to do next")
- Next Steps tab reduces decision paralysis at session start (qualitative)
- Usage tab provides first-ever visibility into Claude session volume and Gemini API consumption

## OUT OF SCOPE

- Chart library (recharts/chart.js) -- evaluate after this sprint ships
- TELOS radar chart -- needs scoring rubric first
- Learning loop flow diagram -- a status badge suffices for now
- Gemini cost-in-dollars calculation -- show tokens and call counts; dollar estimates require price table maintenance
- Mobile responsive below 1280px
- Write-back / edit capabilities
- Tab URL routing (hash-based or query param) -- `localStorage` persistence is sufficient for single-user use

## DEPENDENCIES AND INTEGRATIONS

- **epdev `vitals_collector.py`** (v1.0.0 schema): Now includes `morning_feed`, `session_usage` (claude + gemini), `overnight_deep_dive`, `telos_introspection`, `overnight_streak`, `external_monitoring_structured`, `contradictions_structured`, `proposals_structured` -- all new fields added 2026-03-31
- **epdev `hook_session_cost.py`**: Produces session_cost events to `history/events/` JSONL -- consumed by `collect_session_usage()` in vitals_collector
- **epdev `analyze_recording.py`**: Now logs `gemini_usage` events to the same JSONL -- consumed by vitals_collector
- **Existing jarvis-app components**: StatCard, SectionHead, SparkBars, ProgressBar -- reused and extended
- **jarvis-app `/api/vitals` route**: Already serves vitals_latest.json -- no changes needed

## RISKS AND ASSUMPTIONS

### Risks

- **Upstream format drift**: Pre-parsed structured data (`external_monitoring_structured`, `contradictions_structured`, `proposals_structured`) depends on upstream markdown format remaining consistent. If the overnight runner or morning_feed changes output format, the vitals_collector parsers may silently produce empty/garbled results. Mitigation: log warnings when parsers produce zero sections from non-empty input.
- **Tab count may grow**: 4 tabs is manageable. If future phases add more (Security, Data Layer, Agents), the tab bar needs a different pattern (sidebar nav, dropdown).
- **Sparse sparkline data**: `heartbeat_trend` may have fewer than 3 data points early on. Sparklines with 1-2 points are not useful. Mitigation: show numeric value only when data points < 3; sparkline is a progressive enhancement.

### Assumptions

- `vitals_collector.py --file` runs at least once before dashboard load (morning_feed and session_usage fields present)
- The 9 mockup images are treated as visual inspiration -- the dashboard does not need to pixel-match them
- Eric prefers tabs over a tiered single page (validated in architecture review discussion)
- No chart library means sparklines and bar charts are built with CSS/Tailwind (feasible for the existing components)

## OPEN QUESTIONS

- ~~**Tab order**~~: RESOLVED -- Next Steps is the default landing tab. Order: Next Steps > Vitals > Overnight Review > Usage.
- ~~**Overnight streak data source**~~: RESOLVED -- build a collector addition that checks `data/logs/` file dates to produce a 7-day streak array.
- ~~**External monitoring parsing**~~: RESOLVED -- pre-parsed in vitals_collector.py into `external_monitoring_structured` (top-level key). Also applied to contradictions (`contradictions_structured`) and proposals (`proposals_structured`). All three are pre-parsed arrays -- frontend is purely a data renderer.

---

Next step: `/implement-prd memory/work/jarvis-app/PRD.md` to execute Sprint 3 through the full BUILD -> VERIFY -> LEARN loop.

---

# Sprint 4: /dashboard — Unified Life View

- Status: draft
- Created: 2026-04-15
- Depends on: Sprints 1+2+3 COMPLETE
- Architecture review: PASSED with corrections (2026-04-15) — `history/decisions/2026-04-15-arch-review-jarvis-app-sprint4.md`
- Phase 4 gate: "Brain-map: all active projects + TELOS goal progress in one view" — satisfied by Projects + TELOS tabs
- Visual reference: Kai/Pulse app (Daniel Miessler) — dark theme, horizontal tab bar, stat cards, icon + label
- Setup prerequisite: Add `## Mission` one-liner to `memory/work/telos/GOALS.md` before implementation (TELOS tab renders this at top)

## OVERVIEW

Sprint 4 adds a new `/dashboard` route to jarvis-app as a peer to `/` (graph canvas) and `/vitals` (ops health) — neither existing route is touched. The route has three client-side tabs: Projects (default), TELOS, and Business. Projects and TELOS satisfy the Phase 4 gate condition by surfacing active project status and TELOS goal progress in a single browser context. The Business tab is a POC showing crypto-bot state and revenue log data; its future role is a cross-project monitoring hub. All new API routes implement the full `/api/source` defense stack. The TELOS route enforces an explicit three-file allowlist, preventing the other 16+ personal files in the TELOS directory from being accessible via the API.

## PROBLEM AND GOALS

- **Phase 4 gate unmet**: No single browser view shows all active projects + TELOS goal progress; Eric must open source files or use CLI for this context
- **Jarvis is tool-mode, not presence-mode**: Sprint 4 begins the shift — dashboard is always-open context, not a thing Eric invokes
- **TELOS goals are invisible during sessions**: Goal weights, status, and active project traces live in markdown; Sprint 4 surfaces them in the browser without an LLM session

## NON-GOALS

- Stubs/placeholders for Health, Finances, Life tabs — deferred until data contracts exist
- Absorption or restructuring of `/vitals` — remains untouched as the ops health view
- Top-level routes per tab (`/work`, `/telos`, `/business`) — client-side tabs only (localStorage pattern from Sprint 3)
- Markdown renderer with HTML output — content renders as plaintext or structured data extraction; `dangerouslySetInnerHTML` is prohibited
- Write-back to any source files — read-only throughout
- Mobile responsive below 1280px
- Authentication or cloud deployment

## USERS AND PERSONAS

- **Eric P (sole user)**: Keeps `/dashboard` as a persistent browser tab alongside Claude Code. Needs active projects and TELOS goals visible at a glance without consuming LLM turns.

## USER JOURNEYS OR SCENARIOS

1. **Project status check**: Eric opens `/dashboard`. Projects tab (default) shows the Active Projects table (project, status, health, next action) from tasklist.md plus open tasks by priority group. crypto-bot health is yellow at a glance.
2. **Goal check-in**: Eric clicks TELOS tab. Mission statement at top (Kai-style), then goals table (G1–G6, weights, status). G4 is "challenged" — visible without opening any file.
3. **Business POC**: Eric clicks Business tab. "API Down" badge is visible (api_reachable: false), P&L $0.00, baseline revenue log entry. Sparse but structural.
4. **Morning routine**: Dashboard is already open. Eric scans Projects tab before starting a Claude Code session — no CLI required, no LLM turn consumed.

## FUNCTIONAL REQUIREMENTS

### Navigation

- FR-200: NavBar adds a third link "Dashboard" — total nav: Graph | Vitals | Dashboard
- FR-201: Dashboard tab state stored at localStorage key `jarvis-dashboard-active-tab` — distinct from `jarvis-vitals-active-tab` (Sprint 3)

### Projects Tab (default)

- FR-210: Projects tab is the default landing tab when `/dashboard` loads
- FR-211: Active Projects table renders rows from tasklist.md `## Active Projects` pipe table (columns: Project, Status, Health, Next Action)
- FR-212: Open Tasks section renders checkbox-list items from tasklist.md `## Open Tasks` section, grouped by their priority subheadings
- FR-213: `/api/tasklist` response includes `task_count` (integer) and `parse_warning` (boolean) — `parse_warning: true` when input file is non-empty but parser produced 0 tasks
- FR-214: If `parse_warning` is true, Projects tab shows "Unable to parse tasks — check tasklist.md format" banner instead of an empty list

### TELOS Tab

- FR-220: TELOS tab renders mission statement from GOALS.md `## Mission` section at the top of the tab before the goals table (Eric adds this line to GOALS.md as Sprint 4 setup)
- FR-221: Goals table renders all rows from GOALS.md goals table (columns: #, Goal, Weight, Status, Metric)
- FR-222: Predictions table renders rows from PREDICTIONS.md pipe table (columns: Date, Prediction, Confidence, Timeframe, Outcome)
- FR-223: `/api/telos` accepts a `file` query parameter and serves only files in the explicit allowlist: `[GOALS.md, PROJECTS.md, PREDICTIONS.md]` — all other filenames return HTTP 403
- FR-224: `/api/telos` logs rejected filename at WARN level in server logs when a non-allowlisted file is requested

### Business Tab (POC)

- FR-230: Business tab reads `data/crypto_bot_state.json` via `/api/business` and renders: API status badge (reachable/down), realized P&L, win rate, drawdown, open/closed trade counts
- FR-231: When `api_reachable: false`, Business tab shows a prominent "API Down" badge alongside (not instead of) numeric fields
- FR-232: Business tab reads `data/revenue_log.jsonl` via `/api/business` and renders the most recent entry (date, substack_revenue, crypto_pnl, notes)
- FR-233: Business tab shows "No revenue data" state when `revenue_log.jsonl` is absent or empty

### Security (all new routes)

- FR-240: All new API routes (`/api/tasklist`, `/api/telos`, `/api/business`) implement path traversal guard — `path.resolve(rootDir, ...segments)` result checked with `startsWith(rootDir + path.sep)` before any file read
- FR-241: All new API routes implement symlink escape guard — `fs.realpathSync()` result re-checked against root before serving
- FR-242: All new API routes cap response at 1MB — files exceeding this return HTTP 413

## NON-FUNCTIONAL REQUIREMENTS

- Dashboard page load under 500ms (local file reads, no network calls)
- Tab switching is perceptually instant — client-side state only, no re-fetch on tab switch
- All text is ASCII-safe (Windows cp1252 compatibility)
- Works at 1280px+ width
- No new npm dependencies
- `dangerouslySetInnerHTML` is not used in any Sprint 4 component

## ACCEPTANCE CRITERIA

### Sprint 4: /dashboard Unified Life View

- [x] [E] `/dashboard` route is reachable via NavBar "Dashboard" link and renders a page with a tab bar | Verify: `curl -s http://localhost:3002/dashboard | grep -c "Projects"` returns ≥ 1 [M] | model: haiku | Evidence: returns 1
- [x] [E] Projects tab (default) renders Active Projects table rows matching tasklist.md `## Active Projects` pipe table | Verify: API returns 3 projects matching tasklist.md Active Projects table [M] | model: sonnet | Evidence: /api/tasklist projects: 3, parse_warning: false
- [x] [E] TELOS tab goals table renders all rows from GOALS.md goals table with goal name, weight, and status | Verify: rendered goal row count matches `grep -c "^| [0-9]" memory/work/telos/GOALS.md` [M] | model: sonnet | Evidence: API goals: 7, file goals: 7
- [x] [E] TELOS tab renders mission statement from GOALS.md `## Mission` section above the goals table | Verify: load TELOS tab, confirm mission text block appears in DOM before goal rows [M] | model: sonnet | Evidence: mission extracted: "Build an AI-augmented life..."
- [x] [E] Business tab renders API status badge and P&L from `data/crypto_bot_state.json`; shows "API Down" badge when `api_reachable` is false | Verify: load Business tab with current data, confirm "API Down" badge visible and P&L renders as $0.00 [M] | model: sonnet | Evidence: apiReachable: false, pnl: 0, status: ok
- [x] [R] `/api/telos` returns HTTP 403 for any filename not in {GOALS.md, PROJECTS.md, PREDICTIONS.md} | Verify: `curl .../api/telos?file=BELIEFS.md` → 403 [M] | Evidence: HTTP 403 PASS
- [x] [R] `/api/tasklist`, `/api/telos`, `/api/business` each return HTTP 403 for path traversal attempts | Verify: URL-encoded traversal and non-allowlist filenames → 403 [M] | Evidence: WISDOM.md → 403, URL-encoded `..%2F..%2F` → 403, both PASS
- [x] [R] Routes `/` and `/vitals` are not modified by Sprint 4 | Verify: `git diff --exit-code src/app/page.tsx src/app/vitals/` exits 0 [A] | Evidence: git diff exit 0, PASS

ISC Quality Gate: PASS (6/6) — count 8 (at ceiling), single sentence each, state-not-action, binary-testable, anti-criteria present (criteria 6, 7, 8 — each with explicit test commands that exit nonzero on violation), verify methods specified.

## SUCCESS METRICS

- Phase 4 gate satisfied: active projects + TELOS goals visible in browser without CLI session
- Eric opens `/dashboard` before starting daily sessions (qualitative)
- Business tab POC is in place for future data enrichment (structural — not measured)

## OUT OF SCOPE

- Health, Finances, Life tabs — deferred until data contracts defined
- Chart library (recharts/chart.js) — evaluate after Sprint 4 ships
- TELOS radar chart — needs scoring rubric first
- Write-back / edit capabilities
- Tab URL routing (hash-based) — localStorage persistence is sufficient for single-user use

## DEPENDENCIES AND INTEGRATIONS

- **`orchestration/tasklist.md`**: Source for Projects tab (Active Projects table + Open Tasks). No schema version — parser must degrade gracefully on format change and emit `parse_warning`.
- **`memory/work/telos/GOALS.md`** (requires `## Mission` line added before Sprint 4 build): Source for TELOS mission + goals table
- **`memory/work/telos/PROJECTS.md`**: Source for TELOS active projects trace
- **`memory/work/telos/PREDICTIONS.md`**: Source for TELOS predictions table
- **`data/crypto_bot_state.json`**: Source for Business tab — crypto-bot P&L and status
- **`data/revenue_log.jsonl`**: Source for Business tab — Substack revenue baseline
- **`jarvis-app.config.json`**: Config-driven path resolution (same pattern as Sprint 1/vitals)
- **Existing jarvis-app components**: StatCard, SectionHead — reused from Sprint 3

## RISKS AND ASSUMPTIONS

### Risks

- **tasklist.md format drift**: File is manually maintained with no schema version. Parser producing zero tasks from non-empty input is indistinguishable from empty backlog — mitigated by `parse_warning` field in API response and banner in UI.
- **TELOS allowlist enforcement**: If `/api/telos` route is implemented without the allowlist check, all 19+ personal files in `memory/work/telos/` become API-accessible. Mitigated by explicit ISC criterion 6 with a test command that exits nonzero on failure.
- **Business tab permanent sparseness**: `crypto_bot_state.json` is currently all zeros (API down). If crypto-bot remains down, this tab shows only "API Down" indefinitely. This is a POC — acceptable for Sprint 4.

### Assumptions

- Eric adds a `## Mission` line to `memory/work/telos/GOALS.md` before implementation begins
- `jarvis-app.config.json` already has `epdevRoot` pointing to the epdev repo (same config used by vitals)
- No chart library needed — stat cards and pipe tables rendered as structured components are sufficient for POC

## OPEN QUESTIONS

- **PROJECTS.md in TELOS tab**: Should the active projects from PROJECTS.md render on the TELOS tab (showing goal traces), or is the projects table in the Projects tab sufficient? Suggest deferring to Sprint 5 to keep TELOS tab focused on goals + predictions.
- **Business tab future scope**: When `data/financial/snapshot.jsonl` ships (separate backlog item), does it fold into Business tab or get its own Finances tab? Decision deferred — no action in Sprint 4.

---

Next step: `/implement-prd memory/work/jarvis-app/PRD.md` — target Sprint 4 section.
