"""Tests for verify_synthesis_recall -- parse_synthesis and is_recent."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_synthesis_recall as vsr
from tools.scripts.verify_synthesis_recall import (
    parse_synthesis, is_recent, most_recent_synthesis, resolve_signal,
)


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

    def test_old_file_is_not_recent(self, tmp_path):
        import os, time
        p = tmp_path / "old.md"
        p.write_text("x")
        old_time = time.time() - (30 * 86400)  # 30 days ago
        os.utime(p, (old_time, old_time))
        assert is_recent(p) is False


class TestMostRecentSynthesis:
    def test_missing_dir_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SYNTH_DIR", tmp_path / "nosuchdir")
        assert most_recent_synthesis() is None

    def test_empty_dir_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SYNTH_DIR", tmp_path)
        assert most_recent_synthesis() is None

    def test_returns_single_md_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SYNTH_DIR", tmp_path)
        p = tmp_path / "synth.md"
        p.write_text("x")
        assert most_recent_synthesis() == p

    def test_returns_most_recent_of_multiple(self, tmp_path, monkeypatch):
        import os, time
        monkeypatch.setattr(vsr, "SYNTH_DIR", tmp_path)
        older = tmp_path / "older.md"
        newer = tmp_path / "newer.md"
        older.write_text("a")
        newer.write_text("b")
        os.utime(older, (time.time() - 100, time.time() - 100))
        os.utime(newer, (time.time(), time.time()))
        assert most_recent_synthesis() == newer

    def test_ignores_non_md_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SYNTH_DIR", tmp_path)
        (tmp_path / "synth.txt").write_text("x")
        assert most_recent_synthesis() is None


class TestResolveSignal:
    def test_file_in_signals_dir_resolves(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SIGNALS_DIR", tmp_path)
        monkeypatch.setattr(vsr, "PROCESSED_DIR", tmp_path / "processed")
        monkeypatch.setattr(vsr, "ABSORBED_DIR", tmp_path / "absorbed")
        monkeypatch.setattr(vsr, "ABSORBED_PROCESSED", tmp_path / "absorbed" / "processed")
        (tmp_path / "sig1.md").write_text("x")
        assert resolve_signal("sig1.md") is True

    def test_missing_file_does_not_resolve(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vsr, "SIGNALS_DIR", tmp_path)
        monkeypatch.setattr(vsr, "PROCESSED_DIR", tmp_path / "processed")
        monkeypatch.setattr(vsr, "ABSORBED_DIR", tmp_path / "absorbed")
        monkeypatch.setattr(vsr, "ABSORBED_PROCESSED", tmp_path / "absorbed" / "processed")
        assert resolve_signal("nosuchfile.md") is False
