"""Edge case tests for overnight_path_guard."""

import pytest
from pathlib import Path
from overnight_path_guard import (
    validate_write_path, PathViolation, REPO_ROOT,
    _is_under, DIMENSION_SCOPES, ALWAYS_ALLOWED,
)


def test_is_under_true():
    parent = Path("C:/Users/ericp/Github/epdev-overnight")
    child = Path("C:/Users/ericp/Github/epdev-overnight/tools/scripts/foo.py")
    assert _is_under(child, parent) is True


def test_is_under_false():
    parent = Path("C:/Users/ericp/Github/epdev-overnight/tools")
    child = Path("C:/Users/ericp/Github/epdev-overnight/memory/test.md")
    assert _is_under(child, parent) is False


def test_is_under_same_path():
    p = Path("C:/Users/ericp/Github/epdev-overnight/tools")
    assert _is_under(p, p) is True


def test_data_dir_always_allowed():
    """data/ is in ALWAYS_ALLOWED for all dimensions."""
    result = validate_write_path(REPO_ROOT / "data/state.json", "unknown")
    assert result.is_absolute()


def test_autoresearch_dir_always_allowed():
    result = validate_write_path(
        REPO_ROOT / "memory/work/jarvis/autoresearch/run-2026-03-29/metrics.json",
        "external_monitoring",
    )
    assert result.is_absolute()


def test_knowledge_synthesis_scope():
    result = validate_write_path(
        REPO_ROOT / "memory/learning/synthesis/weekly.md",
        "knowledge_synthesis",
    )
    assert result.is_absolute()


def test_knowledge_synthesis_wrong_path_blocked():
    with pytest.raises(PathViolation):
        validate_write_path(REPO_ROOT / "tools/scripts/foo.py", "knowledge_synthesis")


def test_key_file_blocked():
    with pytest.raises(PathViolation, match="protected pattern"):
        validate_write_path(REPO_ROOT / "data/server.key", "codebase_health")


def test_settings_json_blocked():
    with pytest.raises(PathViolation, match="protected path"):
        validate_write_path(REPO_ROOT / ".claude/settings.json", "scaffolding")


def test_dimension_scopes_keys_exist():
    """All documented dimensions have scope entries."""
    expected = {"scaffolding", "codebase_health", "knowledge_synthesis",
                "external_monitoring", "prompt_quality", "cross_project",
                "algorithm_adherence"}
    assert set(DIMENSION_SCOPES.keys()) == expected
