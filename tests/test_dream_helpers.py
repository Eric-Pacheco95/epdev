"""Tests for dream.py -- _slug_from_theme and _infer_memory_type."""

from tools.scripts.dream import _slug_from_theme, _infer_memory_type


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
