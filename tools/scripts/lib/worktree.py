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
        subprocess.run(
            ["git", "worktree", "remove", str(wt), "--force"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )

    # Delete stale branch if it exists (from previous run)
    subprocess.run(
        ["git", "branch", "-D", branch],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )

    # Create worktree with new branch
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(wt)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(
            f"ERROR: Failed to create worktree: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return None

    print(f"  Worktree created at {wt} (branch: {branch})")

    if symlink_memory:
        _symlink_local_memory(wt)

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


def _symlink_local_memory(wt: Path) -> None:
    """Replace gitkeep-only dirs in worktree with symlinks to real local dirs.

    Lets workers read accumulated signals/synthesis/failures that are
    gitignored (personal content stays local).
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
            continue

        try:
            dst.symlink_to(src, target_is_directory=True)
            mode = "read-only" if readonly else "read-write"
            print(f"  Symlinked {rel_path} -> {src} ({mode})")
        except OSError:
            # Symlinks require admin/Developer Mode on Windows.
            # Fall back to junction points (mklink /J) which work unprivileged.
            if os.name == "nt":
                try:
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                        capture_output=True, text=True, encoding="utf-8",
                    )
                    if result.returncode == 0:
                        mode = "read-only" if readonly else "read-write"
                        print(f"  Junction {rel_path} -> {src} ({mode})")
                    else:
                        print(
                            f"  WARNING: Junction failed for {rel_path}: {result.stderr.strip()}",
                            file=sys.stderr,
                        )
                except OSError as exc2:
                    print(
                        f"  WARNING: Could not link {rel_path}: {exc2}",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"  WARNING: Could not symlink {rel_path}",
                    file=sys.stderr,
                )


def worktree_cleanup(worktree_dir: Optional[Path] = None) -> None:
    """Remove the worktree. Safe to call even if it doesn't exist."""
    wt = worktree_dir or (REPO_ROOT.parent / "epdev-worktree")
    if wt.exists():
        subprocess.run(
            ["git", "worktree", "remove", str(wt), "--force"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
    subprocess.run(
        ["git", "worktree", "prune"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )


def cleanup_old_branches(prefix: str, days: int = 7) -> None:
    """Delete branches matching prefix* older than N days.

    Uses the last commit date on each branch (not branch name parsing),
    so it works for both date-named branches (jarvis/overnight-2026-03-31)
    and ID-named branches (jarvis/auto-5b-004).
    """
    cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()

    result = subprocess.run(
        ["git", "branch", "--list", f"{prefix}*"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    for line in result.stdout.splitlines():
        branch_name = line.strip().lstrip("* ")
        if not branch_name:
            continue

        # Get the last commit's Unix timestamp on this branch
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", branch_name],
            capture_output=True, text=True, encoding="utf-8",
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
                capture_output=True, text=True, encoding="utf-8",
                cwd=str(REPO_ROOT),
            )
            print(f"  Cleaned up old branch: {branch_name}")


def git_diff_stat(cwd: Optional[str] = None) -> str:
    """Get diff stat for latest commit."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD~1..HEAD"],
        capture_output=True, text=True, encoding="utf-8",
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
        capture_output=True, text=True, encoding="utf-8",
        cwd=cwd or str(REPO_ROOT),
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def git_commit_count(branch: str, base: str = "main", cwd: Optional[str] = None) -> int:
    """Return number of commits on branch ahead of base (merge-base)."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base}...{branch}"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=cwd or str(REPO_ROOT),
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0
