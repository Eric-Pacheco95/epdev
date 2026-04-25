"""Tests for hook_session_start.py -- pure helper functions."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# hook_session_start.py replaces sys.stdout at import time; restore to avoid
# breaking pytest capture (same fix as test_theme_shuffle.py).
_saved_stdout = sys.stdout
import tools.scripts.hook_session_start as hss
if sys.stdout is not _saved_stdout:
    sys.stdout.detach()
sys.stdout = _saved_stdout


class TestAsciiSafe:
    def test_em_dash_replaced(self):
        assert hss._ascii_safe("—") == "--"

    def test_en_dash_replaced(self):
        assert hss._ascii_safe("–") == "-"

    def test_left_single_quote(self):
        assert hss._ascii_safe("‘") == "'"

    def test_right_single_quote(self):
        assert hss._ascii_safe("’") == "'"

    def test_ellipsis(self):
        assert hss._ascii_safe("…") == "..."

    def test_bullet(self):
        assert hss._ascii_safe("•") == "-"

    def test_plain_text_unchanged(self):
        assert hss._ascii_safe("hello world") == "hello world"

    def test_empty_string(self):
        assert hss._ascii_safe("") == ""

    def test_right_arrow(self):
        assert hss._ascii_safe("→") == "->"


class TestUncheckedTasks:
    def test_returns_unchecked_items(self):
        text = "- [ ] Task one\n- [x] Done\n- [ ] Task two\n"
        result = hss._unchecked_tasks(text)
        assert "Task one" in result
        assert "Task two" in result
        assert "Done" not in result

    def test_empty_text_returns_empty(self):
        assert hss._unchecked_tasks("") == []

    def test_all_checked_returns_empty(self):
        text = "- [x] Done\n- [X] Also done\n"
        assert hss._unchecked_tasks(text) == []

    def test_indented_items_included(self):
        text = "  - [ ] Indented task\n"
        result = hss._unchecked_tasks(text)
        assert "Indented task" in result

    def test_non_task_lines_ignored(self):
        text = "# Header\nSome text\n- [ ] Real task\n"
        result = hss._unchecked_tasks(text)
        assert len(result) == 1
        assert result[0] == "Real task"


class TestCountFiles:
    def test_empty_dir_returns_zero(self, tmp_path):
        assert hss._count_files(tmp_path) == 0

    def test_counts_md_files(self, tmp_path):
        (tmp_path / "a.md").touch()
        (tmp_path / "b.md").touch()
        assert hss._count_files(tmp_path) == 2

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "a.md").touch()
        (tmp_path / "b.txt").touch()
        assert hss._count_files(tmp_path) == 1

    def test_custom_extension(self, tmp_path):
        (tmp_path / "a.json").touch()
        (tmp_path / "b.md").touch()
        assert hss._count_files(tmp_path, ext=".json") == 1

    def test_missing_dir_returns_zero(self, tmp_path):
        assert hss._count_files(tmp_path / "missing") == 0


class TestSynthesisDue:
    def test_hard_ceiling_triggers(self):
        with patch.object(hss, "_hours_since_last_synthesis", return_value=1.0):
            due, reason = hss._synthesis_due(hss.SYNTHESIS_HARD_CEILING)
        assert due is True
        assert "hard ceiling" in reason

    def test_below_threshold_not_due(self):
        with patch.object(hss, "_hours_since_last_synthesis", return_value=1.0):
            due, reason = hss._synthesis_due(5)
        assert due is False

    def test_tier_threshold_triggers(self):
        with patch.object(hss, "_hours_since_last_synthesis", return_value=100.0):
            due, reason = hss._synthesis_due(15)
        assert due is True
