#!/usr/bin/env python3
"""Jarvis Failure Playbook Registry -- L2 graduated self-heal skeleton.

Defines known failure patterns and their pre-approved remediation actions.
Used by self_diagnose_wrapper.py for classification (L1) and, once graduated,
for auto-execution (L2).

Graduation criteria for auto_eligible:
  - 10+ accurate L1 diagnoses matching this playbook
  - >90% classification accuracy confirmed by human review
  - Eric explicitly flips auto_eligible to True

This file is a data structure only -- no execution logic.
The L2 executor will be a separate module built after graduation.
"""

from __future__ import annotations

PLAYBOOKS: list[dict] = [
    {
        "pattern": r"claude CLI not found|FileNotFoundError.*claude",
        "category": "path_resolution",
        "description": "Claude CLI binary not found in PATH or at hardcoded location",
        "fix": "Use absolute path to claude.exe; check install location",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"daily .* cap reached|cap reached \(\d+\)",
        "category": "slack_cap",
        "description": "Slack daily message cap exhausted before this runner posted",
        "fix": "Skip Slack post, continue runner execution",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"Worktree .* already exists|fatal: .* is already checked out",
        "category": "stale_worktree",
        "description": "Git worktree from previous run not cleaned up",
        "fix": "git worktree remove --force + git worktree prune",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"TimeoutExpired|timed out after \d+s|Command timed out",
        "category": "timeout",
        "description": "Subprocess or API call exceeded timeout limit",
        "fix": "Retry once with 2x timeout; if persistent, investigate root cause",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"ModuleNotFoundError|ImportError",
        "category": "import_error",
        "description": "Python module not found -- missing dependency or wrong Python path",
        "fix": "Check Python path, verify module exists, check for typos in import",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"QUALITY_GATE:\s*FAIL",
        "category": "quality_gate_fail",
        "description": "Overnight quality gate detected issues in generated code",
        "fix": "Review quality gate output; revert suspect commits on overnight branch",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"SECURITY_AUDIT:\s*FAIL",
        "category": "security_audit_fail",
        "description": "Overnight security audit detected violations",
        "fix": "Review security audit output; revert commits that touch protected paths",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"ConnectionError|URLError|NetworkError|ECONNREFUSED",
        "category": "network_error",
        "description": "Network request failed -- API down, DNS issue, or firewall block",
        "fix": "Retry after delay; check network connectivity; verify API status",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
    {
        "pattern": r"PermissionError|Access is denied|EACCES",
        "category": "permission_error",
        "description": "File or resource permission denied",
        "fix": "Check file permissions and ownership; verify Task Scheduler user context",
        "reversible": True,
        "auto_eligible": False,
        "l1_matches": 0,
        "l1_correct": 0,
    },
]


def match_playbook(output: str) -> dict | None:
    """Find the first playbook matching the output. Returns playbook dict or None."""
    import re
    for pb in PLAYBOOKS:
        if re.search(pb["pattern"], output):
            return pb
    return None


def list_categories() -> list[str]:
    """Return all playbook category names."""
    return [pb["category"] for pb in PLAYBOOKS]
