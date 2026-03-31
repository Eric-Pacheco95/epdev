"""Tests for validate_agents.check_agent() with actual file I/O."""

import tempfile
import os
from validate_agents import check_agent, REQUIRED_SECTIONS


def test_check_agent_all_sections():
    content = "\n".join(f"## {s}\nContent for {s}\n" for s in REQUIRED_SECTIONS)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        name, found, missing = check_agent(f.name)
    assert len(missing) == 0
    assert len(found) == 6


def test_check_agent_missing_sections():
    content = "## Identity\nSome agent\n## Mission\nDo stuff\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        name, found, missing = check_agent(f.name)
    assert "Identity" in found
    assert "Mission" in found
    assert "Critical Rules" in missing
    assert "Deliverables" in missing


def test_check_agent_case_insensitive_match():
    content = "## identity\n## mission\n## critical rules\n## deliverables\n## workflow\n## success metrics\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        name, found, missing = check_agent(f.name)
    assert len(missing) == 0


def test_check_agent_name_from_filename():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                      prefix="test_agent_") as f:
        f.write("## Identity\n")
        f.flush()
        name, found, missing = check_agent(f.name)
    assert name.startswith("test_agent_")
