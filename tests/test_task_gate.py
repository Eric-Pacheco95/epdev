"""Tests for task_gate pure functions."""

from tools.scripts.task_gate import (
    _has_verifiable_isc,
    _check_has_isc,
    _check_no_arch_keywords,
    _is_duplicate,
    GateResult,
)


# ── _has_verifiable_isc ──────────────────────────────────────────────

def test_has_verifiable_isc_yes():
    isc = ["Auth tokens expire | Verify: test -f tokens.json"]
    assert _has_verifiable_isc(isc) is True


def test_has_verifiable_isc_no_verify():
    isc = ["Auth tokens expire"]
    assert _has_verifiable_isc(isc) is False


def test_has_verifiable_isc_empty():
    assert _has_verifiable_isc([]) is False


def test_has_verifiable_isc_empty_verify():
    isc = ["Auth tokens expire | Verify:"]
    assert _has_verifiable_isc(isc) is False


def test_has_verifiable_isc_no_space():
    isc = ["Auth tokens expire |Verify: grep something"]
    assert _has_verifiable_isc(isc) is True


# ── _check_has_isc ───────────────────────────────────────────────────

def test_check_has_isc_pass():
    passed, msg = _check_has_isc(["X | Verify: test -f foo"])
    assert passed is True


def test_check_has_isc_fail_empty():
    passed, msg = _check_has_isc([])
    assert passed is False


def test_check_has_isc_fail_no_verify():
    passed, msg = _check_has_isc(["No verify method here"])
    assert passed is False


# ── _check_no_arch_keywords ──────────────────────────────────────────

def test_no_arch_keywords_clean():
    passed, msg = _check_no_arch_keywords("Run security audit", "Weekly check")
    assert passed is True


def test_arch_keywords_detected():
    passed, msg = _check_no_arch_keywords("Redesign the auth system", "")
    assert passed is False
    assert "redesign" in msg.lower()


def test_arch_keywords_migration():
    passed, msg = _check_no_arch_keywords("Schema migration needed", "")
    assert passed is False


def test_arch_keywords_rewrite():
    passed, msg = _check_no_arch_keywords("Rewrite the auth module", "")
    assert passed is False


# ── _is_duplicate ────────────────────────────────────────────────────

def test_is_duplicate_yes():
    tasks = [{"description": "Run audit", "status": "pending"}]
    assert _is_duplicate("Run audit", tasks) is True


def test_is_duplicate_case_insensitive():
    tasks = [{"description": "Run Audit", "status": "pending"}]
    assert _is_duplicate("run audit", tasks) is True


def test_is_duplicate_different_status():
    tasks = [{"description": "Run audit", "status": "done"}]
    assert _is_duplicate("Run audit", tasks) is False


def test_is_duplicate_no_match():
    tasks = [{"description": "Something else", "status": "pending"}]
    assert _is_duplicate("Run audit", tasks) is False


def test_is_duplicate_empty():
    assert _is_duplicate("Run audit", []) is False


# ── GateResult ───────────────────────────────────────────────────────

def test_gate_result_defaults():
    r = GateResult(route="backlog", reason="passed all checks")
    assert r.task_id is None
    assert r.check_results == {}
