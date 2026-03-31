"""Tests for query_events.status_badge -- all metric types and edges."""

from query_events import status_badge


def test_sessions_per_day_ok():
    assert status_badge("sessions_per_day", 2.0) == "OK"


def test_sessions_per_day_warn():
    assert status_badge("sessions_per_day", 0.3) == "WARN"


def test_sessions_per_day_boundary():
    assert status_badge("sessions_per_day", 0.5) == "OK"


def test_unknown_metric_ok():
    assert status_badge("unknown_metric", 999) == "OK"


def test_failure_rate_zero():
    assert status_badge("failure_rate", 0.0) == "OK"


def test_failure_rate_boundary_warn():
    assert status_badge("failure_rate", 0.05) == "WARN"


def test_failure_rate_boundary_crit():
    assert status_badge("failure_rate", 0.15) == "CRITICAL"
