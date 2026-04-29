"""Tests for lib/backlog -- validate_task and backlog_append."""

import json
import tempfile
from pathlib import Path

from tools.scripts.lib.backlog import (
    validate_task,
    backlog_append,
    VALID_STATUSES,
    ACTIVE_STATUSES,
)


def _minimal_task(**overrides):
    """Build a minimal valid task dict."""
    base = {
        "description": "Run security audit",
        "tier": 1,
        "autonomous_safe": True,
        "isc": ["Audit report exists | Verify: test -f report.md"],
        "priority": 3,
    }
    base.update(overrides)
    return base


# ── validate_task ────────────────────────────────────────────────────

def test_validate_minimal_valid():
    errors = validate_task(_minimal_task())
    assert errors == []


def test_validate_missing_description():
    t = _minimal_task()
    del t["description"]
    errors = validate_task(t)
    assert any("description" in e for e in errors)


def test_validate_missing_tier():
    t = _minimal_task()
    del t["tier"]
    errors = validate_task(t)
    assert any("tier" in e for e in errors)


def test_validate_bad_tier():
    errors = validate_task(_minimal_task(tier=5))
    assert any("tier" in e for e in errors)


def test_validate_missing_autonomous_safe():
    t = _minimal_task()
    del t["autonomous_safe"]
    errors = validate_task(t)
    assert any("autonomous_safe" in e for e in errors)


def test_validate_empty_isc():
    errors = validate_task(_minimal_task(isc=[]))
    assert any("isc" in e for e in errors)


def test_validate_missing_priority():
    t = _minimal_task()
    del t["priority"]
    errors = validate_task(t)
    assert any("priority" in e for e in errors)


def test_validate_bad_status():
    errors = validate_task(_minimal_task(status="invalid_status"))
    assert any("status" in e for e in errors)


def test_validate_valid_status():
    for status in ["pending", "done", "failed"]:
        errors = validate_task(_minimal_task(status=status))
        assert not any("status" in e for e in errors)


def test_validate_secret_in_isc():
    t = _minimal_task(isc=["Check secrets | Verify: cat .env"])
    errors = validate_task(t)
    assert any("secret path" in e for e in errors)


# ── backlog_append ───────────────────────────────────────────────────

def test_backlog_append_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        result = backlog_append(_minimal_task(), backlog_path=bp)
        assert result is not None
        assert "id" in result
        assert bp.exists()
        lines = bp.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1


def test_backlog_append_auto_fills():
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        result = backlog_append(_minimal_task(), backlog_path=bp)
        assert result["status"] == "pending"
        assert result["model"] == "sonnet"
        assert "created" in result


def test_backlog_append_dedup():
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        t = _minimal_task(routine_id="weekly-audit")
        backlog_append(t, backlog_path=bp)
        result = backlog_append(t, backlog_path=bp)
        assert result is None  # deduped


def test_backlog_append_validation_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        try:
            backlog_append({"description": ""}, backlog_path=bp)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "validation failed" in str(e).lower()


# ── validate_task edge cases ─────────────────────────────────────────

def test_validate_id_with_invalid_chars():
    t = _minimal_task(id="id with space/slash")
    errors = validate_task(t)
    assert any("id" in e for e in errors)


def test_validate_id_empty_string():
    t = _minimal_task(id="")
    errors = validate_task(t)
    assert any("id" in e for e in errors)


def test_validate_autonomous_safe_non_boolean():
    errors = validate_task(_minimal_task(autonomous_safe="yes"))
    assert any("autonomous_safe" in e for e in errors)


def test_validate_isc_non_list():
    errors = validate_task(_minimal_task(isc="should-be-a-list"))
    assert any("isc" in e for e in errors)


def test_validate_isc_no_executable_verify():
    errors = validate_task(_minimal_task(isc=["Criterion | Verify: Review"]))
    assert any("executable" in e for e in errors)


def test_validate_generation_too_high():
    errors = validate_task(_minimal_task(generation=3))
    assert any("generation" in e for e in errors)


def test_validate_generation_negative():
    errors = validate_task(_minimal_task(generation=-1))
    assert any("generation" in e for e in errors)


def test_validate_generation_valid_zero():
    errors = validate_task(_minimal_task(generation=0))
    assert not any("generation" in e for e in errors)


def test_validate_created_non_string():
    errors = validate_task(_minimal_task(created=12345))
    assert any("created" in e for e in errors)


def test_validate_priority_non_integer():
    errors = validate_task(_minimal_task(priority="high"))
    assert any("priority" in e for e in errors)
