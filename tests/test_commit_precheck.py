"""Tests for commit_precheck pure functions."""

from tools.scripts.commit_precheck import (
    classify_file,
    check_dangerous_files,
    DANGEROUS_EXTENSIONS,
    DANGEROUS_FILENAMES,
)


# ── classify_file ────────────────────────────────────────────────────

def test_classify_test_by_name():
    assert classify_file("tests/test_foo.py") == "test"


def test_classify_test_by_path():
    assert classify_file("some/test/helper.py") == "test"


def test_classify_skill():
    assert classify_file(".claude/skills/commit/SKILL.md") == "skill"


def test_classify_script():
    assert classify_file("tools/scripts/foo.py") == "script"


def test_classify_code_by_ext():
    assert classify_file("src/main.py") == "code"
    assert classify_file("app/index.ts") == "code"


def test_classify_config():
    assert classify_file("config/settings.json") == "config"
    assert classify_file("pyproject.toml") == "config"


def test_classify_docs():
    assert classify_file("README.md") == "docs"


def test_classify_other():
    assert classify_file("image.png") == "other"


# ── check_dangerous_files ────────────────────────────────────────────

def test_dangerous_extension():
    result = check_dangerous_files([".env", "cert.pem", "main.py"])
    dangerous = [r["file"] for r in result]
    assert ".env" in dangerous
    assert "cert.pem" in dangerous
    assert "main.py" not in dangerous


def test_dangerous_filename():
    result = check_dangerous_files(["credentials.json"])
    assert len(result) == 1
    assert "Sensitive filename" in result[0]["reason"]


def test_no_dangerous_files():
    result = check_dangerous_files(["src/app.py", "README.md"])
    assert result == []


def test_dangerous_keystore():
    result = check_dangerous_files(["app.keystore"])
    assert len(result) == 1
