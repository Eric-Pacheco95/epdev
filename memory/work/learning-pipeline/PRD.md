# PRD: Learning Pipeline Repair + Wisdom Promotion + Vector DB

## OVERVIEW

The Jarvis learning pipeline -- the system that captures session learnings, synthesizes them into themes, and promotes mature insights into durable wisdom -- is structurally broken. Signals are not persisting (4 files vs 116 invocations/30d), synthesis documents are caught in an overnight revert cycle, the manifest database never existed, and there is no promotion path from synthesis to wisdom or TELOS. This PRD repairs the pipeline end-to-end across three phases: (A) fix signal/synthesis durability and unify the index layer, (B) build an auto-promote engine that graduates established themes into wisdom, knowledge, or steering rules, and (C) activate ChromaDB vector retrieval alongside grep for semantic memory search. The goal is a self-sustaining compound learning loop where every session produces durable, searchable, promotable insights.

## PROBLEM AND GOALS

- **Learning data is lost**: /learning-capture runs 116x/month but only 4 signal files exist on disk. Root causes: worktree writes vanish on cleanup, manifest DB was never created, overnight synthesis commits get reverted because files are gitignored.
- **No compound learning**: Synthesis themes are a dead end with no promotion to wisdom, TELOS, or steering rules. The LEARN phase of TheAlgorithm has been skipped for 30+ days.
- **No semantic retrieval**: Memory search is grep-only. Concept queries ("what has Eric learned about decision fatigue") return nothing. The embedding_service.py code exists but was deferred.
- **Goal**: A fully flowing pipeline where signals accumulate (threshold: 35) -> synthesize into themes -> promote mature themes (threshold: 15 synthesis docs) -> write to wisdom/TELOS/steering rules. All content indexed in ChromaDB for semantic + grep hybrid retrieval.

## NON-GOALS

- Building a new skill framework or changing the skill execution model
- Migrating off local storage to cloud-hosted vector DB
- Real-time streaming retrieval (batch nightly reindex is sufficient)
- Changing the /research -> knowledge/ pipeline (that works independently)
- Building a UI for the learning pipeline (jarvis-app integration is a separate effort)

## USERS AND PERSONAS

- **Eric (operator)**: Reviews synthesis proposals during morning brief, approves promotions to steering rules and TELOS, uses semantic search to recall past learnings
- **Jarvis (autonomous)**: Writes signals during /learning-capture, runs overnight synthesis, proposes promotions, indexes content into vector DB, retrieves context for skills

## USER JOURNEYS OR SCENARIOS

1. **Session learning capture**: Eric finishes a session -> /learning-capture writes 2-5 signal files to `memory/learning/signals/` -> files persist across sessions and are indexed
2. **Overnight synthesis**: Overnight runner detects 35+ unprocessed signals -> runs /synthesize-signals -> writes synthesis theme docs to `memory/learning/synthesis/` -> generates promotion proposals -> proposals surface in morning /vitals Step 3
3. **Morning promotion review**: Eric runs /vitals -> Step 3 shows "2 themes ready for promotion" -> Eric approves -> wisdom articles written to `memory/learning/wisdom/`, steering rule staged for /update-steering-rules
4. **Semantic recall**: During a session, Jarvis needs context on "Eric's views on premature optimization" -> hybrid router queries both grep and ChromaDB -> returns relevant wisdom doc + 2 signals -> context injected into prompt

## FUNCTIONAL REQUIREMENTS

### Phase A: Pipeline Repair (P0)

