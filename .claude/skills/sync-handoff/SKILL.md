---
name: sync-handoff
description: Reconcile a session handoff against current git state — flag pending efforts already shipped. User-invocable only.
disable-model-invocation: true
---

# IDENTITY and PURPOSE

Jarvis handoff reconciliation engine. Reads a session handoff file, extracts every effort under `## Pending Efforts`, runs deterministic git checks, and reports which entries are already shipped vs still pending. The fix for the stale-handoff failure mode caught 3+ times in 24h: handoff written before commits land → next session re-attempts already-done work.

# DISCOVERY

## Stage
OBSERVE

## Syntax
/sync-handoff [path]

## Parameters
- `path`: handoff file (default: newest `data/session_handoff_*.md` by mtime)

## Examples
- `/sync-handoff` — reconcile newest handoff
- `/sync-handoff data/session_handoff_2026-04-27_evening_c.md` — specific file

## Chains
- Before: any session that opens on a handoff (especially after multi-session activity)
- After: nothing (terminal observation step; the human acts on the report)
- Full: [session start] → `/sync-handoff` → [resume work on STILL-PENDING items only]

## Output Contract
- Input: handoff file path
- Output: per-effort verdict table — DONE / LIKELY-DONE / KEYWORD-HIT / PENDING — with candidate commit hashes
- Side effects: none (read-only — runs `git log`, never writes)

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- No input and no handoff files in `data/`: print DISCOVERY block, STOP
- Explicit path given but file not found: "Handoff not found at {path}. Files in data/: {list}" STOP
- Explicit path points to a file with no `## Pending Efforts` section: print CONTRACT `empty-pending` error, STOP
- `--help` or unknown flags: print DISCOVERY block, STOP

## Step 1: RUN AUDIT

Run `python tools/scripts/sync_handoff.py [path]`. The script:

1. Resolves the handoff (default = newest in `data/`).
2. Parses the `## Pending Efforts` section into discrete `### ` entries.
3. For each effort: extracts file paths from the body, distinctive title keywords (≥8 chars).
4. Backdates the cutoff 48h from the handoff mtime — the staleness pattern is "handoff written *after* the work it lists," so a strict mtime cutoff filters out exactly the commits we want.
5. Queries `git log --since=<cutoff>` for path-touching commits and (separately) keyword-grepping commits.
6. Verdict: DONE if any commit hits both path and keyword; LIKELY-DONE if path-only; KEYWORD-HIT if grep-only; PENDING otherwise.

## Step 2: PRESENT TO USER

Show the script output verbatim. For each item flagged DONE/LIKELY-DONE, name the candidate commit hashes Eric should verify. Do not auto-mark anything done — the script collects evidence, the human decides.

## Step 3: RECOMMEND NEXT ACTION

- All efforts DONE → "Handoff is fully shipped. Archive or delete it." Recommend `mv data/session_handoff_X.md data/archive/`.
- Some DONE, some PENDING → "Pick up only the still-PENDING items. Skip [list of done ones]."
- All PENDING → "Handoff is current. Resume kickoff prompt for [first item]."

# VERIFY

- Script ran and parsed at least one effort (or reported empty Pending Efforts) | Verify: `python tools/scripts/sync_handoff.py --self-test`
- Handoff path resolved (default or explicit) | Verify: output line "Handoff: data/..."
- Verdict assigned to every effort | Verify: each `### ` block in output has a `Verdict:` line
- No files were modified during execution (read-only constraint) | Verify: `git diff --stat` shows no changes
- Recommendation section present (all DONE / some DONE / all PENDING) | Verify: output contains "Handoff is" or "Pick up only"

# CONSTRAINTS

- **Read-only**: never modifies the handoff file or git state. Archiving/deleting is a separate user-driven action.
- **Path heuristic limits**: handoffs that reference target files via wildcard (`.claude/skills/*/SKILL.md`) or by skill name only won't get path hits — fall back to keyword evidence.
- **48h lookback**: covers same-day-thread overlap. Handoffs older than 48h get a stale-window warning (TODO: not yet implemented; the script just reports the cutoff).
- **No auto-archive**: even when all efforts are DONE, the user decides whether to delete the handoff or keep it as a thread record.

# LEARN

- Stale-handoff pattern fires this skill: when invoked, log how many efforts were DONE — repeated high-DONE counts signal `/draft-handoff` is being called *before* the work it summarizes lands; consider hooking `/sync-handoff` into session-start.
- If KEYWORD-HIT count is consistently high but verdict is PENDING, the handoff schema is too vague — push back via `/draft-handoff` LEARN to require explicit file paths in each Effort body.
- Track verdict distribution across sessions — DONE:PENDING ratio below 0.5 across 5+ invocations signals the 48h lookback window needs extending; above 0.9 signals overly-broad keyword matching.
- If `--self-test` fails repeatedly, the sync_handoff.py script has drifted from the handoff schema; flag for `/self-heal` with the mismatch diff.

# INPUT

Run `/sync-handoff` to reconcile the newest handoff, or pass an explicit path. The script handles all I/O.

# CONTRACT

## Errors
- **no-handoff**: no handoff files in `data/` → exit; nothing to reconcile
- **path-not-found**: explicit path doesn't exist → exit with stderr message
- **empty-pending**: handoff has no `## Pending Efforts` section → "Handoff lists no pending efforts" + exit clean
