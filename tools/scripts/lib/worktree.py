"""Reusable git worktree library for Jarvis autonomous execution.

Extracted from overnight_runner.py. Provides worktree create/cleanup,
branch management, and memory symlink support. Used by both the
overnight runner and the autonomous dispatcher.

All operations target a sibling directory so the main working tree is
never touched -- no stash, no branch switch, no conflict with active
Claude Code sessions.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]

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

        # Remove the worktree's empty dir (contains only .gitkeep)
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)

        if dst.exists() or dst.is_symlink():
            continue

        try:
            dst.symlink_to(src, target_is_directory=True)
            mode = "read-only" if readonly else "read-write"
            print(f"  Symlinked {rel_path} -> {src} ({mode})")
        except OSError as exc:
            print(
                f"  WARNING: Could not symlink {rel_path}: {exc}",
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
    """Delete branches matching prefix-* older than N days.

    Expects branch names like: prefix-YYYY-MM-DD or prefix-YYYY-MM-DD-suffix.
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = subprocess.run(
        ["git", "branch", "--list", f"{prefix}-*"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    for line in result.stdout.splitlines():
        branch_name = line.strip().lstrip("* ")
        # Extract date from branch name after the prefix
        after_prefix = branch_name[len(prefix) + 1:]  # skip "prefix-"
        parts = after_prefix.split("-")
        if len(parts) >= 3:
            try:
                branch_date = "-".join(parts[:3])
                if branch_date < cutoff:
                    subprocess.run(
                        ["git", "branch", "-D", branch_name],
                        capture_output=True, text=True, encoding="utf-8",
                        cwd=str(REPO_ROOT),
                    )
                    print(f"  Cleaned up old branch: {branch_name}")
            except (ValueError, IndexError):
                pass


def git_diff_stat(cwd: Optional[str] = None) -> str:
    """Get diff stat for latest commit."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD~1..HEAD"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=cwd or str(REPO_ROOT),
    )
    return result.stdout.strip() if result.returncode == 0 else "(no diff available)"
