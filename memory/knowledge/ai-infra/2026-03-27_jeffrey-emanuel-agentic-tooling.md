---
domain: ai-infra
source: /research (backfill)
date: 2026-03-27
topic: Jeffrey Emanuel's Agentic Tooling — Value Assessment for Jarvis
confidence: 8
source_files:
  - memory/work/emanuel_tools/research_brief.md
tags: [agentic-tools, security-validator, meta-skill, cass, session-search, multi-agent]
---

## Key Findings
- Of Emanuel's 8 major tools, only 3 deliver immediate ROI for Jarvis; the rest are multi-agent infrastructure relevant only when running parallel Claude Code sessions
- **dcg (Destructive Command Guard)**: Rust binary, SIMD-accelerated, 49+ security packs — covers gaps Jarvis's `validate_tool_use.py` misses (git reset --hard, inline script AST scanning, database/cloud commands); requires WSL on Windows so the better move is extracting dcg's pattern list into the existing Python validator
- **meta_skill**: SQLite + Git persistence, BM25 + semantic search, MCP server for skill discovery, Thompson sampling bandit for adaptive suggestions — high value but timing-sensitive; the flat CLAUDE.md registry becomes a bottleneck at 50-75+ skills; the YAML frontmatter metadata format is worth adopting NOW for seamless future migration
- **CASS (Session Search)**: Indexes conversation history from 11+ AI providers into a unified searchable timeline with sub-60ms queries; Windows support via Scoop; fills the gap that Jarvis has no cross-session search at all
- Emanuel's *patterns* (planning documents, skill management, session memory) are more valuable to extract than his *tools*, which assume Linux + tmux + agent swarms

## Context
Emanuel runs a 52+ agent farm spending ~$12K/month on AI coding subscriptions with 85K+ GitHub contributions in the past year. His tooling solves coordination problems at that scale. For Jarvis (single-agent evolving toward Phase 4 autonomy), the immediate actions are: (1) extract dcg's blocked patterns for git destructive commands and add to `validate_tool_use.py`, (2) add YAML frontmatter metadata to SKILL.md files, (3) evaluate CASS for cross-session search after Phase 3.

## Open Questions
- At what skill count (50? 75?) does meta_skill's MCP-based discovery become necessary?
- Can CASS run passively in the background without affecting session performance?
- Which specific dcg security packs have the highest hit rate in practice?
