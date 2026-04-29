"""Tests for isc_validator.py pure helper functions."""
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
    check_count,
    check_conciseness,
    check_anti_criteria,
    check_verify_methods,
)


class TestSanitizeAscii:
    def test_arrow(self):
        assert _sanitize_ascii("→ next") == "-> next"

    def test_em_dash(self):
        assert _sanitize_ascii("before—after") == "before--after"

    def test_en_dash(self):
        assert _sanitize_ascii("a–b") == "a-b"

    def test_ellipsis(self):
        assert _sanitize_ascii("wait…") == "wait..."

    def test_bullet(self):
        assert _sanitize_ascii("• item") == "* item"

    def test_plain_ascii_unchanged(self):
        assert _sanitize_ascii("hello world") == "hello world"


class TestNormalizeUnicode:
    def test_curly_single_quotes(self):
        result = _normalize_unicode("‘hello’")
        assert result == "'hello'"

    def test_curly_double_quotes(self):
        result = _normalize_unicode("“hello”")
        assert result == '"hello"'

    def test_nonbreaking_space(self):
        result = _normalize_unicode("a b")
        assert result == "a b"

    def test_em_dash_becomes_double_hyphen(self):
        result = _normalize_unicode("a—b")
        assert result == "a--b"

    def test_plain_text_unchanged(self):
        assert _normalize_unicode("normal text") == "normal text"


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\nstakes: high\nambiguity: low\n---\nbody"
        fm = parse_frontmatter(text)
        assert fm is not None
        assert fm["stakes"] == "high"
        assert fm["ambiguity"] == "low"

    def test_no_frontmatter_returns_none(self):
        text = "# Title\nNo frontmatter here"
        assert parse_frontmatter(text) is None

    def test_unclosed_frontmatter_returns_none(self):
        text = "---\nstakes: high\n"
        assert parse_frontmatter(text) is None

    def test_empty_values(self):
        text = "---\nkey: \n---\n"
        fm = parse_frontmatter(text)
        assert fm is not None
        assert fm["key"] == ""

    def test_quoted_values_stripped(self):
        text = '---\nstakes: "high"\n---\n'
        fm = parse_frontmatter(text)
        assert fm is not None
        assert fm["stakes"] == "high"

    def test_comments_skipped(self):
        text = "---\n# comment line\nstakes: low\n---\n"
        fm = parse_frontmatter(text)
        assert fm is not None
        assert "stakes" in fm


class TestParseIscItems:
    def test_unchecked_item(self):
        text = "- [ ] The thing works | Verify: pytest passes"
        items = parse_isc_items(text)
        assert len(items) == 1
        assert items[0]["checked"] is False
        assert "thing works" in items[0]["criterion"]

    def test_checked_item_lowercase_x(self):
        text = "- [x] Done criterion | Verify: grep check"
        items = parse_isc_items(text)
        assert items[0]["checked"] is True

    def test_checked_item_uppercase_x(self):
        text = "- [X] Done criterion | Verify: grep check"
        items = parse_isc_items(text)
        assert items[0]["checked"] is True

    def test_verify_method_extracted(self):
        text = "- [ ] Criterion | Verify: run pytest"
        items = parse_isc_items(text)
        assert items[0]["verify_method"] == "run pytest"

    def test_missing_verify_empty_string(self):
        text = "- [ ] Criterion with no verify"
        items = parse_isc_items(text)
        assert items[0]["verify_method"] == ""

    def test_confidence_tag_extracted(self):
        text = "- [ ] Criterion [E] | Verify: check"
        items = parse_isc_items(text)
        assert items[0]["confidence"] == "E"

    def test_empty_text_returns_empty(self):
        assert parse_isc_items("") == []

    def test_non_isc_lines_skipped(self):
        text = "# Header\nSome prose\n- [ ] Real criterion | Verify: cmd\n"
        items = parse_isc_items(text)
        assert len(items) == 1


class TestCheckCount:
    def _phase(self, name, n):
        return {"name": name, "items": [{"criterion": f"c{i}"} for i in range(n)]}

    def test_three_items_passes(self):
        results = check_count([self._phase("p1", 3)])
        assert results[0]["passed"] is True

    def test_eight_items_passes(self):
        results = check_count([self._phase("p1", 8)])
        assert results[0]["passed"] is True

    def test_two_items_fails(self):
        results = check_count([self._phase("p1", 2)])
        assert results[0]["passed"] is False

    def test_nine_items_fails(self):
        results = check_count([self._phase("p1", 9)])
        assert results[0]["passed"] is False

    def test_value_included_in_result(self):
        results = check_count([self._phase("p1", 5)])
        assert results[0]["value"] == 5


class TestCheckAntiCriteria:
    def _item(self, text):
        return {"criterion": text, "verify_method": "cmd", "confidence": None, "verify_type": None}

    def test_no_anti_fails(self):
        items = [self._item("The system processes input"), self._item("Output is written")]
        result = check_anti_criteria(items)
        assert result["passed"] is False
        assert result["anti_count"] == 0

    def test_never_keyword_passes(self):
        items = [self._item("The system never exposes credentials")]
        result = check_anti_criteria(items)
        assert result["passed"] is True
        assert result["anti_count"] == 1

    def test_must_not_keyword_passes(self):
        items = [self._item("Process must not fail silently")]
        result = check_anti_criteria(items)
        assert result["passed"] is True


class TestCheckVerifyMethods:
    def _item(self, verify):
        return {"criterion": "Some criterion", "verify_method": verify}

    def test_with_verify_method_passes(self):
        results = check_verify_methods([self._item("grep output")])
        assert results[0]["passed"] is True

    def test_empty_verify_method_fails(self):
        results = check_verify_methods([self._item("")])
        assert results[0]["passed"] is False

    def test_multiple_items_mixed(self):
        items = [self._item("cmd"), self._item("")]
        results = check_verify_methods(items)
        assert results[0]["passed"] is True
        assert results[1]["passed"] is False
