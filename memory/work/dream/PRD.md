# PRD: /dream — Jarvis Memory Consolidation + Semantic Search

- **Date**: 2026-04-04
- **Phase**: 5C
- **Status**: DRAFT
- **Research inputs**: memory_consolidation_research_brief.md, local-embeddings research_brief.md, /first-principles run, smoke test (dream_smoke_test.py)

---

## OVERVIEW

`/dream` is a Jarvis memory consolidation skill that runs periodically to keep all memory tiers clean, deduplicated, and semantically indexed. It is backed by `embedding_service.py`, a standalone utility that embeds Jarvis memory files using `nomic-embed-text` (already installed via Ollama) and stores vectors in a persistent ChromaDB index. `/dream` runs the 4-phase AutoDream cycle — Orient, Gather Signal, Consolidate, Prune & Index — across all four memory tiers: auto-memory files, learning signals, synthesis distillations, and decision history. The name is a deliberate neuroscience metaphor: like REM sleep consolidating biological memory, `/dream` consolidates Jarvis's accumulated knowledge while the operator is away.

---

## PROBLEM AND GOALS

- Auto-memory files (~23 today, growing ~2/day) are append-only with no dedup or contradiction resolution — quality decay is inevitable and compounds silently
- Synthesis insights and learning signals accumulate in `memory/learning/` but never promote into the auto-memory tier that shapes every session — wisdom is captured but not applied
- Semantic duplicates (same insight written in different words across sessions) are invisible to grep-based tools — they inflate memory size and dilute session context
- Stale pointers in MEMORY.md (references to deleted/moved files) cause silent retrieval failures
- **Goal: Clean auto-memory** — every auto-memory file is deduplicated, contradiction-free, and uses absolute dates; MEMORY.md index is accurate and under 200 lines
- **Goal: Semantic retrieval** — any Jarvis skill can call `embedding_service.search(query)` to find relevant memory/signals/decisions without knowing exact file names or keywords
- **Goal: Living memory** — high-signal synthesis insights are promoted to auto-memory, closing the loop from raw observation to behavioral change
- **Goal: Autonomous maintenance** — `/dream` runs overnight without human intervention; human review is required only for flagged duplicates and promotion candidates, not for routine cleanup

---

## NON-GOALS

- CLAUDE.md steering rules consolidation — `/update-steering-rules` owns that workflow
- Real-time memory indexing on every write — batch re-index on demand or scheduled
- Vector DB server or Docker dependency — ChromaDB embedded mode only
- Chunking pipeline — files are small enough to embed whole (validated by smoke test)
- Automatic TELOS file modification — TELOS writes are interactive-only (`JARVIS_SESSION_TYPE` enforcement)
- Cross-project memory (crypto-bot, jarvis-app) — epdev memory only in v1

---

## USERS AND PERSONAS

- **Eric (sole user, interactive mode)** — runs `/dream` manually from a Claude Code session when he wants an immediate consolidation report; reviews flagged duplicate candidates and promotion proposals one-by-one
- **Overnight runner (autonomous mode)** — executes `/dream` as a scheduled Task Scheduler job; produces a consolidation report and queues human-review items without blocking or requiring interaction

---

## USER JOURNEYS OR SCENARIOS

1. **Manual interactive run**: Eric types `/dream`. Jarvis checks the lock file (none), reads MEMORY.md, inventories all 4 tiers, embeds any un-indexed files, runs `find_similar()`. Reports: "Indexed 23 auto-memory + 284 signals + 12 synthesis + 8 decisions. Found 2 duplicate candidates, 0 stale pointers, 3 relative dates." Walks Eric through each duplicate pair with similarity score — Eric approves merge or dismisses. Converts relative dates inline. Rebuilds MEMORY.md. Writes `history/changes/dream_log.md`. Emits health signal.

