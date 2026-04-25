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

_GH_ALLOWLIST_PATH = Path(__file__).resolve().parent / "gh-allowlist.json"

# Write patterns for gh CLI — only operations that mutate state on GitHub.
# gh api is excluded: repo is embedded in the URL path, not --repo flag.
_GH_WRITE_RE = re.compile(
    r"\bgh\s+pr\s+create\b"
    r"|\bgh\s+repo\s+(?:create|delete|rename|fork|transfer|archive)\b"
)
_GH_REPO_FLAG_RE = re.compile(r"--repo[= ](\S+)")

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


# Match read-like function calls with a string-literal path argument.
# Quotes are matched as paired (double-double OR single-single) to avoid the
# mixed-class bug where [\"'] opens with " and closes at the first '.
_INLINE_READ_CALL_RE = re.compile(
    r"""
    (?:
        \bopen\s*\(
        | \b(?:fs\.)?readFileSync\s*\(
        | \b(?:fs\.)?readFile\s*\(
        | \bPath\s*\(
        | \bread_text\s*\(
    )
    \s*
    (?: "([^"]+)" | '([^']+)' )
    """,
    re.VERBOSE,
)

# Body extractors: capture content inside a balanced pair of quotes.
# Group 1 = double-quoted body, group 2 = single-quoted body.
_PY_INLINE_RE = re.compile(r'\bpython[3]?\s+-c\s+(?:"([^"]*)"|\'([^\']*)\')')
_NODE_INLINE_RE = re.compile(r'\bnode\s+-e\s+(?:"([^"]*)"|\'([^\']*)\')')
_SH_INLINE_RE = re.compile(r'\b(?:ba)?sh\s+-c\s+(?:"([^"]*)"|\'([^\']*)\')')

# cat/less/head/tail/etc. on a direct path token.
_SHELL_READ_TOOL_RE = re.compile(
    r"\b(?:cat|less|more|head|tail|xxd|od|strings|base64)\b\s+([^\s;|&><]+)"
)


def _scan_body_for_secret_read(body: str) -> str | None:
    for rm in _INLINE_READ_CALL_RE.finditer(body):
        path = rm.group(1) or rm.group(2)
        if path and _is_secret_path(path):
            return path
    return None


def _inline_script_reads_secret(cmd: str) -> str | None:
    """Detect inline scripts (python -c, node -e, bash -c) that read secret files.

    Returns the matched secret path string if found, else None.
    """
    for pattern in (_PY_INLINE_RE, _NODE_INLINE_RE):
        for m in pattern.finditer(cmd):
            body = m.group(1) or m.group(2) or ""
            hit = _scan_body_for_secret_read(body)
            if hit:
                return hit
    for m in _SH_INLINE_RE.finditer(cmd):
        body = m.group(1) or m.group(2) or ""
        for rm in _SHELL_READ_TOOL_RE.finditer(body):
            path = rm.group(1).strip("\"'")
            if _is_secret_path(path):
                return path
        hit = _scan_body_for_secret_read(body)
        if hit:
            return hit
    return None


