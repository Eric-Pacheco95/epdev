"""Tests for promotion_check pure helper functions."""

import tempfile
from pathlib import Path

from tools.scripts.promotion_check import (
    _classify_route,
    _is_already_promoted,
    _parse_themes,
    _proposal_id,
)


# ---------------------------------------------------------------------------
# _classify_route
# ---------------------------------------------------------------------------

def _theme(name, pattern="", implication=""):
    return {"name": name, "pattern": pattern, "implication": implication}


def test_classify_route_telos_by_name():
    assert _classify_route(_theme("telos update for mission")) == "telos"


def test_classify_route_telos_by_implication():
    assert _classify_route(_theme("observation", implication="aligns with goal")) == "telos"


def test_classify_route_steering_by_name():
    assert _classify_route(_theme("workflow discipline insight")) == "steering"


def test_classify_route_steering_by_pattern():
    assert _classify_route(_theme("insight", pattern="must always check")) == "steering"


def test_classify_route_wisdom_default():
    assert _classify_route(_theme("crypto market structure")) == "wisdom"


# ---------------------------------------------------------------------------
# _proposal_id
# ---------------------------------------------------------------------------

def test_proposal_id_slugifies_name():
    pid = _proposal_id("My Theme Name!", "synthesis_2026.md")
    assert pid == "synthesis_2026.md:my-theme-name"


def test_proposal_id_stable():
    assert _proposal_id("X", "f.md") == _proposal_id("X", "f.md")


# ---------------------------------------------------------------------------
# _is_already_promoted
# ---------------------------------------------------------------------------

def test_is_already_promoted_true():
    proposals = [{"id": "f.md:theme", "status": "promoted"}]
    assert _is_already_promoted("f.md:theme", proposals) is True


def test_is_already_promoted_pending_not_promoted():
    proposals = [{"id": "f.md:theme", "status": "pending"}]
    assert _is_already_promoted("f.md:theme", proposals) is False


def test_is_already_promoted_empty():
    assert _is_already_promoted("f.md:theme", []) is False


# ---------------------------------------------------------------------------
# _parse_themes
# ---------------------------------------------------------------------------

SAMPLE_SYNTHESIS = """\
# Synthesis Doc

### Theme: Workflow Automation Gains
- Maturity: validated
- Confidence: 8
- Anti-pattern: false
- Supporting signals: `sig1`, `sig2`
- Pattern: Automate repetitive tasks
- Implication: Reduces toil
- Action: Add to skill library

### Theme: Anti-pattern Detected
- Maturity: candidate
- Confidence: 5
- Anti-pattern: true
- Supporting signals: `sig3`
- Pattern: Manual overrides without logging
- Implication: Audit gaps
- Action: Add steering rule
"""


def test_parse_themes_count():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_SYNTHESIS)
        path = Path(f.name)
    themes = _parse_themes(path)
    assert len(themes) == 2


def test_parse_themes_first_theme_fields():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_SYNTHESIS)
        path = Path(f.name)
    themes = _parse_themes(path)
    t = themes[0]
    assert t["name"] == "Workflow Automation Gains"
    assert t["confidence"] == 8
    assert t["maturity"] == "validated"
    assert t["anti_pattern"] is False
    assert "sig1" in t["supporting_signals"]


def test_parse_themes_anti_pattern_flag():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_SYNTHESIS)
        path = Path(f.name)
    themes = _parse_themes(path)
    assert themes[1]["anti_pattern"] is True


def test_parse_themes_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# No themes here\n")
        path = Path(f.name)
    themes = _parse_themes(path)
    assert themes == []
