"""Tests for overnight_path_guard -- path validation security logic."""

import pytest
from pathlib import Path
from overnight_path_guard import validate_write_path, PathViolation, REPO_ROOT


def test_telos_write_blocked():
    with pytest.raises(PathViolation, match="protected path"):
        validate_write_path(REPO_ROOT / "memory/work/telos/GOALS.md", "scaffolding")


def test_constitutional_rules_blocked():
    with pytest.raises(PathViolation, match="protected path"):
        validate_write_path(REPO_ROOT / "security/constitutional-rules.md", "codebase_health")


def test_claude_md_blocked():
    with pytest.raises(PathViolation, match="protected path"):
        validate_write_path(REPO_ROOT / "CLAUDE.md", "scaffolding")


def test_env_file_blocked():
    with pytest.raises(PathViolation, match="protected"):
        validate_write_path(REPO_ROOT / ".env", "scaffolding")


def test_secret_pattern_blocked():
    with pytest.raises(PathViolation, match="protected pattern"):
        validate_write_path(REPO_ROOT / "tools/credentials.json", "scaffolding")


def test_pem_pattern_blocked():
    with pytest.raises(PathViolation, match="protected pattern"):
        validate_write_path(REPO_ROOT / "tools/server.pem", "codebase_health")


def test_path_traversal_blocked():
    with pytest.raises(PathViolation, match="outside repo root"):
        validate_write_path(Path("C:/Users/ericp/.ssh/id_rsa"), "scaffolding")


def test_allowed_skill_write_scaffolding():
    result = validate_write_path(
        REPO_ROOT / ".claude/skills/test/SKILL.md", "scaffolding"
    )
    assert result.is_absolute()


def test_allowed_autoresearch_report():
    result = validate_write_path(
        REPO_ROOT / "memory/work/jarvis/autoresearch/overnight-2026-03-29/report.md",
        "scaffolding",
    )
    assert result.is_absolute()


def test_allowed_test_file_codebase_health():
    result = validate_write_path(
        REPO_ROOT / "tests/test_example.py", "codebase_health"
    )
    assert result.is_absolute()


def test_wrong_dimension_blocked():
    with pytest.raises(PathViolation, match="not in allowed scope"):
        validate_write_path(REPO_ROOT / "tools/scripts/test.py", "scaffolding")
