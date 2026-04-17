"""Tests for tools/scripts/lib/backlog.py -- validate_task and backlog_append."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.backlog import (
    ACTIVE_STATUSES,
    VALID_STATUSES,
    backlog_append,
    validate_task,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_task(**overrides) -> dict:
    """Return a minimal valid task dict. Override fields with kwargs."""
    base = {
        "id": "test-001",
        "description": "Do the thing",
        "tier": 1,
        "priority": 2,
        "autonomous_safe": True,
        "isc": ["The thing is done | Verify: test -f tools/scripts/isc_validator.py"],
        "status": "pending",
        "created": "2026-04-02",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# validate_task tests
# ---------------------------------------------------------------------------

class TestValidateTask:
    def test_valid_task_no_errors(self):
        errors = validate_task(_minimal_task())
        assert errors == []

    def test_missing_description_rejected(self):
        task = _minimal_task()
        del task["description"]
        errors = validate_task(task)
        assert any("description" in e for e in errors)

    def test_empty_description_rejected(self):
        errors = validate_task(_minimal_task(description="   "))
        assert any("description" in e for e in errors)

    def test_missing_tier_rejected(self):
        task = _minimal_task()
        del task["tier"]
        errors = validate_task(task)
        assert any("tier" in e for e in errors)

    def test_tier_out_of_range_rejected(self):
        errors = validate_task(_minimal_task(tier=3))
        assert any("tier" in e for e in errors)

    def test_tier_negative_rejected(self):
        errors = validate_task(_minimal_task(tier=-1))
        assert any("tier" in e for e in errors)

    def test_tier_zero_valid(self):
        errors = validate_task(_minimal_task(tier=0))
        assert errors == []

    def test_tier_two_valid(self):
        errors = validate_task(_minimal_task(tier=2))
        assert errors == []

    def test_invalid_status_rejected(self):
        errors = validate_task(_minimal_task(status="not-a-status"))
        assert any("status" in e for e in errors)

    def test_all_valid_statuses_accepted(self):
        for s in VALID_STATUSES:
            errors = validate_task(_minimal_task(status=s))
            assert errors == [], f"Status '{s}' should be valid"

    def test_missing_autonomous_safe_rejected(self):
        task = _minimal_task()
        del task["autonomous_safe"]
        errors = validate_task(task)
        assert any("autonomous_safe" in e for e in errors)

    def test_autonomous_safe_non_bool_rejected(self):
        errors = validate_task(_minimal_task(autonomous_safe="yes"))
        assert any("autonomous_safe" in e for e in errors)

    def test_missing_isc_rejected(self):
        task = _minimal_task()
        del task["isc"]
        errors = validate_task(task)
        assert any("isc" in e for e in errors)

    def test_empty_isc_rejected(self):
        errors = validate_task(_minimal_task(isc=[]))
        assert any("isc" in e for e in errors)

    def test_no_executable_isc_rejected(self):
        # Only a manual/review verify method -- no executable
        errors = validate_task(_minimal_task(isc=["The thing is done | Verify: Review output"]))
        assert any("executable" in e.lower() for e in errors)

    def test_missing_priority_rejected(self):
        task = _minimal_task()
        del task["priority"]
        errors = validate_task(task)
        assert any("priority" in e for e in errors)

    def test_priority_non_int_rejected(self):
        errors = validate_task(_minimal_task(priority="high"))
        assert any("priority" in e for e in errors)

    def test_secret_path_in_isc_rejected(self):
        errors = validate_task(_minimal_task(isc=[
            "Cred file exists | Verify: test -f ~/.ssh/id_rsa"
        ]))
        assert any("secret path" in e.lower() for e in errors)

    def test_dot_env_in_isc_rejected(self):
        errors = validate_task(_minimal_task(isc=[
            "Env loaded | Verify: grep -c KEY .env"
        ]))
        assert any("secret path" in e.lower() for e in errors)

    def test_id_absent_is_ok(self):
        """id absence is fine; backlog_append will auto-generate."""
        task = _minimal_task()
        del task["id"]
        errors = validate_task(task)
        assert errors == []

    def test_id_empty_string_rejected(self):
        errors = validate_task(_minimal_task(id="  "))
        assert any("id" in e for e in errors)

    def test_created_absent_is_ok(self):
        """created absence is fine; backlog_append will auto-fill."""
        task = _minimal_task()
        del task["created"]
        errors = validate_task(task)
        assert errors == []


# ---------------------------------------------------------------------------
# backlog_append tests
# ---------------------------------------------------------------------------

class TestBacklogAppend:
    def test_valid_task_appends(self, tmp_path):
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task()
        result = backlog_append(task, backlog_path=backlog_file)

        assert result is not None
        assert result["id"] == "test-001"
        assert backlog_file.exists()

        lines = backlog_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        written = json.loads(lines[0])
        assert written["id"] == "test-001"
        assert written["description"] == "Do the thing"

    def test_missing_id_autogenerated(self, tmp_path):
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task()
        del task["id"]
        result = backlog_append(task, backlog_path=backlog_file)

        assert result is not None
        assert result["id"].startswith("task-")

        lines = backlog_file.read_text(encoding="utf-8").strip().splitlines()
        written = json.loads(lines[0])
        assert written["id"].startswith("task-")

    def test_missing_created_autofilled(self, tmp_path):
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task()
        del task["created"]
        result = backlog_append(task, backlog_path=backlog_file)

        assert result is not None
        assert result["created"]  # non-empty string

    def test_optional_fields_autofilled(self, tmp_path):
        """Optional fields get defaults when absent."""
        backlog_file = tmp_path / "backlog.jsonl"
        task = {
            "description": "Minimal",
            "tier": 0,
            "priority": 1,
            "autonomous_safe": False,
            "isc": ["Done | Verify: test -f tools/scripts/isc_validator.py"],
        }
        result = backlog_append(task, backlog_path=backlog_file)
        assert result is not None
        assert result["dependencies"] == []
        assert result["context_files"] == []
        assert result["skills"] == []
        assert result["model"] == "sonnet"
        assert result["review_model"] is None
        assert result["status"] == "pending_review"  # autonomous_safe=False forces promotion
        assert result["retry_count"] == 0
        assert result["notes"] == ""

    def test_missing_isc_rejected(self, tmp_path):
        import pytest
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task()
        del task["isc"]
        with pytest.raises(ValueError, match="isc"):
            backlog_append(task, backlog_path=backlog_file)
        assert not backlog_file.exists()

    def test_no_executable_isc_rejected(self, tmp_path):
        import pytest
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task(isc=["Thing done | Verify: Review it manually"])
        with pytest.raises(ValueError, match="executable"):
            backlog_append(task, backlog_path=backlog_file)

    def test_invalid_tier_rejected(self, tmp_path):
        import pytest
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task(tier=5)
        with pytest.raises(ValueError, match="tier"):
            backlog_append(task, backlog_path=backlog_file)

    def test_secret_path_in_isc_rejected(self, tmp_path):
        import pytest
        backlog_file = tmp_path / "backlog.jsonl"
        task = _minimal_task(isc=["Key exists | Verify: test -f ~/.ssh/id_rsa"])
        with pytest.raises(ValueError, match="secret path"):
            backlog_append(task, backlog_path=backlog_file)

    def test_dedup_by_routine_id(self, tmp_path):
        backlog_file = tmp_path / "backlog.jsonl"

        # First append succeeds
        task1 = _minimal_task(id="t-001", routine_id="daily-cleanup", status="pending")
        result1 = backlog_append(task1, backlog_path=backlog_file)
        assert result1 is not None

        # Second append with same routine_id and active status returns None
        task2 = _minimal_task(id="t-002", routine_id="daily-cleanup", status="pending")
        result2 = backlog_append(task2, backlog_path=backlog_file)
        assert result2 is None

        # Only one line in backlog
        lines = backlog_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_dedup_skips_only_active_statuses(self, tmp_path):
        """dedup only fires when existing routine_id task is in ACTIVE_STATUSES."""
        backlog_file = tmp_path / "backlog.jsonl"

        # Append a "done" task with a routine_id
        task1 = _minimal_task(id="t-001", routine_id="weekly-sync", status="done")
        result1 = backlog_append(task1, backlog_path=backlog_file)
        assert result1 is not None

        # A second task with same routine_id but existing is "done" -- should append
        task2 = _minimal_task(id="t-002", routine_id="weekly-sync", status="pending")
        result2 = backlog_append(task2, backlog_path=backlog_file)
        assert result2 is not None

        lines = backlog_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_atomic_write(self, tmp_path):
        """Append to an existing backlog preserves existing tasks."""
        backlog_file = tmp_path / "backlog.jsonl"

        # Pre-populate backlog with two tasks
        existing = [
            {"id": "old-001", "description": "Existing task 1", "tier": 0,
             "priority": 1, "autonomous_safe": True,
             "isc": ["Done | Verify: test -f CLAUDE.md"], "status": "done"},
            {"id": "old-002", "description": "Existing task 2", "tier": 1,
             "priority": 2, "autonomous_safe": False,
             "isc": ["Done | Verify: test -f CLAUDE.md"], "status": "pending"},
        ]
        backlog_file.write_text(
            "\n".join(json.dumps(t) for t in existing) + "\n",
            encoding="utf-8",
        )

        # Append a new task
        new_task = _minimal_task(id="new-001")
        result = backlog_append(new_task, backlog_path=backlog_file)
        assert result is not None

        # Verify backlog now has 3 tasks, in order
        lines = backlog_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

        tasks = [json.loads(line) for line in lines]
        assert tasks[0]["id"] == "old-001"
        assert tasks[1]["id"] == "old-002"
        assert tasks[2]["id"] == "new-001"

    def test_does_not_mutate_caller_dict(self, tmp_path):
        """backlog_append should not modify the caller's task dict."""
        backlog_file = tmp_path / "backlog.jsonl"
        task = {
            "description": "Immutable check",
            "tier": 0,
            "priority": 1,
            "autonomous_safe": True,
            "isc": ["Done | Verify: test -f tools/scripts/isc_validator.py"],
        }
        original_keys = set(task.keys())
        backlog_append(task, backlog_path=backlog_file)
        # Caller's dict should be unchanged
        assert set(task.keys()) == original_keys
        assert "id" not in task  # auto-fill should not bleed into caller's dict
