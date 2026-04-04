"""
PreToolUse validator: read proposed tool use from stdin as JSON, emit allow/block JSON.

Validates:
- Bash commands: destructive patterns, secrets, injection, protected paths
- Write/Edit tools: blocks TELOS file writes in autonomous sessions (JARVIS_SESSION_TYPE=autonomous)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from security.validators.secret_scanner import line_has_secret

# Lazy import -- path guard lives in tools/scripts which is not always importable.
# We import it only when JARVIS_OVERNIGHT_DIMENSION is set to avoid adding a hard
# dependency for non-overnight sessions.
def _import_path_guard():
    """Return validate_write_path and PathViolation, or (None, None) on import failure."""
    try:
        from tools.scripts.overnight_path_guard import validate_write_path, PathViolation
        return validate_write_path, PathViolation
    except ImportError:
        return None, None


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


def _blocked_git_destructive(cmd: str) -> bool:
    """Patterns from dcg: git commands that destroy uncommitted work."""
    if not re.search(r"\bgit\b", cmd):
        return False
    # git reset --hard / --merge (destroys working tree)
    if re.search(r"\bgit\s+reset\b.*(?:--hard|--merge)\b", cmd):
        return True
    # git checkout -- <file> or git checkout . (discards uncommitted changes)
    if re.search(r"\bgit\s+checkout\b.*\s--\s", cmd):
        return True
    if re.search(r"\bgit\s+checkout\s+\.\s*$", cmd):
        return True
    # git clean -f (deletes untracked files)
    if re.search(r"\bgit\s+clean\b.*-[a-z]*f", cmd):
        return True
    # git stash drop / git stash clear (destroys stashed work)
    if re.search(r"\bgit\s+stash\s+(?:drop|clear)\b", cmd):
        return True
    # git branch -D (force-delete branch)
    if re.search(r"\bgit\s+branch\s+-D\b", cmd):
        return True
    # git restore . (discard all working tree changes)
    if re.search(r"\bgit\s+restore\s+\.\s*$", cmd):
        return True
    # git commit --amend (rewrites history -- prevents scope creep bypass via revert-before-diff)
    if re.search(r"\bgit\s+commit\b.*--amend\b", cmd):
        return True
    # git restore --source (reverts to arbitrary tree state -- bypasses diff-based scope check)
    if re.search(r"\bgit\s+restore\b.*--source\b", cmd):
        return True
    # git show redirected to file (extracts content to overwrite arbitrary path)
    if re.search(r"\bgit\s+show\b.*\s>", cmd):
        return True
    return False


def _inline_script_destructive(cmd: str) -> bool:
    """Patterns from dcg: destructive commands hidden in inline scripts."""
    # python -c / python3 -c with dangerous calls
    py_inline = re.search(r"\bpython[3]?\s+-c\s+[\"'](.+?)[\"']", cmd)
    if py_inline:
        body = py_inline.group(1)
        if re.search(r"\b(?:os\.remove|os\.unlink|shutil\.rmtree|os\.system)\b", body):
            return True
    # node -e with dangerous calls
    node_inline = re.search(r"\bnode\s+-e\s+[\"'](.+?)[\"']", cmd)
    if node_inline:
        body = node_inline.group(1)
        if re.search(r"\b(?:unlinkSync|rmdirSync|rmSync|execSync)\b", body):
            return True
    # bash -c / sh -c wrapping destructive commands
    sh_inline = re.search(r"\b(?:ba)?sh\s+-c\s+[\"'](.+?)[\"']", cmd)
    if sh_inline:
        body = sh_inline.group(1)
        if re.search(r"\brm\s+-[a-z]*rf\b", body) or re.search(r"\bgit\s+reset\s+--hard\b", body):
            return True
    return False


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


def _bash_writes_telos(cmd: str) -> bool:
    """Check if a Bash command writes to memory/work/telos/ paths."""
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return False
    telos = r"memory[/\\]work[/\\]telos[/\\]"
    # Redirect writes: > or >> to telos path
    if re.search(r">+\s*[^\s]*" + telos, cmd):
        return True
    # tee to telos path
    if re.search(r"\btee\b.*" + telos, cmd):
        return True
    # cp or mv targeting telos
    if re.search(r"\b(?:cp|mv)\b.*" + telos, cmd):
        return True
    # echo/cat with redirect to telos
    if re.search(r"\b(?:echo|cat|printf)\b.*>.*" + telos, cmd):
        return True
    # python -c writing to telos
    if re.search(r"\bpython[3]?\b.*" + telos, cmd):
        return True
    return False


def validate_bash_command(command: str) -> dict[str, Any]:
    if not command or not command.strip():
        return _result("allow")

    cmd = command

    if _bash_writes_telos(cmd):
        return _result("block", "Autonomous sessions MUST NOT write to memory/work/telos/ via Bash")

    if FORK_BOMB_RE.search(cmd):
        return _result("block", "Fork bomb pattern blocked")

    if _blocked_rm_rf(cmd):
        return _result("block", "Blocked recursive delete pattern (constitutional rules)")

    if _blocked_git_destructive(cmd):
        return _result("block", "Destructive git command blocked (dcg pattern)")

    if _inline_script_destructive(cmd):
        return _result("block", "Destructive command in inline script blocked (dcg pattern)")

    if _blocked_git_force_main(cmd):
        return _result("block", "git push --force to main/master is blocked")

    if re.search(r"\bgit\b", cmd) and re.search(r"--no-verify\b", cmd):
        return _result("block", "--no-verify bypasses pre-commit hooks and is blocked")

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


TELOS_PATH_PATTERN = re.compile(
    r"memory[/\\]work[/\\]telos[/\\]", re.IGNORECASE
)

# Context profiles are read by the dispatcher at prompt-assembly time.
# Workers must never modify them -- a compromised profile is a persistent
# prompt injection vector that poisons every future worker in that tier.
CONTEXT_PROFILES_PATH_PATTERN = re.compile(
    r"orchestration[/\\]context_profiles[/\\]", re.IGNORECASE
)

# Static producer configs -- title field flows into worker prompt notes unsanitized.
# A tampered title enables prompt injection into every worker spawned for that topic.
RESEARCH_TOPICS_PATH_PATTERN = re.compile(
    r"orchestration[/\\]research_topics\.json$", re.IGNORECASE
)

# Producer registry -- controls which producers run and whether alerts fire.
# Guard is autonomous-session-only; interactive sessions are operator-controlled.
# A prompt-injected autonomous worker could tamper to suppress alerts or unsuspend producers.
PRODUCERS_REGISTRY_PATH_PATTERN = re.compile(
    r"orchestration[/\\]producers\.json$", re.IGNORECASE
)

# Secrets patterns for Read tool blocking (autonomous sessions)
_SECRET_FILE_PATTERNS = re.compile(
    r"(?:^|[/\\])\.env(?:[/\\]|$)"
    r"|(?:^|[/\\])credentials\.json$"
    r"|\.pem$"
    r"|\.key$"
    r"|(?:^|[/\\])\.ssh[/\\]"
    r"|(?:^|[/\\])\.aws[/\\]",
    re.IGNORECASE,
)


def _check_autonomous_telos_write(tool: str, inp: dict) -> dict[str, Any] | None:
    """Block Write/Edit to memory/work/telos/ or context_profiles/ in autonomous sessions.

    Returns a block result if the write should be blocked, None otherwise.
    """
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return None

    if tool not in ("Write", "Edit"):
        return None

    file_path = str(inp.get("file_path", "") or "")

    if CONTEXT_PROFILES_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to orchestration/context_profiles/. "
            f"Profile poisoning is a persistent prompt injection vector. "
            f"Blocked: {tool} to {file_path}"
        )

    if TELOS_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to memory/work/telos/. "
            f"TELOS proposals must be queued for interactive review. "
            f"Blocked: {tool} to {file_path}"
        )

    if RESEARCH_TOPICS_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to orchestration/research_topics.json. "
            f"Topic titles flow into worker prompt notes -- tampering enables prompt injection. "
            f"Blocked: {tool} to {file_path}"
        )

    if PRODUCERS_REGISTRY_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to orchestration/producers.json. "
            f"This file controls which producers run and whether watchdog alerts fire -- "
            f"tampering can silently disable all producer monitoring. "
            f"Blocked: {tool} to {file_path}"
        )

    return None


def _check_autonomous_git_push(cmd: str) -> bool:
    """Block ALL git push commands in autonomous sessions (not just force-push)."""
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return False
    return bool(re.search(r"\bgit\s+push\b", cmd))


def _check_autonomous_read_secrets(tool: str, inp: dict) -> dict[str, Any] | None:
    """Block Read tool on secret files in autonomous sessions.

    Interactive sessions rely on user judgment; autonomous sessions must be
    validator-enforced because there is no human in the loop.
    """
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return None

    if tool != "Read":
        return None

    file_path = str(inp.get("file_path", "") or "")
    if _SECRET_FILE_PATTERNS.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT read secret files. "
            f"Blocked: Read {file_path}"
        )

    return None


def _check_autonomous_file_containment(tool: str, inp: dict) -> dict[str, Any] | None:
    """Block Read/Write/Edit outside worktree in autonomous sessions.

    Workers must only access files within their git worktree. The worktree
    path is communicated via JARVIS_WORKTREE_ROOT env var (set by dispatcher).
    If the env var is not set, this check is skipped (allows non-dispatcher
    autonomous jobs like overnight runner to work).
    """
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return None

    worktree_root = os.environ.get("JARVIS_WORKTREE_ROOT")
    if not worktree_root:
        return None  # No containment when worktree root not specified

    if tool not in ("Read", "Write", "Edit"):
        return None

    file_path = str(inp.get("file_path", "") or "")
    if not file_path:
        return None

    # Normalize paths for comparison
    try:
        resolved = str(Path(file_path).resolve()).replace("\\", "/").lower()
        wt_resolved = str(Path(worktree_root).resolve()).replace("\\", "/").lower()
    except (OSError, ValueError):
        return _result("block", f"Cannot resolve path for containment check: {file_path}")

    if not resolved.startswith(wt_resolved):
        return _result(
            "block",
            f"Autonomous worker file access blocked: path escapes worktree. "
            f"Allowed root: {worktree_root}. Blocked: {tool} {file_path}"
        )

    return None


def _check_overnight_path_scope(tool: str, inp: dict) -> dict[str, Any] | None:
    """Enforce dimension-scoped write rules for overnight autonomous sessions.

    Active when JARVIS_OVERNIGHT_DIMENSION is set AND session type is autonomous.
    Delegates to overnight_path_guard.validate_write_path() which encodes per-
    dimension allowed directories and global BLOCKED_PATHS (including history/).

    Returns a block result if the write should be blocked, None otherwise.
    """
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return None

    dimension = os.environ.get("JARVIS_OVERNIGHT_DIMENSION")
    if not dimension:
        return None

    if tool not in ("Write", "Edit"):
        return None

    file_path = str(inp.get("file_path", "") or "")
    if not file_path:
        return None

    validate_write_path, PathViolation = _import_path_guard()
    if validate_write_path is None:
        # Guard unavailable -- fail open with a warning; do not silently allow
        # writes when the guard itself cannot be loaded.
        return _result(
            "block",
            f"OVERNIGHT PATH GUARD UNAVAILABLE: cannot import overnight_path_guard. "
            f"Blocking {tool} to {file_path} to prevent unvalidated writes."
        )

    try:
        validate_write_path(file_path, dimension=dimension)
        return None  # allowed
    except PathViolation as exc:
        return _result(
            "block",
            f"Overnight path guard rejected write for dimension '{dimension}': {exc}"
        )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps(_result("block", f"Invalid JSON on stdin: {e}")))
        sys.exit(1)

    tool = data.get("tool", "")
    inp = data.get("input") or {}
    if isinstance(inp, str):
        inp = {}

    # -- Autonomous session protections (Phase 5 P0 security) --

    # TELOS write protection (Write/Edit tools)
    telos_block = _check_autonomous_telos_write(tool, inp)
    if telos_block:
        print(json.dumps(telos_block))
        return

    # Overnight dimension-scoped write protection (Write/Edit tools)
    # Runs when JARVIS_OVERNIGHT_DIMENSION is set; enforces per-dimension allowed
    # directories and global BLOCKED_PATHS including history/ immutability.
    overnight_block = _check_overnight_path_scope(tool, inp)
    if overnight_block:
        print(json.dumps(overnight_block))
        return

    # Secret file read protection (Read tool)
    secret_block = _check_autonomous_read_secrets(tool, inp)
    if secret_block:
        print(json.dumps(secret_block))
        return

    # Worktree file containment (Read/Write/Edit tools)
    containment_block = _check_autonomous_file_containment(tool, inp)
    if containment_block:
        print(json.dumps(containment_block))
        return

    # Bash command validation
    if tool != "Bash":
        print(json.dumps(_result("allow")))
        return

    command = str(inp.get("command", "") or "")

    # Autonomous git push blocking (all push, not just force-push)
    if _check_autonomous_git_push(command):
        print(json.dumps(_result("block", "Autonomous sessions MUST NOT run git push")))
        return

    result = validate_bash_command(command)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
