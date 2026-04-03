"""Tests for code_prescan pure functions."""

from tools.scripts.code_prescan import (
    _ruff_severity,
    _sanitize_ascii,
)


def test_ruff_severity_security():
    assert _ruff_severity("S101") == "high"
    assert _ruff_severity("S301") == "high"


def test_ruff_severity_error():
    assert _ruff_severity("E501") == "medium"
    assert _ruff_severity("F401") == "medium"


def test_ruff_severity_low():
    assert _ruff_severity("W291") == "low"
    assert _ruff_severity("I001") == "low"
    assert _ruff_severity("C901") == "low"


def test_sanitize_ascii_prescan():
    assert "->" in _sanitize_ascii("\u2192")
    assert "..." in _sanitize_ascii("\u2026")
    assert "*" in _sanitize_ascii("\u2022")
