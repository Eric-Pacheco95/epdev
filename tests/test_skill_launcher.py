"""Tests for tools/scripts/skill_launcher.py pure functions."""

import hashlib
from pathlib import Path

import pytest

from tools.scripts.skill_launcher import check_skill_safety, hash_skill


class TestHashSkill:
    def test_deterministic(self):
        content = "some skill content"
        assert hash_skill(content) == hash_skill(content)

    def test_returns_sha256_hex(self):
        content = "skill content"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert hash_skill(content) == expected

    def test_different_content_different_hash(self):
        assert hash_skill("a") != hash_skill("b")

    def test_empty_string(self):
        result = hash_skill("")
        assert len(result) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in result)


class TestCheckSkillSafety:
    def test_missing_file_returns_false(self, tmp_path):
        safe, content = check_skill_safety(tmp_path / "nonexistent.md")
        assert safe is False
        assert content == ""

    def test_autonomous_safe_true_inline(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("## SKILL\nautonomous_safe: true\nother: stuff", encoding="utf-8")
        safe, content = check_skill_safety(f)
        assert safe is True
        assert "autonomous_safe" in content

    def test_autonomous_safe_false_inline(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("autonomous_safe: false\n", encoding="utf-8")
        safe, _ = check_skill_safety(f)
        assert safe is False

    def test_autonomous_safe_section_header_true(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("## autonomous_safe\ntrue\n", encoding="utf-8")
        safe, _ = check_skill_safety(f)
        assert safe is True

    def test_autonomous_safe_section_header_false(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("## autonomous_safe\nfalse\n", encoding="utf-8")
        safe, _ = check_skill_safety(f)
        assert safe is False

    def test_no_autonomous_safe_field_returns_false(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("# My Skill\nSome description with no safety field.\n", encoding="utf-8")
        safe, _ = check_skill_safety(f)
        assert safe is False

    def test_case_insensitive_field_name(self, tmp_path):
        f = tmp_path / "SKILL.md"
        f.write_text("AUTONOMOUS_SAFE: true\n", encoding="utf-8")
        safe, _ = check_skill_safety(f)
        assert safe is True

    def test_returns_full_content_on_success(self, tmp_path):
        f = tmp_path / "SKILL.md"
        text = "autonomous_safe: true\nextra content here"
        f.write_text(text, encoding="utf-8")
        _, content = check_skill_safety(f)
        assert content == text
