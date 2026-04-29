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


# --- validate_follow_up_payload edge cases ---

def test_validate_empty_payload_errors():
    errs = validate_follow_up_payload({})
    assert len(errs) > 0


def test_validate_isc_non_list_errors():
    errs = validate_follow_up_payload({"isc": "not a list"})
    assert any("isc" in e for e in errs)


def test_validate_isc_with_non_string_item_errors():
    errs = validate_follow_up_payload({"isc": [123]})
    assert any("isc" in e for e in errs)


def test_validate_non_dict_payload_errors():
    errs = validate_follow_up_payload("not a dict")
    assert errs == ["payload must be a JSON object"]


# --- list_pending ---

def test_list_pending_missing_file(tmp_path):
    from tools.scripts.lib.followon_pending import list_pending
    assert list_pending(tmp_path / "nonexistent.jsonl") == []


def test_list_pending_returns_only_pending(tmp_path):
    import json as _json
    from tools.scripts.lib.followon_pending import list_pending
    p = tmp_path / "q.jsonl"
    rows = [
        {"status": "pending", "id": "1"},
        {"status": "promoted", "id": "2"},
        {"status": "pending", "id": "3"},
    ]
    p.write_text("\n".join(_json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    result = list_pending(p)
    assert len(result) == 2
    assert all(r["status"] == "pending" for r in result)


def test_list_pending_skips_invalid_json(tmp_path):
    from tools.scripts.lib.followon_pending import list_pending
    p = tmp_path / "q.jsonl"
    p.write_text('invalid\n{"status": "pending", "id": "1"}\n', encoding="utf-8")
    result = list_pending(p)
    assert len(result) == 1


# --- count_by_status ---

def test_count_by_status_missing_file(tmp_path):
    from tools.scripts.lib.followon_pending import count_by_status
    assert count_by_status(tmp_path / "nonexistent.jsonl") == {}


def test_count_by_status_multiple(tmp_path):
    import json as _json
    from tools.scripts.lib.followon_pending import count_by_status
    p = tmp_path / "q.jsonl"
    rows = [
        {"status": "pending"},
        {"status": "promoted"},
        {"status": "pending"},
        {"status": "promoted"},
        {"status": "promoted"},
    ]
    p.write_text("\n".join(_json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    result = count_by_status(p)
    assert result == {"pending": 2, "promoted": 3}
