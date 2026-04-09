"""Tests for finance_recap.py pure helpers."""

from tools.scripts.finance_recap import calc_hold_days, format_recap


# ---------------------------------------------------------------------------
# calc_hold_days
# ---------------------------------------------------------------------------

def test_calc_hold_days_invalid_date():
    assert calc_hold_days("not-a-date") == 0


def test_calc_hold_days_none():
    assert calc_hold_days(None) == 0


def test_calc_hold_days_future_date():
    # A date far in the future should return a negative or zero value
    result = calc_hold_days("2099-01-01")
    assert result < 0


def test_calc_hold_days_old_date():
    result = calc_hold_days("2020-01-01")
    assert result > 365 * 5  # at least 5 years ago


def test_calc_hold_days_today():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    result = calc_hold_days(today)
    assert result == 0


# ---------------------------------------------------------------------------
# format_recap
# ---------------------------------------------------------------------------

def test_format_recap_no_positions():
    result = format_recap([], [], [], token_age_hours=1.0)
    assert "Finance Recap" in result
    assert "No open positions" in result


def test_format_recap_token_age_warning():
    result = format_recap([], [], [], token_age_hours=60.0)
    assert "token last refreshed" in result.lower() or "60h ago" in result


def test_format_recap_no_token_warning_when_fresh():
    result = format_recap([], [], [], token_age_hours=10.0)
    assert "token last refreshed" not in result.lower()


def test_format_recap_questrade_position():
    pos = {
        "ticker": "UCO",
        "shares": 100,
        "entry_price": 25.0,
        "current_price": 27.5,
        "open_pnl": 250.0,
        "open_pnl_pct": 10.0,
        "leveraged": False,
    }
    result = format_recap([pos], [], [], token_age_hours=1.0)
    assert "UCO" in result
    assert "+$250.00" in result


def test_format_recap_summary_line():
    qt_pos = [{
        "ticker": "NRGU", "shares": 10, "entry_price": 50.0,
        "current_price": 55.0, "open_pnl": 50.0, "open_pnl_pct": 10.0,
        "leveraged": True,
    }]
    result = format_recap(qt_pos, [], [], token_age_hours=1.0)
    assert "1 Questrade" in result
    assert "1 leveraged" in result
