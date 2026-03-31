"""Tests for isc_validator.py -- ISC quality gate checks.

Covers: extraction, 6-check quality gate, Unicode normalization, error handling.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

from isc_validator import (
    check_anti_criteria,
    check_binary_testable,
    check_conciseness,
    check_count,
    check_state_not_action,
    check_verify_methods,
    detect_phases,
    parse_isc_items,
    run_quality_gate,
    _normalize_unicode,
)


# -- Fixtures --

GOOD_PRD = """\
## ACCEPTANCE CRITERIA

### Phase 1: Foundation (3 criteria)

- [ ] System produces JSON output on stdout [E] | Verify: CLI test
- [ ] No secrets are exposed in output [E] | Verify: grep for patterns
- [ ] Exit code is 0 on success and 1 on failure [E] | Verify: test runner

### Phase 2: Integration (3 criteria)

- [ ] Script integrates with existing pipeline [E] | Verify: smoke test
- [ ] Output matches expected schema [E] | Verify: JSON schema check
- [ ] Neither script writes files unless flag is passed [E] [A] | Verify: code review
"""

BAD_PRD_COMPOUND = """\
## ACCEPTANCE CRITERIA

### Phase 1: Bad (3 criteria)

- [ ] System outputs JSON and also writes a log file and sends a notification [E] | Verify: test
- [ ] Config is loaded. System starts. | Verify: run it
- [ ] Output is valid [E] | Verify: check
"""

BAD_PRD_ACTION_VERBS = """\
## ACCEPTANCE CRITERIA

### Phase 1: Actions (4 criteria)

- [ ] Implement the parser for ISC extraction [E] | Verify: test
- [ ] Create a new module for validation [E] | Verify: test
- [ ] Build the CLI interface [E] | Verify: test
- [ ] No files are modified without explicit flag [E] | Verify: review
"""

BAD_PRD_NO_VERIFY = """\
## ACCEPTANCE CRITERIA

### Phase 1: Missing verify (3 criteria)

- [ ] System produces output [E]
- [ ] Output is valid JSON [E]
- [ ] No errors occur [E] | Verify: test
"""

BAD_PRD_NO_ANTI = """\
## ACCEPTANCE CRITERIA

### Phase 1: No anti (3 criteria)

- [ ] System produces JSON output [E] | Verify: test
- [ ] Output matches schema [E] | Verify: test
- [ ] Exit code is correct [E] | Verify: test
"""

UNICODE_PRD = """\
## ACCEPTANCE CRITERIA

### Phase 1: Unicode (3 criteria)

