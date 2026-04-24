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
    parse_frontmatter,
    _redact_secrets,
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


# \u2500\u2500 parse_frontmatter \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def test_parse_frontmatter_no_leading_dashes():
    assert parse_frontmatter("title: test\ncontent") is None


def test_parse_frontmatter_valid():
    text = "---\ntitle: my doc\nauthor: eric\n---\nbody text"
    result = parse_frontmatter(text)
    assert result == {"title": "my doc", "author": "eric"}


def test_parse_frontmatter_lowercases_keys_and_values():
    text = "---\nTITLE: My Doc\n---"
    result = parse_frontmatter(text)
    assert result["title"] == "my doc"


def test_parse_frontmatter_strips_quotes():
    text = '---\ntitle: "quoted value"\n---'
    result = parse_frontmatter(text)
    assert result["title"] == "quoted value"


def test_parse_frontmatter_missing_closing_dashes():
    text = "---\ntitle: test\n"
    assert parse_frontmatter(text) is None


def test_parse_frontmatter_empty_block():
    text = "---\n---\ncontent"
    result = parse_frontmatter(text)
    assert result == {}


def test_parse_frontmatter_ignores_comments():
    text = "---\n# this is a comment\ntitle: x\n---"
    result = parse_frontmatter(text)
    assert "title" in result
    assert "#" not in str(result)


def test_parse_frontmatter_ignores_blank_lines():
    text = "---\n\ntitle: x\n\n---"
    result = parse_frontmatter(text)
    assert result == {"title": "x"}


# \u2500\u2500 _redact_secrets \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def test_redact_secrets_clean_line_unchanged():
    assert _redact_secrets("All tests passed") == "All tests passed"


def test_redact_secrets_env_var_pattern():
    result = _redact_secrets("API_KEY=abc123xyz")
    assert "REDACTED" in result
    assert "abc123" not in result


def test_redact_secrets_secret_path():
    result = _redact_secrets("config loaded from /home/user/.ssh/id_rsa")
    assert "REDACTED" in result


def test_redact_secrets_multiline_preserves_clean():
    text = "line one ok\nAPI_TOKEN=secret999\nline three ok"
    result = _redact_secrets(text)
    lines = result.splitlines()
    assert lines[0] == "line one ok"
    assert "REDACTED" in lines[1]
    assert lines[2] == "line three ok"


def test_redact_secrets_empty_string():
    assert _redact_secrets("") == ""
