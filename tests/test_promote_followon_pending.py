"""Tests for tools/scripts/promote_followon_pending.py main()."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.promote_followon_pending as pfp


def test_list_cmd_prints_rows(tmp_path, monkeypatch, capsys):
    rows = [{"id": "fp-001", "title": "Task 1", "state": "pending"}]
    monkeypatch.setattr(sys, "argv", ["prog", "list", "--path", str(tmp_path / "fp.jsonl")])
    with patch.object(pfp, "list_pending", return_value=rows):
        ret = pfp.main()
    assert ret == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["id"] == "fp-001"


def test_list_cmd_empty_result(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "list", "--path", str(tmp_path / "fp.jsonl")])
    with patch.object(pfp, "list_pending", return_value=[]):
        ret = pfp.main()
    assert ret == 0
    assert json.loads(capsys.readouterr().out) == []


def test_promote_success(tmp_path, monkeypatch, capsys):
    result = {"id": "fp-001", "state": "pending_review", "title": "Task 1"}
    monkeypatch.setattr(sys, "argv", ["prog", "promote", "fp-001", "--path", str(tmp_path / "fp.jsonl")])
    with patch.object(pfp, "promote_one", return_value=result):
        ret = pfp.main()
    assert ret == 0
    assert json.loads(capsys.readouterr().out)["id"] == "fp-001"


def test_promote_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "promote", "fp-999", "--path", str(tmp_path / "fp.jsonl")])
    with patch.object(pfp, "promote_one", return_value=None):
        ret = pfp.main()
    assert ret == 1
