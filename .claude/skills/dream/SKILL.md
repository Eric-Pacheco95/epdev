# IDENTITY and PURPOSE

You are the Jarvis memory consolidation engine. You run the /dream cycle: orient across all memory files, detect semantic duplicates and stale entries using nomic-embed-text embeddings, auto-merge duplicates with snapshots for rollback safety, and rebuild the index. Eric reviews the post-hoc report — he does not approve individual changes before they happen.

# DISCOVERY

## One-liner
Consolidate, deduplicate, and semantically index all Jarvis memory files

## Stage
EXECUTE

## Syntax
/dream [--dry-run]

## Parameters
- --dry-run: show what would change without making any writes

## Examples
- /dream
- /dream --dry-run

## Chains
- Before: (standalone, or overnight runner)
- After: /learning-capture (if significant consolidation occurred)
- Related: /update-steering-rules (CLAUDE.md rules -- separate skill, not /dream scope)

## Output Contract
- Input: none
- Output: consolidation report (stdout + data/dream_last_report.md)
- Side effects: merges duplicate memory files (with snapshots), fixes relative dates,
  removes stale MEMORY.md pointers, updates embedding index, writes dream_log.md,
  emits health signal

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION
- --dry-run: run in preview mode -- report what would change, make no writes
- No other arguments needed -- scope is fixed (auto-memory files)

## Step 1: EXECUTE
Run the dream worker:

```
python tools/scripts/dream.py [--dry-run]
```

The worker handles all 4 phases internally:
- Phase 1: Orient (inventory files, check lock, last-run timestamp)
- Phase 2: Gather Signal (semantic duplicate scan via embedding_service, stale pointer grep, relative date grep)
- Phase 3: Consolidate (auto-merge at >= 0.92 similarity with pre-merge snapshots, fix dates, remove stale pointers)
- Phase 4: Prune & Index (check MEMORY.md line count, update embedding index, write log + health signal)

## Step 2: REPORT
After the worker completes, read and present the report from data/dream_last_report.md.
Highlight any merges that occurred so Eric can spot-check them.

## Step 3: ROLLBACK GUIDANCE (if Eric wants to undo a merge)
If Eric wants to revert a merge:
1. Find the snapshot in data/dream_snapshots/ (named {timestamp}_{filename}.md)
2. Copy it back over the merged file
3. Or: git checkout the file if it was committed before /dream ran

# OUTPUT INSTRUCTIONS

- Present the dream_last_report.md content directly -- no additional wrapping
- If merges occurred, note the snapshot directory location for rollback
- If memory is clean (no changes), say so in one line
- Do not invent changes that didn't happen -- report exactly what the worker produced

# CONTRACT

## Errors
- **ollama-not-running**: embedding_service cannot reach Ollama
  - recover: start Ollama (`ollama serve`), then re-run /dream
- **lock-held**: another dream run is in progress
  - recover: wait for it to complete; if lock is stale (>2h), delete data/dream.lock manually
- **chromadb-missing**: embedding_service import fails
  - recover: `pip install chromadb`, then re-run

# SKILL CHAIN

- **Composes:** embedding_service.py (semantic similarity engine)
- **Related:** /update-steering-rules (CLAUDE.md only -- separate)
- **Escalate to:** manual git restore if a merge produced bad output

# VERIFY

- `data/dream_last_report.md` exists and is non-empty (dream ran successfully) | Verify: `ls data/dream_last_report.md` exits 0 and file size > 0
- No merges occurred on protected files (TELOS.md, constitutional-rules.md, CLAUDE.md) | Verify: Read dream_last_report.md merge list — protected filenames must not appear
- Similarity threshold used was >= 0.80 (nomic-embed-text sparse corpus floor) | Verify: Read dream_last_report.md threshold field
- If dream_last_report.md is missing, failure was reported and CONTRACT error recovery steps were surfaced | Verify: Read session output for error report
- If a protected file was merged, alert issued immediately with rollback path from `data/dream_snapshots/` | Verify: Read session output for rollback path if applicable

# LEARN

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_dream-consolidation.md when the run produces >= 3 merges
- Include: which files were merged, similarity scores, whether the corpus is healthy or showing noise at threshold
- Rating: 6-7 for routine consolidation; 8+ if a critical pattern was surfaced that should become a steering rule; do not write signal for clean (no-change) runs
