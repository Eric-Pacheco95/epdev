"""Tests for verify_bat_date_tokens.audit_bat() -- pure function, no I/O side effects."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_bat_date_tokens as vbdt
from tools.scripts.verify_bat_date_tokens import audit_bat


def _write_bat(tmp_path: Path, content: str, name: str = "run_test.bat") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestAuditBat:
    def test_skip_when_no_logdate(self, tmp_path, monkeypatch):
        """Bat files without SET LOGDATE= are irrelevant -- skip, not fail."""
        bat = _write_bat(tmp_path, "@echo off\necho hello\n")
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert result["status"] == "skip"
        assert "no LOGDATE" in result["reason"]

    def test_pass_with_native_date_token(self, tmp_path, monkeypatch):
        """SET LOGDATE= without subprocess pattern returns pass."""
        content = "@echo off\nset LOGDATE=%DATE:~10,4%-%DATE:~4,2%\necho %LOGDATE%\n"
        bat = _write_bat(tmp_path, content)
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert result["status"] == "pass"

    def test_fail_with_python_subprocess_date(self, tmp_path, monkeypatch):
        """SET LOGDATE= combined with for /f python today.py pattern returns fail."""
        content = (
            "@echo off\n"
            "set LOGDATE=dummy\n"
            "for /f \"tokens=*\" %%d in ('python today.py') do set LOGDATE=%%d\n"
            "echo %LOGDATE%\n"
        )
        bat = _write_bat(tmp_path, content)
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert result["status"] == "fail"
        assert "hits" in result
        assert len(result["hits"]) >= 1

    def test_fail_with_powershell_date(self, tmp_path, monkeypatch):
        """powershell Get-Date via for /f is also a forbidden pattern."""
        content = (
            "@echo off\n"
            "set LOGDATE=x\n"
            "for /f %%d in ('powershell Get-Date -f yyyyMMdd') do set LOGDATE=%%d\n"
        )
        bat = _write_bat(tmp_path, content)
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert result["status"] == "fail"

    def test_result_contains_required_fields(self, tmp_path, monkeypatch):
        """audit_bat always returns a dict with file and status keys."""
        bat = _write_bat(tmp_path, "@echo off\n")
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert "file" in result
        assert "status" in result

    def test_logdate_case_insensitive(self, tmp_path, monkeypatch):
        """SET logdate= (lowercase) is still detected."""
        content = "@echo off\nset logdate=%DATE%\necho done\n"
        bat = _write_bat(tmp_path, content)
        monkeypatch.setattr(vbdt, "REPO_ROOT", tmp_path.parent)
        result = audit_bat(bat)
        assert result["status"] == "pass"
