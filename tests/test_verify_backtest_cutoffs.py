"""Tests for verify_backtest_cutoffs.py -- leakage guard verifier."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
import yaml

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "verify_backtest_cutoffs.py"


def _load():
    spec = importlib.util.spec_from_file_location("verify_backtest_cutoffs", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _write_events(tmp_path: Path, events: list) -> Path:
    f = tmp_path / "backtest_events.yaml"
    f.write_text(yaml.dump({"events": events}), encoding="utf-8")
    return f


class TestEffectiveThreshold:
    def test_threshold_is_24_months_before_cutoff(self):
        mod = _load()
        # Opus 4.6: 2025-05, buffer 24 → 2023-05
        t = mod._effective_threshold()
        assert t == date(2023, 5, 1)

    def test_threshold_day_is_always_1(self):
        mod = _load()
        t = mod._effective_threshold()
        assert t.day == 1


class TestParseCutoff:
    def test_date_object_passthrough(self):
        mod = _load()
        d = date(2022, 1, 15)
        assert mod._parse_cutoff(d) == d

    def test_string_yyyy_mm_dd(self):
        mod = _load()
        assert mod._parse_cutoff("2022-06-01") == date(2022, 6, 1)

    def test_string_with_straight_quotes(self):
        mod = _load()
        assert mod._parse_cutoff('"2021-12-31"') == date(2021, 12, 31)

    def test_string_with_smart_quotes(self):
        mod = _load()
        assert mod._parse_cutoff("\u201c2020-03-01\u201d") == date(2020, 3, 1)

    def test_invalid_string_returns_none(self):
        mod = _load()
        assert mod._parse_cutoff("not-a-date") is None

    def test_non_string_non_date_returns_none(self):
        mod = _load()
        assert mod._parse_cutoff(12345) is None


class TestMainVerifier:
    def test_missing_events_file_returns_1(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", tmp_path / "missing.yaml")
        assert mod.main() == 1

    def test_all_valid_cutoffs_returns_0(self, tmp_path, monkeypatch, capsys):
        events = [
            {"event_id": "e1", "knowledge_cutoff_date": "2020-01-01"},
            {"event_id": "e2", "knowledge_cutoff_date": "2021-06-01"},
        ]
        f = _write_events(tmp_path, events)
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        result = mod.main()
        assert result == 0
        assert "PASS" in capsys.readouterr().out

    def test_cutoff_at_threshold_is_violation(self, tmp_path, monkeypatch, capsys):
        # threshold is 2023-05-01 — equal is a violation (>= check)
        events = [{"event_id": "e1", "knowledge_cutoff_date": "2023-05-01"}]
        f = _write_events(tmp_path, events)
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        result = mod.main()
        assert result == 1
        assert "FAIL" in capsys.readouterr().out

    def test_cutoff_after_threshold_is_violation(self, tmp_path, monkeypatch):
        events = [{"event_id": "e1", "knowledge_cutoff_date": "2024-01-01"}]
        f = _write_events(tmp_path, events)
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        assert mod.main() == 1

    def test_missing_cutoff_field_returns_1(self, tmp_path, monkeypatch, capsys):
        events = [{"event_id": "e1"}]
        f = _write_events(tmp_path, events)
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        result = mod.main()
        assert result == 1
        assert "missing knowledge_cutoff_date" in capsys.readouterr().out

    def test_empty_events_list_returns_1(self, tmp_path, monkeypatch):
        f = tmp_path / "backtest_events.yaml"
        f.write_text(yaml.dump({"events": []}), encoding="utf-8")
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        assert mod.main() == 1

    def test_unparseable_cutoff_is_violation(self, tmp_path, monkeypatch, capsys):
        events = [{"event_id": "e1", "knowledge_cutoff_date": "garbage"}]
        f = _write_events(tmp_path, events)
        mod = _load()
        monkeypatch.setattr(mod, "EVENTS_FILE", f)
        result = mod.main()
        assert result == 1
        out = capsys.readouterr().out
        assert "FAIL" in out
