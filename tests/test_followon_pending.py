"""Tests for 5E-3 followon_pending staging."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.followon_pending import (  # noqa: E402
    capture_follow_up_from_stdout,
    count_by_status,
    followon_pending_append,
    list_pending,
    validate_follow_up_payload,
)


def test_validate_follow_up_payload_accepts_description_only():
    assert validate_follow_up_payload({"description": "Do the thing"}) == []


def test_validate_follow_up_payload_accepts_isc_only():
    assert validate_follow_up_payload({"isc": ["x | Verify: test -f y"]}) == []


def test_capture_from_stdout_stages_json(tmp_path):
    p = tmp_path / "q.jsonl"
    out = """
Some text
FOLLOW_UP: {"description": "Next task", "isc": ["c1 | Verify: test -f README.md"]}
TASK_RESULT: id=t1 status=failed isc_passed=0/1 branch=b
"""
    n = capture_follow_up_from_stdout(out, "task-src-1", path=p)
    assert n == 1
    line = p.read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["status"] == "pending"
    assert row["source_task_id"] == "task-src-1"
    assert row["follow_up_task"]["description"] == "Next task"


def test_followon_pending_append_validates(tmp_path):
    p = tmp_path / "q.jsonl"
    with pytest.raises(ValueError):
        followon_pending_append({"follow_up_task": {}}, path=p)


def test_validate_empty_payload_returns_error():
    errs = validate_follow_up_payload({})
    assert len(errs) > 0


def test_validate_non_dict_payload():
    errs = validate_follow_up_payload("not a dict")
    assert errs == ["payload must be a JSON object"]


def test_validate_isc_non_list_returns_error():
    errs = validate_follow_up_payload({"isc": "not-a-list"})
    assert any("list" in e for e in errs)


def test_validate_isc_with_non_string_element():
    errs = validate_follow_up_payload({"isc": [42]})
    assert any("isc[0]" in e for e in errs)


def test_capture_no_follow_up_line_returns_zero(tmp_path):
    p = tmp_path / "q.jsonl"
    n = capture_follow_up_from_stdout("just regular output", "task-1", path=p)
    assert n == 0
    assert not p.exists()


def test_capture_invalid_json_skipped(tmp_path):
    p = tmp_path / "q.jsonl"
    out = "FOLLOW_UP: {not valid json}\n"
    n = capture_follow_up_from_stdout(out, "task-1", path=p)
    assert n == 0


def test_capture_multiple_entries(tmp_path):
    p = tmp_path / "q.jsonl"
    out = (
        'FOLLOW_UP: {"description": "task one"}\n'
        'FOLLOW_UP: {"description": "task two"}\n'
    )
    n = capture_follow_up_from_stdout(out, "src", path=p)
    assert n == 2
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_list_pending_filters_promoted(tmp_path):
    p = tmp_path / "q.jsonl"
    import json as _json
    p.write_text(
        _json.dumps({"id": "1", "status": "pending"}) + "\n"
        + _json.dumps({"id": "2", "status": "promoted"}) + "\n",
        encoding="utf-8",
    )
    rows = list_pending(path=p)
    assert len(rows) == 1
    assert rows[0]["id"] == "1"


def test_list_pending_empty_file(tmp_path):
    p = tmp_path / "q.jsonl"
    p.write_text("", encoding="utf-8")
    assert list_pending(path=p) == []


def test_list_pending_missing_file(tmp_path):
    p = tmp_path / "nonexistent.jsonl"
    assert list_pending(path=p) == []


def test_count_by_status(tmp_path):
    p = tmp_path / "q.jsonl"
    import json as _json
    p.write_text(
        _json.dumps({"status": "pending"}) + "\n"
        + _json.dumps({"status": "pending"}) + "\n"
        + _json.dumps({"status": "promoted"}) + "\n",
        encoding="utf-8",
    )
    counts = count_by_status(path=p)
    assert counts["pending"] == 2
    assert counts["promoted"] == 1


def test_count_by_status_missing_file(tmp_path):
    p = tmp_path / "nonexistent.jsonl"
    assert count_by_status(path=p) == {}
