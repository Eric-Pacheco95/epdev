"""Tests for content_pipeline/collect_sources.py -- pure helper functions."""

from datetime import datetime, timedelta, timezone

from tools.scripts.content_pipeline.collect_sources import (
    parse_frontmatter_date,
    parse_rating,
    safety_check,
    within_days,
)


# --- parse_frontmatter_date ---

def test_parse_date_basic():
    content = "date: 2026-04-01\nSome content."
    result = parse_frontmatter_date(content)
    assert result == datetime(2026, 4, 1, tzinfo=timezone.utc)


def test_parse_date_with_dashes():
    content = "--- date: 2026-03-15\nContent."
    result = parse_frontmatter_date(content)
    assert result == datetime(2026, 3, 15, tzinfo=timezone.utc)


def test_parse_date_uppercase():
    content = "Date: 2026-01-01\n"
    result = parse_frontmatter_date(content)
    assert result == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_parse_date_not_found():
    result = parse_frontmatter_date("No date in here.")
    assert result is None


def test_parse_date_invalid():
    result = parse_frontmatter_date("date: 9999-99-99")
    assert result is None


# --- parse_rating ---

def test_parse_rating_basic():
    assert parse_rating("Rating: 7") == 7


def test_parse_rating_signal_prefix():
    assert parse_rating("Signal rating: 9") == 9


def test_parse_rating_lowercase():
    assert parse_rating("rating: 5") == 5


def test_parse_rating_not_found():
    assert parse_rating("No rating here.") is None


def test_parse_rating_zero():
    assert parse_rating("Rating: 0") == 0


# --- safety_check ---

def test_safety_check_clean():
    passes, reason = safety_check("Normal session signal content here.", "signal.md")
    assert passes is True
    assert reason is None


def test_safety_check_blocks_confidential():
    passes, reason = safety_check("This is confidential information.", "signal.md")
    assert passes is False
    assert reason is not None


def test_safety_check_blocks_employer_phrase():
    passes, reason = safety_check("At my employer we do things differently.", "signal.md")
    assert passes is False
    assert reason is not None


# --- within_days ---

def test_within_days_recent():
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=3)
    assert within_days(recent, 7, now) is True


def test_within_days_old():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=30)
    assert within_days(old, 7, now) is False


def test_within_days_none_uses_fallback_recent():
    now = datetime.now(timezone.utc)
    recent_fallback = now - timedelta(days=2)
    assert within_days(None, 7, recent_fallback) is True


def test_within_days_none_uses_fallback_old():
    now = datetime.now(timezone.utc)
    old_fallback = now - timedelta(days=30)
    assert within_days(None, 7, old_fallback) is False
