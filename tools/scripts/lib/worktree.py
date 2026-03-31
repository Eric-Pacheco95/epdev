"""Reusable git worktree library for Jarvis autonomous execution.

Extracted from overnight_runner.py. Provides worktree create/cleanup,
branch management, and memory symlink support. Used by both the
overnight runner and the autonomous dispatcher.

All operations target a sibling directory so the main working tree is
never touched -- no stash, no branch switch, no conflict with active
Claude Code sessions.
"""

from __future__ import annotations

import os
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
