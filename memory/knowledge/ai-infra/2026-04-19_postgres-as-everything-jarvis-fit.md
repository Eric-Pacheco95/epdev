---
domain: ai-infra
source: /research
date: 2026-04-19
topic: Postgres-as-everything — Coding Gopher analysis + Jarvis architecture fit
confidence: 8
source_files:
  - memory/work/postgres-jarvis-migration/research_brief.md
  - https://www.youtube.com/watch?v=TdondBmyNXc
tags: [postgres, pgvector, architecture, migration, hybrid-search, jarvis, jsonb, skip-locked, postgrest, rls]
---

## Key Findings

- **Grep reads markdown directly from the filesystem** — confirmed. Claude Code's Read/Grep/Glob are filesystem-native tools; any "move grep to Postgres" plan either keeps markdown canonical + Postgres as secondary index, or requires rewriting every skill via an MCP wrapper. Full migration is blocked by the harness, not by Postgres capability.
- **Honest architecture = markdown canonical + Postgres derived for Tier 1 (signals, dispatcher, vitals, predictions, vector index)**, rebuildable from the git repo. Preserves "history is sacred" and TELOS filesystem isolation; unlocks structured queries.
- **Five of the Coding Gopher's nine claims map cleanly to Jarvis**: JSONB (signals), SKIP LOCKED (dispatcher), pgvector+HNSW (migrate from ChromaDB), partition+BRIN (signals/vitals), materialized views (rollups). Three don't apply (PostGIS, tsvector-vs-grep loses, RLS-as-backend is wrong for single-user). Actively reject **PostgREST + RLS as backend** — inverts security review surface.
- **Scale trigger met, pain trigger not yet met**: 514 memory files crossed the 400-file revisit threshold set in the 2026-04-02 deferral decision, but no documented grep failures or dispatcher incidents have accumulated. Don't start migration without Tier-1 pain evidence.
- **Cheapest first move when ready**: ChromaDB → pgvector in `embedding_service.py`. Low-risk evaluation of Postgres-on-Windows ergonomics with existing code shape.

## Context

Triggered by The Coding Gopher's 2026-04-16 video "I replaced my entire stack with Postgres" (~300K views, Neon-sponsored, CC Attribution). Eric asked whether Jarvis can migrate most functions to Postgres given planned hybrid grep + vector retrieval. Answer: hybrid (Path B) is the only option that survives `/architecture-review`, because Claude Code's harness is filesystem-native and 49 skills currently rely on Read/Grep. Full migration would require rewriting every skill and losing git-as-history. The 2026-04-02 Phase-6 deferral decision still holds in spirit — hybrid retrieval on the existing ChromaDB stack must ship and accumulate query-pattern data before any DB migration is considered.

## Open Questions

- Is dispatcher pain bad enough to justify Postgres now, or does one more iteration on filesystem-JSON queues buy 3-6 more months?
- Measured win of ChromaDB → pgvector swap: worth the consolidation, or defer until Tier-1 work begins?
- Where does Postgres live — WSL2, Neon free tier, or Windows-native (no `pg_cron`)?
