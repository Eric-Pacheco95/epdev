"""Tests for security_scan.py -- apply_false_positive_filter and scan_settings_permissions."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.security_scan import apply_false_positive_filter, scan_settings_permissions


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


# --- scan_settings_permissions ---

def test_scan_settings_no_file(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    assert scan_settings_permissions() == []


def test_scan_settings_no_allow_list(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {}}), encoding="utf-8"
    )
    assert scan_settings_permissions() == []


def test_scan_settings_clean_allow_list(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    settings = {"permissions": {"allow": ["Read", "Write", "Bash"]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    assert scan_settings_permissions() == []


def test_scan_settings_slack_wildcard_flagged(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    settings = {"permissions": {"allow": ["mcp__claude_ai_Slack__*", "Read"]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    findings = scan_settings_permissions()
    assert any(f["check"] == "permissive_mcp_wildcard" for f in findings)
    assert any("Slack" in f.get("detail", "") for f in findings)


def test_scan_settings_notion_wildcard_flagged(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    settings = {"permissions": {"allow": ["mcp__claude_ai_Notion__*"]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    findings = scan_settings_permissions()
    assert len(findings) >= 1


def test_scan_settings_invalid_json_returns_empty(tmp_path, monkeypatch):
    import tools.scripts.security_scan as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("not_json", encoding="utf-8")
    assert scan_settings_permissions() == []
