"""Tests for isc_validator.py -- pure helper functions."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.isc_validator import (
    _sanitize_ascii,
    _normalize_unicode,
    parse_frontmatter,
    parse_isc_items,
)


# ---------------------------------------------------------------------------
# _sanitize_ascii
# ---------------------------------------------------------------------------

class TestSanitizeAscii:
    def test_arrow_replaced(self):
        assert _sanitize_ascii("A → B") == "A -> B"

    def test_em_dash_replaced(self):
        assert _sanitize_ascii("one—two") == "one--two"

    def test_curly_quotes_replaced(self):
        result = _sanitize_ascii("“hello”")
        assert result == '"hello"'

    def test_bullet_replaced(self):
        assert _sanitize_ascii("• item") == "* item"

    def test_plain_text_unchanged(self):
        assert _sanitize_ascii("hello world") == "hello world"

    def test_empty_string(self):
        assert _sanitize_ascii("") == ""


# ---------------------------------------------------------------------------
# _normalize_unicode
# ---------------------------------------------------------------------------

class TestNormalizeUnicode:
    def test_curly_single_quotes_normalized(self):
        result = _normalize_unicode("‘hi’")
        assert result == "'hi'"

    def test_non_breaking_space_becomes_space(self):
        result = _normalize_unicode("a b")
        assert result == "a b"

    def test_em_dash_normalized(self):
        result = _normalize_unicode("one—two")
        assert result == "one--two"

    def test_plain_text_unchanged(self):
        assert _normalize_unicode("hello world") == "hello world"


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\nstakes: high\nambiguity: low\n---\nBody here.\n"
        fm = parse_frontmatter(text)
        assert fm is not None
        assert fm["stakes"] == "high"
        assert fm["ambiguity"] == "low"

    def test_no_frontmatter_returns_none(self):
        assert parse_frontmatter("# Just a heading\nsome text") is None

    def test_missing_closing_delimiter_returns_none(self):
        text = "---\nkey: value\n"
        assert parse_frontmatter(text) is None

    def test_values_lowercased(self):
        text = "---\nstakes: HIGH\n---\n"
        fm = parse_frontmatter(text)
        assert fm["stakes"] == "high"

    def test_empty_value(self):
        text = "---\nkey:\n---\n"
        fm = parse_frontmatter(text)
        assert fm["key"] == ""

    def test_comments_skipped(self):
        text = "---\n# this is a comment\nstakes: medium\n---\n"
        fm = parse_frontmatter(text)
        assert "stakes" in fm
        assert "#" not in fm


# ---------------------------------------------------------------------------
# parse_isc_items
# ---------------------------------------------------------------------------

class TestParseIscItems:
    def test_unchecked_item(self):
        text = "- [ ] The system must respond in under 1s\n"
        items = parse_isc_items(text)
        assert len(items) == 1
        assert items[0]["checked"] is False

    def test_checked_item(self):
        text = "- [x] The system must respond in under 1s\n"
        items = parse_isc_items(text)
        assert items[0]["checked"] is True

    def test_uppercase_X_checked(self):
        text = "- [X] Done item\n"
        items = parse_isc_items(text)
        assert items[0]["checked"] is True

    def test_verify_method_extracted(self):
        text = "- [ ] File exists | Verify: ls output\n"
        items = parse_isc_items(text)
        assert items[0]["verify_method"] == "ls output"

    def test_no_verify_method_empty_string(self):
        text = "- [ ] Simple criterion\n"
        items = parse_isc_items(text)
        assert items[0]["verify_method"] == ""

    def test_confidence_tag_extracted(self):
        text = "- [ ] Some criterion [E]\n"
        items = parse_isc_items(text)
        assert items[0]["confidence"] == "E"

    def test_no_confidence_tag_is_none(self):
        text = "- [ ] No confidence tag\n"
        items = parse_isc_items(text)
        assert items[0]["confidence"] is None

    def test_non_isc_lines_skipped(self):
        text = "# Heading\nSome prose.\n- [ ] Real ISC item\n"
        items = parse_isc_items(text)
        assert len(items) == 1

    def test_empty_text_returns_empty(self):
        assert parse_isc_items("") == []

    def test_multiple_items(self):
        text = "- [ ] Item 1\n- [x] Item 2\n- [ ] Item 3\n"
        items = parse_isc_items(text)
        assert len(items) == 3
