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

Next step: `/implement-prd memory/work/jarvis-app/PRD.md` to execute this PRD through the full BUILD -> VERIFY -> LEARN loop.
