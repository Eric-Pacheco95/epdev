"""Tests for isc_validator pure functions."""

from tools.scripts.isc_validator import (
    parse_isc_items,
    check_count,
    check_conciseness,
    check_state_not_action,
    check_binary_testable,
    check_anti_criteria,
    check_verify_methods,
    detect_phases,
    _sanitize_ascii,
    _normalize_unicode,
    ACTION_VERBS,
)


# ── parse_isc_items ──────────────────────────────────────────────────

def test_parse_isc_items_basic():
    text = "- [ ] Auth tokens expire after 24h [E] | Verify: CLI"
    items = parse_isc_items(text)
    assert len(items) == 1
    assert items[0]["checked"] is False
    assert items[0]["confidence"] == "E"
    assert items[0]["verify_method"] == "CLI"


def test_parse_isc_items_checked():
    text = "- [x] Deploy complete [I] [M] | Verify: Test"
    items = parse_isc_items(text)
    assert len(items) == 1
    assert items[0]["checked"] is True
    assert items[0]["confidence"] == "I"
    assert items[0]["verify_type"] == "M"


def test_parse_isc_items_no_verify():
    text = "- [ ] Something without verify"
    items = parse_isc_items(text)
    assert len(items) == 1
    assert items[0]["verify_method"] == ""


def test_parse_isc_items_multiple():
    text = (
        "- [ ] First criterion [E] | Verify: CLI\n"
        "- [x] Second criterion [I] | Verify: Test\n"
        "Some non-criterion line\n"
        "- [ ] Third criterion [R] | Verify: Grep\n"
    )
    items = parse_isc_items(text)
    assert len(items) == 3


def test_parse_isc_items_asterisk_bullet():
    text = "* [ ] Asterisk bullet [E] | Verify: Read"
    items = parse_isc_items(text)
    assert len(items) == 1


def test_parse_isc_items_empty():
    assert parse_isc_items("") == []
    assert parse_isc_items("no criteria here") == []


# ── check_count ──────────────────────────────────────────────────────

def test_check_count_valid():
    phases = [{"name": "p1", "items": [{}] * 5}]
    results = check_count(phases)
    assert results[0]["passed"] is True


def test_check_count_too_few():
    phases = [{"name": "p1", "items": [{}] * 2}]
    results = check_count(phases)
    assert results[0]["passed"] is False


def test_check_count_too_many():
    phases = [{"name": "p1", "items": [{}] * 9}]
    results = check_count(phases)
    assert results[0]["passed"] is False


# ── check_conciseness ───────────────────────────────────────────────

def test_check_conciseness_ok():
    items = [{"criterion": "Auth tokens expire after 24h [E]"}]
    results = check_conciseness(items)
    assert results[0]["passed"] is True


def test_check_conciseness_two_sentences():
    items = [{"criterion": "Auth tokens expire. Refresh tokens are revoked."}]
    results = check_conciseness(items)
    assert results[0]["passed"] is False


# ── check_state_not_action ───────────────────────────────────────────

def test_state_not_action_ok():
    items = [{"criterion": "Auth tokens expire after 24h"}]
    results = check_state_not_action(items)
    assert results[0]["passed"] is True


def test_state_not_action_fails():
    items = [{"criterion": "Implement token expiry logic"}]
    results = check_state_not_action(items)
    assert results[0]["passed"] is False
    assert "implement" in results[0]["message"]


# ── check_binary_testable ───────────────────────────────────────────

def test_binary_testable_ok():
    items = [{"criterion": "Tokens expire after 24h", "verify_method": "CLI"}]
    results = check_binary_testable(items)
    assert results[0]["passed"] is True


def test_binary_testable_no_verify():
    items = [{"criterion": "Tokens expire", "verify_method": ""}]
    results = check_binary_testable(items)
    assert results[0]["passed"] is False


def test_binary_testable_subjective():
    items = [{"criterion": "Output looks appropriate", "verify_method": "Review"}]
    results = check_binary_testable(items)
    assert results[0]["passed"] is False


# ── check_anti_criteria ──────────────────────────────────────────────

def test_anti_criteria_present():
    items = [
        {"criterion": "Auth tokens expire after 24h"},
        {"criterion": "No secrets are logged to stdout"},
    ]
    result = check_anti_criteria(items)
    assert result["passed"] is True
    assert result["anti_count"] == 1


def test_anti_criteria_missing():
    items = [{"criterion": "Auth tokens expire after 24h"}]
    result = check_anti_criteria(items)
    assert result["passed"] is False


# ── check_verify_methods ─────────────────────────────────────────────

def test_verify_methods_present():
    items = [{"criterion": "X", "verify_method": "CLI"}]
    results = check_verify_methods(items)
    assert results[0]["passed"] is True


def test_verify_methods_missing():
    items = [{"criterion": "X", "verify_method": ""}]
    results = check_verify_methods(items)
    assert results[0]["passed"] is False


# ── detect_phases ────────────────────────────────────────────────────

def test_detect_phases_no_headers():
    text = "- [ ] Criterion [E] | Verify: CLI"
    items = parse_isc_items(text)
    phases = detect_phases(text, items)
    assert len(phases) == 1
    assert phases[0]["name"] == "all"


def test_detect_phases_with_headers():
    text = (
        "## Phase 1: Setup\n"
        "- [ ] First [E] | Verify: CLI\n"
        "## Phase 2: Build\n"
        "- [ ] Second [E] | Verify: Test\n"
    )
    items = parse_isc_items(text)
    phases = detect_phases(text, items)
    assert len(phases) == 2


# ── helper functions ─────────────────────────────────────────────────

def test_sanitize_ascii():
    assert "->" in _sanitize_ascii("\u2192")
    assert "--" in _sanitize_ascii("\u2014")


def test_normalize_unicode_smart_quotes():
    assert "'" in _normalize_unicode("\u2018")
    assert '"' in _normalize_unicode("\u201c")
