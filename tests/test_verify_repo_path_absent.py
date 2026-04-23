"""Tests for tools/scripts/verify_repo_path_absent.py."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.verify_repo_path_absent import _safe_target, main, REPO_ROOT
import tools.scripts.verify_repo_path_absent as vrpa


def test_safe_target_valid():
    p = _safe_target("tools/scripts/verify_repo_path_absent.py")
    assert p.is_absolute()
    assert REPO_ROOT in p.parents


def test_safe_target_rejects_absolute():
    import pytest
    with pytest.raises(ValueError, match="repo-relative"):
        _safe_target("/etc/passwd")


def test_safe_target_rejects_dotdot():
    import pytest
    with pytest.raises(ValueError, match="'\\.\\.'"):
        _safe_target("tools/../../outside")


def test_main_path_absent(tmp_path, monkeypatch):
    with patch.object(vrpa, "REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "nonexistent.py"])
        assert vrpa.main() == 0


def test_main_path_exists(tmp_path, monkeypatch):
    (tmp_path / "exists.py").write_text("x=1", encoding="utf-8")
    with patch.object(vrpa, "REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "exists.py"])
        assert vrpa.main() == 1


def test_main_absolute_path_rejected(tmp_path, monkeypatch):
    with patch.object(vrpa, "REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "/etc/passwd"])
        assert vrpa.main() == 2
