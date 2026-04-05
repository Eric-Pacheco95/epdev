"""Tests for security_scan.py -- apply_false_positive_filter."""

from tools.scripts.security_scan import apply_false_positive_filter


def test_no_findings():
    real, fps = apply_false_positive_filter([])
    assert real == []
    assert fps == []


def test_real_finding_not_filtered():
    findings = [{"check": "secret_pattern", "file": "tools/scripts/scan.py", "detail": "API key"}]
    real, fps = apply_false_positive_filter(findings)
    assert len(real) == 1
    assert fps == []


def test_test_fixture_is_false_positive():
    findings = [{"check": "secret_pattern", "file": "tests/fixtures/sample.py"}]
    real, fps = apply_false_positive_filter(findings)
    assert real == []
    assert len(fps) == 1
    assert fps[0]["fp_tag"] == "test_fixture"


def test_example_file_is_false_positive():
    findings = [{"check": "secret_pattern", "file": "docs/example_config.py"}]
    real, fps = apply_false_positive_filter(findings)
    assert fps[0]["fp_tag"] == "example_file"


def test_template_file_is_false_positive():
    findings = [{"check": "secret_pattern", "path": "templates/env.template"}]
    real, fps = apply_false_positive_filter(findings)
    assert fps[0]["fp_tag"] == "template_file"


def test_fabric_upstream_is_false_positive():
    findings = [{"check": "secret_pattern", "file": "tools/fabric-upstream/data/patterns/p.md"}]
    real, fps = apply_false_positive_filter(findings)
    assert fps[0]["fp_tag"] == "upstream_vendored"


def test_wrong_check_type_not_filtered():
    """path_contains match but wrong check type -- should be real."""
    findings = [{"check": "gitignore_missing", "file": "tests/something.py"}]
    real, fps = apply_false_positive_filter(findings)
    assert len(real) == 1
    assert fps == []


def test_mixed_findings():
    findings = [
        {"check": "secret_pattern", "file": "tests/conftest.py"},
        {"check": "secret_pattern", "file": "tools/scripts/main.py"},
    ]
    real, fps = apply_false_positive_filter(findings)
    assert len(real) == 1
    assert len(fps) == 1


def test_false_positive_flag_set():
    findings = [{"check": "secret_pattern", "file": "tests/test_scan.py"}]
    _, fps = apply_false_positive_filter(findings)
    assert fps[0]["false_positive"] is True
