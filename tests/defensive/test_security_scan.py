#!/usr/bin/env python3
"""Defensive tests for security_scan.py -- secret patterns, clean pass-through, gitignore gaps.

Tests the deterministic scanner's functions directly, not the CLI wrapper.
Run with: python -m pytest tests/defensive/test_security_scan.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security.validators.secret_scanner import line_has_secret, scan_text
from tools.scripts.security_scan import (
    REQUIRED_FILES,
    REQUIRED_GITIGNORE_PATTERNS,
    FALSE_POSITIVE_RULES,
    PERSONAL_CONTENT_GLOBS,
    apply_false_positive_filter,
    scan_gitignore_completeness,
    scan_required_files,
    scan_settings_permissions,
)


# --- Secret pattern detection ---

class TestSecretPatterns:
    """Known secret patterns must be detected."""

    @pytest.mark.parametrize("line,expected_pattern", [
        ("key = sk-123456789012345678901234567890", "sk-"),
        ("export AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF", "AKIA"),
        ("token ghp_fakefakefakefakefakefakefake1234567890", "ghp_"),
        ("slack xoxb-123-456-abcdef0123456789", "xoxb-"),
        ("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN"),
        ("-----BEGIN EC PRIVATE KEY-----", "-----BEGIN"),
        ("-----BEGIN PRIVATE KEY-----", "-----BEGIN"),
    ])
    def test_known_patterns_detected(self, line: str, expected_pattern: str):
        found, name = line_has_secret(line)
        assert found, f"Pattern '{expected_pattern}' not detected in: {line}"
        assert name == expected_pattern

    @pytest.mark.parametrize("line", [
        "hello world no secrets here",
        "just a normal config line",
        "DEBUG=true",
        "PORT=8080",
        "# This is a comment",
        "def function_name():",
        "import os",
    ])
    def test_clean_lines_pass_through(self, line: str):
        found, name = line_has_secret(line)
        assert not found, f"False positive: pattern '{name}' on clean line: {line}"

    def test_multiline_scan(self):
        text = (
            "line one is clean\n"
            "line two has AKIA1234567890ABCDEF\n"
            "line three is clean\n"
            "line four has ghp_fakefakefakefakefakefakefake1234567890\n"
        )
        hits = scan_text(text)
        assert len(hits) == 2
        assert hits[0][0] == 2  # line number
        assert hits[0][1] == "AKIA"
        assert hits[1][0] == 4
        assert hits[1][1] == "ghp_"


# --- Gitignore completeness ---

class TestGitignoreCompleteness:
    """Required patterns must be covered by .gitignore."""

    def test_required_patterns_list_nonempty(self):
        assert len(REQUIRED_GITIGNORE_PATTERNS) >= 5

    def test_actual_gitignore_covers_required(self):
        """Run against the real .gitignore in the repo."""
        findings = scan_gitignore_completeness()
        gaps = [f for f in findings if f["check"] == "gitignore_gap"]
        if gaps:
            missing = [f["pattern"] for f in gaps]
            pytest.fail(f"Gitignore gaps found: {missing}")

    def test_env_file_covered(self):
        """The .env pattern must be in gitignore."""
        findings = scan_gitignore_completeness()
        env_gaps = [f for f in findings if f.get("pattern") == ".env"]
        assert len(env_gaps) == 0, ".env not covered by .gitignore"


# --- Required security files ---

class TestRequiredFiles:
    """Required security infrastructure files must exist."""

    def test_required_files_list_nonempty(self):
        assert len(REQUIRED_FILES) >= 3

    def test_all_required_files_exist(self):
        findings = scan_required_files()
        if findings:
            missing = [f["file"] for f in findings]
            pytest.fail(f"Required security files missing: {missing}")


# --- Settings permissions ---

class TestSettingsPermissions:
    """Settings should not have dangerous MCP wildcards."""

    def test_no_mutation_wildcards(self):
        findings = scan_settings_permissions()
        wildcards = [f for f in findings if f["check"] == "permissive_mcp_wildcard"]
        assert len(wildcards) == 0, f"Dangerous MCP wildcards: {[f['setting'] for f in wildcards]}"


# --- CLI output contract ---

class TestCLIOutput:
    """The CLI must produce valid JSON with required fields."""

    def test_cli_produces_valid_json(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "scripts" / "security_scan.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(ROOT),
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["_schema_version"] == "1.0.0"
        assert "_provenance" in data
        assert "findings" in data
        assert "summary" in data
        assert "errors" in data
        assert isinstance(data["findings"], list)
        assert isinstance(data["errors"], list)

    def test_no_secret_values_in_output(self):
        """Findings must never contain actual secret values."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "scripts" / "security_scan.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(ROOT),
        )
        output = result.stdout
        # None of these should appear in the output
        for _, pattern in [("sk-", "sk-[a-zA-Z0-9]{20,}"),
                           ("AKIA", "AKIA[0-9A-Z]{16}")]:
            import re
            # Allow the pattern name field (e.g. "pattern": "sk-") but not actual values
            lines = output.splitlines()
            for line in lines:
                found, name = line_has_secret(line)
                if found:
                    # Only OK if it's in a "pattern" field value
                    if '"pattern"' not in line:
                        pytest.fail(f"Secret value leaked in output: pattern={name}")


