"""Reusable git worktree library for Jarvis autonomous execution.

Extracted from overnight_runner.py. Provides worktree create/cleanup,
branch management, memory symlink support, and a global claude -p
mutex to prevent subprocess contention between autonomous processes.

All operations target a sibling directory so the main working tree is
never touched -- no stash, no branch switch, no conflict with active
Claude Code sessions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]

# Global mutex for claude -p invocations. All autonomous processes
# (dispatcher, overnight runner, autoresearch) must acquire this before
# running claude -p to prevent subprocess contention and hangs.
_CLAUDE_LOCK = REPO_ROOT / "data" / "claude_session.lock"
_CLAUDE_LOCK_STALE_HOURS = 3


def acquire_claude_lock(owner: str, timeout_hours: float = 3) -> bool:
    """Acquire global claude -p mutex. Returns True if acquired.

    Args:
        owner: Identifier for the process acquiring the lock (e.g., "dispatcher", "overnight").
        timeout_hours: How long before a lock is considered stale and auto-broken.

    Uses atomic O_CREAT|O_EXCL to prevent races. Stale locks (older than
    timeout_hours) are automatically broken -- handles crash recovery.
    """
    _CLAUDE_LOCK.parent.mkdir(parents=True, exist_ok=True)

    # Check for stale lock
    if _CLAUDE_LOCK.exists():
        try:
            lock_data = json.loads(_CLAUDE_LOCK.read_text(encoding="utf-8"))
            locked_at = datetime.fromisoformat(lock_data.get("locked_at", ""))
            age_hours = (datetime.now(timezone.utc) - locked_at).total_seconds() / 3600
            if age_hours > timeout_hours:
                print(f"  Breaking stale claude lock (owner={lock_data.get('owner')}, "
                      f"age={age_hours:.1f}h)", file=sys.stderr)
                _CLAUDE_LOCK.unlink(missing_ok=True)
            else:
                print(f"  Claude lock held by {lock_data.get('owner')} "
                      f"({age_hours:.1f}h ago) -- skipping", file=sys.stderr)
                return False
        except (json.JSONDecodeError, OSError, ValueError):
            # Corrupted lock file -- break it
            _CLAUDE_LOCK.unlink(missing_ok=True)

    # Atomic create
    try:
        fd = os.open(str(_CLAUDE_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        lock_data = {
            "owner": owner,
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        }
        os.write(fd, json.dumps(lock_data).encode("utf-8"))
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_claude_lock() -> None:
    """Release global claude -p mutex."""
    _CLAUDE_LOCK.unlink(missing_ok=True)

# Directories to symlink from main repo into worktree.
# Each tuple: (relative path from repo root, read-only flag for logging).
_MEMORY_SYMLINKS = [
    ("memory/learning/signals", True),
    ("memory/learning/synthesis", False),
    ("memory/learning/failures", True),
]


def backup_learning_signals(backup_root: Optional[Path] = None) -> Optional[Path]:
    """Copy all .md files from memory/learning/ subdirs to a timestamped backup.

    Keeps last 7 backups (prunes older ones automatically).
    Called before worktree removal so signals survive any subsequent merge
    that could replace the signal directories with git blobs.

    Returns the backup path if files were copied, None if nothing to back up.
    """
    subdirs = ["signals", "failures", "synthesis", "absorbed", "wisdom"]
    backup_root = backup_root or (REPO_ROOT / "data" / "backups" / "learning")
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = backup_root / ts

    total = 0
    for d in subdirs:
        src_dir = REPO_ROOT / "memory" / "learning" / d
        if not src_dir.is_dir():
            continue
        for f in src_dir.glob("*.md"):
            dest_dir = dest / d
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest_dir / f.name)
            total += 1

    if total == 0:
        return None

    print(f"  Backed up {total} learning files -> {dest}")

    # Prune: keep last 7 backups
    try:
        all_backups = sorted(
            [p for p in backup_root.iterdir() if p.is_dir()],
            key=lambda p: p.name,
        )
        for old in all_backups[:-7]:
            shutil.rmtree(old, ignore_errors=True)
    except OSError:
        pass

    return dest


def worktree_setup(
    branch: str,
    worktree_dir: Optional[Path] = None,
    symlink_memory: bool = True,
) -> Optional[Path]:
    """Create a git worktree for the given branch. Returns worktree path.

    Args:
        branch: Git branch name to create in the worktree.
        worktree_dir: Directory for the worktree. Defaults to ../epdev-worktree.
        symlink_memory: Whether to symlink gitignored memory dirs into worktree.

    Returns:
        Path to the worktree, or None on failure.
    """
    wt = worktree_dir or (REPO_ROOT.parent / "epdev-worktree")

    # Clean up stale worktree if it exists (crash recovery)
    if wt.exists():
        print(f"  Cleaning up stale worktree at {wt}")
        backup_learning_signals()  # protect signals before stale worktree removal
        if not _safe_worktree_remove(wt):
            print(
                f"ERROR: stale worktree removal aborted — "
                f"not creating new worktree to avoid compounding risk.",
                file=sys.stderr,
            )
            return None

    # Delete stale branch if it exists (from previous run)
    subprocess.run(
        ["git", "branch", "-D", branch],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )

    # Create worktree with new branch.
    # Retry on WinError 1455 (paging file too small) -- transient OOM at 04:00
    # can resolve if other processes free memory. Up to 3 attempts with backoff.
    import time as _time
    result = None
    for attempt in range(3):
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(wt)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            break
        stderr = (result.stderr or "")
        is_oom = ("1455" in stderr) or ("paging file" in stderr.lower())
        if not is_oom or attempt == 2:
            break
        wait_s = 30 * (attempt + 1)
        print(
            f"  WARN: worktree add hit WinError 1455 (paging file too small). "
            f"Retrying in {wait_s}s (attempt {attempt + 2}/3)",
            file=sys.stderr,
        )
        _time.sleep(wait_s)
        # Clean up partial branch state from failed attempt
        subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )

    if result is None or result.returncode != 0:
        stderr = (result.stderr.strip() if result else "no result")
        print(
            f"ERROR: Failed to create worktree: {stderr}",
            file=sys.stderr,
        )
        return None

    print(f"  Worktree created at {wt} (branch: {branch})")

    if symlink_memory:
        if not _symlink_local_memory(wt):
            print(
                f"  ERROR: memory link hide failed — removing worktree to prevent "
                f"signal file deletion on next merge.",
                file=sys.stderr,
            )
            _safe_worktree_remove(wt)
            return None

    return wt


def _is_junction(path: Path) -> bool:
    """Check if path is a Windows junction point (reparse point)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return attrs != -1 and bool(attrs & 0x400)
    except (OSError, AttributeError):
        return False


