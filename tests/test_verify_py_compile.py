"""Tests for tools/scripts/verify_py_compile.py."""
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.verify_py_compile import _safe_target, main, REPO_ROOT


# --- _safe_target ---

def test_safe_target_valid_relative():
    p = _safe_target("tools/scripts/verify_py_compile.py")
    assert p.is_absolute()
    assert REPO_ROOT in p.parents


def test_safe_target_rejects_absolute_path():
    import pytest
    with pytest.raises(ValueError, match="repo-relative"):
        _safe_target("/etc/passwd")


def test_safe_target_rejects_dotdot():
    import pytest
    with pytest.raises(ValueError, match="'\\.\\.'"):
        _safe_target("tools/../../../etc/passwd")


def test_safe_target_rejects_empty():
    import pytest
    with pytest.raises(ValueError):
        _safe_target("")


# --- main ---

def test_main_valid_python_file(tmp_path, monkeypatch):
    src = tmp_path / "valid.py"
    src.write_text("x = 1\n", encoding="utf-8")
    fake_root = tmp_path
    with patch("tools.scripts.verify_py_compile.REPO_ROOT", fake_root):
        monkeypatch.setattr(sys, "argv", ["prog", "valid.py"])
        result = main()
    assert result == 0


def test_main_invalid_python_file(tmp_path, monkeypatch):
    src = tmp_path / "broken.py"
    src.write_text("def foo(\n", encoding="utf-8")
    with patch("tools.scripts.verify_py_compile.REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "broken.py"])
        result = main()
    assert result == 1


def test_main_nonexistent_file(tmp_path, monkeypatch):
    with patch("tools.scripts.verify_py_compile.REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "nope.py"])
        result = main()
    assert result == 1


def test_main_non_py_file(tmp_path, monkeypatch):
    src = tmp_path / "file.txt"
    src.write_text("hello\n", encoding="utf-8")
    with patch("tools.scripts.verify_py_compile.REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "file.txt"])
        result = main()
    assert result == 1


def test_main_absolute_path_rejected(tmp_path, monkeypatch):
    with patch("tools.scripts.verify_py_compile.REPO_ROOT", tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "/etc/passwd"])
        result = main()
    assert result == 2
