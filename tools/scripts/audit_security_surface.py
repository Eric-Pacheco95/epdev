#!/usr/bin/env python3
"""audit_security_surface.py -- Read-only scanner of validate_tool_use.py.

Emits security/validators/AUDIT_SURFACE.md listing every guard function,
protected path, and blocked pattern with its rationale.

Usage:
    python tools/scripts/audit_security_surface.py          # write AUDIT_SURFACE.md
    python tools/scripts/audit_security_surface.py --print  # print to stdout only

Outputs:
    security/validators/AUDIT_SURFACE.md  -- generated audit surface doc
"""

from __future__ import annotations

import ast
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_FILE = REPO_ROOT / "security" / "validators" / "validate_tool_use.py"
OUTPUT_FILE = REPO_ROOT / "security" / "validators" / "AUDIT_SURFACE.md"


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_guard_functions(source: str) -> list[dict]:
    """Extract all _blocked_* / _protected_* / _check_* functions with their docstrings."""
    tree = ast.parse(source)
    guards = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = node.name
        if not (name.startswith("_blocked_") or name.startswith("_protected_")
                or name.startswith("_check_") or name.startswith("_inline_")
                or name.startswith("_system_") or name.startswith("_remote_")
                or name.startswith("_bash_")):
            continue
        doc = ast.get_docstring(node) or ""
        guards.append({"name": name, "doc": doc, "lineno": node.lineno})
    return sorted(guards, key=lambda g: g["lineno"])


def _extract_constants(source: str) -> list[dict]:
    """Extract named regex / list constants that define blocked patterns."""
    patterns = []

    # INJECTION_SUBSTRINGS
    m = re.search(r"INJECTION_SUBSTRINGS\s*=\s*\((.*?)\)", source, re.DOTALL)
    if m:
        items = re.findall(r'"([^"]+)"', m.group(1))
        patterns.append({
            "name": "INJECTION_SUBSTRINGS",
            "type": "string list",
            "values": items,
            "desc": "Prompt injection / instruction manipulation strings",
        })

    # FORK_BOMB_RE
    m = re.search(r"FORK_BOMB_RE\s*=\s*re\.compile\(r?([\"'])(.+?)\1", source)
    if m:
        patterns.append({
            "name": "FORK_BOMB_RE",
            "type": "regex",
            "values": [m.group(2)],
            "desc": "Fork bomb pattern: :() { :|:& };",
        })

    # DISK_DANGER
    m = re.search(r"DISK_DANGER\s*=\s*re\.compile\(\s*r?([\"'])(.+?)\1", source, re.DOTALL)
    if m:
        patterns.append({
            "name": "DISK_DANGER",
            "type": "regex",
            "values": [m.group(2).replace("\n", " ")],
            "desc": "Disk format / partition commands (mkfs, dd, fdisk, diskpart)",
        })

    # PATH_TRAVERSAL_SENSITIVE
    m = re.search(r"PATH_TRAVERSAL_SENSITIVE\s*=\s*re\.compile\(\s*r?([\"'])(.+?)\1", source, re.DOTALL)
    if m:
        patterns.append({
            "name": "PATH_TRAVERSAL_SENSITIVE",
            "type": "regex",
            "values": [m.group(2).replace("\n", " ")],
            "desc": "Path traversal to sensitive directories (etc, passwd, ssh, root)",
        })

    return patterns


def _extract_protected_path_patterns(source: str) -> list[str]:
    """Extract the guarded path patterns from _protected_path()."""
    # Find the function body and pull out the re.search patterns
    fn_match = re.search(
        r"def _protected_path\(cmd.*?\n(.*?)(?=\ndef |\Z)", source, re.DOTALL
    )
    if not fn_match:
        return []
    body = fn_match.group(1)
    raw = re.findall(r'r"([^"]+)"', body)
    return raw


