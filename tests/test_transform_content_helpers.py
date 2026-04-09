"""Tests for content_pipeline/transform_content.py pure helper functions."""

from tools.scripts.content_pipeline.transform_content import (
    build_draft_markdown,
    build_frontmatter,
    format_source_block,
    parse_draft_output,
)


# ---------------------------------------------------------------------------
# format_source_block
# ---------------------------------------------------------------------------

def test_format_source_block_basic():
    source = {"type": "signal", "date": "2026-01-01", "path": "signals/test.md", "content": "Some content"}
    result = format_source_block(source)
    assert "SIGNAL" in result
    assert "test.md" in result
    assert "2026-01-01" in result
    assert "Some content" in result


def test_format_source_block_with_rating():
    source = {"type": "signal", "date": "2026-01-01", "path": "x.md", "content": "", "rating": 8}
    result = format_source_block(source)
    assert "Rating: 8" in result


def test_format_source_block_truncates_long_content():
    source = {"type": "signal", "date": "2026-01-01", "path": "x.md", "content": "A" * 4000}
    result = format_source_block(source)
    assert "truncated" in result
    assert len(result) < 4000


def test_format_source_block_no_path():
    source = {"type": "research", "date": "2026-01-01", "content": "short"}
    result = format_source_block(source)
    assert "RESEARCH" in result


# ---------------------------------------------------------------------------
# parse_draft_output
# ---------------------------------------------------------------------------

SAMPLE_OUTPUT = """\
TITLE: The Gate Before The Gate
SUBTITLE: Why task selection is the hardest problem
TLDR:
- Key insight one
- Key insight two

BODY:
This is the body text.
It continues here.
"""


def test_parse_draft_output_title():
    parsed = parse_draft_output(SAMPLE_OUTPUT)
    assert parsed["title"] == "The Gate Before The Gate"


def test_parse_draft_output_subtitle():
    parsed = parse_draft_output(SAMPLE_OUTPUT)
    assert parsed["subtitle"] == "Why task selection is the hardest problem"


def test_parse_draft_output_tldr():
    parsed = parse_draft_output(SAMPLE_OUTPUT)
    assert len(parsed["tldr"]) == 2
    assert "- Key insight one" in parsed["tldr"]


def test_parse_draft_output_body():
    parsed = parse_draft_output(SAMPLE_OUTPUT)
    assert "body text" in parsed["body"]


def test_parse_draft_output_empty():
    parsed = parse_draft_output("")
    assert parsed["title"] == ""
    assert parsed["body"] == ""
    assert parsed["tldr"] == []


# ---------------------------------------------------------------------------
# build_frontmatter
# ---------------------------------------------------------------------------

def test_build_frontmatter_contains_title():
    fm = build_frontmatter("My Title", "2026-01-01")
    assert "title: My Title" in fm


def test_build_frontmatter_status_draft():
    fm = build_frontmatter("T", "2026-01-01")
    assert "status: draft" in fm


def test_build_frontmatter_wrapped_in_dashes():
    fm = build_frontmatter("T", "2026-01-01")
    assert fm.startswith("---")


# ---------------------------------------------------------------------------
# build_draft_markdown
# ---------------------------------------------------------------------------

def test_build_draft_markdown_includes_title_h1():
    parsed = {"title": "My Post", "subtitle": "Sub", "tldr": [], "body": "Body here."}
    result = build_draft_markdown(parsed, "2026-01-01")
    assert "# My Post" in result


def test_build_draft_markdown_includes_body():
    parsed = {"title": "T", "subtitle": "", "tldr": [], "body": "The real content."}
    result = build_draft_markdown(parsed, "2026-01-01")
    assert "The real content." in result
