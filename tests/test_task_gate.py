"""Tests for task_gate pure functions."""

import tools.scripts.task_gate as tg
from tools.scripts.task_gate import (
    _has_verifiable_isc,
    _check_has_isc,
    _check_no_arch_keywords,
    _check_skill_tier,
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


# ── _check_skill_tier ────────────────────────────────────────────────

def test_skill_tier_empty_skills_passes():
    passed, msg = _check_skill_tier([])
    assert passed is True
    assert "No skill constraint" in msg


def test_skill_tier_unknown_skill_fails(monkeypatch):
    monkeypatch.setattr(tg, "_load_autonomy_map", lambda: {})
    passed, msg = _check_skill_tier(["nonexistent-skill"])
    assert passed is False
    assert "not found" in msg


def test_skill_tier_too_high_fails(monkeypatch):
    monkeypatch.setattr(tg, "_load_autonomy_map", lambda: {
        "heavy-skill": {"tier": 3, "autonomous_safe": True}
    })
    passed, msg = _check_skill_tier(["heavy-skill"])
    assert passed is False
    assert "Tier 3" in msg


def test_skill_tier_not_autonomous_safe_fails(monkeypatch):
    monkeypatch.setattr(tg, "_load_autonomy_map", lambda: {
        "risky-skill": {"tier": 1, "autonomous_safe": False}
    })
    passed, msg = _check_skill_tier(["risky-skill"])
    assert passed is False
    assert "autonomous_safe" in msg


def test_skill_tier_valid_passes(monkeypatch):
    monkeypatch.setattr(tg, "_load_autonomy_map", lambda: {
        "safe-skill": {"tier": 1, "autonomous_safe": True}
    })
    passed, msg = _check_skill_tier(["safe-skill"])
    assert passed is True


def test_skill_tier_multiple_one_fails(monkeypatch):
    monkeypatch.setattr(tg, "_load_autonomy_map", lambda: {
        "good": {"tier": 0, "autonomous_safe": True},
        "bad":  {"tier": 4, "autonomous_safe": True},
    })
    passed, msg = _check_skill_tier(["good", "bad"])
    assert passed is False


# ── GateResult ───────────────────────────────────────────────────────

def test_gate_result_defaults():
    r = GateResult(route="backlog", reason="passed all checks")
    assert r.task_id is None
    assert r.check_results == {}
