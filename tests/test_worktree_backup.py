"""Tests for lib/worktree.py -- backup_learning_signals."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.lib.worktree as wt_mod
from tools.scripts.lib.worktree import backup_learning_signals


def _make_signals(repo_root: Path, subdir: str, filenames: list[str]) -> None:
    d = repo_root / "memory" / "learning" / subdir
    d.mkdir(parents=True, exist_ok=True)
    for name in filenames:
        (d / name).write_text(f"# {name}\ncontent", encoding="utf-8")


class TestBackupLearningSignals:
    def test_no_learning_files_returns_none(self, tmp_path):
        fake_repo = tmp_path / "repo"
        fake_repo.mkdir()
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is None

    def test_copies_signals_md_files(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "signals", ["sig1.md", "sig2.md"])
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is not None
        copied = list((result / "signals").glob("*.md"))
        assert len(copied) == 2

    def test_copies_failures_md_files(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "failures", ["fail1.md"])
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is not None
        assert (result / "failures" / "fail1.md").exists()

    def test_skips_non_md_files(self, tmp_path):
        fake_repo = tmp_path / "repo"
        d = fake_repo / "memory" / "learning" / "signals"
        d.mkdir(parents=True, exist_ok=True)
        (d / "signal.md").write_text("# sig", encoding="utf-8")
        (d / "data.json").write_text("{}", encoding="utf-8")
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is not None
        backed_up = list(result.rglob("*"))
        names = [f.name for f in backed_up if f.is_file()]
        assert "signal.md" in names
        assert "data.json" not in names

    def test_creates_backup_root_if_missing(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "signals", ["sig.md"])
        backup_root = tmp_path / "new" / "backup" / "dir"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is not None
        assert result.exists()

    def test_returns_timestamped_path(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "wisdom", ["w1.md"])
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert result is not None
        # Timestamp format: YYYY-MM-DD_HHMMSS
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{6}", result.name)

    def test_multiple_subdirs_all_backed_up(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "signals", ["s.md"])
        _make_signals(fake_repo, "failures", ["f.md"])
        _make_signals(fake_repo, "absorbed", ["a.md"])
        backup_root = tmp_path / "backups"
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            result = backup_learning_signals(backup_root=backup_root)
        assert (result / "signals" / "s.md").exists()
        assert (result / "failures" / "f.md").exists()
        assert (result / "absorbed" / "a.md").exists()

    def test_prunes_old_backups_keeps_7(self, tmp_path):
        fake_repo = tmp_path / "repo"
        _make_signals(fake_repo, "signals", ["s.md"])
        backup_root = tmp_path / "backups"
        # Pre-create 9 old backup dirs
        for i in range(9):
            old = backup_root / f"2026-01-0{i if i < 9 else 9}_120000"
            old.mkdir(parents=True)
        with mock.patch.object(wt_mod, "REPO_ROOT", fake_repo):
            backup_learning_signals(backup_root=backup_root)
        remaining = sorted(p for p in backup_root.iterdir() if p.is_dir())
        assert len(remaining) <= 7
