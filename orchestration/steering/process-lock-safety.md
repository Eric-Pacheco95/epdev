# Process, Lock & Worktree Safety — Steering Rules

> Behavioral constraints for subprocess spawning, file locking, worktree integrity, and concurrency primitives.
> Extracted from `autonomous-rules.md` 2026-04-27 to keep that file under the 20 KB cap.
> Auto-injected by dispatcher into every dispatched task via STEERING_ALWAYS_INJECT (alongside autonomous-rules.md).
> Also load explicitly in BUILD-phase work that touches subprocesses, locks, or worktree machinery.

## Worktree & Git Integrity

- Any scheduled or background process that mutates git state must operate in a git worktree, never in the main working tree — worktrees with self-healing cleanup (auto-prune stale worktrees on next run) eliminate dirty-tree bugs entirely
- **Never call `git worktree remove --force` directly — use `_safe_worktree_remove()` from `tools/scripts/lib/worktree.py`.** The `memory/learning/synthesis/` directory must be excluded from ALL pipeline cleanup, rotation, and move-to-processed logic. Why: git's internal rm-rf follows Windows junctions and destroyed 367 signals across 4 days; the same class of cleanup bug independently destroyed a synthesis doc. How to apply: any overnight or dispatcher cleanup step that prunes worktrees or rotates output directories must call `_safe_worktree_remove()` and explicitly exclude `memory/learning/synthesis/` from its scope.
- **When a worktree setup step modifies tracked files, hide those changes from git before any `git add -A` runs.** Use `git update-index --skip-worktree <file>` (keeps the index entry intact, silences `git status` and `git add -A`) plus a `/.git/info/exclude` entry for the replacement path (junction/symlink). Never assume worktree setup is git-neutral — verify with `git status --porcelain` after setup completes. Why: 2026-04-17 — `_symlink_local_memory` replaced tracked `.keep` dirs with junctions; pre-loop auto-commit used `git add -A` and committed them; overnight branch merged to main producing self-referential symlinks (mode 120000). `git rm --cached` is the wrong fix — it stages a deletion that `git commit` will include. How to apply: `_hide_symlink_from_git()` in `tools/scripts/lib/worktree.py` is the reference implementation.
- **When relocating a file other code reads, delete/stub/symlink the old path in the same commit.** Gitignored orphans are invisible to `git status` — grep hits both copies and the stale one misleads future investigations. Same-commit `rm`, error-stub, or symlink — never leave a gitignored parallel copy.
- **Sessions that create worktree experiment stub directories (`_wt-*`, `_wt-test-*`, `_wt-hide-*`) must delete them before closing — `git worktree prune` does not remove non-registered stub dirs.** How to apply: at end of any session that ran worktree-mechanics tests or `_hide_symlink_from_git` experiments, `ls _wt-*` and `rm -rf` any leftover stubs; consider a session-end hook that warns when `_wt-*` dirs exist in the repo root. Why: Apr 22-23 worktree experiments left `_wt-hide-pytest`, `_wt-hide-pytest2`, `_wt-test-hide` accumulating in the repo root and required manual cleanup.

## Lock Primitives

- **Any shared mutex release must check ownership before unlinking — use `if acquired: release()`, not `finally: release()`.** A process releasing a lock it does not own silently corrupts the lock state of the actual owner. Full three-component lock pattern: (1) atomic create via `O_CREAT|O_EXCL` — never open-then-write in two steps; (2) ownership check before release — set a boolean flag (`_acquired_lock`) only on successful acquire, release only if True; (3) dual-signal stale detection — declare a lock stale only when BOTH age-TTL is exceeded AND PID is no longer alive (`OpenProcess(SYNCHRONIZE, pid)` on Windows; `os.kill(pid, 0)` on POSIX) — TTL-alone creates races on slow jobs; PID-alone creates ghost locks after PID reuse. Reference: `tools/scripts/lib/worktree.py`. Why: dispatcher's `finally` block unconditionally deleted overnight's live lock file on every stop_lock exit; the latent consequence was overnight could resume a new `claude -p` while dispatcher had already stolen the lock, with no error raised.

## Subprocess & Spawn-Site Discipline

- **For orphan-process and spawn-safety bugs specifically, fix the spawn site — do not add a downstream scanner or reaper.** When a subprocess leak is diagnosed, the correct fix is at the `subprocess.run` / `Popen` / `.bat` call site: remove `shell=True`, resolve dates via native Windows tokens instead of `for /f today.py`, or wrap the spawn in a Job Object (see platform-specific.md). Building a reaper to mop up leaked orphans treats the symptom and hides the architectural cause. Carve-out: reapers are legitimate when the producer is external (not owned by epdev code) — but the default answer is always creation-site. Why: 2026-04-18 OOM — the initial proposal was a commit-pressure reaper; the correct fix was removing the three spawn mechanisms (shell=True, .bat for /f, un-jobbed claude -p). Reapers would have masked the recurrence.

## Loaded by

- `tools/scripts/jarvis_dispatcher.py` — STEERING_ALWAYS_INJECT (every dispatched task)
- `.claude/skills/implement-prd/SKILL.md` — BUILD-phase reference for worktree/subprocess work
- `.claude/skills/quality-gate/SKILL.md` — verifier reference
