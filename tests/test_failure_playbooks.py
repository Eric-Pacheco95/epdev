"""Pytest tests for tools/scripts/failure_playbooks.py — pattern matching and categories."""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so tools.scripts is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.failure_playbooks import match_playbook, list_categories, PLAYBOOKS


class TestMatchPlaybook:
    def test_claude_cli_not_found(self):
        result = match_playbook("FileNotFoundError: claude not found")
        assert result is not None
        assert result["category"] == "path_resolution"

    def test_slack_cap_reached(self):
        result = match_playbook("daily message cap reached")
        assert result is not None
        assert result["category"] == "slack_cap"

    def test_stale_worktree(self):
        result = match_playbook("fatal: /tmp/wt is already checked out")
        assert result is not None
        assert result["category"] == "stale_worktree"

    def test_timeout(self):
        result = match_playbook("TimeoutExpired: process took too long")
        assert result is not None
        assert result["category"] == "timeout"

    def test_import_error(self):
        result = match_playbook("ModuleNotFoundError: No module named 'foo'")
        assert result is not None
        assert result["category"] == "import_error"

    def test_quality_gate_fail(self):
        result = match_playbook("QUALITY_GATE: FAIL")
        assert result is not None
        assert result["category"] == "quality_gate_fail"

    def test_security_audit_fail(self):
        result = match_playbook("SECURITY_AUDIT: FAIL")
        assert result is not None
        assert result["category"] == "security_audit_fail"

    def test_network_error(self):
        result = match_playbook("ConnectionError: could not reach host")
        assert result is not None
        assert result["category"] == "network_error"

    def test_permission_error(self):
        result = match_playbook("PermissionError: [Errno 13] Access denied")
        assert result is not None
        assert result["category"] == "permission_error"

    def test_no_match(self):
        result = match_playbook("Everything is fine, no errors here")
        assert result is None

    def test_empty_string(self):
        result = match_playbook("")
        assert result is None

    def test_first_match_wins(self):
        """When multiple patterns could match, the first one in PLAYBOOKS wins."""
        result = match_playbook("ModuleNotFoundError and also TimeoutExpired")
        assert result is not None
        # timeout comes before import_error in the list? Check order:
        # import_error is index 4, timeout is index 3 — timeout wins
        assert result["category"] == "timeout"


class TestListCategories:
    def test_returns_list(self):
        cats = list_categories()
        assert isinstance(cats, list)

    def test_length_matches_playbooks(self):
        cats = list_categories()
        assert len(cats) == len(PLAYBOOKS)

    def test_known_categories_present(self):
        cats = list_categories()
        assert "path_resolution" in cats
        assert "timeout" in cats
        assert "network_error" in cats

    def test_all_playbooks_have_required_keys(self):
        for pb in PLAYBOOKS:
            assert "pattern" in pb
            assert "category" in pb
            assert "description" in pb
            assert "fix" in pb
