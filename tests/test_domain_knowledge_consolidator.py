"""Tests for domain_knowledge_consolidator -- _enforce_cap and _detect_domains."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.domain_knowledge_consolidator as dkc
from tools.scripts.domain_knowledge_consolidator import _enforce_cap, _detect_domains


class TestEnforceCap:
    def test_returns_content_unchanged_when_under_cap(self):
        content = "short content"
        result = _enforce_cap(content, cap=1000, label="test")
        assert result == content

    def test_truncates_and_adds_notice_when_over_cap(self):
        content = "x" * 200
        result = _enforce_cap(content, cap=100, label="test.md")
        assert len(result) <= 100
        assert "TRUNCATED" in result

    def test_exact_cap_not_truncated(self):
        content = "a" * 50
        result = _enforce_cap(content, cap=50, label="test")
        assert result == content

    def test_truncation_notice_includes_label(self):
        result = _enforce_cap("x" * 200, cap=100, label="my_domain.md")
        assert "my_domain.md" in result


class TestDetectDomains:
    def test_returns_empty_when_knowledge_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", tmp_path / "nonexistent")
        result = _detect_domains({})
        assert result == []

    def test_returns_subdirectory_names(self, tmp_path, monkeypatch):
        (tmp_path / "crypto").mkdir()
        (tmp_path / "fintech").mkdir()
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", tmp_path)
        result = _detect_domains({})
        assert "crypto" in result
        assert "fintech" in result

    def test_excludes_hidden_dirs(self, tmp_path, monkeypatch):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible").mkdir()
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", tmp_path)
        result = _detect_domains({})
        assert ".hidden" not in result
        assert "visible" in result

    def test_excludes_files_returns_only_dirs(self, tmp_path, monkeypatch):
        (tmp_path / "domain_dir").mkdir()
        (tmp_path / "_context.md").write_text("x")
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", tmp_path)
        result = _detect_domains({})
        assert "_context.md" not in result