def _find_reparse_points(root: Path) -> list[Path]:
    """Return all directory reparse points (junctions/symlinks) under root.

    Walks without following reparse points — junctions are collected, not
    descended into. Root itself is not returned.
    """
    found: list[Path] = []
    if not root.exists():
        return found
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            p = Path(e.path)
            try:
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            if _is_junction(p) or p.is_symlink():
                found.append(p)
            else:
                stack.append(p)
    return found


def _safe_worktree_remove(wt: Path) -> bool:
    """Remove a worktree safely on Windows.

    Pre-unlinks any reparse points under wt/memory/ via os.rmdir (which
    removes the junction without following it), then re-verifies none
    survive before invoking ``git worktree remove --force``. Aborts the
    git call if any reparse point persists — preventing git's bundled
    rm-rf from traversing a junction and deleting the main repo's
    learning data (2026-04-10 incident).

    Returns True when removal was attempted (or worktree already absent),
    False when aborted due to surviving reparse points.
    """
    if not wt.exists():
        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )
        return True

    memory_root = wt / "memory"
    for p in _find_reparse_points(memory_root):
        try:
            os.rmdir(str(p))
        except OSError as exc:
            print(
                f"  WARN: could not unlink reparse point {p}: {exc}",
                file=sys.stderr,
            )

    survivors = _find_reparse_points(memory_root)
    if survivors:
        print(
            f"  ABORT worktree removal: {len(survivors)} reparse point(s) "
            f"survived unlink; refusing 'git worktree remove' to prevent "
            f"destruction of junction targets. Survivors: "
            f"{[str(p) for p in survivors]}",
            file=sys.stderr,
        )
        return False

    subprocess.run(
        ["git", "worktree", "remove", str(wt), "--force"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )
    subprocess.run(
        ["git", "worktree", "prune"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )
    return True


def _exclude_file_has_line(existing: str, pattern: str) -> bool:
    """True if exclude file text already contains this exact non-comment line."""
    for raw in existing.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == pattern:
            return True
    return False


def _hide_symlink_from_git(wt: Path, rel_path: str) -> None:
    """Hide symlink/junction from git so it is never committed back to main.

    Two operations:
    1. --skip-worktree on every tracked file under rel_path: git pretends
       those files are unchanged even though the dir is now a junction.
       Unlike 'git rm --cached', this leaves the index entry intact and
       stages no deletion — so git status / git add -A see nothing.
    2. Add anchored exclude patterns under .git/info/exclude so the junction
       directory and everything under it stay off git status. Windows
       junctions see huge untracked trees; `/path`, `/path/`, and `/path/**`
       together fix the 2026-04-22 leak (`?? memory/learning/signals`).

    Called after a symlink/junction is created in the worktree so the
    replacement is never committed and never merged back into main.
    """
    # Mark every tracked file under rel_path as skip-worktree
    ls = subprocess.run(
        ["git", "ls-files", rel_path],
        capture_output=True, text=True, encoding="utf-8", cwd=str(wt),
    )
    for tracked in ls.stdout.splitlines():
        tracked = tracked.strip()
        if tracked:
            subprocess.run(
                ["git", "update-index", "--skip-worktree", tracked],
                capture_output=True, cwd=str(wt),
            )

    # Add to worktree-local exclude so the symlink/junction is invisible to git add -A.
    # In git worktrees, wt/.git is a FILE pointing to the real gitdir
    # (main_repo/.git/worktrees/<name>) -- constructing wt/.git/info/exclude directly
    # raises WinError 183 on Windows. Resolve the real gitdir via git rev-parse.
    # See 2026-04-21_self-diagnose-overnight-runner.md (severity 6).
    try:
        gitdir_proc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(wt), check=True,
        )
        gitdir_raw = gitdir_proc.stdout.strip()
        gitdir = Path(gitdir_raw)
        if not gitdir.is_absolute():
            gitdir = (wt / gitdir).resolve()
        exclude_path = gitdir / "info" / "exclude"
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
        patterns = (f"/{rel_path}", f"/{rel_path}/", f"/{rel_path}/**")
        to_add = [p for p in patterns if not _exclude_file_has_line(existing, p)]
        if to_add:
            block = "\n# jarvis: hide memory junction from index (overnight worktree)\n"
            block += "\n".join(to_add) + "\n"
            with open(exclude_path, "a", encoding="utf-8") as f:
                f.write(block)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"  WARNING: Could not update .git/info/exclude for {rel_path}: {exc}",
              file=sys.stderr)


