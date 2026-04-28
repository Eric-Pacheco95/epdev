"""Tests for tools/scripts/verify_learning_retention.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_learning_retention as vlr


# --- list_signal_names ---

def test_list_signal_names_empty_dir(tmp_path):
    with patch.object(vlr, "SIGNALS_DIR", tmp_path):
        assert vlr.list_signal_names() == set()


def test_list_signal_names_missing_dir(tmp_path):
    with patch.object(vlr, "SIGNALS_DIR", tmp_path / "nosuchdir"):
        assert vlr.list_signal_names() == set()


def test_list_signal_names_md_files(tmp_path):
    (tmp_path / "2026-01-01_signal.md").write_text("x", encoding="utf-8")
    (tmp_path / "2026-01-02_signal.md").write_text("y", encoding="utf-8")
    with patch.object(vlr, "SIGNALS_DIR", tmp_path):
        names = vlr.list_signal_names()
    assert "2026-01-01_signal.md" in names
    assert "2026-01-02_signal.md" in names


def test_list_signal_names_gz_stripped(tmp_path):
    (tmp_path / "2026-01-01_signal.md.gz").write_text("x", encoding="utf-8")
    with patch.object(vlr, "SIGNALS_DIR", tmp_path):
        names = vlr.list_signal_names()
    assert "2026-01-01_signal.md" in names


def test_list_signal_names_skips_underscore_prefix(tmp_path):
    (tmp_path / "_internal.md").write_text("x", encoding="utf-8")
    (tmp_path / "real.md").write_text("y", encoding="utf-8")
    with patch.object(vlr, "SIGNALS_DIR", tmp_path):
        names = vlr.list_signal_names()
    assert "_internal.md" not in names
    assert "real.md" in names


# --- load_lineage_references ---

def test_load_lineage_references_missing(tmp_path):
    with patch.object(vlr, "LINEAGE_PATH", tmp_path / "no.jsonl"):
        assert vlr.load_lineage_references() == []


def test_load_lineage_references_valid(tmp_path):
    f = tmp_path / "lineage.jsonl"
    row = {"synthesis_id": "s1", "signals": ["sig1.md", "sig2.md"]}
    f.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with patch.object(vlr, "LINEAGE_PATH", f):
        refs = vlr.load_lineage_references()
    assert ("s1", "sig1.md") in refs
    assert ("s1", "sig2.md") in refs


def test_load_lineage_references_skips_bad_json(tmp_path):
    f = tmp_path / "lineage.jsonl"
    f.write_text("not json\n" + json.dumps({"synthesis_id": "s2", "signals": ["a.md"]}) + "\n",
                 encoding="utf-8")
    with patch.object(vlr, "LINEAGE_PATH", f):
        refs = vlr.load_lineage_references()
    assert len(refs) == 1


# --- load_state / save_state ---

def test_load_state_missing(tmp_path):
    with patch.object(vlr, "STATE_PATH", tmp_path / "state.json"):
        state = vlr.load_state()
    assert state["high_water_count"] == 0


def test_save_load_roundtrip(tmp_path):
    f = tmp_path / "state.json"
    with patch.object(vlr, "STATE_PATH", f):
        vlr.save_state({"high_water_count": 42, "last_check_utc": "2026-01-01T00:00:00"})
        state = vlr.load_state()
    assert state["high_water_count"] == 42


# --- main ---

def test_main_all_signals_present(tmp_path):
    sig_dir = tmp_path / "signals"
    sig_dir.mkdir()
    (sig_dir / "sig1.md").write_text("x", encoding="utf-8")

    lineage = tmp_path / "lineage.jsonl"
    lineage.write_text(json.dumps({"synthesis_id": "s1", "signals": ["sig1.md"]}) + "\n",
                       encoding="utf-8")
    state_f = tmp_path / "state.json"

    with patch.object(vlr, "SIGNALS_DIR", sig_dir), \
         patch.object(vlr, "LINEAGE_PATH", lineage), \
         patch.object(vlr, "STATE_PATH", state_f):
        result = vlr.main()
    assert result == 0


def test_main_missing_lineage_signal(tmp_path):
    sig_dir = tmp_path / "signals"
    sig_dir.mkdir()

    lineage = tmp_path / "lineage.jsonl"
    lineage.write_text(json.dumps({"synthesis_id": "s1", "signals": ["missing.md"]}) + "\n",
                       encoding="utf-8")
    state_f = tmp_path / "state.json"

    with patch.object(vlr, "SIGNALS_DIR", sig_dir), \
         patch.object(vlr, "LINEAGE_PATH", lineage), \
         patch.object(vlr, "STATE_PATH", state_f):
        result = vlr.main()
    assert result == 1


def test_main_count_violation_triggers_failure(tmp_path):
    sig_dir = tmp_path / "signals"
    sig_dir.mkdir()
    (sig_dir / "sig1.md").write_text("x", encoding="utf-8")

    lineage = tmp_path / "lineage.jsonl"
    lineage.write_text("", encoding="utf-8")  # no lineage refs

    state_f = tmp_path / "state.json"
    # Set high-water at 100 — current count is 1, far below tolerance
    state_f.write_text(json.dumps({"high_water_count": 100}), encoding="utf-8")

    with patch.object(vlr, "SIGNALS_DIR", sig_dir), \
         patch.object(vlr, "LINEAGE_PATH", lineage), \
         patch.object(vlr, "STATE_PATH", state_f):
        result = vlr.main()
    assert result == 1


def test_main_high_water_updated_on_new_max(tmp_path):
    sig_dir = tmp_path / "signals"
    sig_dir.mkdir()
    for i in range(5):
        (sig_dir / f"sig{i}.md").write_text("x", encoding="utf-8")

    lineage = tmp_path / "lineage.jsonl"
    lineage.write_text("", encoding="utf-8")

    state_f = tmp_path / "state.json"
    state_f.write_text(json.dumps({"high_water_count": 2}), encoding="utf-8")

    with patch.object(vlr, "SIGNALS_DIR", sig_dir), \
         patch.object(vlr, "LINEAGE_PATH", lineage), \
         patch.object(vlr, "STATE_PATH", state_f):
        result = vlr.main()

    assert result == 0
    saved = json.loads(state_f.read_text(encoding="utf-8"))
    assert saved["high_water_count"] == 5
