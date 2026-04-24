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


def test_format_table_tool_unavailable():
    report = _make_report("pass", 0)
    report["tools"] = [{
        "tool": "ruff", "status": "tool_unavailable",
        "message": "ruff not found in PATH",
    }]
    result = format_table(report)
    assert "TOOL_UNAVAILABLE" in result
    assert "ruff not found in PATH" in result


def test_format_table_tool_timeout():
    report = _make_report("fail", 0)
    report["tools"] = [{
        "tool": "ruff", "status": "timeout",
        "message": "ruff exceeded 60s timeout",
    }]
    result = format_table(report)
    assert "TIMEOUT" in result
    assert "exceeded 60s timeout" in result


def test_format_table_tool_error():
    report = _make_report("fail", 0)
    report["tools"] = [{
        "tool": "security_scan", "status": "error",
        "message": "unexpected crash",
    }]
    result = format_table(report)
    assert "ERROR" in result
    assert "unexpected crash" in result


def test_format_table_findings_shown():
    finding = {"file": "tools/scripts/foo.py", "line": 42, "code": "S101", "message": "assert used"}
    report = _make_report("fail", 1)
    report["tools"] = [{"tool": "ruff", "status": "fail", "finding_count": 1, "findings": [finding]}]
    result = format_table(report)
    assert "tools/scripts/foo.py" in result
    assert "S101" in result


def test_format_table_more_than_five_findings():
    findings = [{"file": f"f{i}.py", "line": i, "code": "W", "message": "x"} for i in range(8)]
    report = _make_report("fail", 8)
    report["tools"] = [{"tool": "ruff", "status": "fail", "finding_count": 8, "findings": findings}]
    result = format_table(report)
    assert "3 more" in result


def test_format_table_no_version_no_v_prefix():
    report = _make_report("pass", 0)
    report["tools"] = [{"tool": "ruff", "status": "pass", "finding_count": 0, "findings": []}]
    result = format_table(report)
    assert " v" not in result


# --- _sanitize_ascii coverage for remaining Unicode chars ---

def test_sanitize_em_dash():
    assert _sanitize_ascii("—") == "--"


def test_sanitize_en_dash():
    assert _sanitize_ascii("–") == "-"


def test_sanitize_left_single_quote():
    assert _sanitize_ascii("‘") == "'"


def test_sanitize_right_single_quote():
    assert _sanitize_ascii("’") == "'"


def test_sanitize_left_double_quote():
    assert _sanitize_ascii("“") == '"'


def test_sanitize_right_double_quote():
    assert _sanitize_ascii("”") == '"'


def test_sanitize_multiplication_sign():
    assert _sanitize_ascii("×") == "x"


def test_sanitize_plain_ascii_unchanged():
    assert _sanitize_ascii("hello world 123") == "hello world 123"


def test_sanitize_empty_string():
    assert _sanitize_ascii("") == ""


# --- _ruff_severity edge cases ---

def test_ruff_severity_empty_code():
    assert _ruff_severity("") == "low"


def test_ruff_severity_unknown_prefix():
    assert _ruff_severity("T001") == "low"
