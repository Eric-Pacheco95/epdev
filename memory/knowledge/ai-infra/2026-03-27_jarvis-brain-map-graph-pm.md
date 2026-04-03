---
domain: ai-infra
source: /research (backfill)
date: 2026-03-27
topic: Jarvis Brain Map — AI-Native Graph Project Management Tool
confidence: 8
source_files:
  - memory/work/jarvis_brain_map/research_brief.md
tags: [react-flow, graph-canvas, project-management, git-native, brain-map, ux]
---

## Key Findings
- No existing tool combines: markdown/git as source of truth, interactive zoomable graph canvas, semantic node typing (TELOS → Goals → Projects → ISC → Tasks), AI gap-closing co-pilot, and write-back to source files
- **React Flow** is the confirmed UI library: 35.6K GitHub stars, 4.59M weekly npm installs, MIT license; Contextual Zoom is a documented built-in pattern using `useStore` hook — nodes read zoom level and render accordingly
- Zoom-layer design: `<0.2` → TELOS+Goals only; `0.2–0.5` → +Projects+Phases; `0.5–0.8` → +ISC nodes (red/green gap edges); `>0.8` → +Tasks with full detail panel
- The closest competitor is Obsidian Canvas + Dataview plugin — power users can approximate a graph over markdown, but no typed semantic nodes, no ISC gap detection, no AI co-pilot
- Market validation: backlog.md went viral on dev.to; Obsidian has millions of users — the "graph over your own files" category has massive PMF; React Flow's install count confirms ecosystem readiness

## Context
The competitive moat rests on five combined capabilities no tool has: parses your files, types nodes semantically, zoom-layer granularity, AI gap-closing co-pilot, and write-back to markdown. The OKR software market is $1B+ globally and none of those tools are git-native or graph-canvas. "Agents are the engineers, humans are the project managers" is an emerging thesis that makes this kind of visual PM tool increasingly valuable.

## Open Questions
- What is the right node type for "learning signal" or "steering rule" — do they belong in the graph?
- Should the write-back be direct file mutation or a proposed diff requiring human approval?
- At what node count does React Flow virtualization become necessary to maintain performance?
