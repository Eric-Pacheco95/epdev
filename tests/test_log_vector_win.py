"""Tests for tools/scripts/log_vector_win.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.log_vector_win as lvw


def test_missing_args_returns_1(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert lvw.main() == 1


def test_too_few_args_returns_1(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "query", "path"])
    assert lvw.main() == 1


def test_valid_args_appends_signal(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "my query", "memory/file.md", "0.85"])
    with patch("tools.scripts.log_vector_win.append_signal") as mock_append, \
         patch.object(lvw, "SIGNAL_PATH", tmp_path / "vector-wins.jsonl"):
        ret = lvw.main()
    assert ret == 0
    record = mock_append.call_args[0][1]
    assert record["query"] == "my query"
    assert record["hit_path"] == "memory/file.md"
    assert abs(record["score"] - 0.85) < 1e-6
    assert record["source_tier"] == "eric"
    assert record["loaded_by_user"] is True


def test_custom_source_tier(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "q", "p", "0.90", "autonomous"])
    with patch("tools.scripts.log_vector_win.append_signal") as mock_append, \
         patch.object(lvw, "SIGNAL_PATH", tmp_path / "vector-wins.jsonl"):
        lvw.main()
    record = mock_append.call_args[0][1]
    assert record["source_tier"] == "autonomous"


def test_score_parsed_as_float(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "q", "p", "0.92"])
    with patch("tools.scripts.log_vector_win.append_signal") as mock_append, \
         patch.object(lvw, "SIGNAL_PATH", tmp_path / "vector-wins.jsonl"):
        lvw.main()
    record = mock_append.call_args[0][1]
    assert isinstance(record["score"], float)
