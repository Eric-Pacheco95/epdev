"""Tests for verify_synthesis_recall -- parse_synthesis and is_recent."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.verify_synthesis_recall import parse_synthesis, is_recent


def _write_synthesis(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "synthesis.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestParseSynthesis:
    def test_empty_file_returns_zero(self, tmp_path):
        p = _write_synthesis(tmp_path, "")
        cited, themes = parse_synthesis(p)
        assert cited == set()
        assert themes == 0

    def test_parses_supporting_signals_line(self, tmp_path):
        lines = [
            "### Theme: Test Theme",
            "- Supporting signals: signal_2026-01-01.md, signal_2026-01-02.md",
        ]
        p = _write_synthesis(tmp_path, chr(10).join(lines))
        cited, themes = parse_synthesis(p)
        assert "signal_2026-01-01.md" in cited
        assert "signal_2026-01-02.md" in cited
        assert themes == 1

    def test_skips_none_placeholder(self, tmp_path):
        lines = [
            "### Theme: Empty Theme",
            "- Supporting signals: none",
        ]
        p = _write_synthesis(tmp_path, chr(10).join(lines))
        cited, themes = parse_synthesis(p)
        assert len(cited) == 0
        assert themes == 0

    def test_deduplicates_citations(self, tmp_path):
        lines = [
            "### Theme: Dup Theme",
            "- Supporting signals: dup.md, dup.md",
        ]
        p = _write_synthesis(tmp_path, chr(10).join(lines))
        cited, _ = parse_synthesis(p)
        assert len(cited) == 1

    def test_multiple_themes_counted_separately(self, tmp_path):
        lines = [
            "### Theme: Theme A",
            "- Supporting signals: a.md",
            "### Theme: Theme B",
            "- Supporting signals: b.md",
        ]
        p = _write_synthesis(tmp_path, chr(10).join(lines))
        cited, themes = parse_synthesis(p)
        assert len(cited) == 2
        assert themes == 2


class TestIsRecent:
    def test_new_file_is_recent(self, tmp_path):
        p = tmp_path / "synth.md"
        p.write_text("x")
        assert is_recent(p) is True

    def test_missing_file_is_not_recent(self, tmp_path):
        assert is_recent(tmp_path / "missing.md") is False