class TestApplyFalsePositiveFilter:
    def _finding(self, check="secret_pattern", file="src/main.py", **kwargs):
        f = {"check": check, "file": file}
        f.update(kwargs)
        return f

    def test_clean_finding_stays_real(self):
        finding = self._finding(file="src/app.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(real) == 1
        assert len(fps) == 0

    def test_test_fixture_tagged_as_fp(self):
        finding = self._finding(file="tests/fixtures/creds.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(fps) == 1
        assert fps[0]["fp_tag"] == "test_fixture"
        assert fps[0].get("false_positive") is True

    def test_example_file_tagged_as_fp(self):
        finding = self._finding(file="docs/example_config.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(fps) == 1
        assert fps[0]["fp_tag"] == "example_file"

    def test_template_file_tagged_as_fp(self):
        finding = self._finding(file="tools/template_hook.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(fps) == 1
        assert fps[0]["fp_tag"] == "template_file"

    def test_upstream_vendored_tagged_as_fp(self):
        finding = self._finding(file="fabric-upstream/patterns/extract.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(fps) == 1
        assert fps[0]["fp_tag"] == "upstream_vendored"

    def test_wrong_check_type_not_filtered(self):
        finding = self._finding(check="tracked_personal", file="tests/something.py")
        real, fps = apply_false_positive_filter([finding])
        assert len(real) == 1
        assert len(fps) == 0

    def test_empty_input(self):
        real, fps = apply_false_positive_filter([])
        assert real == [] and fps == []

    def test_mixed_findings(self):
        findings = [
            self._finding(file="src/main.py"),
            self._finding(file="tests/test_foo.py"),
            self._finding(file="fabric-upstream/x.py"),
        ]
        real, fps = apply_false_positive_filter(findings)
        assert len(real) == 1
        assert len(fps) == 2

    def test_path_field_fallback(self):
        finding = {"check": "secret_pattern", "path": "tests/helpers.py"}
        real, fps = apply_false_positive_filter([finding])
        assert len(fps) == 1
        assert fps[0]["fp_tag"] == "test_fixture"

    def test_false_positive_rules_nonempty(self):
        assert len(FALSE_POSITIVE_RULES) > 0

    def test_personal_content_globs_nonempty(self):
        assert len(PERSONAL_CONTENT_GLOBS) > 0

    def test_required_gitignore_covers_env_and_pem(self):
        assert ".env" in REQUIRED_GITIGNORE_PATTERNS
        assert "*.pem" in REQUIRED_GITIGNORE_PATTERNS

    def test_constitutional_rules_in_required_files(self):
        assert any("constitutional" in f for f in REQUIRED_FILES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