def _blocked_rm_rf(cmd: str) -> bool:
    if not re.search(r"\brm\b", cmd):
        return False
    compact = re.sub(r"\s+", " ", cmd)
    # Match -rf, -fr, or split -r -f flags
    _RF = r"(?:-[a-z]*rf[a-z]*|-[a-z]*fr[a-z]*|-r\s+-f)"
    if not re.search(_RF, compact, re.IGNORECASE):
        return False
    # rm (-rf|-fr) /  -- absolute root
    if (
        re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s/\s", compact)
        or re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s/\s*[\"']", compact)
        or re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s/\s*$", compact)
    ):
        return True
    # rm (-rf|-fr) ~  -- home directory
    if (
        re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s~\s*$", compact)
        or re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s~\s*[;&|]", compact)
        or re.search(r"\brm\b[^;]*" + _RF + r"""[^;]*[\"']~[\"']""", compact)
    ):
        return True
    # rm (-rf|-fr) *  -- wildcard
    if re.search(r"\brm\b[^;]*" + _RF + r"[^;]*\s\*\s*;?", compact) or re.search(
        r"\brm\b[^;]*" + _RF + r"""[^;]*\s\*[\"']""", compact
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


def _check_gh_allowlist(cmd: str) -> dict[str, Any] | None:
    """Block gh write calls whose --repo is absent or outside the allowlist.

    Intercepts gh pr create and gh repo write subcommands.  Fail-closed:
    any exception (missing allowlist file, malformed JSON) blocks the call.
    Fast-path: returns None immediately if 'gh' is not in the command string.
    """
    if "gh" not in cmd:
        return None
    # Only fire when gh is the actual leading command token (after optional
    # KEY=val env assignments). Prevents false positives on git commit -m bodies,
    # echo literals, or python -c inline code that mention gh syntax as text.
    if not re.match(r"^(?:\w+=\S+\s+)*gh\b", cmd.lstrip()):
        return None
    if not _GH_WRITE_RE.search(cmd):
        return None

    try:
        data = json.loads(_GH_ALLOWLIST_PATH.read_text())
        allowed: set[str] = set(data.get("allowlist", []))
    except Exception as exc:
        return _result("block", f"gh-allowlist.json unavailable — failing closed: {exc}")

    m = _GH_REPO_FLAG_RE.search(cmd)
    if not m:
        return _result(
            "block",
            "gh write command requires explicit --repo <owner/repo>; "
            "env-var (GH_REPO=) and gh-config defaults are not accepted"
        )

    repo = m.group(1).strip("\"'")
    if repo not in allowed:
        return _result(
            "block",
            f"gh --repo '{repo}' is not in the allowlist {sorted(allowed)}"
        )

    return None


def validate_bash_command(command: str) -> dict[str, Any]:
    if not command or not command.strip():
        return _result("allow")

    cmd = command

    if _bash_writes_telos(cmd):
        return _result("block", "Autonomous sessions MUST NOT write to memory/work/telos/ via Bash")

    gh_block = _check_gh_allowlist(cmd)
    if gh_block:
        return gh_block

    if FORK_BOMB_RE.search(cmd):
        return _result("block", "Fork bomb pattern blocked")

    if _blocked_rm_rf(cmd):
        return _result("block", "Blocked recursive delete pattern (constitutional rules)")

    if _blocked_git_destructive(cmd):
        return _result("block", "Destructive git command blocked (dcg pattern)")

    if _inline_script_destructive(cmd):
        return _result("block", "Destructive command in inline script blocked (dcg pattern)")

    secret_read = _inline_script_reads_secret(cmd)
    if secret_read:
        return _result(
            "block",
            f"Inline script reads secret file blocked: {secret_read}"
        )

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

# Claude Code session settings -- controls allowed tools, hook commands, MCP servers.
# A compromised worker rewriting settings.json could escalate its own permissions.
# Guard is autonomous-session-only; interactive sessions are operator-controlled.
SETTINGS_PATH_PATTERN = re.compile(
    r"\.claude[/\\]settings\.json$", re.IGNORECASE
)

# Root instruction file -- controls identity, steering rules, and skill routing.
# An autonomous worker modifying CLAUDE.md could weaken security rules, alter
# model routing, or inject persistent instructions into every future session.
CLAUDE_MD_PATH_PATTERN = re.compile(
    r"CLAUDE\.md$", re.IGNORECASE
)

# tools/scripts/ -- autonomous workers spawn subprocesses that resolve under
# this directory (jarvis_dispatcher allowlist, overnight runners, producers).
# A prompt-injected worker writing arbitrary Python here could execute under
# the autonomous agent's authority on the next dispatcher run. Write-protection
# is the first half of autonomous-rules.md rule (the second is an explicit
# Bash allowlist; tracked separately).
TOOLS_SCRIPTS_PATH_PATTERN = re.compile(
    r"tools[/\\]scripts[/\\]", re.IGNORECASE
)

def _is_secret_path(path_str: str) -> bool:
    """Return True if the path references a secret/credential file.

    Canonical implementation -- used by both validate_tool_use.py and
    jarvis_dispatcher.py (duplicated there with a comment pointing here).

    Handles:
      - .env, .env.local, .env.production, .env.dev, etc.
      - credentials*, *secret*, *.key, *.pem (and .key.bak, .pem.old, etc.)
      - .ssh/, .aws/ directory prefixes
    """
    if not path_str:
        return False
    s = str(path_str).rstrip("/").rstrip("\\")
    basename = s.split("/")[-1].split("\\")[-1].lower()
    if not basename:
        return False
    # .env, .env.local, .env.production, .env.dev, etc.
    if basename == ".env" or basename.startswith(".env."):
        return True
    # Common secret/credential filename patterns
    if "credential" in basename or "secret" in basename:
        return True
    # Key/cert files (any backup/old variant too: .key.bak, .pem.old, etc.)
    for suffix in (".key", ".pem", ".p12", ".pfx"):
        if basename.endswith(suffix):
            return True
        if suffix + "." in basename:  # .key.bak, .pem.old, etc.
            return True
    # .ssh/ or .aws/ directory anywhere in the path
    normalized = s.replace("\\", "/").lower()
    if "/.ssh/" in normalized or normalized.startswith(".ssh/"):
        return True
    if "/.aws/" in normalized or normalized.startswith(".aws/"):
        return True
    return False


# Secrets patterns for Read tool blocking (autonomous sessions)
# NOTE: _is_secret_path() is the canonical check; this regex is kept as a
# belt-and-suspenders fallback for paths that need regex-level matching.
_SECRET_FILE_PATTERNS = re.compile(
    r"(?:^|[/\\])\.env(?:(?:[/\\]|$)|\.)"
    r"|(?:^|[/\\])credentials[^/\\]*$"
    r"|\.pem(?:\.|$)"
    r"|\.key(?:\.|$)"
    r"|(?:^|[/\\])\.ssh(?:[/\\]|$)"
    r"|(?:^|[/\\])\.aws(?:[/\\]|$)",
    re.IGNORECASE,
)


def _check_autonomous_telos_write(tool: str, inp: dict) -> dict[str, Any] | None:
    """Block Write/Edit to protected paths in autonomous sessions.

    Protected paths: TELOS, context_profiles, research_topics, producers,
    settings.json, CLAUDE.md.

    IMPORTANT: Any new autonomous entry point (script that calls claude -p or
    spawns a worker) MUST set JARVIS_SESSION_TYPE=autonomous in the subprocess
    env. Without it, all protections in this function are bypassed (fail-open).
    See jarvis_dispatcher.py line 963 for the assertion pattern to copy.

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

    if SETTINGS_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to .claude/settings.json. "
            f"This file controls allowed tools, hook commands, and MCP servers -- "
            f"a compromised worker rewriting it could escalate its own permissions. "
            f"Blocked: {tool} to {file_path}"
        )

    if CLAUDE_MD_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to CLAUDE.md. "
            f"This root instruction file controls identity, steering rules, and "
            f"skill routing -- autonomous modification could weaken security or "
            f"inject persistent instructions into every future session. "
            f"Blocked: {tool} to {file_path}"
        )

    if TOOLS_SCRIPTS_PATH_PATTERN.search(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT write to tools/scripts/. "
            f"Subprocesses resolved under this directory execute under the "
            f"autonomous agent's authority on the next dispatcher run -- "
            f"a prompt-injected worker writing arbitrary Python here could "
            f"escalate to arbitrary code execution. "
            f"Blocked: {tool} to {file_path}"
        )

    return None


def _check_autonomous_git_push(cmd: str) -> bool:
    """Block ALL git push commands in autonomous sessions (not just force-push)."""
    if os.environ.get("JARVIS_SESSION_TYPE") != "autonomous":
        return False
    return bool(re.search(r"\bgit\s+push\b", cmd))


def _is_autonomous_financial_snapshot_path(file_path: str) -> bool:
    """Tier-0 financial snapshots are human-briefing only (Phase 4→5 bridge)."""
    if not file_path:
        return False
    norm = file_path.replace("\\", "/").lower()
    return "data/financial/" in norm


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
    if _SECRET_FILE_PATTERNS.search(file_path) or _is_secret_path(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT read secret files. "
            f"Blocked: Read {file_path}"
        )

    if _is_autonomous_financial_snapshot_path(file_path):
        return _result(
            "block",
            f"Autonomous sessions MUST NOT read data/financial/ (human briefing + G1 only). "
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
        # Fail closed for Write/Edit; fail open for Read (reads are harder to
        # universally block and less dangerous without a worktree anchor).
        if tool in ("Write", "Edit"):
            return _result(
                "block",
                "Autonomous Write/Edit requires JARVIS_WORKTREE_ROOT to be set"
            )
        return None

    if tool not in ("Read", "Write", "Edit"):
        return None

    file_path = str(inp.get("file_path", "") or "")
    if not file_path:
        return None

    # Normalize paths for comparison; use is_relative_to (Python 3.9+) to
    # avoid the epdev/epdev_evil prefix-collision false-pass.
    try:
        resolved = Path(file_path).resolve()
        wt_resolved = Path(worktree_root).resolve()
        contained = resolved.is_relative_to(wt_resolved)
    except (OSError, ValueError):
        return _result("block", f"Cannot resolve path for containment check: {file_path}")

    if not contained:
        return _result(
            "block",
            f"Autonomous worker file access blocked: path escapes worktree. "
            f"Allowed root: {worktree_root}. Blocked: {tool} {file_path}"
        )

    return None


def _remap_worktree_path(filepath: str) -> str | None:
    """If filepath is in a git worktree, return equivalent main-repo path.

    Hooks run from the main repo -- the main repo path guard uses REPO_ROOT
    anchored to the main repo.  When overnight sessions run in a worktree,
    writes target the worktree path which the main-repo guard doesn't know
    about.  This remaps the worktree path to its main-repo equivalent so
    validate_write_path sees a path it can authorise.
    """
    p = Path(filepath).resolve()
    for parent in [p] + list(p.parents):
        git_path = parent / ".git"
        if git_path.is_file():
            try:
                text = git_path.read_text().strip()
                if text.startswith("gitdir:"):
                    gitdir_str = text.split(":", 1)[1].strip()
                    gitdir = Path(gitdir_str).resolve()
                    # gitdir = <main>/.git/worktrees/<name>
                    main_repo = gitdir.parent.parent.parent
                    if main_repo.is_dir():
                        rel = p.relative_to(parent)
                        return str(main_repo / rel)
            except (OSError, ValueError):
                pass
            break
        elif git_path.is_dir():
            break
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

    # Remap worktree paths to main-repo equivalents before validating.
    # Hooks run from main repo; its path guard expects main-repo paths.
    remapped = _remap_worktree_path(file_path)
    check_path = remapped if remapped is not None else file_path

    try:
        validate_write_path(check_path, dimension=dimension)
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

    # Accept both canonical Claude Code hook schema (tool_name/tool_input)
    # and legacy (tool/input) for any older callers or tests.
    tool = data.get("tool_name") or data.get("tool", "")
    inp = data.get("tool_input") or data.get("input") or {}
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

    # Glob/Grep secret-path + containment checks
    if tool in ("Glob", "Grep"):
        target = str(inp.get("path") or inp.get("pattern") or "")
        if target and _is_secret_path(target):
            print(json.dumps(_result("block", f"Glob/Grep on secret path forbidden: {target}")))
            return
        if target and os.environ.get("JARVIS_SESSION_TYPE") == "autonomous":
            wt = os.environ.get("JARVIS_WORKTREE_ROOT")
            if wt:
                try:
                    target_path = Path(target).resolve()
                    wt_path = Path(wt).resolve()
                    if not target_path.is_relative_to(wt_path):
                        print(json.dumps(_result("block", f"Glob/Grep outside worktree: {target}")))
                        return
                except (ValueError, OSError):
                    pass
        print(json.dumps(_result("allow")))
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
