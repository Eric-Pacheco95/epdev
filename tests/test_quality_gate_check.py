"""Tests for quality_gate_check pure functions."""

import tempfile
from pathlib import Path

from tools.scripts.quality_gate_check import (
    extract_file_refs,
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
