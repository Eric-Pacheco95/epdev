"""Tests for morning_feed.py -- pure helper functions."""

from tools.scripts.morning_feed import _clean_html, parse_discovered_sources


# --- _clean_html ---

def test_clean_html_strips_tags():
    assert _clean_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_clean_html_no_tags():
    assert _clean_html("Plain text") == "Plain text"


def test_clean_html_empty():
    assert _clean_html("") == ""


def test_clean_html_strips_whitespace():
    assert _clean_html("  <br/>  hello  ") == "hello"


def test_clean_html_self_closing_tags():
    assert _clean_html("line1<br/>line2") == "line1line2"


# --- parse_discovered_sources ---

def test_parse_no_marker():
    assert parse_discovered_sources("No discovery section here.") == []


def test_parse_empty_discovery_block():
    text = "DISCOVERED_SOURCES:\n(none found)\n"
    assert parse_discovered_sources(text) == []


def test_parse_single_source():
    text = (
        "DISCOVERED_SOURCES:\n"
        '- name: "Test Feed" | url: "https://example.com/rss" | type: ai_engineering | reason: "good"\n'
    )
    result = parse_discovered_sources(text)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/rss"
    assert result[0]["name"] == "Test Feed"
    assert result[0]["type"] == "ai_engineering"


def test_parse_multiple_sources():
    text = (
        "DISCOVERED_SOURCES:\n"
        '- name: "Feed A" | url: "https://a.com" | type: crypto | reason: "r1"\n'
        '- name: "Feed B" | url: "https://b.com" | type: fintech | reason: "r2"\n'
    )
    result = parse_discovered_sources(text)
    assert len(result) == 2
    assert result[0]["url"] == "https://a.com"
    assert result[1]["url"] == "https://b.com"


def test_parse_stops_at_non_dash_line():
    text = (
        "DISCOVERED_SOURCES:\n"
        '- name: "Feed A" | url: "https://a.com" | type: crypto | reason: "r"\n'
        "Some other content\n"
        '- name: "Feed B" | url: "https://b.com" | type: fintech | reason: "r2"\n'
    )
    result = parse_discovered_sources(text)
    assert len(result) == 1  # stops at "Some other content"


def test_parse_skips_entry_without_url():
    text = (
        "DISCOVERED_SOURCES:\n"
        '- name: "No URL" | type: crypto | reason: "r"\n'
    )
    result = parse_discovered_sources(text)
    assert result == []
