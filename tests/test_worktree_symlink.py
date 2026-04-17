"""Tests for _hide_symlink_from_git and _symlink_local_memory in lib/worktree.py.

These tests guard against the 2026-04-17 regression where memory/learning
symlinks created in a worktree were committed and merged back to main as
self-referential symlinks (git mode 120000).
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

import tools.scripts.lib.worktree as wt_mod
from tools.scripts.lib.worktree import _hide_symlink_from_git, _symlink_local_memory


def _git(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, encoding="utf-8", cwd=str(cwd),
    )


def _init_fake_worktree(tmp_path: Path) -> Path:
    """Create a minimal git repo mimicking an overnight worktree.

    Commits a .keep file in each _MEMORY_SYMLINKS path so the worktree
    starts in a clean state with tracked content — exactly as a real
    worktree looks before _symlink_local_memory runs.
    """
    wt = tmp_path / "epdev-worktree"
    wt.mkdir()

    _git(["init", "-b", "main"], wt)
    _git(["config", "user.email", "test@test.com"], wt)
    _git(["config", "user.name", "Test"], wt)
    # Disable symlink support so Windows tests don't need Developer Mode
    _git(["config", "core.symlinks", "false"], wt)

    for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
        keep = wt / rel_path / ".keep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch()
        _git(["add", str(keep.relative_to(wt))], wt)

    _git(["commit", "-m", "init: add .keep files"], wt)
    return wt


# ---------------------------------------------------------------------------
# _hide_symlink_from_git
# ---------------------------------------------------------------------------

class TestHideSymlinkFromGit:
    def test_keep_flagged_skip_worktree(self, tmp_path):
        """_hide_symlink_from_git sets --skip-worktree on .keep so git status ignores it."""
        wt = _init_fake_worktree(tmp_path)
        rel = "memory/learning/signals"

        _hide_symlink_from_git(wt, rel)

        # git ls-files -v shows 'S' prefix for skip-worktree entries
        ls_v = _git(["ls-files", "-v", f"{rel}/.keep"], wt)
        assert ls_v.stdout.strip().startswith("S "), (
            f"Expected skip-worktree flag (S), got: {ls_v.stdout.strip()!r}"
        )

    def test_adds_path_to_exclude(self, tmp_path):
        wt = _init_fake_worktree(tmp_path)
        rel = "memory/learning/synthesis"

        _hide_symlink_from_git(wt, rel)

        exclude = (wt / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        assert f"/{rel}" in exclude

    def test_idempotent_exclude(self, tmp_path):
        """Calling twice must not duplicate the exclude entry."""
        wt = _init_fake_worktree(tmp_path)
        rel = "memory/learning/failures"

        _hide_symlink_from_git(wt, rel)
        _hide_symlink_from_git(wt, rel)

        exclude = (wt / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        assert exclude.count(f"/{rel}") == 1

    def test_worktree_clean_after_hide(self, tmp_path):
        """After hiding all three paths, git status --porcelain must be empty."""
        wt = _init_fake_worktree(tmp_path)

        for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
            # Simulate the deletion that shutil.rmtree performs
            keep = wt / rel_path / ".keep"
            if keep.exists():
                keep.unlink()
            keep.parent.rmdir()
            # Write a fake symlink file (core.symlinks=false → plain text)
            (wt / rel_path).write_text(str(wt / rel_path), encoding="utf-8")
            _hide_symlink_from_git(wt, rel_path)

        status = _git(["status", "--porcelain"], wt)
        assert status.stdout.strip() == "", (
            f"Worktree should be clean after _hide_symlink_from_git, got:\n{status.stdout}"
        )


# ---------------------------------------------------------------------------
# _symlink_local_memory — integration: worktree stays git-clean
# ---------------------------------------------------------------------------

class TestSymlinkLocalMemory:
    def _make_src_dirs(self, tmp_path: Path) -> Path:
        """Create a fake REPO_ROOT with real memory/learning/* directories."""
        src_root = tmp_path / "epdev-main"
        for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
            (src_root / rel_path).mkdir(parents=True, exist_ok=True)
        return src_root

    def test_worktree_git_clean_after_symlink(self, tmp_path):
        """After _symlink_local_memory, git status inside the worktree is empty."""
        src_root = self._make_src_dirs(tmp_path)
        wt = _init_fake_worktree(tmp_path)

        with mock.patch.object(wt_mod, "REPO_ROOT", src_root):
            _symlink_local_memory(wt)

        status = _git(["status", "--porcelain"], wt)
        assert status.stdout.strip() == "", (
            f"Worktree should be git-clean after _symlink_local_memory, got:\n{status.stdout}"
        )

    def test_keep_skip_worktree_flagged_after_symlink(self, tmp_path):
        """After _symlink_local_memory, .keep files are skip-worktree flagged."""
        src_root = self._make_src_dirs(tmp_path)
        wt = _init_fake_worktree(tmp_path)

        with mock.patch.object(wt_mod, "REPO_ROOT", src_root):
            _symlink_local_memory(wt)

        for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
            ls_v = _git(["ls-files", "-v", f"{rel_path}/.keep"], wt)
            assert ls_v.stdout.strip().startswith("S "), (
                f"{rel_path}/.keep missing skip-worktree flag: {ls_v.stdout.strip()!r}"
            )

    def test_all_paths_in_exclude(self, tmp_path):
        """All _MEMORY_SYMLINKS paths are added to .git/info/exclude."""
        src_root = self._make_src_dirs(tmp_path)
        wt = _init_fake_worktree(tmp_path)

        with mock.patch.object(wt_mod, "REPO_ROOT", src_root):
            _symlink_local_memory(wt)

        exclude = (wt / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
            assert f"/{rel_path}" in exclude, (
                f"/{rel_path} missing from .git/info/exclude"
            )

    def test_skips_when_src_missing(self, tmp_path):
        """Paths whose src does not exist on disk are skipped (no crash)."""
        src_root = tmp_path / "epdev-main"
        src_root.mkdir()
        # Don't create any memory/learning/* dirs — all are missing
        wt = _init_fake_worktree(tmp_path)

        with mock.patch.object(wt_mod, "REPO_ROOT", src_root):
            _symlink_local_memory(wt)  # must not raise

        # Index unchanged — .keep files still tracked
        for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
            ls = _git(["ls-files", f"{rel_path}/.keep"], wt)
            assert f"{rel_path}/.keep" in ls.stdout


# ---------------------------------------------------------------------------
# Regression: git index currently has no mode-120000 symlinks
# ---------------------------------------------------------------------------

def test_no_self_referential_symlinks_in_main_index():
    """Verify that memory/learning/{signals,synthesis,failures} are not symlinks in HEAD."""
    result = subprocess.run(
        ["git", "ls-files", "--stage",
         "memory/learning/signals", "memory/learning/synthesis", "memory/learning/failures"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(wt_mod.REPO_ROOT),
    )
    # Mode 120000 = symlink. None of these paths should appear at all as symlinks.
    for line in result.stdout.splitlines():
        assert not line.startswith("120000"), (
            f"Self-referential symlink still in git index: {line}"
        )

def test_memory_learning_dirs_are_real_directories():
    """Verify the three dirs are real directories, not symlinks, on disk."""
    for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
        p = wt_mod.REPO_ROOT / rel_path
        assert p.exists() and p.is_dir() and not p.is_symlink(), (
            f"{rel_path} is not a real directory: exists={p.exists()}, "
            f"is_dir={p.is_dir()}, is_symlink={p.is_symlink()}"
        )

def test_keep_files_tracked_in_main_index():
    """Verify .keep files for the three dirs are in the git index."""
    for rel_path, _ in wt_mod._MEMORY_SYMLINKS:
        result = subprocess.run(
            ["git", "ls-files", f"{rel_path}/.keep"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(wt_mod.REPO_ROOT),
        )
        assert f"{rel_path}/.keep" in result.stdout, (
            f"{rel_path}/.keep not tracked in git index"
        )