def _debug_worktree_exclude_tail(wt: Path, max_lines: int = 40) -> str:
    """Last lines of this worktree's info/exclude (for diagnostics on hide failure)."""
    try:
        gitdir_proc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(wt), check=True,
        )
        gitdir_raw = gitdir_proc.stdout.strip()
        gitdir = Path(gitdir_raw)
        if not gitdir.is_absolute():
            gitdir = (wt / gitdir).resolve()
        exclude_path = gitdir / "info" / "exclude"
        if not exclude_path.is_file():
            return f"(no exclude file at {exclude_path})"
        lines = exclude_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        return "\n".join(tail)
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"(could not read exclude: {exc})"


def _symlink_local_memory(wt: Path) -> bool:
    """Replace gitkeep-only dirs in worktree with symlinks to real local dirs.

    Lets workers read accumulated signals/synthesis/failures that are
    gitignored (personal content stays local).

    On Windows, directory junctions (``mklink /J``) are preferred over file
    symlinks so behavior matches the common unprivileged path and the
    triple-pattern ``info/exclude`` hide (see 4da029e; 2026-04-22 04:00 runs
    predated that fix and still used the older single-line exclude).

    Returns True if all memory links were successfully hidden from git.
    Returns False if any link leaked into the git index — caller must
    abort the worktree to prevent the next merge from deleting signal files.
    """
    for rel_path, readonly in _MEMORY_SYMLINKS:
        src = REPO_ROOT / rel_path
        dst = wt / rel_path

        if not src.is_dir():
            continue

        # Remove the worktree's empty dir (contains only .gitkeep).
        # Check for junction points (Windows) which report is_dir=True
        # but is_symlink=False. Removing a junction with rmtree would
        # delete the real files in the main repo.
        if dst.is_dir() and not dst.is_symlink() and not _is_junction(dst):
            shutil.rmtree(dst)

        if dst.exists() or dst.is_symlink() or _is_junction(dst):
            # Already linked — still ensure git index is clean (idempotent)
            _hide_symlink_from_git(wt, rel_path)
            continue

        linked = False
        mode = "read-only" if readonly else "read-write"
        # Windows: prefer junction first (unprivileged, same as CI and most
        # laptops). Symlink first caused "Symlinked" logs while exclude+status
        # behavior was validated primarily on junctions.
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
                if result.returncode == 0:
                    print(f"  Junction {rel_path} -> {src} ({mode})")
                    _hide_symlink_from_git(wt, rel_path)
                    linked = True
                else:
                    err = (result.stderr or result.stdout or "").strip()
                    print(
                        f"  WARNING: Junction failed for {rel_path}: {err}",
                        file=sys.stderr,
                    )
            except OSError as exc2:
                print(
                    f"  WARNING: Junction mklink failed for {rel_path}: {exc2}",
                    file=sys.stderr,
                )
        if not linked:
            try:
                dst.symlink_to(src, target_is_directory=True)
                print(f"  Symlinked {rel_path} -> {src} ({mode})")
                _hide_symlink_from_git(wt, rel_path)
            except OSError as exc:
                if os.name == "nt":
                    print(
                        f"  WARNING: Could not symlink {rel_path} after junction: {exc}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"  WARNING: Could not symlink {rel_path}: {exc}",
                        file=sys.stderr,
                    )

    # Verify: no memory link leaked into the git index.
    # If git status sees any change at a memory/learning path, the hide failed —
    # merging this branch back to main would replace the real directory with a
    # blob and destroy all untracked signal files.
    leaked = []
    for rel_path, _ in _MEMORY_SYMLINKS:
        check = subprocess.run(
            ["git", "status", "--porcelain", rel_path],
            capture_output=True, text=True, encoding="utf-8", cwd=str(wt),
        )
        if check.stdout.strip():
            leaked.append((rel_path, check.stdout.strip()))

    if leaked:
        print(
            f"  ERROR: {len(leaked)} memory link(s) leaked into git index after hide:",
            file=sys.stderr,
        )
        for path, status in leaked:
            print(f"    {path}: {status}", file=sys.stderr)
        print(
            "  DEBUG: tail of worktree info/exclude:",
            file=sys.stderr,
        )
        for line in _debug_worktree_exclude_tail(wt).splitlines():
            print(f"    | {line}", file=sys.stderr)
        print(
            "  CRITICAL: merging this branch would delete all signal files. "
            "Caller must remove this worktree.",
            file=sys.stderr,
        )
        return False

    return True


