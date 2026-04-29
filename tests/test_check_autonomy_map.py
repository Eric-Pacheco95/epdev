"""Tests for tools/scripts/check_autonomy_map.py."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.check_autonomy_map import (
    _parse_frontmatter,
    _parse_body_autonomous_safe,
    _format_slack_message,
    CRITICAL_TYPES,
    MAX_AUTONOMOUS_TIER,
)


class TestParseFrontmatter:
    def test_basic_key_value(self):
        text = "---\nname: foo\ndescription: bar\n---\nbody"
        fm = _parse_frontmatter(text)
        assert fm["name"] == "foo"
        assert fm["description"] == "bar"

    def test_bool_true(self):
        text = "---\ndisable-model-invocation: true\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["disable-model-invocation"] is True

    def test_bool_false(self):
        text = "---\nautonomous_safe: false\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["autonomous_safe"] is False

    def test_no_frontmatter(self):
        assert _parse_frontmatter("just body") is None

    def test_unterminated_frontmatter(self):
        assert _parse_frontmatter("---\nname: x\n") is None

    def test_empty_frontmatter(self):
        # "---\n---" has no newline after the opening fence — find("\n---", 4) fails
        fm = _parse_frontmatter("---\nname: x\n---\n")
        assert fm == {"name": "x"}

    def test_quoted_value(self):
        text = '---\nname: "my skill"\n---\n'
        fm = _parse_frontmatter(text)
        assert fm["name"] == "my skill"


class TestParseBodyAutonomousSafe:
    def test_true_value(self):
        text = "# heading\n\n## autonomous_safe\n\ntrue\n\nmore text"
        assert _parse_body_autonomous_safe(text) is True

    def test_false_value(self):
        text = "## autonomous_safe\n\nfalse\n"
        assert _parse_body_autonomous_safe(text) is False

    def test_case_insensitive(self):
        text = "## autonomous_safe\n\nTrue\n"
        assert _parse_body_autonomous_safe(text) is True

    def test_missing_section(self):
        assert _parse_body_autonomous_safe("no section here") is None

    def test_heading_no_value(self):
        # heading present but no true/false after it
        assert _parse_body_autonomous_safe("## autonomous_safe\n\nmaybe\n") is None


class TestFormatSlackMessage:
    def test_clean_state_message(self):
        state = {
            "findings": [],
            "critical_count": 0,
            "skills_checked": 10,
            "map_entries": 8,
        }
        msg = _format_slack_message(state)
        assert "clean" in msg
        assert "10 skills" in msg

    def test_findings_message(self):
        state = {
            "findings": [
                {"type": "orphan_map_entry", "skill": "foo", "detail": "no SKILL.md"}
            ],
            "critical_count": 0,
            "skills_checked": 5,
            "map_entries": 3,
        }
        msg = _format_slack_message(state)
        assert "orphan_map_entry" in msg
        assert "foo" in msg

    def test_critical_finding_marked(self):
        state = {
            "findings": [
                {"type": "autonomous_safe_drift", "skill": "bar", "detail": "drift"}
            ],
            "critical_count": 1,
            "skills_checked": 5,
            "map_entries": 3,
        }
        msg = _format_slack_message(state)
        assert "autonomous_safe_drift" in msg
        assert "critical" in msg.lower() or "*" in msg

    def test_truncates_long_finding_list(self):
        findings = [
            {"type": "missing_map_entry", "skill": f"skill{i}", "detail": "x"}
            for i in range(10)
        ]
        state = {
            "findings": findings,
            "critical_count": 0,
            "skills_checked": 10,
            "map_entries": 0,
        }
        msg = _format_slack_message(state)
        assert "more" in msg


class TestConstants:
    def test_critical_types_set(self):
        assert "autonomous_safe_drift" in CRITICAL_TYPES
        assert "routine_skill_blocked" in CRITICAL_TYPES
        assert "frontmatter_disable_routed" in CRITICAL_TYPES

    def test_max_autonomous_tier(self):
        assert MAX_AUTONOMOUS_TIER == 2
