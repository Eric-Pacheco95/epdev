#!/usr/bin/env python3
"""isc_common -- shared ISC sanitization and classification logic.

Imported by:
    tools/scripts/isc_validator.py    (format validation + --execute mode)
    tools/scripts/jarvis_dispatcher.py (autonomous task execution)

Zero external dependencies (stdlib only).
"""

from __future__ import annotations

import re
from typing import Optional

# -- Allowlist ----------------------------------------------------------------
#
# Commands permitted as the first word of each ISC verify pipeline segment.
# Intentionally excludes:
#   python / python3  -- bare `python -c` enables sandbox escape; explicit
#                        repo-relative script paths are allowed separately via
#                        _PYTHON_SCRIPT_PREFIXES and classify_verify_method()
#   echo              -- trivial-pass pattern; always exits 0, verifies nothing
#
ISC_ALLOWED_COMMANDS = frozenset({
    "test", "grep", "jq", "cat", "ls", "wc",
    "head", "tail", "find", "diff", "stat", "file",
})

# Python verify commands are only allowed when pointing at an explicit
# repo-relative script path under one of these prefixes.
_PYTHON_SCRIPT_PREFIXES = ("tools/scripts/", "tools\\scripts\\")

# -- Secret path patterns -----------------------------------------------------
#
# Ported from security/validators/validate_tool_use.py::_protected_path().
# Applied to ALL token positions in an ISC verify command (not just the
# command name), so `grep PATTERN .env` is blocked even though grep is allowed.
#
SECRET_PATH_PATTERNS = re.compile(
    r"[/\\]\.ssh[/\\]|[~][/\\]\.ssh\b"
    r"|\.aws[/\\]credentials"
    r"|(?:^|[\s/\\])\.env(?:[\s\"'$]|$)"
    r"|[/\\][^\s\"']*credentials[^\s\"']*"
    r"|[/\\][^\s\"']*secret[^\s\"']*"
    r"|[^\s\"']+\.pem(?:[\s\"']|$)"
    r"|[^\s\"']+\.key(?:[\s\"']|$)",
    re.IGNORECASE,
)

# -- Destructive inline script patterns ---------------------------------------
#
# Ported from security/validators/validate_tool_use.py::_inline_script_destructive().
# Blocks destructive calls that may be smuggled inside quoted arguments.
#
_DESTRUCTIVE_INLINE_RE = re.compile(
    r"\b(?:os\.remove|os\.unlink|shutil\.rmtree|os\.system|subprocess\.run)\b",
    re.IGNORECASE,
)

# -- Manual-required prefixes -------------------------------------------------
#
# Verify methods starting with these keywords are freeform descriptions, not
# shell commands. They require human or LLM judgment and must not be executed.
#
_MANUAL_PREFIXES = (
    "review ",
    "review\t",
    "slack ",
    "read --",
    "cli --",
    "manual ",
    "check --",
    "confirm ",
    "inspect ",
)

# -- Sentinel -----------------------------------------------------------------
#
# Returned by classify_verify_method() for safe-but-non-executable verify
# methods (Review, Slack, freeform descriptions).
#
# Callers MUST distinguish MANUAL_REQUIRED from None (blocked/missing):
#   MANUAL_REQUIRED  -- not executable, not dangerous; skip gracefully
#   None             -- blocked dangerous command; skip with warning
#
MANUAL_REQUIRED: str = "manual_required"


# -- Public API ---------------------------------------------------------------

def classify_verify_method(verify_str: str) -> str:
    """Classify an ISC string's verify method.

    Args:
        verify_str: Full ISC string, e.g.
            "File exists | Verify: test -f tools/scripts/foo.py"
            or just the command part after '| Verify:'.

    Returns:
        'executable'      -- shell command; safe to pass to sanitize_isc_command()
        'manual_required' -- freeform description; skip gracefully, flag for human
        'blocked'         -- dangerous pattern; skip with security warning

    Callers should only invoke sanitize_isc_command() when this returns 'executable'.
    """
    cmd = _extract_cmd(verify_str)
    if cmd is None:
        return MANUAL_REQUIRED

    cmd_lower = cmd.lower()

    # Freeform description: starts with a manual-required keyword
    for prefix in _MANUAL_PREFIXES:
        if cmd_lower.startswith(prefix):
            return MANUAL_REQUIRED

    first = _first_word(cmd)

    # Python: explicit repo-relative script allowed; -c inline always blocked
    if first in ("python", "python3"):
        rest = cmd[len(first):].strip()
        if re.match(r"-c\b|'-c'|\"+-c\"", rest):
            return "blocked"
        if any(rest.startswith(p) for p in _PYTHON_SCRIPT_PREFIXES):
            return "executable"
        # python with unrecognized argument structure -- block
        return "blocked"

    # echo: trivial-pass, no verification value; classify as manual_required
    if first == "echo":
        return MANUAL_REQUIRED

    # Recognized shell command
    if first in ISC_ALLOWED_COMMANDS:
        return "executable"

    # Unknown first word -- freeform description
    return MANUAL_REQUIRED


def sanitize_isc_command(verify_str: str) -> Optional[str]:
    """Extract and validate the verify command from an ISC string.

    Returns the sanitized command string, or None if blocked.

    Security checks (in order):
        1. Shell metacharacter blocking (; && || $() backticks)
        2. Per-segment first-word allowlist validation
        3. Secret path check on ALL tokens (not just command name)
        4. Destructive inline pattern check

    Precondition: classify_verify_method(verify_str) == 'executable'.
    Callers should run classify_verify_method() first.
    """
    cmd = _extract_cmd(verify_str)
    if cmd is None:
        return None

    # 1. Block dangerous shell metacharacters
    if re.search(r"`|\$\(|;|&&|\|\||>>?\s*/", cmd):
        return None

    # Split on pipe and validate each segment
    segments = [s.strip() for s in cmd.split("|") if s.strip()]
    for seg in segments:
        first = _first_word(seg)

        # 2a. Python: only explicit script paths
        if first in ("python", "python3"):
            rest = seg[len(first):].strip()
            if not any(rest.startswith(p) for p in _PYTHON_SCRIPT_PREFIXES):
                return None
        # 2b. Standard allowlist
        elif first not in ISC_ALLOWED_COMMANDS:
            return None

        # 3. Secret path check on full segment text (all arguments)
        if SECRET_PATH_PATTERNS.search(seg):
            return None

        # 4. Destructive inline pattern check -- only meaningful for code-executing
        # commands (python/node/bash). grep/cat/test args are not executed, so
        # `grep shutil.rmtree file.py` is legitimate and must not be blocked.
        if first in ("python", "python3", "node", "bash", "sh"):
            if _DESTRUCTIVE_INLINE_RE.search(seg):
                return None

    return cmd


# -- Helpers ------------------------------------------------------------------

def _extract_cmd(verify_str: str) -> Optional[str]:
    """Extract the command portion from a verify string.

    Accepts two forms:
        Full ISC string: "Criterion text | Verify: test -f foo.py"
        Bare command:    "test -f foo.py"  (no separator present)
    """
    if "| Verify:" in verify_str:
        parts = verify_str.split("| Verify:", 1)
        cmd = parts[1].strip()
        return cmd if cmd else None
    # No separator -- treat entire input as the command
    cmd = verify_str.strip()
    return cmd if cmd else None


def _first_word(cmd: str) -> str:
    """Return the lowercased basename of the first token in a command."""
    tokens = cmd.split()
    if not tokens:
        return ""
    return tokens[0].split("/")[-1].split("\\")[-1].lower()
