# Technical Research: Jarvis Dashboard UI
- Date: 2026-03-29
- Type: Technical
- Depth: full
- Sources consulted: 18

## What It Is

A local-first dashboard that visualizes the entire Jarvis data layer — heartbeat metrics, signal velocity, agent activity, task status, hooks, settings, and autonomous work results. Reads directly from existing JSON/markdown files on disk. No database. Shareable as a template for other "normal at-home devs."

## How It Works

### Recommended Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 16 (App Router)** | 67% React market share, RSC for server-side file reads, static export option |
| Components | **shadcn/ui** | Copy-paste components, Radix primitives, full control, massive template ecosystem |
| Charts | **Tremor** (Vercel-owned, free) + **Recharts** | Tremor has 300+ dashboard blocks, acquired by Vercel in 2025, now fully open-source |
| Styling | **Tailwind CSS v4** | Standard with shadcn/ui |
| Data layer | **API routes reading local JSON/markdown** | fs.readFile on heartbeat_latest.json, _signal_meta.json, tasklist.md, etc. |
| Desktop (future) | **Tauri** | Rust core, React frontend, secure file system access, ~5MB binary vs 150MB+ Electron |

### Architecture: File-System API Routes

```
Jarvis Dashboard (Next.js)
├── /api/heartbeat     → reads data/heartbeat_latest.json + heartbeat_history.jsonl
├── /api/signals       → reads memory/learning/_signal_meta.json + signals/processed/
├── /api/tasks         → reads orchestration/tasklist.md (parses markdown checkboxes)
├── /api/overnight     → reads data/overnight_state.json + autoresearch reports
├── /api/agents        → reads orchestration/autonomous/dispatch_log.md (future)
├── /api/hooks         → reads .claude/settings.json hooks config
├── /api/skills        → reads .claude/skills/*/SKILL.md metadata
├── /api/config        → reads heartbeat_config.json, sources.yaml, slack-routing.md
└── /api/vitals        → aggregated health score from all above
```

No database. No external services. Each API route does `fs.readFile()` on the existing Jarvis file structure and returns parsed JSON. The frontend polls or uses SWR for refresh.

### Data Flow

```
Jarvis files (JSON/MD) → Next.js API routes → React components → shadcn/ui + Tremor charts
```

For real-time feel: poll every 30s (aligned with heartbeat cadence). No WebSockets needed for a single-user local app.

## Ecosystem

### Free Dashboard Templates Worth Starting From

| Template | Stars | Key Features | Fit for Jarvis |
|----------|-------|-------------|----------------|
| **shadcn-admin** (satnaing) | 6K+ | Sidebar, data tables, auth, dark mode | Best free starting point |
| **next-shadcn-dashboard-starter** (Kiranism) | 2K+ | App Router, charts, responsive | Clean minimal base |
| **Shadboard** | 1K+ | Built-in apps (email, chat, calendar) | Overkill but good reference |
| **Tremor blocks** | 300+ blocks | KPI cards, charts, tables, copy-paste | Perfect for the metrics views |

### Agent Observability Landscape (context, not adoption)

| Tool | Model | Relevance to Jarvis |
|------|-------|-------------------|
| **Langfuse** | MIT, self-hosted, Python/TS SDK | Designed for LLM tracing — overkill for Jarvis's file-based data. But good design reference for trace visualization |
| **Definable** | Self-hosted, zero-config, SSE events | Closest to Jarvis's model (built-in observability, no external deps). Design patterns worth studying |
| **AgentOps** | SaaS, agent-specific | Per-tool analytics and run replay concepts apply to Jarvis dispatcher |
| **Laminar** | Open source, span-tree debugging | Real-time trace visibility during long-running ops — relevant for overnight runner monitoring |

**Key insight**: These tools all assume you're instrumenting an LLM pipeline with spans/traces. Jarvis is simpler — its data already exists as structured files. The dashboard just needs to **read and visualize**, not instrument. Don't adopt any of these; absorb their UI patterns.

## Gotchas & Limitations

1. **Next.js API routes can't watch files** — they respond to requests, not file changes. For "live" feel, use client-side polling (SWR with 30s refresh) or implement a simple file-watcher WebSocket endpoint
2. **Markdown parsing** — tasklist.md needs a markdown parser (remark/unified) to extract checkbox state. Not complex but needs a reliable parser
3. **Path handling on Windows** — API routes using `fs` need Windows-compatible paths. Use `path.join()` everywhere, never hardcode `/`
4. **Static export limitations** — if you want to share as a static build (no Node.js server), API routes won't work. You'd need to pre-generate JSON files instead. For POC, local dev server is fine
5. **Security: never expose .env** — API routes must filter out any credential content before sending to frontend. Apply the same "grep -c only" rule from CLAUDE.md

