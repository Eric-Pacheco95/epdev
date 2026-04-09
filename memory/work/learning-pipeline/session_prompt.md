# Session Prompt: Learning Pipeline Repair

Continue from morning brief completed 2026-04-06. Priority:

## Implement learning-pipeline PRD Phase A

`/implement-prd memory/work/learning-pipeline/PRD.md`

Focus on Phase A only (pipeline repair). Key files to modify:
- `.claude/skills/learning-capture/SKILL.md` -- worktree write fix (use absolute main tree path), failure capture to failures/, meta reconciliation (count files, don't increment)
- `.claude/skills/synthesize-signals/SKILL.md` -- multi-source input (signals/ + failures/ + absorbed/), threshold change to 35
- `tools/scripts/overnight_runner.py` -- stop committing synthesis files to git
- `tools/scripts/jarvis_index.py` -- extend to index gitignored content (signals, synthesis, failures, absorbed)
- `tools/scripts/compress_signals.py` -- verify processed/ flow works with gitignored paths
- Remove ALL `jarvis_manifest.db` references from codebase

Root cause chain (diagnosed 2026-04-06):
1. Worktree writes vanish -- overnight runners write signals to worktree-relative paths that get pruned
2. Synthesis revert cycle -- overnight commits synthesis to git, but it's gitignored, so next run reverts
3. Manifest DB never existed -- velocity metrics and synthesis triggers read from nonexistent DB
4. No promotion path -- synthesis themes are dead end (Phase B addresses this)

Architecture review and full gap analysis completed. See PRD for ISC criteria.

After Phase A: validate by running /learning-capture, confirming signals persist, then running /synthesize-signals manually to confirm end-to-end flow.

## Then: ISC Producer Design

Run `/architecture-review` on building an ISC producer (`tools/scripts/isc_producer.py`):
- Scans all active PRDs for `- [ ]` items with `| Verify:` suffixes
- Executes verify commands (grep, test -f, read, etc.)
- Auto-proposes `[x]` for items that pass (batch for morning review)
- Creates backlog tasks for items that are close but need work
- Reports ISC velocity in /vitals dashboard
- Runs as overnight dimension or standalone weekly producer

Key questions for arch review:
- Should this be an overnight dimension or a standalone producer?
- How to handle verify commands that need interactive context vs pure CLI checks?
- Should it auto-mark haiku-tier items and only propose opus-tier items for review?

## Housekeeping

- Remove steering rules audit tasks from dispatcher backlog (collaborative, not autonomous)
- Set up bi-weekly `/update-steering-rules --audit` as a recurring calendar item
- Review 15 [A]-rated morning feed proposals from Apr 4-6 (especially Claude Code v2.1.89 "defer" permission for dispatcher)
