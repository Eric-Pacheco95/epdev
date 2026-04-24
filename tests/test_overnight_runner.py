"""Unit tests for tools/scripts/overnight_runner.py pure helpers."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from tools.scripts.overnight_runner import (
    next_dimension,
    dimensions_to_run,
    validate_command,
    DIMENSION_ORDER,
    SAFE_COMMAND_PREFIXES,
)


class TestNextDimension:
    def test_force_overrides_state(self):
        state = {"last_dimension": "scaffolding"}
        result = next_dimension(state, force="codebase_health")
        assert result == "codebase_health"

    def test_force_invalid_ignored(self):
        state = {"last_dimension": "scaffolding"}
        result = next_dimension(state, force="nonexistent")
        # Falls through to normal logic
        assert result in DIMENSION_ORDER

    def test_no_prior_state_returns_first(self):
        state = {}
        assert next_dimension(state) == DIMENSION_ORDER[0]

    def test_advances_to_next(self):
        for i, dim in enumerate(DIMENSION_ORDER[:-1]):
            state = {"last_dimension": dim}
            expected = DIMENSION_ORDER[i + 1]
            assert next_dimension(state) == expected, f"After {dim}, expected {expected}"

    def test_wraps_around_from_last(self):
        state = {"last_dimension": DIMENSION_ORDER[-1]}
        assert next_dimension(state) == DIMENSION_ORDER[0]

    def test_unknown_last_returns_first(self):
        state = {"last_dimension": "unknown_dimension"}
        assert next_dimension(state) == DIMENSION_ORDER[0]


class TestDimensionsToRun:
    def _all_enabled(self):
        return {dim: {"enabled": True} for dim in DIMENSION_ORDER}

    def _with_disabled(self, disabled: str):
        dims = self._all_enabled()
        dims[disabled]["enabled"] = False
        return dims

    def test_force_returns_single_enabled(self):
        dims = self._all_enabled()
        result = dimensions_to_run({}, dims, force="codebase_health")
        assert result == ["codebase_health"]

    def test_force_disabled_returns_empty(self):
        dims = self._with_disabled("codebase_health")
        result = dimensions_to_run({}, dims, force="codebase_health")
        assert result == []

    def test_force_invalid_falls_through_to_normal(self):
        # Invalid force name is not in DIMENSION_ORDER → falls through and
        # returns all enabled dimensions as normal rotation
        dims = self._all_enabled()
        result = dimensions_to_run({}, dims, force="nonexistent_dim")
        assert set(result) == set(DIMENSION_ORDER)

    def test_all_enabled_returns_all(self):
        dims = self._all_enabled()
        result = dimensions_to_run({}, dims)
        assert set(result) == set(DIMENSION_ORDER)

    def test_disabled_dimension_skipped(self):
        dims = self._with_disabled("knowledge_synthesis")
        result = dimensions_to_run({}, dims)
        assert "knowledge_synthesis" not in result
        assert len(result) == len(DIMENSION_ORDER) - 1

    def test_returns_list(self):
        result = dimensions_to_run({}, self._all_enabled())
        assert isinstance(result, list)


class TestValidateCommand:
    def test_pytest_allowed(self):
        assert validate_command("python -m pytest tests/ --tb=no -q", "metric") is True

    def test_flake8_allowed(self):
        assert validate_command("python -m flake8 --count --select=E9 tools/", "guard") is True

    def test_grep_allowed(self):
        assert validate_command("grep -c pattern file.txt", "metric") is True

    def test_wc_allowed(self):
        assert validate_command("wc -l file.txt", "metric") is True

    def test_empty_command_allowed(self):
        assert validate_command("", "field") is True

    def test_parens_command_allowed(self):
        # Commands starting with "(" pass through
        assert validate_command("(none)", "field") is True

    def test_unsafe_command_blocked(self, capsys):
        result = validate_command("rm -rf /tmp/test", "metric")
        assert result is False

    def test_curl_blocked(self, capsys):
        result = validate_command("curl http://example.com", "guard")
        assert result is False

    def test_all_safe_prefixes_pass(self):
        for prefix in SAFE_COMMAND_PREFIXES:
            cmd = f"{prefix} some-arg"
            assert validate_command(cmd, "test") is True, f"Prefix '{prefix}' should be allowed"