- FR-A01: Signal files written by /learning-capture persist in `memory/learning/signals/` across session boundaries, including when written from worktree contexts (write to main tree absolute path, not worktree-relative)
- FR-A02: /learning-capture writes failure files to `memory/learning/failures/` when session failures are discussed, using the same accumulation rules as signals
- FR-A03: /synthesize-signals reads from `signals/`, `failures/`, AND `absorbed/` directories as input sources
- FR-A04: Synthesis threshold is 35 unprocessed items (signals + failures + absorbed combined)
- FR-A05: Processed signals are moved to `signals/processed/` after synthesis and persist there
- FR-A06: Overnight runner does NOT commit synthesis files to git (synthesis is local-only, never tracked)
- FR-A07: A single SQLite FTS5 database at `data/jarvis_index.db` serves all index queries; all references to `jarvis_manifest.db` are removed
- FR-A08: `jarvis_index.py backfill` indexes gitignored content (signals, synthesis, failures, absorbed) from local filesystem paths
- FR-A09: /vitals reads signal velocity and learning loop health from `jarvis_index.db`
- FR-A10: `_signal_meta.json` is reconciled against actual filesystem state on every /learning-capture run (count files, don't just increment)
- FR-A11: No index writes occur from worktree contexts (worktree = read-only for index)

### Phase B: Wisdom Promotion (P1)

- FR-B01: When 15+ synthesis theme docs exist in `memory/learning/synthesis/`, a promotion check runs automatically
- FR-B02: Themes at "established" maturity (4+ supporting signals across 2+ sessions) generate promotion proposals
- FR-B03: Promotion proposals are written to a staging file (`data/promotion_proposals.json`) for morning review
- FR-B04: /vitals morning brief Step 3 surfaces pending promotion proposals alongside backlog triage
- FR-B05: Promotion targets are routed by content type:
  - Domain insights -> `memory/learning/wisdom/{topic}.md` (auto-write on approval)
  - Identity/goal insights -> TELOS update proposal (requires Eric approval via /telos-update)
  - Behavioral patterns -> steering rule proposal (requires Eric approval via /update-steering-rules)
- FR-B06: Promoted wisdom articles follow a standard format with source lineage (which signals/synthesis contributed)
- FR-B07: `memory/learning/wisdom/` directory is created and gitignored (personal content)
- FR-B08: Promotion creates an audit trail entry in `history/decisions/`
- FR-B09: Themes already promoted are flagged and skipped on subsequent runs (no duplicates)

### Phase C: Vector Retrieval (P2)

- FR-C01: ChromaDB vectorstore at `~/.jarvis/vectorstore/` indexes all learning content (signals, synthesis, failures, absorbed, wisdom) plus tracked content (knowledge, decisions, TELOS, auto-memory)
- FR-C02: Embeddings use nomic-embed-text via local Ollama (no cloud API calls)
- FR-C03: Nightly reindex job (scheduled task) performs incremental updates (skip unchanged files by mtime)
- FR-C04: `embedding_service.py` serves as the vector DB interface with index/search/similar/update/stats commands
- FR-C05: A hybrid retrieval router selects grep, vector, or both based on query structure:
  - Exact keywords/file references -> grep path
  - Concept/semantic queries -> vector path
  - Broad queries -> hybrid (both, merged + deduplicated)
- FR-C06: Retrieved content passed to LLM prompts is sanitized: length-capped, injection patterns stripped
- FR-C07: Skills that consume retrieval (/research, /dream, /absorb) use the router API, not direct grep
- FR-C08: If Ollama is not running, vector operations degrade gracefully to grep-only with a warning

## NON-FUNCTIONAL REQUIREMENTS

- All file writes use ASCII-safe encoding (Windows cp1252 compatibility)
- Signal/synthesis/wisdom files are gitignored (personal content, privacy)
- Vector DB full rebuild completes in under 5 minutes for current corpus (~300 files)
- Hybrid retrieval router adds < 200ms latency to any query (p95)
- ChromaDB version pinned in requirements.txt to prevent breaking changes
- No network calls for embedding (Ollama is local-only)

## ACCEPTANCE CRITERIA

### Phase A: Pipeline Repair

- [ ] Signal files written by /learning-capture exist on disk after session exit | Verify: Write test signal, exit, verify in new session [M]
- [ ] Worktree-context signal writes land in main tree `memory/learning/signals/`, not worktree path | Verify: Grep overnight runner for absolute path usage [A]
- [ ] Failure files appear in `memory/learning/failures/` when failures are discussed in a session | Verify: Trigger known failure, run /learning-capture, `ls failures/` [M]
- [ ] /synthesize-signals processes files from signals/, failures/, AND absorbed/ | Verify: Place test files in all three dirs, run synthesis, confirm all referenced in output [M]
- [ ] Synthesis threshold fires at 35 unprocessed items | Verify: Create 34 test signals, confirm no auto-synthesis; add 1 more, confirm trigger [M]
- [ ] No synthesis files are committed to git by overnight runner | Verify: `git log --oneline -20 -- memory/learning/synthesis/` shows no new entries after fix [M]
- [ ] `jarvis_manifest.db` references are removed from codebase | Verify: `grep -r "manifest" tools/ .claude/` returns zero hits [M] | model: haiku |
- [ ] `jarvis_index.db` indexes gitignored signals and synthesis from local paths | Verify: Run backfill, query for known signal title, confirm hit [M]
- [ ] /vitals learning_loop_health metric reads from jarvis_index.db and reports non-null | Verify: Run /vitals after backfill, confirm "Last synthesis: Xd ago" not "NEVER" [M]

Anti-criterion:
- [ ] No signal data is silently lost during normal operation (write-then-read-back verification) | Verify: Count signals written in session output matches `ls signals/*.md | wc -l` delta [M]

### Phase B: Wisdom Promotion

- [ ] Promotion proposals are generated when 15+ synthesis docs exist and themes reach established maturity | Verify: Create 15 synthesis docs with 1 established theme, run promotion check, confirm proposal in staging file [M]
- [ ] Promotion proposals surface in /vitals morning brief | Verify: Run /vitals with pending proposals, confirm Step 3 shows them [M]
- [ ] Domain insights promote to `memory/learning/wisdom/{topic}.md` on approval | Verify: Approve a domain proposal, confirm file exists with correct format [M]
- [ ] Steering rule proposals require explicit Eric approval before writing | Verify: Run promotion with behavioral theme, confirm proposal staged but NOT written to CLAUDE.md [A]
- [ ] Promoted wisdom articles include source lineage (contributing signals/synthesis) | Verify: Read a promoted wisdom file, confirm lineage section present [M] | model: haiku |
- [ ] Audit trail entry created in history/decisions/ for each promotion | Verify: `ls history/decisions/*promote*` after promotion [M] | model: haiku |

Anti-criterion:
- [ ] No duplicate promotions occur for themes already promoted | Verify: Run promotion twice for same theme, confirm second run skips with "already promoted" message [M]

### Phase C: Vector Retrieval

- [ ] ChromaDB vectorstore indexes all scoped content (signals, synthesis, wisdom, knowledge, decisions, TELOS, auto-memory) | Verify: `python embedding_service.py stats` file count matches corpus total [M]
- [ ] Semantic search returns relevant results for concept queries | Verify: Search "Eric's decision-making patterns", confirm relevant signals/wisdom appear [M]
- [ ] Nightly reindex is incremental (unchanged files skipped by mtime) | Verify: Run index twice, second run indexes 0 files [M]
- [ ] Hybrid router selects correct path per query type | Verify: Test exact query -> grep, concept query -> vector, broad query -> hybrid [M]
- [ ] Graceful degradation when Ollama is not running | Verify: Stop Ollama, run search, confirm grep-only results with warning [M]

Anti-criteria:
- [ ] Embedded content containing injection patterns ("ignore all previous instructions") does not override Jarvis behavior | Verify: Embed adversarial file, search for it, confirm no instruction override [M]
- [ ] No vectorstore data is committed to git or stored inside the repo directory | Verify: Confirm `~/.jarvis/vectorstore/` path, no vectorstore in repo [A] | model: haiku |

ISC Quality Gate: PASS (6/6)

## SUCCESS METRICS

- Signal persistence rate: 100% of /learning-capture runs that write signals result in files on disk (current: ~3%)
- Synthesis cadence: at least 1 synthesis run per week (current: 0 in 30 days)
- Wisdom promotion: first promoted wisdom article within 2 weeks of Phase B deployment
- Vector retrieval usage: at least 1 semantic query per session within 1 week of Phase C deployment
- Learning loop health in /vitals: reports HEALTHY (not OFFLINE/WARN) within 24h of Phase A deployment

## OUT OF SCOPE

- Jarvis-app UI for learning pipeline visualization (separate PRD)
- Cloud-hosted vector DB or embedding API
- Cross-device sync of gitignored learning content (local-only)
- Automated steering rule writing without Eric approval
- Changes to /research -> memory/knowledge/ pipeline

## DEPENDENCIES AND INTEGRATIONS

- **Ollama + nomic-embed-text**: Must be installed and running for Phase C. Already pulled (`ollama pull nomic-embed-text`).
- **ChromaDB**: `pip install chromadb` required for Phase C. Pin version.
- **jarvis_index.py**: Existing FTS5 indexer at `tools/scripts/` -- extended in Phase A to handle gitignored content
- **embedding_service.py**: Existing ChromaDB wrapper at `tools/scripts/` -- activated in Phase C
- **compress_signals.py**: Existing signal management tool -- used in Phase A for stats/move/grouping
- **Overnight runner**: `tools/scripts/overnight_runner.py` -- modified in Phase A (stop committing synthesis) and Phase B (run promotion check)
- **/vitals skill**: Modified in Phase B to surface promotion proposals in morning brief
- **/learning-capture skill**: Modified in Phase A for write durability and failure capture
- **/synthesize-signals skill**: Modified in Phase A for multi-source input and threshold change (35)

## RISKS AND ASSUMPTIONS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Signal writes still fail silently after fix | LOW | HIGH | Write-then-read-back verification; ISC anti-criterion tests this |
| ChromaDB version breaks on upgrade | LOW | MEDIUM | Pin version; full rebuild < 5 min |
| Auto-promote generates low-quality wisdom from thin data | MEDIUM | MEDIUM | 15 synthesis + 4-signal established threshold is conservative; Eric reviews all non-knowledge promotions |
| Prompt injection via embedded content | LOW | HIGH | Sanitize at index time; STRIDE analysis completed; injection test in ISC |
| Overnight synthesis produces noisy proposals | MEDIUM | LOW | Morning brief is a batch review surface; Eric can dismiss in bulk |
| Nightly reindex conflicts with overnight runner | LOW | LOW | Schedule reindex after overnight runner completes (sequential, not parallel) |

### Assumptions

- Ollama will remain available locally (no plan to remove it)
- Signal volume will increase once pipeline is repaired (116 invocations/month should produce 200+ signals)
- The 35-signal threshold is high enough to prevent noisy synthesis but low enough to produce regular synthesis runs
- ChromaDB at `~/.jarvis/vectorstore/` is acceptable storage location (outside repo, user-only permissions)
- Eric will review promotion proposals at least weekly via /vitals morning brief

## OPEN QUESTIONS

- Should wisdom articles be organized by domain subdirectories (like knowledge/) or flat in `wisdom/`? Flat is simpler to start; subdirectories can be added when volume warrants.
- Should the hybrid retrieval router be a standalone script or integrated into embedding_service.py? Leaning toward extending embedding_service.py with a `route` command.
- What is the right confidence decay rate for wisdom articles? Synthesis themes decay if not revalidated in 90 days -- should wisdom follow the same schedule or be more durable?
