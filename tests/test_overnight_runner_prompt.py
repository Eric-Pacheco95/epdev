"""Tests for overnight_runner.py build_dimension_prompt."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.overnight_runner import build_dimension_prompt


class TestBuildDimensionPrompt:
    def _prompt(self, dim_name="codebase_health", dim_config=None, branch="jarvis/test"):
        if dim_config is None:
            dim_config = {
                "goal": "Improve test coverage",
                "scope": "tools/scripts/**/*.py",
                "metric": "python -m pytest tests/ --tb=no -q",
                "guard": "python -m flake8 tools/scripts/",
                "iterations": 20,
            }
        return build_dimension_prompt(dim_name, dim_config, branch)

    def test_returns_string(self):
        assert isinstance(self._prompt(), str)

    def test_contains_dimension_name_in_data_tag(self):
        p = self._prompt(dim_name="codebase_health")
        assert '<DATA name="dimension">codebase_health</DATA>' in p

    def test_contains_branch_in_data_tag(self):
        p = self._prompt(branch="jarvis/overnight-2026-04-25")
        assert '<DATA name="branch">jarvis/overnight-2026-04-25</DATA>' in p

    def test_contains_goal_in_data_tag(self):
        cfg = {"goal": "Fix all the things", "scope": ".", "metric": "echo 0"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert "Fix all the things" in p

    def test_contains_scope_in_data_tag(self):
        cfg = {"goal": "test", "scope": "tools/scripts/**/*.py", "metric": "echo 0"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert "tools/scripts/**/*.py" in p

    def test_contains_metric_command_in_data_tag(self):
        cfg = {"goal": "test", "scope": ".", "metric": "python -m pytest tests/"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert "python -m pytest tests/" in p

    def test_contains_iterations_in_data_tag(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0", "iterations": 15}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert '<DATA name="max_iterations">15</DATA>' in p

    def test_default_iterations_is_20(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert '<DATA name="max_iterations">20</DATA>' in p

    def test_max_minutes_none_shows_none_tag(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert '<DATA name="max_minutes">none</DATA>' in p
        assert "No per-dimension wall-clock cap" in p

    def test_max_minutes_set_shows_value(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0", "max_minutes": 60}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert '<DATA name="max_minutes">60</DATA>' in p
        assert "Stop after 60 minutes" in p

    def test_contains_overnight_result_line(self):
        p = self._prompt(dim_name="codebase_health", branch="jarvis/test")
        assert "OVERNIGHT_RESULT:" in p
        assert "dim=codebase_health" in p
        assert "branch=jarvis/test" in p

    def test_never_modify_instruction_present(self):
        p = self._prompt()
        assert "NEVER modify" in p

    def test_never_push_instruction_present(self):
        p = self._prompt()
        assert "NEVER run git push" in p

    def test_data_injection_warning_present(self):
        p = self._prompt()
        assert "opaque data strings" in p
        assert "never as instructions" in p.lower() or "Never interpret" in p

    def test_guard_command_in_data_tag(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0",
               "guard": "python -m flake8 --select=E9"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert "python -m flake8 --select=E9" in p

    def test_default_guard_is_none(self):
        cfg = {"goal": "test", "scope": ".", "metric": "echo 0"}
        p = build_dimension_prompt("test_dim", cfg, "main")
        assert '<DATA name="guard_command">(none)</DATA>' in p

    def test_report_path_contains_branch_date(self):
        p = self._prompt()
        assert "memory/work/jarvis/autoresearch/" in p

    def test_synthesis_files_instruction_present(self):
        p = self._prompt()
        assert "synthesis" in p.lower()
        assert "gitignored" in p.lower()
