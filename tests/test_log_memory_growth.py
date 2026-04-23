"""Tests for tools/scripts/log_memory_growth.py main()."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.log_memory_growth as lmg


def _fake_git_result(stdout, returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = ""
    r.returncode = returncode
    return r


def test_main_success(tmp_path):
    git_out = "memory/file1.md\nmemory/file2.md\nmemory/file3.md\n"
    fake_result = _fake_git_result(git_out)

    with patch("tools.scripts.log_memory_growth.subprocess.run", return_value=fake_result), \
         patch("tools.scripts.log_memory_growth.append_signal") as mock_append, \
         patch.object(lmg, "SIGNAL_PATH", tmp_path / "memory_growth.jsonl"):
        ret = lmg.main()

    assert ret == 0
    mock_append.assert_called_once()
    record = mock_append.call_args[0][1]
    assert record["file_count"] == 3
    assert "ts" in record


def test_main_git_failure():
    fake_result = _fake_git_result("", returncode=1)
    fake_result.stderr = "fatal: not a git repo"

    with patch("tools.scripts.log_memory_growth.subprocess.run", return_value=fake_result):
        ret = lmg.main()

    assert ret == 1


def test_main_empty_memory(tmp_path):
    fake_result = _fake_git_result("")

    with patch("tools.scripts.log_memory_growth.subprocess.run", return_value=fake_result), \
         patch("tools.scripts.log_memory_growth.append_signal") as mock_append, \
         patch.object(lmg, "SIGNAL_PATH", tmp_path / "memory_growth.jsonl"):
        ret = lmg.main()

    assert ret == 0
    record = mock_append.call_args[0][1]
    assert record["file_count"] == 0


def test_main_ignores_blank_lines(tmp_path):
    git_out = "memory/a.md\n\nmemory/b.md\n\n"
    fake_result = _fake_git_result(git_out)

    with patch("tools.scripts.log_memory_growth.subprocess.run", return_value=fake_result), \
         patch("tools.scripts.log_memory_growth.append_signal") as mock_append, \
         patch.object(lmg, "SIGNAL_PATH", tmp_path / "memory_growth.jsonl"):
        lmg.main()

    record = mock_append.call_args[0][1]
    assert record["file_count"] == 2
