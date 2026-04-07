"""Tests for quality_gate_check pure functions."""

import tempfile
from pathlib import Path

from tools.scripts.quality_gate_check import (
    _sanitize_ascii,
    extract_file_refs,
    format_report,
    parse_isc_items,
)


# ── extract_file_refs ────────────────────────────────────────────────

def test_extract_file_refs_backtick():
    text = "See `tools/scripts/foo.py` for details"
    refs = extract_file_refs(text)
    assert "tools/scripts/foo.py" in refs


def test_extract_file_refs_markdown_link():
    text = "Read [the guide](docs/guide.md) first"
    refs = extract_file_refs(text)
    assert "docs/guide.md" in refs


def test_extract_file_refs_ignores_urls():
    text = "See [link](https://example.com/page.html)"
    refs = extract_file_refs(text)
    assert len(refs) == 0


def test_extract_file_refs_multiple():
    text = "`src/main.py` and `tests/test_main.py`"
    refs = extract_file_refs(text)
    assert len(refs) == 2


def test_extract_file_refs_no_path():
    text = "`foo` is not a path"
    refs = extract_file_refs(text)
    assert len(refs) == 0


# ── parse_isc_items ──────────────────────────────────────────────────

def test_parse_isc_items_basic():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write("- [ ] Auth tokens expire [E] | Verify: CLI\n")
        f.write("- [x] Deploy complete [I] [M] | Verify: Test\n")
        f.flush()
        p = Path(f.name)

    items = parse_isc_items(p)
    assert len(items) == 2
    assert items[0]["checked"] is False
    assert items[0]["confidence"] == "E"
    assert items[1]["checked"] is True
    assert items[1]["verify_type"] == "M"
    p.unlink()


def test_parse_isc_items_nonexistent():
    items = parse_isc_items(Path("/nonexistent/prd.md"))
    assert items == []


def test_parse_isc_items_no_criteria():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write("# Just a heading\n\nSome text\n")
        f.flush()
        p = Path(f.name)

    items = parse_isc_items(p)
    assert items == []
    p.unlink()


# ── _sanitize_ascii ──────────────────────────────────────────────────

def test_sanitize_ascii_arrow():
    assert _sanitize_ascii("A \u2192 B") == "A -> B"


def test_sanitize_ascii_em_dash():
    assert _sanitize_ascii("foo\u2014bar") == "foo--bar"


def test_sanitize_ascii_smart_quotes():
    assert _sanitize_ascii("\u201chello\u201d") == '"hello"'


def test_sanitize_ascii_no_change():
    assert _sanitize_ascii("plain text") == "plain text"


# ── format_report ────────────────────────────────────────────────────

def test_format_report_no_issues():
    report = {
        "tasklist": None,
        "decisions": None,
        "file_checks": [],
        "issues": [],
    }
    result = format_report(report)
    assert "No issues found." in result


def test_format_report_with_issues():
    report = {
        "tasklist": None,
        "decisions": None,
        "file_checks": [],
        "issues": [{"severity": "warn", "message": "Something might be wrong"}],
    }
    result = format_report(report)
    assert "WARN" in result
    assert "Something might be wrong" in result


def test_format_report_tasklist():
    report = {
        "tasklist": {"total": 10, "checked": 7, "unchecked": 3, "completion_pct": 70, "open_items": []},
        "decisions": None,
        "file_checks": [],
        "issues": [],
    }
    result = format_report(report)
    assert "10 tasks" in result
    assert "70%" in result