- [ ] System handles \u201csmart quotes\u201d correctly [E] | Verify: test
- [ ] Output uses em-dashes \u2014 not hyphens [E] | Verify: test
- [ ] No files are written outside stdout [E] | Verify: review
"""


# -- Tests: Extraction --

class TestExtraction:
    def test_extracts_correct_count(self):
        items = parse_isc_items(GOOD_PRD)
        assert len(items) == 6

    def test_extracts_criterion_text(self):
        items = parse_isc_items(GOOD_PRD)
        assert "System produces JSON output on stdout" in items[0]["criterion"]

    def test_extracts_verify_method(self):
        items = parse_isc_items(GOOD_PRD)
        assert items[0]["verify_method"] == "CLI test"

    def test_extracts_confidence_tag(self):
        items = parse_isc_items(GOOD_PRD)
        assert items[0]["confidence"] == "E"

    def test_extracts_verify_type_tag(self):
        items = parse_isc_items(GOOD_PRD)
        # Last item has [A] tag
        assert items[5]["verify_type"] == "A"

    def test_handles_checked_items(self):
        text = "- [x] Done item [E] | Verify: test\n- [ ] Open item [E] | Verify: test"
        items = parse_isc_items(text)
        assert items[0]["checked"] is True
        assert items[1]["checked"] is False

    def test_handles_star_bullets(self):
        text = "* [ ] Star bullet item [E] | Verify: test"
        items = parse_isc_items(text)
        assert len(items) == 1

    def test_empty_text_returns_empty(self):
        assert parse_isc_items("") == []

    def test_no_isc_items_returns_empty(self):
        assert parse_isc_items("# Just a heading\nSome text\n") == []


# -- Tests: Unicode Normalization --

class TestUnicode:
    def test_smart_quotes_normalized(self):
        items = parse_isc_items(UNICODE_PRD)
        assert len(items) == 3
        # Smart quotes should be replaced with ASCII
        assert '"smart quotes"' in items[0]["criterion"]

    def test_em_dash_normalized(self):
        items = parse_isc_items(UNICODE_PRD)
        assert "--" in items[1]["criterion"]

    def test_normalize_function(self):
        assert _normalize_unicode("\u201chello\u201d") == '"hello"'
        assert _normalize_unicode("a\u2014b") == "a--b"
        assert _normalize_unicode("it\u2019s") == "it's"


# -- Tests: Phase Detection --

class TestPhaseDetection:
    def test_detects_phases(self):
        items = parse_isc_items(GOOD_PRD)
        phases = detect_phases(GOOD_PRD, items)
        assert len(phases) == 2
        assert len(phases[0]["items"]) == 3
        assert len(phases[1]["items"]) == 3

    def test_no_phases_groups_all(self):
        text = "- [ ] Item one [E] | Verify: test\n- [ ] Item two [E] | Verify: test\n- [ ] Item three [E] | Verify: test"
        items = parse_isc_items(text)
        phases = detect_phases(text, items)
        assert len(phases) == 1
        assert phases[0]["name"] == "all"


# -- Tests: Check 1 - Count --

class TestCheckCount:
    def test_valid_count_passes(self):
        items = parse_isc_items(GOOD_PRD)
        phases = detect_phases(GOOD_PRD, items)
        results = check_count(phases)
        assert all(r["passed"] for r in results)

    def test_too_many_fails(self):
        # 14 items in one phase should fail
        lines = "\n".join(
            f"- [ ] Item {i} [E] | Verify: test" for i in range(14)
        )
        items = parse_isc_items(lines)
        phases = detect_phases(lines, items)
        results = check_count(phases)
        assert not results[0]["passed"]

    def test_too_few_fails(self):
        lines = "- [ ] Only one [E] | Verify: test"
        items = parse_isc_items(lines)
        phases = detect_phases(lines, items)
        results = check_count(phases)
        assert not results[0]["passed"]


# -- Tests: Check 2 - Conciseness --

class TestCheckConciseness:
    def test_clean_criteria_pass(self):
        items = parse_isc_items(GOOD_PRD)
        results = check_conciseness(items)
        assert all(r["passed"] for r in results)

    def test_compound_detected(self):
        items = parse_isc_items(BAD_PRD_COMPOUND)
        results = check_conciseness(items)
        # First item has "and ... and" pattern
        assert not results[0]["passed"]

    def test_two_sentences_detected(self):
        items = parse_isc_items(BAD_PRD_COMPOUND)
        results = check_conciseness(items)
        # Second item has "loaded. System" pattern
        assert not results[1]["passed"]


# -- Tests: Check 3 - State-not-Action --

class TestCheckStateNotAction:
    def test_state_criteria_pass(self):
        items = parse_isc_items(GOOD_PRD)
        results = check_state_not_action(items)
        assert all(r["passed"] for r in results)

    def test_action_verbs_warned(self):
        items = parse_isc_items(BAD_PRD_ACTION_VERBS)
        results = check_state_not_action(items)
        # First 3 start with action verbs
        assert not results[0]["passed"]  # "Implement"
        assert not results[1]["passed"]  # "Create"
        assert not results[2]["passed"]  # "Build"

    def test_action_check_is_warning(self):
        items = parse_isc_items(BAD_PRD_ACTION_VERBS)
        results = check_state_not_action(items)
        assert all(r["severity"] == "warning" for r in results)


# -- Tests: Check 4 - Binary Testable --

class TestCheckBinaryTestable:
    def test_with_verify_passes(self):
        items = parse_isc_items(GOOD_PRD)
        results = check_binary_testable(items)
        assert all(r["passed"] for r in results)

    def test_without_verify_fails(self):
        items = parse_isc_items(BAD_PRD_NO_VERIFY)
        results = check_binary_testable(items)
        assert not results[0]["passed"]
        assert not results[1]["passed"]


# -- Tests: Check 5 - Anti-criteria --

class TestCheckAntiCriteria:
    def test_has_anti_passes(self):
        items = parse_isc_items(GOOD_PRD)
        result = check_anti_criteria(items)
        assert result["passed"]
        assert result["anti_count"] >= 1

    def test_no_anti_fails(self):
        items = parse_isc_items(BAD_PRD_NO_ANTI)
        result = check_anti_criteria(items)
        assert not result["passed"]


# -- Tests: Check 6 - Verify Methods --

class TestCheckVerifyMethods:
    def test_all_have_verify(self):
        items = parse_isc_items(GOOD_PRD)
        results = check_verify_methods(items)
        assert all(r["passed"] for r in results)

    def test_missing_verify_fails(self):
        items = parse_isc_items(BAD_PRD_NO_VERIFY)
        results = check_verify_methods(items)
        assert not results[0]["passed"]
        assert not results[1]["passed"]
        assert results[2]["passed"]  # third has verify


# -- Tests: Full Quality Gate --

class TestQualityGate:
    def test_good_prd_passes(self, tmp_path):
        prd = tmp_path / "good.md"
        prd.write_text(GOOD_PRD, encoding="utf-8")
        result = run_quality_gate(prd)
        assert result["gate_passed"]
        assert result["extracted_count"] == 6

    def test_missing_file_fails(self, tmp_path):
        result = run_quality_gate(tmp_path / "nope.md")
        assert not result["gate_passed"]
        assert result["extracted_count"] == 0
        assert len(result["errors"]) > 0

    def test_empty_file_fails(self, tmp_path):
        prd = tmp_path / "empty.md"
        prd.write_text("", encoding="utf-8")
        result = run_quality_gate(prd)
        assert not result["gate_passed"]

    def test_no_isc_fails(self, tmp_path):
        prd = tmp_path / "no_isc.md"
        prd.write_text("# Just a title\nSome content\n", encoding="utf-8")
        result = run_quality_gate(prd)
        assert not result["gate_passed"]
        assert "No ISC criteria found" in result["errors"][0]

    def test_provenance_present(self, tmp_path):
        prd = tmp_path / "good.md"
        prd.write_text(GOOD_PRD, encoding="utf-8")
        result = run_quality_gate(prd)
        assert "_provenance" in result
        assert result["_provenance"]["script"] == "tools/scripts/isc_validator.py"

    def test_unicode_prd_passes(self, tmp_path):
        prd = tmp_path / "unicode.md"
        prd.write_text(UNICODE_PRD, encoding="utf-8")
        result = run_quality_gate(prd)
        assert result["extracted_count"] == 3
        assert result["gate_passed"]
