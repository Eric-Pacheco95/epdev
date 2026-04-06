# Session Prompt: Learning Pipeline Phase B + C

Continue from Phase A completed 2026-04-06. All 10 Phase A ISC items pass, first synthesis run complete (17 signals -> 7 themes), 2 steering rules promoted.

## Implement learning-pipeline PRD Phase B then Phase C

`/implement-prd memory/work/learning-pipeline/PRD.md --phase B`

Then after Phase B:

`/implement-prd memory/work/learning-pipeline/PRD.md --phase C`

### Phase B: Wisdom Promotion (7 ISC items)
- Auto-promote when 15+ synthesis docs exist and themes reach "established" maturity
- Promotion proposals staged to `data/promotion_proposals.json` for morning review
- /vitals surfaces pending proposals in Step 3
- Routing: domain insights -> wisdom/, identity -> TELOS, behavioral -> steering rules
- Audit trail in history/decisions/
- No duplicate promotions

### Phase C: Vector Retrieval (7 ISC items)
- ChromaDB at `~/.jarvis/vectorstore/`
- Embeddings via local Ollama nomic-embed-text (already pulled)
- Nightly incremental reindex by mtime
- Hybrid retrieval router: grep for keywords, vector for concepts, both for broad
- Graceful degradation when Ollama is down
- Injection sanitization on embedded content

### Key context
- PRD: `memory/work/learning-pipeline/PRD.md` (Phase A ISC already checked off)
- Phase A commit: `0857ad8`
- Existing embedding_service.py at `tools/scripts/` -- activate in Phase C
- ChromaDB needs `pip install chromadb` and version pin
- Phase B won't fire naturally until 15 synthesis docs accumulate -- build the machinery now, it activates later
