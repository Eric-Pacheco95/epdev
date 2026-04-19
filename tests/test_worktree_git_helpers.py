"""Tests for lib/worktree git helper functions using real git repos."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.worktree import git_commit_count, git_diff_files


def _git(args, cwd):
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(cwd))


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "README.md").write_text("init")
    _git(["add", "README.md"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


class TestGitCommitCount:
    def test_zero_commits_ahead_on_same_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        count = git_commit_count("main", base="main", cwd=str(repo))
        assert count == 0

    def test_counts_commits_on_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        _git(["checkout", "-b", "feature"], repo)
        (repo / "new.txt").write_text("x")
        _git(["add", "new.txt"], repo)
        _git(["commit", "-m", "add new"], repo)
        count = git_commit_count("feature", base="main", cwd=str(repo))
        assert count == 1

    def test_invalid_branch_returns_zero(self, tmp_path):
        repo = _make_repo(tmp_path)
        count = git_commit_count("nonexistent-branch-xyz", base="main", cwd=str(repo))
        assert count == 0


class TestGitDiffFiles:
    def test_no_files_on_same_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        files = git_diff_files("main", base="main", cwd=str(repo))
        assert files == []

    def test_lists_changed_files_on_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        _git(["checkout", "-b", "feature"], repo)
        (repo / "changed.py").write_text("pass")
        _git(["add", "changed.py"], repo)
        _git(["commit", "-m", "add file"], repo)
        files = git_diff_files("feature", base="main", cwd=str(repo))
        assert "changed.py" in files

    def test_invalid_branch_returns_empty(self, tmp_path):
        repo = _make_repo(tmp_path)
        files = git_diff_files("nonexistent-xyz", base="main", cwd=str(repo))
        assert files == []
