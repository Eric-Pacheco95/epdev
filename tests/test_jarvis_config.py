"""Tests for jarvis_config.is_protected."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_config import is_protected, PROTECTED_FILES, PROTECTED_DIR_PREFIXES


class TestIsProtected:
    def test_protected_filename(self, tmp_path):
        f = tmp_path / "TELOS.md"
        f.touch()
        assert is_protected(f, tmp_path) is True

    def test_protected_dir_prefix(self, tmp_path):
        d = tmp_path / "memory" / "work" / "myfile.md"
        d.parent.mkdir(parents=True)
        d.touch()
        assert is_protected(d, tmp_path) is True

    def test_unprotected_file(self, tmp_path):
        f = tmp_path / "ordinary.md"
        f.touch()
        assert is_protected(f, tmp_path) is False

    def test_protected_constitutional_rules(self, tmp_path):
        f = tmp_path / "constitutional-rules.md"
        f.touch()
        assert is_protected(f, tmp_path) is True

    def test_protected_history_decisions(self, tmp_path):
        d = tmp_path / "history" / "decisions" / "dec.md"
        d.parent.mkdir(parents=True)
        d.touch()
        assert is_protected(d, tmp_path) is True

    def test_outside_repo_root_not_protected(self, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        f = other / "TELOS.md"
        f.touch()
        # Filename match still fires even outside repo root
        assert is_protected(f, fake_root) is True

    def test_claude_md_protected(self, tmp_path):
        f = tmp_path / "CLAUDE.md"
        f.touch()
        assert is_protected(f, tmp_path) is True
