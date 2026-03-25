"""
PreToolUse validator: read proposed Bash command from stdin as JSON, emit allow/block JSON.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from security.validators.secret_scanner import line_has_secret


def _result(decision: str, reason: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"decision": decision}
    if reason:
        out["reason"] = reason
    return out


FORK_BOMB_RE = re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;")

INJECTION_SUBSTRINGS = (
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "disregard all previous",
    "you are now",
    "new instructions:",
    "system prompt",
    "developer message",
    "sudo ignore",
    "dan mode",
    "jailbreak",
)

PATH_TRAVERSAL_SENSITIVE = re.compile(
    r"\.\./.*/(etc|passwd|shadow|ssh|root)|\.\.\\\.\.\\.*\\(etc|passwd)",
    re.IGNORECASE,
)

DISK_DANGER = re.compile(
    r"\b(?:mkfs|mkfs\.\w+|dd\s+.*\bif=/dev/|fdisk|cfdisk|parted|diskpart|format\s+[a-z]:)\b",
    re.IGNORECASE,
)


def _blocked_rm_rf(cmd: str) -> bool:
    if not re.search(r"\brm\b", cmd):
        return False
    compact = re.sub(r"\s+", " ", cmd)
    if not re.search(r"-[a-z]*rf[a-z]*|-[a-z]*fr[a-z]*|-r\s+-f\b", compact, re.IGNORECASE):
        return False
    if (
        re.search(r"\brm\b[^;]*-rf[^;]*\s/\s", compact)
        or re.search(r"\brm\b[^;]*-rf[^;]*\s/\s*[\"']", compact)
        or re.search(r"\brm\b[^;]*-rf[^;]*\s/\s*$", compact)
    ):
        return True
    if (
        re.search(r"\brm\b[^;]*-rf[^;]*\s~\s*$", compact)
        or re.search(r"\brm\b[^;]*-rf[^;]*\s~\s*[;&|]", compact)
        or re.search(r"\brm\b[^;]*-rf[^;]*[\"']~[\"']", compact)
    ):
        return True
    if re.search(r"\brm\b[^;]*-rf[^;]*\s\*\s*;?", compact) or re.search(
        r"\brm\b[^;]*-rf[^;]*\s\*[\"']", compact
    ):
        return True
    return False


def _blocked_git_force_main(cmd: str) -> bool:
    if not re.search(r"\bgit\b", cmd):
        return False
    if not re.search(r"\bpush\b", cmd):
        return False
    if not re.search(r"(?:--force|\s-f\b)", cmd):
        return False
    return bool(re.search(r"\b(?:main|master)\b", cmd))


def _system_paths_write(cmd: str) -> bool:
    if re.search(r"\b(?:rm|mv|chmod|chown|tee|shred)\b.*/(?:etc|boot)(?:/|\s)", cmd):
        return True
    if re.search(r">[\s]*/(?:etc|boot)/", cmd):
        return True
    return False


def _remote_pipe_shell(cmd: str) -> bool:
    return bool(
        re.search(r"\b(?:curl|wget)\b[^|]*\|\s*(?:bash|sh)\b", cmd, re.IGNORECASE)
    )


def _protected_path(cmd: str) -> bool:
    """Constitutional protected paths and globs."""
    c = cmd
    if re.search(r"[/\\]\.ssh[/\\]|[~][/\\]\.ssh\b", c):
        return True
    if re.search(r"\.aws[/\\]credentials", c, re.IGNORECASE):
        return True
    if re.search(r"(?:^|[\s/\\])\.env(?:[\s\"'$]|$)", c):
        return True
    if "*credentials*" in c or "*secret*" in c:
        return True
    if re.search(r"[/\\][^\s\"']*credentials[^\s\"']*", c, re.IGNORECASE):
        return True
    if re.search(r"[/\\][^\s\"']*secret[^\s\"']*", c, re.IGNORECASE):
        return True
    if re.search(r"[^\s\"']+\.pem(?:[\s\"']|$)", c, re.IGNORECASE):
        return True
    if re.search(r"[^\s\"']+\.key(?:[\s\"']|$)", c, re.IGNORECASE):
        return True
    return False


def validate_bash_command(command: str) -> dict[str, Any]:
    if not command or not command.strip():
        return _result("allow")

    cmd = command

    if FORK_BOMB_RE.search(cmd):
        return _result("block", "Fork bomb pattern blocked")

    if _blocked_rm_rf(cmd):
        return _result("block", "Blocked recursive delete pattern (constitutional rules)")

    if _blocked_git_force_main(cmd):
        return _result("block", "git push --force to main/master is blocked")

    if DISK_DANGER.search(cmd):
        return _result("block", "Disk format/partition command blocked")

    if _system_paths_write(cmd):
        return _result("block", "Modification of /etc or /boot paths blocked")

    if _protected_path(cmd):
        return _result("block", "Protected path access blocked")

    if PATH_TRAVERSAL_SENSITIVE.search(cmd):
        return _result("block", "Path traversal to sensitive location blocked")

    lower = cmd.lower()
    for inj in INJECTION_SUBSTRINGS:
        if inj in lower:
            return _result("block", "Prompt injection / instruction pattern in command blocked")

    if _remote_pipe_shell(cmd):
        return _result("block", "Piping remote content to shell blocked")

    found, name = line_has_secret(cmd)
    if found and name:
        return _result("block", f"Secret-like pattern in command blocked ({name})")

    return _result("allow")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps(_result("block", f"Invalid JSON on stdin: {e}")))
        sys.exit(1)

    tool = data.get("tool")
    if tool != "Bash":
        print(json.dumps(_result("allow")))
        return

    command = ""
    inp = data.get("input")
    if isinstance(inp, dict):
        command = str(inp.get("command", "") or "")

    result = validate_bash_command(command)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
