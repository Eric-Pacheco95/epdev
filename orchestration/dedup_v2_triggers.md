# Memory Dedup v2 — Trigger-Gated Backlog

> DO NOT PRE-BUILD. Each item activates only when its named trigger condition is met.
> Source: `memory dedup v1` shipped 2026-04-07 (architecture review + 3 agents). v2 items are deferred pending empirical evidence that v1 is insufficient.

## v2 Build Triggers

| ID | Build When | What Gets Built |
|----|-----------|-----------------|
| `memaudit-v2-producer` | dream patch leaves >5 unresolved cross-tier dupes/week for 2 consecutive weeks | full `memory_audit_producer.py` |
| `memaudit-v2-search` | 2nd skill hits a documented retrieval miss | `memory_search.py` hybrid retrieval router |
| `memaudit-v2-dedup` | 2nd producer (beyond heartbeat) creates ≥3 near-duplicates/week | `producer_dedup.py` write-time guard |
| `memaudit-v2-refs` | a stale-pointer incident causes a real failure | Phase A reference integrity audit |
| `memaudit-v2-decay` | Eric reports acting on stale memory ≥2 times | Phase B TTL decay |
| `memaudit-v2-versioning` | nomic-embed-text upgraded OR corpus exceeds 1000 files | versioned embedding index |
| `memaudit-v2-contradict` | 90-day re-evaluation from 2026-04-07 (≈ 2026-07-06) | Phase D LLM contradiction detection — needs separate PRD first |
| `memaudit-threshold-recal` | second confirmed near-miss below 0.92 threshold | empirically recalibrate dupe threshold; one real cross-tier dupe sits at 0.919 (`2026-03-27_slack-epdev-routing.md` ↔ `slack-routing.md`) |

## Current State (as of 2026-04-07)

- v1 shipped: `dream.py` Phase 3 cross-tier merge (bidirectional provenance, similarity ≥0.85), `embedding_service.py` TELOS exclusion, `purge_orphaned()` on every index(), `jarvis_config.py` PROTECTED_FILES
- Post-GC: 0 dupes, 23 informational related pairs, 46 orphaned rows purged, 3 TELOS rows excluded
- Root cause of "18 phantom duplicates": stale ChromaDB rows for deleted files, NOT real cross-tier dupes
- Remaining: full re-index pending Ollama uptime
