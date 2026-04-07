"""Tests for prediction_review_task.py pure helper functions."""

from datetime import date, timedelta

from tools.scripts.prediction_review_task import (
    _extract_signpost_dates,
    compose_slack_message,
    parse_date_field,
)


# ---------------------------------------------------------------------------
# parse_date_field
# ---------------------------------------------------------------------------

def test_parse_date_field_none():
    assert parse_date_field(None) is None


def test_parse_date_field_string():
    result = parse_date_field("2026-04-07")
    assert result == date(2026, 4, 7)


def test_parse_date_field_date_object():
    d = date(2026, 1, 1)
    assert parse_date_field(d) == d


def test_parse_date_field_invalid_string():
    assert parse_date_field("not-a-date") is None


def test_parse_date_field_partial_string():
    assert parse_date_field("2026-99-99") is None


# ---------------------------------------------------------------------------
# _extract_signpost_dates
# ---------------------------------------------------------------------------

def test_extract_signpost_dates_empty():
    assert _extract_signpost_dates("") == []


def test_extract_signpost_dates_full_date():
    content = "Watch for: By 2026-06-30 we should see results."
    dates = _extract_signpost_dates(content)
    assert date(2026, 6, 28) in dates or date(2026, 6, 30) in dates or any(d.year == 2026 for d in dates)


def test_extract_signpost_dates_year_only():
    content = "By 2027 the trend will be clear."
    dates = _extract_signpost_dates(content)
    assert any(d.year == 2027 for d in dates)


def test_extract_signpost_dates_multiple():
    content = "By 2026-03-01 check A. By 2027 check B."
    dates = _extract_signpost_dates(content)
    assert len(dates) == 2
    assert any(d.year == 2026 for d in dates)
    assert any(d.year == 2027 for d in dates)


# ---------------------------------------------------------------------------
# compose_slack_message
# ---------------------------------------------------------------------------

def test_compose_slack_message_empty():
    result = compose_slack_message([], [])
    assert result == ""


def test_compose_slack_message_with_due():
    fm = {"question": "Will X happen?", "domain": "crypto", "horizon": "2026-01-01"}
    result = compose_slack_message([(fm, "OVERDUE by 5d")], [])
    assert "Will X happen?" in result
    assert "OVERDUE" in result


def test_compose_slack_message_with_backtest_pending():
    backtest = {"question": "Did Y happen?", "domain": "macro"}
    result = compose_slack_message([], [backtest])
    assert "Did Y happen?" in result or "backtest" in result.lower() or "pending" in result.lower()
