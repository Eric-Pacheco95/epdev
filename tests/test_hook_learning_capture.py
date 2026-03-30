"""Pytest tests for tools/scripts/hook_learning_capture.py — _slugify and _unique_path."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.hook_learning_capture import _slugify, _unique_path


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("Fix bug #123!") == "fix-bug-123"

    def test_leading_trailing_stripped(self):
        assert _slugify("  --hello--  ") == "hello"

    def test_empty_fallback(self):
        assert _slugify("") == "signal"

    def test_only_special_chars(self):
        assert _slugify("!!!") == "signal"

    def test_long_title_truncated(self):
        long_title = "a" * 100
        result = _slugify(long_title)
        assert len(result) <= 60

    def test_unicode_chars_stripped(self):
        result = _slugify("caf\u00e9 latt\u00e9")
        assert "caf" in result

    def test_multiple_spaces(self):
        assert _slugify("one   two   three") == "one-two-three"


class TestUniquePath:
    def test_first_path_no_collision(self, tmp_path):
        result = _unique_path(tmp_path, "test-signal")
        assert result == tmp_path / "test-signal.md"

    def test_increments_on_collision(self, tmp_path):
        (tmp_path / "test-signal.md").write_text("existing")
        result = _unique_path(tmp_path, "test-signal")
        assert result == tmp_path / "test-signal_2.md"

    def test_increments_further(self, tmp_path):
        (tmp_path / "test-signal.md").write_text("existing")
        (tmp_path / "test-signal_2.md").write_text("existing")
        result = _unique_path(tmp_path, "test-signal")
        assert result == tmp_path / "test-signal_3.md"

    def test_different_stems_no_collision(self, tmp_path):
        (tmp_path / "other.md").write_text("existing")
        result = _unique_path(tmp_path, "test-signal")
        assert result == tmp_path / "test-signal.md"
