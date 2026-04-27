"""Tests for commit_precheck pure functions."""

from tools.scripts.commit_precheck import (
    classify_file,
    check_dangerous_files,
    _sanitize_ascii,
    format_table,
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


# ── _sanitize_ascii ──────────────────────────────────────────────────

def test_sanitize_arrow():
    assert _sanitize_ascii("A → B") == "A -> B"

def test_sanitize_em_dash():
    assert _sanitize_ascii("one—two") == "one--two"

def test_sanitize_smart_quotes():
    assert _sanitize_ascii("“hello”") == '"hello"'

def test_sanitize_no_change_plain_text():
    assert _sanitize_ascii("hello world") == "hello world"

def test_sanitize_empty_string():
    assert _sanitize_ascii("") == ""


# ── format_table ─────────────────────────────────────────────────────

def test_format_table_nothing_staged():
    report = {"status": "nothing_staged", "unstaged": [], "untracked": []}
    result = format_table(report)
    assert "Nothing staged" in result

def test_format_table_shows_branch():
    report = {
        "status": "ok",
        "branch": "main",
        "staged_count": 2,
        "diff_stats": {"total_added": 10, "total_removed": 3, "files": []},
        "categories": {},
        "secrets": [],
    }
    result = format_table(report)
    assert "main" in result

def test_format_table_shows_secrets_warning():
    report = {
        "status": "warn",
        "branch": "feature",
        "staged_count": 1,
        "diff_stats": {"total_added": 5, "total_removed": 0, "files": []},
        "categories": {},
        "secrets": [{"type": "API_KEY", "file": "config.py", "line_preview": "secret=abc123"}],
    }
    result = format_table(report)
    assert "SECRETS" in result
