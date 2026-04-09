"""Tests for verify_synthesis_routine.py helper functions."""
from __future__ import annotations

import time
from pathlib import Path
import sys
import types

import pytest


def _load_module(tmp_path: Path):
    """Import verify_synthesis_routine with SYNTH_DIR and SIGNALS_DIR patched to tmp dirs."""
    import importlib.util, importlib

    spec = importlib.util.spec_from_file_location(
        "verify_synthesis_routine",
        Path(__file__).parents[1] / "tools" / "scripts" / "verify_synthesis_routine.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# synthesis_created_today
# ---------------------------------------------------------------------------


class TestSynthesisCreatedToday:
    def test_missing_dir_returns_false(self, tmp_path, monkeypatch):
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", tmp_path / "nonexistent")
        assert mod.synthesis_created_today() is False

    def test_empty_dir_returns_false(self, tmp_path, monkeypatch):
        synth = tmp_path / "synthesis"
        synth.mkdir()
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", synth)
        assert mod.synthesis_created_today() is False

    def test_non_md_file_ignored(self, tmp_path, monkeypatch):
        synth = tmp_path / "synthesis"
        synth.mkdir()
        (synth / "today.txt").write_text("data")
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", synth)
        assert mod.synthesis_created_today() is False

    def test_md_file_modified_today_returns_true(self, tmp_path, monkeypatch):
        synth = tmp_path / "synthesis"
        synth.mkdir()
        f = synth / "synthesis.md"
        f.write_text("content")
        # mtime is now (today) by default
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", synth)
        assert mod.synthesis_created_today() is True

    def test_old_md_file_returns_false(self, tmp_path, monkeypatch):
        synth = tmp_path / "synthesis"
        synth.mkdir()
        f = synth / "old.md"
        f.write_text("old content")
        # Set mtime 10 days in the past
        old_time = time.time() - 10 * 86400
        import os
        os.utime(f, (old_time, old_time))
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", synth)
        assert mod.synthesis_created_today() is False


# ---------------------------------------------------------------------------
# unprocessed_signals_queued
# ---------------------------------------------------------------------------


class TestUnprocessedSignalsQueued:
    def test_missing_dir_returns_zero(self, tmp_path, monkeypatch):
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SIGNALS_DIR", tmp_path / "nonexistent")
        assert mod.unprocessed_signals_queued() == 0

    def test_empty_dir_returns_zero(self, tmp_path, monkeypatch):
        sigs = tmp_path / "signals"
        sigs.mkdir()
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SIGNALS_DIR", sigs)
        assert mod.unprocessed_signals_queued() == 0

    def test_counts_only_md_files(self, tmp_path, monkeypatch):
        sigs = tmp_path / "signals"
        sigs.mkdir()
        (sigs / "a.md").write_text("sig")
        (sigs / "b.md").write_text("sig")
        (sigs / "c.txt").write_text("ignored")
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SIGNALS_DIR", sigs)
        assert mod.unprocessed_signals_queued() == 2

    def test_subdir_not_counted(self, tmp_path, monkeypatch):
        sigs = tmp_path / "signals"
        sigs.mkdir()
        (sigs / "a.md").write_text("sig")
        sub = sigs / "subdir"
        sub.mkdir()
        # subdir itself is not a file — should not be counted
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SIGNALS_DIR", sigs)
        assert mod.unprocessed_signals_queued() == 1


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_pass_no_signals(self, tmp_path, monkeypatch, capsys):
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", tmp_path / "no_synth")
        monkeypatch.setattr(mod, "SIGNALS_DIR", tmp_path / "no_sigs")
        result = mod.main()
        assert result == 0
        assert "PASS" in capsys.readouterr().out

    def test_main_fail_with_signals_no_synthesis(self, tmp_path, monkeypatch, capsys):
        sigs = tmp_path / "signals"
        sigs.mkdir()
        (sigs / "pending.md").write_text("signal")
        mod = _load_module(tmp_path)
        monkeypatch.setattr(mod, "SYNTH_DIR", tmp_path / "no_synth")
        monkeypatch.setattr(mod, "SIGNALS_DIR", sigs)
        result = mod.main()
        assert result == 1
        assert "FAIL" in capsys.readouterr().out
