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
    followon_pending_append,
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
