---
domain: ai-infra
source: /research (backfill)
date: 2026-03-29
topic: Jarvis Dashboard UI — Local-First Data Visualization Stack
confidence: 8
source_files:
  - memory/work/jarvis-dashboard/research_brief.md
tags: [dashboard, nextjs, shadcn, tremor, local-first, file-based, ui]
---

## Key Findings
- Recommended stack: **Next.js 16 (App Router)** + **shadcn/ui** + **Tremor** (300+ dashboard blocks, acquired by Vercel 2025, fully open-source) + **Tailwind CSS v4**; data layer = API routes doing `fs.readFile()` on existing Jarvis JSON/markdown files — no database, no external services
- Architecture: each API route (`/api/heartbeat`, `/api/signals`, `/api/tasks`, `/api/overnight`, etc.) reads one Jarvis file and returns parsed JSON; frontend polls with SWR at 30s refresh intervals aligned with heartbeat cadence
- Best free starting templates: **shadcn-admin** (6K+ stars, sidebar/data tables/dark mode) and **Tremor blocks** (300+ copy-paste KPI cards, charts, tables)
- Future desktop option: **Tauri** (Rust core, React frontend, ~5MB binary vs 150MB+ Electron, secure filesystem access)
- Key Windows gotcha: API routes using `fs` must use `path.join()` everywhere — never hardcode `/`; also never expose `.env` content through API routes (apply grep -c rule)

## Context
The dashboard reads the existing Jarvis file structure rather than instrumenting an LLM pipeline with spans/traces — this is the key architectural distinction from tools like Langfuse, AgentOps, and Laminar. Those tools' UI patterns are worth absorbing but not adopting. The `security/` API route must filter credential content before sending to frontend. For a POC, local dev server is sufficient; static export requires pre-generating JSON files since API routes need a Node.js server.

## Open Questions
- Should the dashboard have a write path (e.g., promote a signal, approve a task) or remain read-only?
- What is the right polling interval when the heartbeat collector runs every 30s — match exactly or use 60s?
- When does the dashboard move from local dev server to Tauri desktop app?
