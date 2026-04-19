"""Tests for verify_no_orphan_spawn_patterns -- audit_{isc_executor,bat_wrappers,py_callers}."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_no_orphan_spawn_patterns as vnosp
from tools.scripts.verify_no_orphan_spawn_patterns import (
    audit_isc_executor,
    audit_bat_wrappers,
    audit_py_callers,
)


class TestAuditIscExecutor:
    def test_pass_when_no_shell_true(self, tmp_path, monkeypatch):
        f = tmp_path / "isc_executor.py"
        f.write_text("subprocess.run(['pytest'], capture_output=True)\n")
        monkeypatch.setattr(vnosp, "_ISC_EXECUTOR", f)
        result = audit_isc_executor()
        assert result["status"] == "pass"
        assert result["hits"] == []

    def test_fail_when_shell_true_present(self, tmp_path, monkeypatch):
        f = tmp_path / "isc_executor.py"
        f.write_text("subprocess.run(cmd, shell=True)\n")
        monkeypatch.setattr(vnosp, "_ISC_EXECUTOR", f)
        result = audit_isc_executor()
        assert result["status"] == "fail"
        assert len(result["hits"]) >= 1

    def test_error_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vnosp, "_ISC_EXECUTOR", tmp_path / "nonexistent.py")
        result = audit_isc_executor()
        assert result["status"] == "error"


class TestAuditBatWrappers:
    def test_pass_with_no_forbidden_patterns(self, tmp_path, monkeypatch):
        bat = tmp_path / "run_test.bat"
        bat.write_text("@echo off\nset LOGDATE=%DATE%\necho %LOGDATE%\n")
        monkeypatch.setattr(vnosp, "_BAT_DIR", tmp_path)
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_bat_wrappers()
        assert result["status"] == "pass"
        assert result["hits"] == []

    def test_fail_with_python_subprocess_date(self, tmp_path, monkeypatch):
        bat = tmp_path / "run_test.bat"
        bat.write_text(
            "@echo off\n"
            "for /f \"tokens=*\" %%d in ('python today.py') do set LOGDATE=%%d\n"
        )
        monkeypatch.setattr(vnosp, "_BAT_DIR", tmp_path)
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_bat_wrappers()
        assert result["status"] == "fail"
        assert len(result["hits"]) >= 1

    def test_pass_with_no_bat_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vnosp, "_BAT_DIR", tmp_path)
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_bat_wrappers()
        assert result["status"] == "pass"


class TestAuditPyCallers:
    def test_pass_when_no_claude_calls(self, tmp_path, monkeypatch):
        py = tmp_path / "runner.py"
        py.write_text("subprocess.run(['pytest', '--tb=short'])\n")
        monkeypatch.setattr(vnosp, "_PY_TARGETS", [py])
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_py_callers()
        assert result["status"] == "pass"

    def test_fail_when_claude_subprocess_present(self, tmp_path, monkeypatch):
        py = tmp_path / "runner.py"
        py.write_text("subprocess.run(['claude', '--dangerously-skip-permissions'])\n")
        monkeypatch.setattr(vnosp, "_PY_TARGETS", [py])
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_py_callers()
        assert result["status"] == "fail"
        assert len(result["hits"]) >= 1

    def test_missing_py_target_counts_as_hit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vnosp, "_PY_TARGETS", [tmp_path / "missing.py"])
        monkeypatch.setattr(vnosp, "REPO_ROOT", tmp_path.parent)
        result = audit_py_callers()
        assert result["status"] == "fail"
