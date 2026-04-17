"""Tests for jarvis_config.py -- is_protected() and constants."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "jarvis_config.py"


def _load():
    spec = importlib.util.spec_from_file_location("jarvis_config", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestIsProtected:
    def test_telos_md_is_protected(self, tmp_path):
        mod = _load()
        f = tmp_path / "TELOS.md"
        f.write_text("content")
        assert mod.is_protected(f, tmp_path) is True

    def test_claude_md_is_protected(self, tmp_path):
        mod = _load()
        f = tmp_path / "CLAUDE.md"
        f.write_text("content")
        assert mod.is_protected(f, tmp_path) is True

    def test_constitutional_rules_is_protected(self, tmp_path):
        mod = _load()
        f = tmp_path / "constitutional-rules.md"
        f.write_text("content")
        assert mod.is_protected(f, tmp_path) is True

    def test_normal_file_is_not_protected(self, tmp_path):
        mod = _load()
        f = tmp_path / "some_script.py"
        f.write_text("code")
        assert mod.is_protected(f, tmp_path) is False

    def test_file_in_protected_dir_is_protected(self, tmp_path):
        mod = _load()
        protected_dir = tmp_path / "memory" / "work" / "telos"
        protected_dir.mkdir(parents=True)
        f = protected_dir / "goals.md"
        f.write_text("goals")
        assert mod.is_protected(f, tmp_path) is True

    def test_file_outside_protected_dir_not_protected(self, tmp_path):
        mod = _load()
        # memory/work/ is now fully protected; use an unprotected top-level dir
        normal_dir = tmp_path / "logs" / "other"
        normal_dir.mkdir(parents=True)
        f = normal_dir / "notes.md"
        f.write_text("notes")
        assert mod.is_protected(f, tmp_path) is False

    def test_outside_repo_root_not_protected(self, tmp_path):
        mod = _load()
        outside = tmp_path.parent / "outside_repo.md"
        outside.write_text("content")
        assert mod.is_protected(outside, tmp_path) is False


class TestConstants:
    def test_protected_files_is_set(self):
        mod = _load()
        assert isinstance(mod.PROTECTED_FILES, set)

    def test_protected_files_contains_key_entries(self):
        mod = _load()
        assert "TELOS.md" in mod.PROTECTED_FILES
        assert "CLAUDE.md" in mod.PROTECTED_FILES
        assert "constitutional-rules.md" in mod.PROTECTED_FILES

    def test_protected_dir_prefixes_is_set(self):
        mod = _load()
        assert isinstance(mod.PROTECTED_DIR_PREFIXES, set)

    def test_telos_dir_in_prefixes(self):
        mod = _load()
        assert any("telos" in p for p in mod.PROTECTED_DIR_PREFIXES)
