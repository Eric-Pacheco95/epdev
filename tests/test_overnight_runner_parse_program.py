"""Tests for overnight_runner.py -- parse_program."""

import tempfile
from pathlib import Path

from tools.scripts.overnight_runner import parse_program


def _write_program(tmp_path, content):
    p = tmp_path / "program.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_program_single_dimension(tmp_path):
    content = (
        "### 1. codebase_health\n"
        "- **enabled:** true\n"
        "- **scope:** tools/scripts/**/*.py\n"
        "- **goal:** Fix warnings\n"
        "- **metric:** `python -m pytest tests/ --tb=no -q`\n"
        "- **guard:** `python -m flake8 tools/scripts/`\n"
        "- **iterations:** 10\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert "codebase_health" in dims
    d = dims["codebase_health"]
    assert d["enabled"] is True
    assert d["scope"] == "tools/scripts/**/*.py"
    assert d["goal"] == "Fix warnings"
    assert d["iterations"] == 10


def test_parse_program_disabled_dimension(tmp_path):
    content = (
        "### 1. scaffolding\n"
        "- **enabled:** false\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert dims["scaffolding"]["enabled"] is False


def test_parse_program_multiple_dimensions(tmp_path):
    content = (
        "### 1. scaffolding\n"
        "- **enabled:** true\n"
        "### 2. codebase_health\n"
        "- **enabled:** true\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert "scaffolding" in dims
    assert "codebase_health" in dims


def test_parse_program_none_value_stripped(tmp_path):
    content = (
        "### 1. codebase_health\n"
        "- **guard:** (none)\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert dims["codebase_health"]["guard"] == ""


def test_parse_program_backtick_stripped(tmp_path):
    content = (
        "### 1. codebase_health\n"
        "- **metric:** `python -m pytest tests/`\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert dims["codebase_health"]["metric"] == "python -m pytest tests/"


def test_parse_program_invalid_iterations_kept_default(tmp_path):
    content = (
        "### 1. codebase_health\n"
        "- **iterations:** notanumber\n"
    )
    p = _write_program(tmp_path, content)
    dims = parse_program(p)
    assert dims["codebase_health"]["iterations"] == 20  # default
