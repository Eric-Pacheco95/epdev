"""Tests for tools/scripts/verify_autoresearch_outcome.py."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_autoresearch_outcome as vao


CFG = {"min_words": 300, "min_citation_urls": 3, "bytes_per_token_min_ratio": 2.0}


# --- _split_body_and_citations ---

class TestSplitBodyAndCitations:
    def test_no_citations_section_returns_full_body(self):
        text = "Some body text\nwith multiple lines."
        body, cites = vao._split_body_and_citations(text)
        assert body == text
        assert cites == ""

    def test_splits_at_citations_heading(self):
        text = "Body content here.\n\n## Citations\n\nhttps://example.com"
        body, cites = vao._split_body_and_citations(text)
        assert "Body content" in body
        assert "## Citations" in cites
        assert "https://example.com" in cites

    def test_splits_at_references_heading(self):
        text = "Body.\n\n## References\n\nhttps://ref.com"
        body, cites = vao._split_body_and_citations(text)
        assert "## References" in cites

    def test_case_insensitive_heading(self):
        text = "Body.\n\n## CITATIONS\n\nhttps://x.com"
        body, cites = vao._split_body_and_citations(text)
        assert "## CITATIONS" in cites

    def test_body_not_included_in_citations(self):
        text = "Pre-heading content.\n\n## Citations\nPost."
        body, cites = vao._split_body_and_citations(text)
        assert "Pre-heading" in body
        assert "Pre-heading" not in cites


# --- _find_target_file ---

class TestFindTargetFile:
    def test_returns_none_for_empty_dir(self, tmp_path):
        result = vao._find_target_file(tmp_path, None)
        assert result is None

    def test_returns_newest_file(self, tmp_path):
        import time
        f1 = tmp_path / "old.md"
        f1.write_text("old content", encoding="utf-8")
        time.sleep(0.02)
        f2 = tmp_path / "new.md"
        f2.write_text("new content", encoding="utf-8")
        result = vao._find_target_file(tmp_path, None)
        assert result.name == "new.md"

    def test_ignores_files_older_than_since_time(self, tmp_path):
        f = tmp_path / "old.md"
        f.write_text("content", encoding="utf-8")
        # since_time = far future
        future = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        result = vao._find_target_file(tmp_path, future)
        assert result is None

    def test_accepts_files_newer_than_since_time(self, tmp_path):
        f = tmp_path / "recent.md"
        f.write_text("content", encoding="utf-8")
        past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        result = vao._find_target_file(tmp_path, past)
        assert result is not None
        assert result.name == "recent.md"

    def test_non_md_files_ignored(self, tmp_path):
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")
        result = vao._find_target_file(tmp_path, None)
        assert result is None

    def test_recurses_into_subdirs(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        f = sub / "deep.md"
        f.write_text("deep content", encoding="utf-8")
        result = vao._find_target_file(tmp_path, None)
        assert result is not None
        assert result.name == "deep.md"


# --- verify_file ---

def _make_file(tmp_path, content, name="knowledge.md"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _enough_words(n=350):
    return " ".join(["word"] * n)


def _enough_urls(n=3):
    return "\n".join(f"https://source{i}.example.com/page" for i in range(n))


class TestVerifyFile:
    def test_passes_valid_file(self, tmp_path, capsys):
        content = _enough_words() + "\n" + _enough_urls()
        p = _make_file(tmp_path, content)
        rc = vao.verify_file(p, CFG, 0)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["exit_code"] == 0

    def test_fails_stub_too_few_words(self, tmp_path, capsys):
        content = "short " * 10 + "\n" + _enough_urls()
        p = _make_file(tmp_path, content)
        rc = vao.verify_file(p, CFG, 0)
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["reason"] == "stub_file_rejected"

    def test_fails_insufficient_citations(self, tmp_path, capsys):
        content = _enough_words() + "\nhttps://only-one.com"
        p = _make_file(tmp_path, content)
        rc = vao.verify_file(p, CFG, 0)
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["reason"] == "insufficient_citations"

    def test_fails_orphan_citations(self, tmp_path, capsys):
        body = _enough_words() + "\n" + _enough_urls()
        orphan_url = "https://orphan.example.com/not-in-body"
        content = body + "\n\n## Citations\n\n" + orphan_url
        p = _make_file(tmp_path, content)
        rc = vao.verify_file(p, CFG, 0)
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["reason"] == "orphan_citations"

    def test_no_orphan_when_url_appears_in_body(self, tmp_path, capsys):
        shared_url = "https://shared.example.com/page"
        body = _enough_words() + "\n" + _enough_urls() + "\n" + shared_url
        content = body + "\n\n## Citations\n\n" + shared_url
        p = _make_file(tmp_path, content)
        rc = vao.verify_file(p, CFG, 0)
        assert rc == 0
