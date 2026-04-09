"""Tests for hook_post_compact.py -- _unchecked_items helper."""

from tools.scripts.hook_post_compact import _unchecked_items


def test_unchecked_items_basic():
    text = "- [ ] Do this\n- [x] Done\n- [ ] Do that\n"
    result = _unchecked_items(text)
    assert result == ["Do this", "Do that"]


def test_unchecked_items_empty():
    assert _unchecked_items("") == []


def test_unchecked_items_all_checked():
    text = "- [x] Done 1\n- [X] Done 2\n"
    assert _unchecked_items(text) == []


def test_unchecked_items_strips_whitespace():
    text = "- [ ]   Task with leading spaces  \n"
    result = _unchecked_items(text)
    assert result == ["Task with leading spaces"]


def test_unchecked_items_indented():
    text = "  - [ ] Indented task\n"
    result = _unchecked_items(text)
    assert result == ["Indented task"]


def test_unchecked_items_ignores_non_checkbox_lines():
    text = "# Header\nSome paragraph\n- [ ] Real task\n- Not a checkbox\n"
    result = _unchecked_items(text)
    assert result == ["Real task"]
