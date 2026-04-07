"""Tests for code_prescan pure functions."""

from tools.scripts.code_prescan import (
    _ruff_severity,
    _sanitize_ascii,
    format_table,
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


def _make_report(status="pass", findings=0):
    return {
        "_provenance": {"scan_path": "tools/scripts/"},
        "overall_status": status,
        "total_findings": findings,
        "tools": [],
    }


def test_format_table_pass_status():
    result = format_table(_make_report("pass", 0))
    assert "PASS" in result
    assert "0 findings" in result


def test_format_table_fail_status():
    result = format_table(_make_report("fail", 3))
    assert "FAIL" in result
    assert "3 findings" in result


def test_format_table_contains_scan_path():
    result = format_table(_make_report())
    assert "tools/scripts/" in result


def test_format_table_tool_entry():
    report = _make_report("pass", 0)
    report["tools"] = [{"tool": "ruff", "status": "pass", "version": "0.3.0", "finding_count": 0, "findings": []}]
    result = format_table(report)
    assert "ruff" in result
    assert "v0.3.0" in result