2. **Overnight scheduled run**: Task Scheduler fires `/dream` at 3am. Lock file acquired. All 4 tiers indexed. 1 duplicate candidate found (score 0.94) — queued to `data/dream_review_queue.jsonl` for human review, NOT auto-merged. Relative dates converted. MEMORY.md rebuilt. Lock released. Health signal written. Morning session-start hook surfaces: "1 /dream review item pending — run `/dream --review`."

3. **Semantic search by another skill**: `/research` skill calls `embedding_service.search("ADHD build discipline", top_k=5)` and gets back ranked file paths and snippets — no grep, no exact keyword match required.

4. **Learning→memory promotion (Phase 2)**: After `/dream` consolidation runs, it scans synthesis files for entries rated 8+/10 that don't have semantic matches in auto-memory (similarity < 0.70). Presents promotion candidates: "This synthesis insight has no auto-memory counterpart — promote to memory? [y/n]". Approved items are written as new memory files with `[promoted: synthesis, 2026-04-04]` tag.

5. **Concurrent run blocked**: Task Scheduler fires `/dream` while Eric is already running it interactively. Script detects `data/dream.lock`, prints "Dream run already in progress (lock acquired at 18:05). Exiting." No duplicate work, no conflict.

6. **ChromaDB index stale**: Eric adds 5 new memory files between `/dream` runs. Next `/dream` run detects files not in the index (via mtime comparison), re-embeds only the new/modified files — surgical update, not full re-index.

---

## FUNCTIONAL REQUIREMENTS

### embedding_service.py

- **FR-001: index(scope)** — Accept a list of directory paths, embed all `.md` files found, store vectors in ChromaDB collection `jarvis_memory` at `~/.jarvis/vectorstore/`; skip files already indexed with matching mtime (surgical updates only)
- **FR-002: search(query, top_k=5)** — Embed the query string, return top-K results as `[(file_path, score, snippet)]` sorted by cosine similarity descending; snippet = first 200 chars of file
- **FR-003: find_similar(threshold=0.92)** — Return all file pairs with cosine similarity >= threshold as `[(score, path_a, path_b)]`; also return pairs in the 0.82-0.91 range tagged as "related" (not duplicate)
- **FR-004: update(file_path)** — Re-embed a single file and upsert its vector in the index; used after `/dream` modifies a memory file
- **FR-005: stats()** — Return index health dict: `{file_count, last_indexed, stale_count, collection_size_mb}`; stale = files in scope dirs that are newer than their indexed mtime
- **FR-006: ASCII output** — All terminal output uses ASCII characters only (Windows cp1252 compatibility)
- **FR-007: Ollama dependency check** — On startup, verify Ollama is reachable at `http://localhost:11434` and `nomic-embed-text` is available; fail fast with a clear error if not

### dream.py + /dream skill

