"""Tests for jarvis_dispatcher.py -- _isc_counts, _validate_routine_schema, _eval_routine_condition."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_dispatcher import (
    _isc_counts,
    _validate_routine_schema,
)


class TestIscCounts:
    def test_all_pass(self):
        results = [{"status": "pass"}, {"status": "pass"}, {"status": "pass"}]
        p, t, e = _isc_counts(results)
        assert p == 3
        assert t == 3
        assert e == 3

    def test_mixed_pass_fail(self):
        results = [{"status": "pass"}, {"status": "fail"}, {"status": "pass"}]
        p, t, e = _isc_counts(results)
        assert p == 2
        assert t == 3
        assert e == 3

    def test_skipped_excluded_from_executable(self):
        results = [{"status": "pass"}, {"status": "skipped"}, {"status": "skipped"}]
        p, t, e = _isc_counts(results)
        assert p == 1
        assert t == 3
        assert e == 1

    def test_empty_returns_zeros(self):
        p, t, e = _isc_counts([])
        assert p == 0
        assert t == 0
        assert e == 0

    def test_all_skipped(self):
        results = [{"status": "skipped"}, {"status": "skipped"}]
        p, t, e = _isc_counts(results)
        assert p == 0
        assert t == 2
        assert e == 0


class TestValidateRoutineSchema:
    def _base(self):
        return {
            "routine_id": "my-routine",
            "interval_days": 7,
        }

    def test_valid_routine_returns_true(self):
        ok, reason = _validate_routine_schema(self._base())
        assert ok is True
        assert reason == ""

    def test_missing_routine_id_fails(self):
        r = {"interval_days": 7}
        ok, reason = _validate_routine_schema(r)
        assert ok is False
        assert "routine_id" in reason

    def test_missing_interval_days_fails(self):
        r = {"routine_id": "my-routine"}
        ok, reason = _validate_routine_schema(r)
        assert ok is False
        assert "interval_days" in reason

    def test_zero_interval_days_fails(self):
        r = {**self._base(), "interval_days": 0}
        ok, reason = _validate_routine_schema(r)
        assert ok is False

    def test_string_interval_days_fails(self):
        r = {**self._base(), "interval_days": "weekly"}
        ok, reason = _validate_routine_schema(r)
        assert ok is False

    def test_valid_with_condition_block(self):
        r = {**self._base(), "condition": {"type": "always"}}
        ok, reason = _validate_routine_schema(r)
        assert ok is True

    def test_invalid_condition_type_fails(self):
        r = {**self._base(), "condition": {"type": "unknown_type"}}
        ok, reason = _validate_routine_schema(r)
        assert ok is False

    def test_valid_file_count_min_condition(self):
        r = {**self._base(), "condition": {"type": "file_count_min", "glob": "*.md", "min": 1}}
        ok, reason = _validate_routine_schema(r)
        assert ok is True

    def test_schedule_with_interval_type(self):
        r = {**self._base(), "schedule": {"type": "interval", "interval_days": 7}}
        ok, reason = _validate_routine_schema(r)
        assert ok is True

    def test_unknown_schedule_type_fails(self):
        r = {**self._base(), "schedule": {"type": "biweekly", "interval_days": 14}}
        ok, reason = _validate_routine_schema(r)
        assert ok is False
