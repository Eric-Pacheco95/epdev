"""Tests for domain_knowledge_consolidator -- _enforce_cap and _detect_domains."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.domain_knowledge_consolidator as dkc
from tools.scripts.domain_knowledge_consolidator import (
    _enforce_cap, _detect_domains, _write_context_md, _write_subdomain_file,
    _build_synthesis_prompt, _read_synthesis_theme_hints,
)


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


class TestWriteContextMd:
    def test_dry_run_does_not_write(self, tmp_path):
        domain_dir = tmp_path / "domain"
        _write_context_md(domain_dir, "content", dry_run=True)
        assert not (domain_dir / "_context.md").exists()

    def test_writes_file_when_not_dry_run(self, tmp_path):
        domain_dir = tmp_path / "domain"
        _write_context_md(domain_dir, "hello", dry_run=False)
        assert (domain_dir / "_context.md").read_text() == "hello"

    def test_creates_parent_dirs(self, tmp_path):
        domain_dir = tmp_path / "nested" / "domain"
        _write_context_md(domain_dir, "x", dry_run=False)
        assert domain_dir.is_dir()

    def test_returns_byte_length(self, tmp_path):
        domain_dir = tmp_path / "domain"
        n = _write_context_md(domain_dir, "abc", dry_run=True)
        assert n == 3


class TestWriteSubdomainFile:
    def test_dry_run_does_not_write(self, tmp_path):
        _write_subdomain_file(tmp_path / "dom", "agents", "content", [], dry_run=True)
        assert not (tmp_path / "dom" / "agents.md").exists()

    def test_writes_file_with_correct_name(self, tmp_path):
        domain_dir = tmp_path / "dom"
        _write_subdomain_file(domain_dir, "agents", "body", [], dry_run=False)
        assert (domain_dir / "agents.md").exists()

    def test_injects_caveats_when_present(self, tmp_path):
        domain_dir = tmp_path / "dom"
        _write_subdomain_file(domain_dir, "agents", "body", ["check this"], dry_run=False)
        text = (domain_dir / "agents.md").read_text()
        assert "Caveats" in text
        assert "check this" in text

    def test_no_duplicate_caveats_if_already_present(self, tmp_path):
        domain_dir = tmp_path / "dom"
        content = "## body\n\n## Caveats\n- existing\n"
        _write_subdomain_file(domain_dir, "agents", content, ["new"], dry_run=False)
        text = (domain_dir / "agents.md").read_text()
        assert text.count("## Caveats") == 1


class TestLoadState:
    def test_returns_empty_dict_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dkc, "STATE_FILE", tmp_path / "state.json")
        result = dkc._load_state()
        assert result == {}

    def test_loads_valid_state(self, tmp_path, monkeypatch):
        import json
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"domains": ["crypto", "fintech"]}), encoding="utf-8")
        monkeypatch.setattr(dkc, "STATE_FILE", f)
        result = dkc._load_state()
        assert result["domains"] == ["crypto", "fintech"]

    def test_returns_empty_on_invalid_json(self, tmp_path, monkeypatch):
        f = tmp_path / "state.json"
        f.write_text("not valid json", encoding="utf-8")
        monkeypatch.setattr(dkc, "STATE_FILE", f)
        result = dkc._load_state()
        assert result == {}

    def test_returns_empty_if_top_level_is_not_dict(self, tmp_path, monkeypatch):
        import json
        f = tmp_path / "state.json"
        f.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
        monkeypatch.setattr(dkc, "STATE_FILE", f)
        result = dkc._load_state()
        assert result == {}


# ---------------------------------------------------------------------------
# _build_synthesis_prompt
# ---------------------------------------------------------------------------

class TestBuildSynthesisPrompt:
    def test_contains_domain_name(self):
        prompt = _build_synthesis_prompt("crypto", [])
        assert "crypto" in prompt

    def test_contains_source_count(self):
        sources = [{"filename": "a.md", "content": "hello", "source_type": "raw"}]
        prompt = _build_synthesis_prompt("market", sources)
        assert "1" in prompt

    def test_includes_existing_context_when_provided(self):
        prompt = _build_synthesis_prompt("geopolitics", [], existing_context="Prior knowledge here")
        assert "Prior knowledge here" in prompt

    def test_omits_context_section_when_empty(self):
        prompt = _build_synthesis_prompt("tech", [], existing_context="")
        assert "Existing _context.md" not in prompt

    def test_includes_article_filename(self):
        sources = [{"filename": "2026-01-15_article.md", "content": "body", "source_type": "raw"}]
        prompt = _build_synthesis_prompt("cooking", sources)
        assert "2026-01-15_article.md" in prompt


# ---------------------------------------------------------------------------
# _read_synthesis_theme_hints
# ---------------------------------------------------------------------------

class TestReadSynthesisThemeHints:
    def test_missing_synthesis_dir_returns_empty(self, monkeypatch):
        monkeypatch.setattr(dkc, "SYNTHESIS_DIR", Path("/no/such/dir"))
        assert _read_synthesis_theme_hints() == []

    def test_returns_themes_from_synthesis_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dkc, "SYNTHESIS_DIR", tmp_path)
        f = tmp_path / "2026-04-01_synthesis.md"
        f.write_text("### Theme 1: Agent Orchestration\nsome content\n### Theme 2: Harness Tooling\n")
        hints = _read_synthesis_theme_hints()
        assert "Agent Orchestration" in hints
        assert "Harness Tooling" in hints

    def test_reads_only_last_three_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dkc, "SYNTHESIS_DIR", tmp_path)
        for i in range(5):
            f = tmp_path / f"2026-04-0{i+1}_synthesis.md"
            f.write_text(f"### Theme 1: Topic{i}\n")
        hints = _read_synthesis_theme_hints()
        assert "Topic0" not in hints  # first two files excluded
        assert "Topic1" not in hints
