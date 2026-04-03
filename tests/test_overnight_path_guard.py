"""Pytest tests for tools/scripts/overnight_path_guard.py — path validation and security."""

import os
import sys
from pathlib import Path
from unittest import mock

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


class TestHistoryBlocked:
    """history/ directory must be immutable -- no autonomous agent may write to it."""

    def test_history_root_blocked(self):
        with pytest.raises(PathViolation, match="protected path"):
            validate_write_path(GUARD_ROOT / "history" / "decisions" / "2026-04-03-test.md", "scaffolding")

    def test_history_blocked_all_dimensions(self):
        """Every dimension must be denied writes to history/."""
        target = GUARD_ROOT / "history" / "changes" / "change.md"
        for dim in ["scaffolding", "codebase_health", "knowledge_synthesis",
                    "external_monitoring", "prompt_quality", "cross_project",
                    "algorithm_adherence"]:
            with pytest.raises(PathViolation, match="protected path"):
                validate_write_path(target, dim)

    def test_history_security_subdir_blocked(self):
        with pytest.raises(PathViolation, match="protected path"):
            validate_write_path(GUARD_ROOT / "history" / "security" / "event.json", "codebase_health")


class TestDimensionEnvVarIntegration:
    """Verify that validate_tool_use.py honours JARVIS_OVERNIGHT_DIMENSION."""

    def test_overnight_dimension_blocks_out_of_scope_write(self):
        """codebase_health must NOT write to .claude/skills/."""
        from security.validators.validate_tool_use import _check_overnight_path_scope
        inp = {"file_path": str(GUARD_ROOT / ".claude" / "skills" / "test" / "SKILL.md")}
        with mock.patch.dict(os.environ, {
            "JARVIS_SESSION_TYPE": "autonomous",
            "JARVIS_OVERNIGHT_DIMENSION": "codebase_health",
        }):
            result = _check_overnight_path_scope("Write", inp)
        assert result is not None
        assert result["decision"] == "block"
        assert "codebase_health" in result.get("reason", "")

    def test_overnight_dimension_allows_in_scope_write(self):
        """scaffolding may write to .claude/skills/."""
        from security.validators.validate_tool_use import _check_overnight_path_scope
        inp = {"file_path": str(GUARD_ROOT / ".claude" / "skills" / "new-skill" / "SKILL.md")}
        with mock.patch.dict(os.environ, {
            "JARVIS_SESSION_TYPE": "autonomous",
            "JARVIS_OVERNIGHT_DIMENSION": "scaffolding",
        }):
            result = _check_overnight_path_scope("Write", inp)
        assert result is None  # allowed

    def test_overnight_dimension_blocks_history_write(self):
        """No dimension may write to history/ -- the path guard blocks it."""
        from security.validators.validate_tool_use import _check_overnight_path_scope
        inp = {"file_path": str(GUARD_ROOT / "history" / "decisions" / "foo.md")}
        with mock.patch.dict(os.environ, {
            "JARVIS_SESSION_TYPE": "autonomous",
            "JARVIS_OVERNIGHT_DIMENSION": "scaffolding",
        }):
            result = _check_overnight_path_scope("Write", inp)
        assert result is not None
        assert result["decision"] == "block"

    def test_no_dimension_env_var_skips_check(self):
        """When JARVIS_OVERNIGHT_DIMENSION is absent, the check is a no-op."""
        from security.validators.validate_tool_use import _check_overnight_path_scope
        inp = {"file_path": str(GUARD_ROOT / "history" / "decisions" / "foo.md")}
        env = {"JARVIS_SESSION_TYPE": "autonomous"}
        # Ensure JARVIS_OVERNIGHT_DIMENSION is absent
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("JARVIS_OVERNIGHT_DIMENSION", None)
            result = _check_overnight_path_scope("Write", inp)
        assert result is None  # no-op when dimension not set

    def test_non_autonomous_session_skips_check(self):
        """Non-autonomous sessions are unaffected by overnight path enforcement."""
        from security.validators.validate_tool_use import _check_overnight_path_scope
        inp = {"file_path": str(GUARD_ROOT / "history" / "decisions" / "foo.md")}
        with mock.patch.dict(os.environ, {
            "JARVIS_SESSION_TYPE": "interactive",
            "JARVIS_OVERNIGHT_DIMENSION": "scaffolding",
        }):
            result = _check_overnight_path_scope("Write", inp)
        assert result is None  # non-autonomous sessions pass through


class TestConstants:
    def test_blocked_paths_nonempty(self):
        assert len(BLOCKED_PATHS) > 0

    def test_blocked_patterns_nonempty(self):
        assert len(BLOCKED_PATTERNS) > 0

    def test_known_dimensions_exist(self):
        for dim in ["scaffolding", "codebase_health", "knowledge_synthesis"]:
            assert dim in DIMENSION_SCOPES

    def test_history_in_blocked_paths(self):
        """history/ must be explicitly listed in BLOCKED_PATHS."""
        history_path = GUARD_ROOT / "history"
        assert any(
            str(p).lower() == str(history_path).lower()
            for p in BLOCKED_PATHS
        ), f"history/ not found in BLOCKED_PATHS: {BLOCKED_PATHS}"

    def test_algorithm_adherence_scope_exists(self):
        """algorithm_adherence dimension must have an explicit scope entry."""
        assert "algorithm_adherence" in DIMENSION_SCOPES

    def test_algorithm_adherence_covers_skills(self):
        """algorithm_adherence scope must include .claude/skills/."""
        skills_path = GUARD_ROOT / ".claude" / "skills"
        scope = DIMENSION_SCOPES.get("algorithm_adherence", [])
        assert any(
            str(p).lower() == str(skills_path).lower()
            for p in scope
        ), f".claude/skills not in algorithm_adherence scope: {scope}"

    def test_scaffolding_covers_skills(self):
        """scaffolding scope must include .claude/skills/ (pre-existing requirement)."""
        skills_path = GUARD_ROOT / ".claude" / "skills"
        scope = DIMENSION_SCOPES.get("scaffolding", [])
        assert any(
            str(p).lower() == str(skills_path).lower()
            for p in scope
        ), f".claude/skills not in scaffolding scope: {scope}"
