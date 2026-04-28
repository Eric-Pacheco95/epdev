"""Tests for morning_feed.py -- pure helper functions."""

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import tools.scripts.morning_feed as mf_mod
from tools.scripts.morning_feed import (
    _clean_html, _text, parse_discovered_sources,
    log_source_candidate, _count_pending_backtests, track_proposals,
)


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


# --- _text ---

def test_text_extracts_element():
    root = ET.fromstring("<item><title>Hello</title></item>")
    assert _text(root, "title") == "Hello"


def test_text_missing_element_returns_empty():
    root = ET.fromstring("<item><title>Hello</title></item>")
    assert _text(root, "description") == ""


def test_text_empty_element_returns_empty():
    root = ET.fromstring("<item><title></title></item>")
    assert _text(root, "title") == ""


def test_text_strips_whitespace():
    root = ET.fromstring("<item><title>  padded  </title></item>")
    assert _text(root, "title") == "padded"


# --- log_source_candidate ---

def test_log_source_candidate_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mf_mod, "CANDIDATES_FILE", tmp_path / "candidates.jsonl")
    log_source_candidate({"name": "Feed A", "url": "https://a.com", "type": "crypto"})
    assert (tmp_path / "candidates.jsonl").exists()


def test_log_source_candidate_deduplicates(tmp_path, monkeypatch):
    f = tmp_path / "candidates.jsonl"
    monkeypatch.setattr(mf_mod, "CANDIDATES_FILE", f)
    log_source_candidate({"name": "Feed A", "url": "https://a.com"})
    log_source_candidate({"name": "Feed A", "url": "https://a.com"})
    lines = [l for l in f.read_text().splitlines() if l.strip()]
    assert len(lines) == 1


def test_log_source_candidate_adds_new_url(tmp_path, monkeypatch):
    f = tmp_path / "candidates.jsonl"
    monkeypatch.setattr(mf_mod, "CANDIDATES_FILE", f)
    log_source_candidate({"name": "Feed A", "url": "https://a.com"})
    log_source_candidate({"name": "Feed B", "url": "https://b.com"})
    lines = [l for l in f.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


# --- _count_pending_backtests ---

def test_count_pending_backtests_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(mf_mod, "BACKTEST_DIR", tmp_path / "no_dir")
    assert _count_pending_backtests() == 0


def test_count_pending_backtests_counts_status(tmp_path, monkeypatch):
    monkeypatch.setattr(mf_mod, "BACKTEST_DIR", tmp_path)
    (tmp_path / "a.md").write_text("status: pending_review\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("status: resolved\n", encoding="utf-8")
    assert _count_pending_backtests() == 1


# --- track_proposals ---

def test_track_proposals_writes_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(mf_mod, "VALUE_FILE", tmp_path / "value.jsonl")
    track_proposals("2026-04-27", "1. Do A\n2. Do B\n3. Do C\n")
    lines = (tmp_path / "value.jsonl").read_text().splitlines()
    assert len(lines) == 3


def test_track_proposals_empty_content(tmp_path, monkeypatch):
    monkeypatch.setattr(mf_mod, "VALUE_FILE", tmp_path / "value.jsonl")
    track_proposals("2026-04-27", "No proposals here.")
    assert not (tmp_path / "value.jsonl").exists()
