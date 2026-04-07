"""Tests for content_pipeline/review_gate.py pure string helpers."""

from tools.scripts.content_pipeline.review_gate import extract_body_preview, parse_title_from_draft


# ---------------------------------------------------------------------------
# parse_title_from_draft
# ---------------------------------------------------------------------------

def test_parse_title_from_frontmatter():
    content = "---\ntitle: My Great Post\ndate: 2026-01-01\n---\n# Different H1\n"
    assert parse_title_from_draft(content) == "My Great Post"


def test_parse_title_from_h1_fallback():
    content = "# The Real Title\n\nSome body text."
    assert parse_title_from_draft(content) == "The Real Title"


def test_parse_title_untitled_fallback():
    content = "No title here, just body text.\n"
    assert parse_title_from_draft(content) == "Untitled"


def test_parse_title_strips_whitespace():
    content = "---\ntitle:   Spaced Title   \n---\n"
    assert parse_title_from_draft(content) == "Spaced Title"


# ---------------------------------------------------------------------------
# extract_body_preview
# ---------------------------------------------------------------------------

def test_extract_body_preview_plain():
    content = "Some body text here that is long enough to preview."
    preview = extract_body_preview(content, chars=20)
    assert len(preview) <= 20
    assert "Some body" in preview


def test_extract_body_preview_strips_frontmatter():
    content = "---\ntitle: T\ndate: 2026\n---\nActual body content."
    preview = extract_body_preview(content)
    assert "Actual body content" in preview
    assert "title:" not in preview


def test_extract_body_preview_strips_h1():
    content = "# Big Title\nBody starts here."
    preview = extract_body_preview(content)
    assert "Big Title" not in preview
    assert "Body starts here" in preview


def test_extract_body_preview_newlines_replaced():
    content = "Line one.\nLine two.\nLine three."
    preview = extract_body_preview(content)
    assert "\n" not in preview


def test_extract_body_preview_empty():
    assert extract_body_preview("") == ""