def _extract_autonomous_guards(source: str) -> list[dict]:
    """Summarize the autonomous-session-only guard functions."""
    guards = []
    for fn, desc in [
        ("_check_autonomous_telos_write", "Write/Edit to TELOS, context_profiles, research_topics, producers, settings.json, CLAUDE.md (autonomous only)"),
        ("_check_autonomous_git_push", "ALL git push commands (autonomous only)"),
        ("_check_autonomous_read_secrets", "Read tool on .env, .ssh/, .aws/, .pem, .key, credentials.json (autonomous only)"),
        ("_check_autonomous_file_containment", "Read/Write/Edit outside JARVIS_WORKTREE_ROOT (autonomous only, when worktree root is set)"),
        ("_check_overnight_path_scope", "Write/Edit outside dimension-scoped allowed dirs during overnight runs (JARVIS_OVERNIGHT_DIMENSION)"),
    ]:
        if fn in source:
            guards.append({"name": fn, "desc": desc})
    return guards


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(source: str) -> str:
    today = date.today().isoformat()
    guards = _extract_guard_functions(source)
    constants = _extract_constants(source)
    auto_guards = _extract_autonomous_guards(source)
    protected_paths = _extract_protected_path_patterns(source)

    lines = [
        f"# Security Audit Surface",
        f"",
        f"> Auto-generated by `tools/scripts/audit_security_surface.py` on {today}.",
        f"> Source: `security/validators/validate_tool_use.py`",
        f"> **Do not edit manually** — re-run the script to refresh.",
        f"",
        f"## Summary",
        f"",
        f"| Category | Count |",
        f"|----------|-------|",
        f"| Guard functions | {len(guards)} |",
        f"| Blocked pattern constants | {len(constants)} |",
        f"| Autonomous-only guards | {len(auto_guards)} |",
        f"| Protected path patterns | {len(protected_paths)} |",
        f"",
    ]

    # --- Guard functions ---
    lines += [
        f"## Guard Functions",
        f"",
        f"These functions are called by `validate_bash_command()` or the tool-level validator.",
        f"",
    ]
    for g in guards:
        lines.append(f"### `{g['name']}` (line {g['lineno']})")
        if g["doc"]:
            lines.append(f"")
            lines.append(f"{g['doc']}")
        lines.append(f"")

    # --- Constants ---
    lines += [
        f"## Blocked Pattern Constants",
        f"",
    ]
    for c in constants:
        lines.append(f"### `{c['name']}` ({c['type']})")
        lines.append(f"")
        lines.append(f"**Purpose:** {c['desc']}")
        lines.append(f"")
        if c["type"] == "string list":
            for v in c["values"]:
                lines.append(f"- `{v}`")
        else:
            for v in c["values"]:
                lines.append(f"```")
                lines.append(v)
                lines.append(f"```")
        lines.append(f"")

    # --- Protected paths ---
    lines += [
        f"## Protected Path Patterns (`_protected_path`)",
        f"",
        f"These regex patterns in `_protected_path()` cause a block when matched in any Bash command:",
        f"",
    ]
    for p in protected_paths:
        lines.append(f"- `{p}`")
    lines.append(f"")

    # --- Autonomous guards ---
    lines += [
        f"## Autonomous-Session-Only Guards",
        f"",
        f"These guards fire only when `JARVIS_SESSION_TYPE=autonomous`.",
        f"Interactive sessions rely on operator judgment.",
        f"",
    ]
    for g in auto_guards:
        lines.append(f"### `{g['name']}`")
        lines.append(f"")
        lines.append(f"{g['desc']}")
        lines.append(f"")

    lines += [
        f"## Validation Order in `validate_bash_command()`",
        f"",
        f"1. `_bash_writes_telos` — TELOS write via redirect/tee/cp (autonomous only)",
        f"2. Fork bomb regex (`FORK_BOMB_RE`)",
        f"3. `_blocked_rm_rf` — recursive delete patterns",
        f"4. `_blocked_git_destructive` — git reset --hard, checkout --, clean -f, branch -D, restore, commit --amend, show >",
        f"5. `_inline_script_destructive` — python/node/bash -c with dangerous calls",
        f"6. `_blocked_git_force_main` — git push --force to main/master",
        f"7. `--no-verify` hook bypass",
        f"8. `DISK_DANGER` — mkfs, dd, fdisk, diskpart",
        f"9. `_system_paths_write` — writes to /etc or /boot",
        f"10. `_protected_path` — .ssh/, .env, .pem, .key, credentials, secrets",
        f"11. `PATH_TRAVERSAL_SENSITIVE` — ../etc/passwd, ../ssh etc.",
        f"12. `INJECTION_SUBSTRINGS` — prompt injection strings",
        f"13. `_remote_pipe_shell` — curl/wget | bash",
        f"14. `line_has_secret` — secret pattern scanner (API keys, tokens)",
        f"",
        f"**Tool-level guards** (run before `validate_bash_command`):",
        f"",
        f"1. `_check_autonomous_telos_write` — Write/Edit to protected paths",
        f"2. `_check_overnight_path_scope` — dimension-scoped writes for overnight",
        f"3. `_check_autonomous_read_secrets` — Read on secret files",
        f"4. `_check_autonomous_file_containment` — file outside worktree",
        f"",
        f"---",
        f"*Re-generate: `python tools/scripts/audit_security_surface.py`*",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    source = VALIDATOR_FILE.read_text(encoding="utf-8")
    report = build_report(source)

    if "--print" in sys.argv:
        print(report)
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"Written: {OUTPUT_FILE.relative_to(REPO_ROOT)}")

    # Summary line
    lines = report.splitlines()
    for line in lines:
        if line.startswith("| Guard functions"):
            print(f"  {line}")
        elif line.startswith("| Blocked"):
            print(f"  {line}")
        elif line.startswith("| Autonomous"):
            print(f"  {line}")
        elif line.startswith("| Protected"):
            print(f"  {line}")


if __name__ == "__main__":
    main()