- **FR-008: Phase 1 — Orient** — Read MEMORY.md, inventory all files across the 4 configured scope dirs, check `data/dream.lock` (exit if locked), check `data/dream_last_run.txt` for last run timestamp
- **FR-009: Phase 2 — Gather Signal** — Call `embedding_service.find_similar(0.92)` for duplicate candidates; grep all auto-memory files for relative date patterns (`last week`, `yesterday`, `recently`, `ago`, `this week`); verify all MEMORY.md pointers resolve to existing files
- **FR-010: Phase 3 — Consolidate (fully autonomous)** — Auto-merge all duplicate candidates at >= 0.92: snapshot both files to `data/dream_snapshots/{ISO-timestamp}_{filename}` before any write, keep the more detailed file, append unique sentences from the other, delete the redundant file, update MEMORY.md; convert relative dates inline; remove stale MEMORY.md pointers; log every action to `history/changes/dream_log.md` as a post-hoc audit trail Eric reviews — no per-item approval gate
- **FR-011: Post-hoc review report** — After each run, print and write to `data/dream_last_report.md`: files merged (with similarity scores), dates converted, pointers removed, snapshots created; Eric reviews this report, not individual decisions; if a merge looks wrong, Eric restores from snapshot or git
- **FR-012: Phase 4 — Prune & Index** — Rebuild MEMORY.md index: scan all auto-memory files, regenerate one-line entries, enforce 200-line hard limit (demote verbose entries to topic files if needed); call `embedding_service.update()` for every file modified in Phase 3; write summary to `history/changes/dream_log.md`; update `data/dream_last_run.txt`; emit health signal to `memory/learning/signals/`
- **FR-013: Lock file management** — Acquire `data/dream.lock` at start with timestamp; release on completion or exception; if lock exists and is > 2 hours old, treat as stale and overwrite (with log entry)
- **FR-014: --review mode** — Scan `data/dream_review_queue.jsonl` for pending items; present each pair interactively for merge/dismiss decision; mark resolved items in queue file
- **FR-015: Overnight runner integration** — `dream.py` accepts `--autonomous` flag that enables queue mode (FR-011) and suppresses interactive prompts; overnight runner calls `python tools/scripts/dream.py --autonomous`
- **FR-016: Session-start hook** — Existing hook checks `data/dream_review_queue.jsonl` for pending items and prints one-liner: "N /dream review items pending — run `/dream --review`"
- **FR-017: Phase 2 scope (v1)** — Auto-memory files only for consolidation; signals/synthesis/history are indexed for semantic search but not consolidated in Phase 1

---

## NON-FUNCTIONAL REQUIREMENTS

- **NFR-001: Latency** — Full `/dream` run (23 auto-memory files + 284 signals) should complete within 3 minutes; incremental re-index (new files only) within 30 seconds
- **NFR-002: Idempotency** — Running `/dream` twice in a row with no changes between runs produces no modifications and no duplicate log entries
- **NFR-003: Isolation** — When invoked via overnight dispatcher, dream.py runs in a git worktree (per steering rule: autonomous jobs = worktrees)
- **NFR-004: Failure visibility** — If dream.py exits with an unhandled exception, it must: release the lock file, write the error to `history/changes/dream_log.md`, and emit a failure signal louder than a normal completion signal (rating 9, category "failure")
- **NFR-005: ASCII-only** — All terminal output uses ASCII characters only; no Unicode box-drawing or emoji
- **NFR-006: ChromaDB path** — Vector store persists at `~/.jarvis/vectorstore/` — never inside the git repo; never gitignored but accidentally included

---

## ACCEPTANCE CRITERIA

### Phase 1: embedding_service.py

- [ ] [E] `embedding_service.index()` embeds all `.md` files in a given directory and persists to ChromaDB without error | Verify: CLI — run `python tools/scripts/embedding_service.py index` on auto-memory dir, confirm ChromaDB collection exists and file count matches
- [ ] [E] `embedding_service.search("autonomous pipeline dispatcher", top_k=3)` returns `project_unified_pipeline_vision.md` as the top result (validated by smoke test) | Verify: CLI — run search command, confirm top result matches expected file
- [ ] [E] `embedding_service.find_similar(0.92)` returns zero pairs on the current 23 auto-memory files (all are distinct per smoke test) | Verify: CLI — run find_similar, confirm 0 pairs at >= 0.92 threshold
- [ ] [I] Re-indexing only re-embeds files with changed mtime — unchanged files are skipped | Verify: CLI — index, touch one file, re-index, confirm only 1 file re-embedded in log
- [ ] [E] `stats()` returns correct file count, last indexed timestamp, and stale count | Verify: CLI — run stats, add a file, re-run stats, confirm stale_count increments by 1
- [ ] [R] No vector data is written inside the git repo — ChromaDB persists to `~/.jarvis/vectorstore/` only | Verify: Grep — `git ls-files ~/.jarvis/` returns empty; `git status` shows no new tracked files

ISC Quality Gate: PASS (6/6)

### Phase 1: dream.py core

