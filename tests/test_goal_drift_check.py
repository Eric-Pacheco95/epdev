"""Tests for tools/scripts/goal_drift_check.py helper functions."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.goal_drift_check as gdc


# --- _load_state / _save_state ---

def test_load_state_missing_file(tmp_path):
    f = tmp_path / "state.json"
    with patch.object(gdc, "STATE_FILE", f):
        state = gdc._load_state()
    assert state == {"alerts": {}}


def test_load_state_existing_file(tmp_path):
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"alerts": {"G1": "2026-01-01T00:00:00Z"}}), encoding="utf-8")
    with patch.object(gdc, "STATE_FILE", f):
        state = gdc._load_state()
    assert state["alerts"]["G1"] == "2026-01-01T00:00:00Z"


def test_load_state_invalid_json(tmp_path):
    f = tmp_path / "state.json"
    f.write_text("not json", encoding="utf-8")
    with patch.object(gdc, "STATE_FILE", f):
        state = gdc._load_state()
    assert state == {"alerts": {}}


def test_save_state_writes_file(tmp_path):
    f = tmp_path / "state.json"
    state = {"alerts": {"G2": "2026-01-01T00:00:00Z"}}
    with patch.object(gdc, "STATE_FILE", f):
        gdc._save_state(state)
    loaded = json.loads(f.read_text(encoding="utf-8"))
    assert loaded["alerts"]["G2"] == "2026-01-01T00:00:00Z"


def test_save_state_creates_parent_dir(tmp_path):
    f = tmp_path / "subdir" / "state.json"
    with patch.object(gdc, "STATE_FILE", f):
        gdc._save_state({"alerts": {}})
    assert f.exists()


# --- _last_signal_date ---

def test_last_signal_date_no_signals_dir(tmp_path):
    missing = tmp_path / "nosuchdir"
    with patch.object(gdc, "SIGNALS", missing):
        result = gdc._last_signal_date("G1")
    assert result is None


def test_last_signal_date_empty_dir(tmp_path):
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert result is None


def test_last_signal_date_g1_match(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("G1 financial signal captured today", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert isinstance(result, datetime)


def test_last_signal_date_g2_match(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("G2 Jarvis pipeline synthesis", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G2")
    assert isinstance(result, datetime)


def test_last_signal_date_no_match(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("unrelated content about cooking", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert result is None


def test_last_signal_date_returns_latest(tmp_path):
    import os, time
    md1 = tmp_path / "old.md"
    md1.write_text("G1 crypto signal", encoding="utf-8")
    time.sleep(0.02)
    md2 = tmp_path / "new.md"
    md2.write_text("G1 financial signal", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    # Should return the mtime of the newest matching file
    expected_mtime = datetime.fromtimestamp(md2.stat().st_mtime, tz=timezone.utc)
    assert abs((result - expected_mtime).total_seconds()) < 1


def test_last_signal_date_non_md_files_ignored(tmp_path):
    txt = tmp_path / "signal.txt"
    txt.write_text("G1 financial trading", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert result is None  # .txt not matched by *.md glob


def test_last_signal_date_case_insensitive(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("TRADING opportunity found today", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert result is not None


def test_last_signal_date_g2_telos_match(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("Updated TELOS goals for Q2", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G2")
    assert result is not None


def test_last_signal_date_g1_does_not_match_g2_keyword(tmp_path):
    md = tmp_path / "signal.md"
    md.write_text("Jarvis skill pipeline updated today", encoding="utf-8")
    with patch.object(gdc, "SIGNALS", tmp_path):
        result = gdc._last_signal_date("G1")
    assert result is None  # Jarvis/skill pipeline are G2 keywords, not G1


def test_load_state_empty_file(tmp_path):
    f = tmp_path / "state.json"
    f.write_text("", encoding="utf-8")
    with patch.object(gdc, "STATE_FILE", f):
        state = gdc._load_state()
    assert state == {"alerts": {}}
