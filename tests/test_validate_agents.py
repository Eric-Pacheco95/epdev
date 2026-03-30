"""Pytest tests for tools/scripts/validate_agents.py — section detection logic."""

import sys
import tempfile
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.validate_agents import find_sections, check_agent, REQUIRED_SECTIONS


class TestFindSections:
    def test_extracts_h2_headings(self):
        content = "# Title\n## Identity\nSome text\n## Mission\nMore text"
        assert find_sections(content) == ["Identity", "Mission"]

    def test_ignores_h1_and_h3(self):
        content = "# H1\n## H2\n### H3\n#### H4"
        assert find_sections(content) == ["H2"]

    def test_empty_content(self):
        assert find_sections("") == []

    def test_strips_whitespace(self):
        content = "## Identity  \n##  Mission \n"
        sections = find_sections(content)
        assert "Identity" in sections
        assert "Mission" in sections

    def test_no_headings(self):
        content = "Just plain text\nNo headings here"
        assert find_sections(content) == []


class TestCheckAgent:
    def test_full_agent_all_pass(self):
        content = "\n".join(f"## {s}\nContent for {s}" for s in REQUIRED_SECTIONS)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            name, found, missing = check_agent(f.name)
        os.unlink(f.name)
        assert len(missing) == 0
        assert len(found) == 6

    def test_missing_sections(self):
        content = "## Identity\nI am an agent\n## Mission\nDo things"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            name, found, missing = check_agent(f.name)
        os.unlink(f.name)
        assert "Identity" in found
        assert "Mission" in found
        assert "Critical Rules" in missing
        assert "Deliverables" in missing

    def test_name_from_filename(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                         prefix="TestAgent_", encoding="utf-8") as f:
            f.write("## Identity\ntest")
            f.flush()
            name, _, _ = check_agent(f.name)
        os.unlink(f.name)
        assert "TestAgent_" in name

    def test_case_insensitive_matching(self):
        content = "## identity\n## mission\n## critical rules\n## deliverables\n## workflow\n## success metrics"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            name, found, missing = check_agent(f.name)
        os.unlink(f.name)
        assert len(missing) == 0


class TestRequiredSections:
    def test_has_six_sections(self):
        assert len(REQUIRED_SECTIONS) == 6

    def test_identity_first(self):
        assert REQUIRED_SECTIONS[0] == "Identity"
