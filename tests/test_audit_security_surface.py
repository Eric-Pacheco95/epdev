"""Tests for audit_security_surface pure functions (AST/regex extraction)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.audit_security_surface import (
    _extract_guard_functions,
    _extract_constants,
    _extract_protected_path_patterns,
    _extract_autonomous_guards,
)


NL = chr(10)
DQ = chr(34)


class TestExtractGuardFunctions:
    def test_finds_blocked_function(self):
        src = f"def _blocked_rm_rf(cmd):{NL}    pass{NL}"
        result = _extract_guard_functions(src)
        assert any(g["name"] == "_blocked_rm_rf" for g in result)

    def test_finds_check_function(self):
        src = f"def _check_secrets(path):{NL}    pass{NL}"
        result = _extract_guard_functions(src)
        assert any(g["name"] == "_check_secrets" for g in result)

    def test_ignores_non_guard_functions(self):
        src = f"def helper():{NL}    pass{NL}{NL}def _blocked_one():{NL}    pass{NL}"
        result = _extract_guard_functions(src)
        assert all(g["name"] != "helper" for g in result)
        assert len(result) == 1

    def test_empty_source_returns_empty_list(self):
        assert _extract_guard_functions("") == []

    def test_multiple_guards_sorted_by_lineno(self):
        src = f"def _check_z():{NL}    pass{NL}{NL}def _blocked_a():{NL}    pass{NL}"
        result = _extract_guard_functions(src)
        assert len(result) == 2
        assert result[0]["lineno"] < result[1]["lineno"]


class TestExtractConstants:
    def test_finds_injection_substrings(self):
        token = "harmless-check-token"
        src = "INJECTION_SUBSTRINGS = (" + NL + "    " + DQ + token + DQ + "," + NL + ")" + NL
        result = _extract_constants(src)
        names = [c["name"] for c in result]
        assert "INJECTION_SUBSTRINGS" in names
        vals = next(c for c in result if c["name"] == "INJECTION_SUBSTRINGS")
        assert token in vals["values"]

    def test_finds_fork_bomb_re(self):
        src = 'FORK_BOMB_RE = re.compile(r":[(][)][{][^}]*:[|]")'  
        result = _extract_constants(src)
        assert "FORK_BOMB_RE" in [c["name"] for c in result]

    def test_returns_empty_for_no_constants(self):
        result = _extract_constants("x = 1" + NL + "y = 2" + NL)
        assert result == []


class TestExtractProtectedPathPatterns:
    def test_extracts_regex_patterns_from_protected_path(self):
        src = (
            "def _protected_path(cmd, tool_input):\n"
            "    if re.search(r\"memory/work/telos/\", cmd):\n"
            "        return True\n"
            "    if re.search(r\"\\.env$\", cmd):\n"
            "        return True\n"
            "\n"
            "def other_fn():\n"
            "    pass\n"
        )
        patterns = _extract_protected_path_patterns(src)
        assert "memory/work/telos/" in patterns

    def test_returns_empty_when_function_absent(self):
        src = "def unrelated():\n    pass\n"
        patterns = _extract_protected_path_patterns(src)
        assert patterns == []


class TestExtractAutonomousGuards:
    def test_detects_present_guard_functions(self):
        src = (
            "def _check_autonomous_git_push(cmd):\n    pass\n"
            "def _check_autonomous_read_secrets(cmd):\n    pass\n"
        )
        guards = _extract_autonomous_guards(src)
        names = [g["name"] for g in guards]
        assert "_check_autonomous_git_push" in names
        assert "_check_autonomous_read_secrets" in names

    def test_returns_empty_when_no_guards_present(self):
        src = "def unrelated():\n    pass\n"
        guards = _extract_autonomous_guards(src)
        assert guards == []

    def test_each_guard_has_name_and_desc(self):
        src = "def _check_autonomous_telos_write(cmd):\n    pass\n"
        guards = _extract_autonomous_guards(src)
        assert len(guards) == 1
        assert "name" in guards[0]
        assert "desc" in guards[0]
        assert guards[0]["desc"]