def worktree_cleanup(worktree_dir: Optional[Path] = None) -> None:
    """Remove the worktree. Safe to call even if it doesn't exist."""
    wt = worktree_dir or (REPO_ROOT.parent / "epdev-worktree")
    backup_learning_signals()  # snapshot before any removal that could follow junctions
    _safe_worktree_remove(wt)


def cleanup_old_branches(prefix: str, days: int = 7) -> None:
    """Delete branches matching prefix* older than N days.

    Uses the last commit date on each branch (not branch name parsing),
    so it works for both date-named branches (jarvis/overnight-2026-03-31)
    and ID-named branches (jarvis/auto-5b-004).
    """
    cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()

    result = subprocess.run(
        ["git", "branch", "--list", f"{prefix}*"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT),
    )
    for line in result.stdout.splitlines():
        branch_name = line.strip().lstrip("* ")
        if not branch_name:
            continue

        # Get the last commit's Unix timestamp on this branch
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", branch_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )
        if date_result.returncode != 0 or not date_result.stdout.strip():
            continue

        try:
            commit_ts = float(date_result.stdout.strip())
        except ValueError:
            continue

        if commit_ts < cutoff_ts:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(REPO_ROOT),
            )
            print(f"  Cleaned up old branch: {branch_name}")


def git_diff_stat(cwd: Optional[str] = None) -> str:
    """Get diff stat for latest commit."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD~1..HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd or str(REPO_ROOT),
    )
    return result.stdout.strip() if result.returncode == 0 else "(no diff available)"


def git_diff_files(branch: str, base: str = "main", cwd: Optional[str] = None) -> list[str]:
    """Return list of files changed on branch vs base.

    Uses the merge-base (three-dot diff) so only commits on the branch are
    counted -- not unrelated changes on main that happened after the branch
    was created.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{branch}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd or str(REPO_ROOT),
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def git_commit_count(branch: str, base: str = "main", cwd: Optional[str] = None) -> int:
    """Return number of commits on branch ahead of base (merge-base)."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base}...{branch}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd or str(REPO_ROOT),
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0
