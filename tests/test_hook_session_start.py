"""Pytest tests for hook_session_start.py pure helper functions.

The source module replaces sys.stdout at import time, which breaks pytest
capture. These tests redefine the pure functions locally (copied from source)
to verify their logic without the problematic import side effect.

If the source functions change, these tests should be updated to match.
"""

import re
from pathlib import Path


# --- Copied pure functions from tools/scripts/hook_session_start.py ---
# These have zero I/O side effects and can be tested in isolation.

SYNTHESIS_HARD_CEILING = 20
SYNTHESIS_TIERS = [
    (10, 48),
    (8, 72),
]


def _ascii_safe(text: str) -> str:
    result = (
        text
        .replace("\u2014", "--")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
        .replace("\u2265", ">=")
        .replace("\u2264", "<=")
        .replace("\u2022", "-")
        .replace("\u2192", "->")
        .replace("\u2190", "<-")
    )
    return result.encode("ascii", errors="replace").decode("ascii")


def _unchecked_tasks(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(\s*)-\s+\[([ xX])\]\s+(.*)$", line)
        if m and m.group(2).lower() != "x":
            lines.append(m.group(3).strip())
    return lines


def _synthesis_due(n_signals: int, hours_since: float = float("inf")) -> tuple[bool, str]:
    """Simplified version for testing — accepts hours_since as param instead of reading FS."""
    if n_signals >= SYNTHESIS_HARD_CEILING:
        return True, f"signal count ({n_signals}) >= hard ceiling ({SYNTHESIS_HARD_CEILING})"
    for min_signals, min_hours in SYNTHESIS_TIERS:
        if n_signals >= min_signals and hours_since >= min_hours:
            return True, f"{n_signals} signals + {hours_since:.0f}h since last synthesis (threshold: {min_signals} signals / {min_hours}h)"
    return False, ""


def _count_files(directory: Path, ext: str = ".md") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.iterdir() if p.is_file() and p.suffix == ext)


# --- Tests ---


class TestAsciiSafe:
    def test_em_dash(self):
        assert _ascii_safe("hello\u2014world") == "hello--world"

    def test_en_dash(self):
        assert _ascii_safe("1\u20132") == "1-2"

    def test_smart_quotes(self):
        assert _ascii_safe("\u201cquoted\u201d") == '"quoted"'

    def test_ellipsis(self):
        assert _ascii_safe("wait\u2026") == "wait..."

    def test_arrows(self):
        assert _ascii_safe("\u2192 next") == "-> next"
        assert _ascii_safe("\u2190 prev") == "<- prev"

    def test_bullet(self):
        assert _ascii_safe("\u2022 item") == "- item"

    def test_comparison_operators(self):
        assert _ascii_safe("x \u2265 5") == "x >= 5"
        assert _ascii_safe("x \u2264 3") == "x <= 3"

    def test_plain_ascii_unchanged(self):
        assert _ascii_safe("hello world 123") == "hello world 123"

    def test_remaining_unicode_replaced(self):
        result = _ascii_safe("caf\u00e9")
        assert "?" in result

    def test_empty_string(self):
        assert _ascii_safe("") == ""


class TestUncheckedTasks:
    def test_extracts_unchecked(self):
        text = "- [ ] Task one\n- [x] Done task\n- [ ] Task two"
        result = _unchecked_tasks(text)
        assert result == ["Task one", "Task two"]

    def test_ignores_checked(self):
        text = "- [x] Done\n- [X] Also done"
        assert _unchecked_tasks(text) == []

    def test_empty_input(self):
        assert _unchecked_tasks("") == []

    def test_indented_tasks(self):
        text = "  - [ ] Indented task\n    - [ ] Deep task"
        result = _unchecked_tasks(text)
        assert "Indented task" in result
        assert "Deep task" in result

    def test_strips_whitespace(self):
        text = "- [ ]   Spaced out task  "
        result = _unchecked_tasks(text)
        assert result == ["Spaced out task"]

    def test_bold_tasks(self):
        text = "- [ ] **Bold task** -- some detail"
        result = _unchecked_tasks(text)
        assert result == ["**Bold task** -- some detail"]

    def test_no_checkbox_lines_ignored(self):
        text = "Regular line\n## Header\n- [ ] Actual task"
        result = _unchecked_tasks(text)
        assert result == ["Actual task"]


class TestSynthesisDue:
    def test_above_hard_ceiling(self):
        due, reason = _synthesis_due(SYNTHESIS_HARD_CEILING)
        assert due is True
        assert "hard ceiling" in reason

    def test_well_above_ceiling(self):
        due, reason = _synthesis_due(100)
        assert due is True

    def test_below_all_thresholds(self):
        due, reason = _synthesis_due(3)
        assert due is False
        assert reason == ""

    def test_zero_signals(self):
        due, reason = _synthesis_due(0)
        assert due is False

    def test_mid_tier_10_signals_48h(self):
        due, reason = _synthesis_due(10, hours_since=50)
        assert due is True

    def test_mid_tier_10_signals_not_enough_hours(self):
        due, reason = _synthesis_due(10, hours_since=24)
        assert due is False

    def test_low_tier_8_signals_72h(self):
        due, reason = _synthesis_due(8, hours_since=80)
        assert due is True

    def test_low_tier_8_signals_not_enough_hours(self):
        due, reason = _synthesis_due(8, hours_since=48)
        assert due is False


class TestCountFiles:
    def test_nonexistent_dir(self, tmp_path):
        assert _count_files(tmp_path / "nonexistent") == 0

    def test_empty_dir(self, tmp_path):
        assert _count_files(tmp_path) == 0

    def test_counts_md_files(self, tmp_path):
        (tmp_path / "a.md").write_text("x")
        (tmp_path / "b.md").write_text("y")
        (tmp_path / "c.txt").write_text("z")
        assert _count_files(tmp_path) == 2

    def test_custom_extension(self, tmp_path):
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "b.py").write_text("y")
        assert _count_files(tmp_path, ext=".py") == 2