- [ ] [E] `/dream` in an interactive session completes all 4 phases, produces a human-readable report, and writes to `history/changes/dream_log.md` | Verify: CLI — run `/dream`, confirm log file updated with timestamp + summary
- [ ] [E] `data/dream.lock` is acquired at start and released on completion (including on exception) | Verify: CLI — run `/dream`, confirm lock created then deleted; kill mid-run, confirm lock is cleared on next run (stale > 2h policy)
- [ ] [E] A second concurrent `/dream` run detects the lock and exits cleanly with an informative message | Verify: CLI — acquire lock manually, run `/dream`, confirm exit message not error
- [ ] [E] Relative date strings in auto-memory files are converted to absolute dates and saved | Verify: CLI — inject "last week" into a test memory file, run `/dream`, confirm it becomes an absolute date
- [ ] [I] Stale MEMORY.md pointers (referencing nonexistent files) are removed and logged | Verify: CLI — add a fake pointer to MEMORY.md, run `/dream`, confirm pointer removed and logged
- [ ] [R] No modifications are made to any file outside `memory/`, `history/changes/`, `data/`, and MEMORY.md | Verify: Review — `git diff` after `/dream` run shows only expected paths

ISC Quality Gate: PASS (6/6)

### Phase 1: Overnight + session hook

- [ ] [E] `dream.py --autonomous` runs without interactive prompts and queues duplicate candidates to `data/dream_review_queue.jsonl` instead of presenting them | Verify: CLI — run with `--autonomous` flag in a terminal, confirm no prompts and queue file updated
- [ ] [E] Session-start hook prints pending review count when `data/dream_review_queue.jsonl` has unresolved items | Verify: CLI — add a mock pending item to queue, start new session, confirm hook one-liner appears
- [ ] [E] `/dream --review` walks through pending queue items one-by-one and marks resolved items | Verify: CLI — add 2 mock items to queue, run `--review`, confirm both presented and resolved markers written

ISC Quality Gate: PASS (6/6)

### Phase 2: Broad scope + learning→memory promotion

- [ ] [E] `embedding_service.index()` successfully indexes all 4 tiers (auto-memory + signals + synthesis + decisions) and search returns results across all tiers | Verify: CLI — run full index, search for a term known to exist only in signals dir, confirm it surfaces
- [ ] [E] `/dream` Phase 2 promotion scan finds synthesis entries rated >= 8 with no semantic match (< 0.70) in auto-memory and presents them as promotion candidates | Verify: CLI — create a test synthesis entry with rating 9 and unique content, run `/dream`, confirm it appears as promotion candidate
- [ ] [I] Approved promotion entries are written as new auto-memory files with `[promoted: synthesis, YYYY-MM-DD]` frontmatter tag | Verify: Read — inspect promoted file for correct tag and no verbatim signal text
- [ ] [R] Rejected promotion candidates are NOT written to auto-memory and NOT re-surfaced on the next `/dream` run | Verify: CLI — reject a candidate, run `/dream` again, confirm candidate does not reappear

ISC Quality Gate: PASS (6/6)

---

## SUCCESS METRICS

- Zero stale MEMORY.md pointers after first `/dream` run
- Zero relative date strings in auto-memory files after first run
- `embedding_service.search()` integrated into at least 2 other skills within 30 days of shipping (suggested: `/research` and `/synthesize-signals`)
- At least 1 duplicate candidate correctly identified within the first 30 days as memory file count grows
- Overnight `/dream` runs successfully on Task Scheduler for 7 consecutive nights without manual intervention
- Eric uses `embedding_service.search()` directly at least 3 times in the first month (validates standalone utility value)

---

## OUT OF SCOPE

- CLAUDE.md steering rules consolidation (`/update-steering-rules` owns this)
- TELOS file modification (interactive-only, `JARVIS_SESSION_TYPE` enforcement applies)
- Cross-project memory indexing (crypto-bot, jarvis-app)
- Chunking pipeline for large files
- Re-ranking models or hybrid dense+sparse search
- Real-time indexing on every memory write
- Automatic merges without human approval — all consolidation is human-gated

