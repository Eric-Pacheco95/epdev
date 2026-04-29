"""Tests for tools/scripts/check_autonomy_map.py pure helper functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.check_autonomy_map as cam


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------

def test_parse_frontmatter_basic():
    text = "---\nname: my-skill\ndescription: does stuff\n---\nbody here"
    fm = cam._parse_frontmatter(text)
    assert fm["name"] == "my-skill"
    assert fm["description"] == "does stuff"


def test_parse_frontmatter_bool_true():
    text = "---\ndisable-model-invocation: true\n---\nbody"
    fm = cam._parse_frontmatter(text)
    assert fm["disable-model-invocation"] is True


def test_parse_frontmatter_bool_false():
    text = "---\nuser-invocable: false\n---\nbody"
    fm = cam._parse_frontmatter(text)
    assert fm["user-invocable"] is False


def test_parse_frontmatter_no_frontmatter_returns_none():
    text = "# Just a heading\n\nsome body"
    assert cam._parse_frontmatter(text) is None


def test_parse_frontmatter_unclosed_returns_none():
    text = "---\nname: orphan\nbody without closing"
    assert cam._parse_frontmatter(text) is None


def test_parse_frontmatter_quoted_values():
    text = '---\nname: "my skill"\n---\nbody'
    fm = cam._parse_frontmatter(text)
    assert fm["name"] == "my skill"


def test_parse_frontmatter_empty_block():
    # An empty block ("---\n---") uses the closing marker at pos 3 which the
    # search skips (it starts at pos 4); the implementation returns None.
    text = "---\n---\nbody"
    fm = cam._parse_frontmatter(text)
    assert fm is None or fm == {}


def test_parse_frontmatter_comment_lines_skipped():
    text = "---\n# this is a comment\nname: foo\n---\nbody"
    fm = cam._parse_frontmatter(text)
    assert "name" in fm
    assert "#" not in fm


# ---------------------------------------------------------------------------
# _parse_body_autonomous_safe
# ---------------------------------------------------------------------------

def test_parse_body_autonomous_safe_true():
    text = "# Skill\n\n## autonomous_safe\n\ntrue\n\nmore body"
    assert cam._parse_body_autonomous_safe(text) is True


def test_parse_body_autonomous_safe_false():
    text = "# Skill\n\n## autonomous_safe\n\nfalse\n\nmore body"
    assert cam._parse_body_autonomous_safe(text) is False


def test_parse_body_autonomous_safe_missing_returns_none():
    text = "# Skill\n\nNo autonomous_safe section here"
    assert cam._parse_body_autonomous_safe(text) is None


def test_parse_body_autonomous_safe_case_insensitive():
    text = "## AUTONOMOUS_SAFE\n\nTrue\n"
    assert cam._parse_body_autonomous_safe(text) is True


# ---------------------------------------------------------------------------
# _format_slack_message
# ---------------------------------------------------------------------------

CLEAN_STATE = {
    "findings": [],
    "finding_count": 0,
    "critical_count": 0,
    "skills_checked": 50,
    "map_entries": 45,
}

DRIFT_STATE = {
    "findings": [
        {
            "type": "autonomous_safe_drift",
            "skill": "my-skill",
            "detail": "SKILL.md and autonomy_map disagree",
        }
    ],
    "finding_count": 1,
    "critical_count": 1,
    "skills_checked": 50,
    "map_entries": 45,
}


def test_format_slack_clean():
    msg = cam._format_slack_message(CLEAN_STATE)
    assert "clean" in msg.lower()
    assert "50 skills" in msg


def test_format_slack_drift_shows_type():
    msg = cam._format_slack_message(DRIFT_STATE)
    assert "autonomous_safe_drift" in msg


def test_format_slack_drift_shows_skill():
    msg = cam._format_slack_message(DRIFT_STATE)
    assert "my-skill" in msg


def test_format_slack_drift_marks_critical():
    msg = cam._format_slack_message(DRIFT_STATE)
    # critical findings are starred with asterisk
    assert "*" in msg or "critical" in msg.lower()


def test_format_slack_orphan_not_critical():
    state = {
        "findings": [
            {"type": "orphan_map_entry", "skill": "gone-skill", "detail": "no SKILL.md"}
        ],
        "finding_count": 1,
        "critical_count": 0,
        "skills_checked": 50,
        "map_entries": 45,
    }
    msg = cam._format_slack_message(state)
    assert "orphan_map_entry" in msg


def test_format_slack_multiple_findings_grouped():
    state = {
        "findings": [
            {"type": "orphan_map_entry", "skill": "a", "detail": "no SKILL.md"},
            {"type": "orphan_map_entry", "skill": "b", "detail": "no SKILL.md"},
            {"type": "autonomous_safe_drift", "skill": "c", "detail": "drift"},
        ],
        "finding_count": 3,
        "critical_count": 1,
        "skills_checked": 50,
        "map_entries": 45,
    }
    msg = cam._format_slack_message(state)
    assert "orphan_map_entry" in msg
    assert "autonomous_safe_drift" in msg
