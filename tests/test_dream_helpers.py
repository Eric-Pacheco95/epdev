"""Tests for dream.py -- _slug_from_theme, _infer_memory_type, _parse_synthesis_themes, _parse_frontmatter_field."""

import tempfile
from pathlib import Path

from tools.scripts.dream import _infer_memory_type, _parse_synthesis_themes, _slug_from_theme, _parse_frontmatter_field


# --- _parse_frontmatter_field ---

class TestParseFrontmatterField:
    def _write(self, tmp_path, content):
        f = tmp_path / "test.md"
        f.write_text(content, encoding="utf-8")
        return f

    def test_reads_existing_field(self, tmp_path):
        f = self._write(tmp_path, "---\nname: My Title\ntype: feedback\n---\nbody\n")
        assert _parse_frontmatter_field(f, "name") == "My Title"

    def test_reads_second_field(self, tmp_path):
        f = self._write(tmp_path, "---\nname: X\ntype: user\n---\n")
        assert _parse_frontmatter_field(f, "type") == "user"

    def test_returns_none_for_missing_field(self, tmp_path):
        f = self._write(tmp_path, "---\nname: X\n---\n")
        assert _parse_frontmatter_field(f, "description") is None

    def test_returns_none_when_no_frontmatter(self, tmp_path):
        f = self._write(tmp_path, "Just plain text\nno frontmatter\n")
        assert _parse_frontmatter_field(f, "name") is None

    def test_returns_none_for_missing_file(self, tmp_path):
        assert _parse_frontmatter_field(tmp_path / "nonexistent.md", "name") is None

    def test_strips_value_whitespace(self, tmp_path):
        f = self._write(tmp_path, "---\nname:   padded value   \n---\n")
        assert _parse_frontmatter_field(f, "name") == "padded value"

    def test_stops_at_closing_fence(self, tmp_path):
        f = self._write(tmp_path, "---\nname: inside\n---\nname: outside\n")
        assert _parse_frontmatter_field(f, "name") == "inside"


# --- _slug_from_theme ---

def test_slug_basic():
    assert _slug_from_theme("Hello World") == "hello-world"


def test_slug_special_chars():
    assert _slug_from_theme("Fix: auth/login bug!") == "fix-auth-login-bug"


def test_slug_truncates_at_60():
    result = _slug_from_theme("a" * 80)
    assert len(result) <= 60


def test_slug_strips_leading_trailing_hyphens():
    result = _slug_from_theme("  --hello--  ")
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_slug_already_lowercase():
    assert _slug_from_theme("abc") == "abc"


# --- _infer_memory_type ---

def test_infer_project_type():
    assert _infer_memory_type("pipeline evolution", "dispatcher needs update") == "project"


def test_infer_user_type():
    assert _infer_memory_type("adhd session pattern", "eric tends to tunnel") == "user"


def test_infer_reference_type():
    assert _infer_memory_type("external tool adoption", "new sdk available") == "reference"


def test_infer_defaults_to_feedback():
    assert _infer_memory_type("miscellaneous theme", "some general observation") == "feedback"


def test_infer_case_insensitive():
    assert _infer_memory_type("ARCHITECTURE review", "System design") == "project"


# --- _parse_synthesis_themes ---

PROVEN_SYNTHESIS = """\
# Synthesis

### Theme: Automation Gains Speed
- Maturity: proven
- Confidence: 95%
- Implication: Reduces toil significantly
- Action: Add to skill library

### Theme: Not Ready Yet
- Maturity: candidate
- Confidence: 70%
- Implication: Needs more data
- Action: Track
"""


def test_parse_synthesis_themes_qualifies_proven():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(PROVEN_SYNTHESIS)
        path = Path(f.name)
    themes = _parse_synthesis_themes(path)
    assert len(themes) == 1
    assert themes[0]["name"] == "Automation Gains Speed"
    assert themes[0]["confidence"] == 95


def test_parse_synthesis_themes_excludes_low_confidence():
    content = "### Theme: Weak Signal\n- Maturity: proven\n- Confidence: 50%\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = Path(f.name)
    themes = _parse_synthesis_themes(path)
    assert themes == []


def test_parse_synthesis_themes_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# No themes\n")
        path = Path(f.name)
    assert _parse_synthesis_themes(path) == []