---

## DEPENDENCIES AND INTEGRATIONS

- **nomic-embed-text** — already installed via `ollama pull`; Ollama must be running for embedding operations
- **ChromaDB** — `pip install chromadb`; only new dependency; embedded mode, no server
- **numpy** — already installed; used for cosine similarity in smoke test (ChromaDB handles this internally in prod)
- **Ollama REST API** — `http://localhost:11434/api/embed`; local only, no external calls
- **Overnight runner** (`tools/scripts/overnight_runner.py`) — extended to call `dream.py --autonomous`
- **Session-start hook** (`tools/scripts/hook_session_start.py`) — extended to check `data/dream_review_queue.jsonl`
- **`memory/learning/signals/`** — read target for Phase 2 broad scope and promotion scan
- **`memory/learning/synthesis/`** — read target for promotion candidates
- **`history/decisions/`** — read target for broad semantic index
- **`data/dream.lock`** — lock file, runtime state
- **`data/dream_last_run.txt`** — last run timestamp
- **`data/dream_review_queue.jsonl`** — pending review items for overnight-initiated runs
- **`history/changes/dream_log.md`** — audit trail for all consolidation actions
- **`~/.jarvis/vectorstore/`** — ChromaDB persistent storage (outside git repo)

---

## RISKS AND ASSUMPTIONS

### Risks

- **Over-aggressive merging (HIGH):** If thresholds are tuned too low, distinct memories get flagged as duplicates. Mitigated by: human approval gate for all merges, 0.92 threshold validated by smoke test to produce zero false positives on current file set, conservative start.
- **ChromaDB index drift (MEDIUM):** If memory files are modified outside `/dream`, the index goes stale silently. Mitigated by: mtime comparison in `stats()`, stale count surfaced in session-start hook.
- **Ollama not running during overnight job (MEDIUM):** If Ollama is stopped when the overnight runner fires, embedding fails. Mitigated by: FR-007 fast-fail check emits a failure signal; overnight runner logs the error; no memory files are modified.
- **Lock file orphaned by hard crash (LOW):** Mitigated by: 2-hour stale lock policy with automatic overwrite and log entry.
- **Promotion of low-quality insights (MEDIUM):** Phase 2 promotion scan could surface synthesis entries that seemed high-signal at capture but are now stale or wrong. Mitigated by: human approval per-item, `[promoted: synthesis]` tag enables future audit of promoted content.

### Assumptions

- Ollama is running as a background service (or Eric starts it before running `/dream` interactively)
- `pip install chromadb` succeeds in Eric's Python 3.12 environment (no known conflicts)
- The 0.92 dedup threshold holds as file count grows — may need tuning at 100+ files
- nomic-embed-text's 2048-token context covers all current memory files (largest observed: ~3K chars = ~750 tokens, well within limit)
- `data/` directory is gitignored and exists (confirmed by current repo structure)

---

## OPEN QUESTIONS

1. **ChromaDB install environment**: Should `chromadb` be installed in the global Python env or a venv? (epdev has no venv today — global is consistent with existing scripts)
2. **Scope dirs config**: Should the 4 scope directories be hardcoded in `dream.py` or configurable via `data/dream_config.json`? Config adds flexibility but scope is stable enough to hardcode for v1.
3. **Promotion rating threshold**: 8+/10 for promotion candidates — is this the right floor, or should it be 7+ to catch more candidates? Calibrate after first 30-day run.
4. **`/research` integration**: `embedding_service.search()` is called automatically at the start of every `/research` run to surface prior briefs and signals — always on, not opt-in. RESOLVED.
5. **MEMORY.md 200-line demotion policy**: When MEMORY.md hits the limit, which entries get demoted to topic files — oldest, lowest-priority type, or shortest hook line? Need a tie-breaking rule.
