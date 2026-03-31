"""Pytest tests for tools/scripts/overnight_path_guard.py — path validation and security."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.overnight_path_guard import (
    validate_write_path,
    _is_under,
    PathViolation,
    REPO_ROOT as GUARD_ROOT,
    BLOCKED_PATHS,
    BLOCKED_PATTERNS,
    DIMENSION_SCOPES,
)
import pytest


class TestIsUnder:
    def test_child_under_parent(self):
        parent = Path("C:/a/b")
        child = Path("C:/a/b/c/d.txt")
        assert _is_under(child, parent) is True

    def test_same_path(self):
        p = Path("C:/a/b")
        assert _is_under(p, p) is True

    def test_not_under(self):
        assert _is_under(Path("C:/x/y"), Path("C:/a/b")) is False


class TestValidateWritePath:
    def test_telos_blocked(self):
        with pytest.raises(PathViolation, match="protected path"):
            validate_write_path(GUARD_ROOT / "memory/work/telos/GOALS.md", "scaffolding")

    def test_constitutional_rules_blocked(self):
        with pytest.raises(PathViolation, match="protected path"):
            validate_write_path(GUARD_ROOT / "security/constitutional-rules.md", "codebase_health")

    def test_claude_md_blocked(self):
        with pytest.raises(PathViolation, match="protected path"):
            validate_write_path(GUARD_ROOT / "CLAUDE.md", "scaffolding")

    def test_env_blocked(self):
        with pytest.raises(PathViolation, match="protected"):
            validate_write_path(GUARD_ROOT / ".env", "scaffolding")

    def test_credential_pattern_blocked(self):
        with pytest.raises(PathViolation, match="protected pattern"):
            validate_write_path(GUARD_ROOT / "tools/credentials.json", "codebase_health")

    def test_pem_pattern_blocked(self):
        with pytest.raises(PathViolation, match="protected pattern"):
            validate_write_path(GUARD_ROOT / "data/server.pem", "codebase_health")

    def test_path_outside_repo_blocked(self):
        with pytest.raises(PathViolation, match="outside repo root"):
            validate_write_path(Path("C:/Windows/System32/test.txt"), "scaffolding")

    def test_wrong_dimension_blocked(self):
        with pytest.raises(PathViolation, match="not in allowed scope"):
            validate_write_path(GUARD_ROOT / ".claude/skills/test/SKILL.md", "codebase_health")

    def test_skill_write_allowed_scaffolding(self):
        result = validate_write_path(GUARD_ROOT / ".claude/skills/test/SKILL.md", "scaffolding")
        assert result is not None

    def test_script_write_allowed_codebase_health(self):
        result = validate_write_path(GUARD_ROOT / "tools/scripts/new_script.py", "codebase_health")
        assert result is not None

    def test_autoresearch_report_always_allowed(self):
        result = validate_write_path(
            GUARD_ROOT / "memory/work/jarvis/autoresearch/overnight/report.md",
            "scaffolding",
        )
        assert result is not None

    def test_data_dir_always_allowed(self):
        result = validate_write_path(GUARD_ROOT / "data/state.json", "scaffolding")
        assert result is not None

    def test_tests_dir_allowed_codebase_health(self):
        result = validate_write_path(GUARD_ROOT / "tests/test_new.py", "codebase_health")
        assert result is not None


class TestConstants:
    def test_blocked_paths_nonempty(self):
        assert len(BLOCKED_PATHS) > 0

    def test_blocked_patterns_nonempty(self):
        assert len(BLOCKED_PATTERNS) > 0

    def test_known_dimensions_exist(self):
        for dim in ["scaffolding", "codebase_health", "knowledge_synthesis"]:
            assert dim in DIMENSION_SCOPES