## Integration Notes: How This Fits Jarvis

### What Already Exists as Structured Data

| Dashboard View | Source File(s) | Format |
|---------------|---------------|--------|
| System Health | `data/heartbeat_latest.json` | JSON with metrics, thresholds, severity |
| Health History | `data/heartbeat_history.jsonl` | JSONL, one snapshot per run |
| ISC Status | `memory/work/isce/heartbeat_latest.json` | JSON with pass/fail counts |
| Signal Velocity | `memory/learning/_signal_meta.json` | JSON with counts and timestamps |
| Task Progress | `orchestration/tasklist.md` | Markdown with `[x]`/`[ ]` checkboxes |
| Overnight Results | `data/overnight_state.json` + run reports | JSON + markdown |
| Skill Registry | `.claude/skills/*/SKILL.md` | Markdown with frontmatter |
| Skill Usage | `data/skill_usage.json` | JSON with invocation counts |
| Hook Config | `.claude/settings.json` | JSON |
| Morning Feed | `memory/work/jarvis/morning_feed/*.md` | Daily markdown files |
| Slack Routing | `memory/work/slack-routing.md` | Markdown table |
| Auth Health | `data/auth_failures.jsonl` | JSONL |
| Notify State | `tools/scripts/.notify_state/*.json` | Daily JSON with caps/dedup |

**Everything the dashboard needs already exists as files.** No new data collection needed for the POC.

### Settings/Config That Could Be Editable

| Setting | File | Edit Complexity |
|---------|------|----------------|
| Heartbeat thresholds | `heartbeat_config.json` | Low — JSON key/value edits |
| Sources list | `sources.yaml` | Medium — YAML structure |
| Slack routing rules | `slack-routing.md` | Low — markdown table |
| Overnight dimensions | `autoresearch_program.md` | Medium — markdown with specific structure |
| Skill enable/disable | Individual SKILL.md files | Low — frontmatter toggle |

For POC: **read-only dashboard first**, settings editing as a Phase 2 feature.

## Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Next.js + shadcn** (recommended) | Shareable, modern, huge ecosystem, React skills transfer | Requires Node.js to run locally | Best balance of POC speed + shareability |
| **Tauri desktop app** | Native desktop, tiny binary, secure fs access | Rust learning curve, harder to share as template | Good for v2 if Eric wants a desktop app |
| **Grafana + file exporters** | Battle-tested dashboards, alerting built in | Overkill infra, not shareable as a simple template, ugly for personal use | Reject — wrong tool |
| **Plain HTML + fetch** | Zero dependencies, simplest possible | No component library, painful to build, hard to maintain | Too primitive |
| **Obsidian plugin** | Eric may already use it, markdown-native | Locked into Obsidian ecosystem, not shareable independently | Reject — platform lock-in |
| **Streamlit (Python)** | Fast to build, data-native | Not shareable as a polished UI, Python not JS, ugly defaults | Reject — not the right audience |

## Open Questions

1. **Where does the dashboard repo live?** Same repo (epdev/ui/) or separate repo? Separate is cleaner for sharing but harder for file access
2. **Auth needed?** For local-only, no. For shareable, basic auth or "private by default" (localhost only)
3. **Settings editing in POC scope?** Read-only is faster. Editing requires careful validation to not corrupt config files
4. **How to handle the Tauri upgrade path?** Next.js can be wrapped in Tauri later — the React components are reusable

## Sources

- shadcn/ui templates: adminlte.io/blog/free-shadcn-admin-dashboards (23 templates compared)
- Tremor blocks: blocks.tremor.so (300+ dashboard components, Vercel-owned)
- Agent observability comparison: agenta.ai/blog/top-llm-observability-platforms
- Langfuse vs LangSmith: huggingface.co/blog/langfuse-vs-langsmith-comparison
- Definable self-hosted agent dashboard: reddit.com/r/LLMDevs (zero-config pattern)
- SitePoint local AI agent tutorial: sitepoint.com (React dashboard + Node.js + local LLM)
- Streakr habit tracker: Tauri + React + JSON file storage pattern
- Next.js 2026 stack guide: builder.io/blog/react-ai-stack-2026
- Shadcnblocks admin: shadcnblocks.com/admin-dashboard (typed JSON data layer with Zod)

## Recommended Next Steps

1. `/first-principles` on dashboard scope — what are the 5 views Eric actually needs daily vs nice-to-have?
2. `/create-prd` for Phase 4F (or new project) — Jarvis Dashboard POC
3. Fork shadcn-admin as starting template, wire up 3 API routes (heartbeat, tasks, signals) as proof of concept
4. `/red-team` the shareable architecture — what breaks when someone else tries to use this with their own AI setup?
