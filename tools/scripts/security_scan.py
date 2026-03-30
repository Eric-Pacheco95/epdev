#!/usr/bin/env python3
"""Deterministic security scanner -- structured JSON output for /security-audit.

Performs all checks that do NOT require LLM judgment:
1. Secret pattern scanning across tracked files (reuses secret_scanner.py)
2. .gitignore completeness verification
3. Tracked personal content detection (git ls-files)
4. Required security file existence checks

The LLM skill triages findings: severity, false positives, remediation.

Usage:
    python tools/scripts/security_scan.py              # JSON to stdout
    python tools/scripts/security_scan.py --pretty     # indented JSON
    python tools/scripts/security_scan.py --file       # also write to data/security_scan_latest.json

Output contract: tools/schemas/security_scan.v1.json
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1.0.0"
OUTPUT_FILE = REPO_ROOT / "data" / "security_scan_latest.json"

# Add repo root to path for imports
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from security.validators.secret_scanner import (
    SECRET_PATTERNS,
    line_has_secret,
    load_gitignore_patterns,
    path_matches_gitignore,
)

# Personal content paths that must NOT be tracked in git
PERSONAL_CONTENT_GLOBS = [
    "memory/work/telos/*.md",
    "memory/learning/signals/**",
    "memory/learning/failures/**",
    "memory/learning/synthesis/**",
    "history/decisions/**",
    "history/changes/**",
    "history/security/**",
]

# Directories to check exist (not the files inside, just the structure)
PERSONAL_CONTENT_DIRS = [
    "memory/learning/signals",
    "memory/learning/failures",
    "memory/learning/synthesis",
    "history/decisions",
    "history/changes",
    "history/security",
]

# Required security files that must exist
REQUIRED_FILES = [
    "security/constitutional-rules.md",
    "security/validators/validate_tool_use.py",
    "security/validators/secret_scanner.py",
    ".gitignore",
]

# Sensitive paths that .gitignore must cover (at least one pattern per directory)
# Uses *.md globs because gitignore covers content files, not the dirs themselves
REQUIRED_GITIGNORE_PATTERNS = [
    ".env",
    "*.pem",
    "*.key",
    "memory/learning/signals/*.md",
    "memory/learning/failures/*.md",
    "memory/learning/synthesis/*.md",
    "history/decisions/*.md",
    "history/changes/*.md",
    "history/security/*.md",
    "history/events/",
    "data/",
]


def scan_secrets() -> list[dict]:
    """Scan tracked files for secret patterns. Returns findings (no actual values)."""
    findings = []
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached"],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return findings

        tracked_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

        for rel_path in tracked_files:
            full_path = REPO_ROOT / rel_path
            if not full_path.is_file():
                continue
            # Skip binary-ish files
            if full_path.suffix in (".png", ".jpg", ".ico", ".woff", ".woff2", ".ttf",
                                     ".eot", ".gif", ".bmp", ".zip", ".gz", ".tar",
                                     ".exe", ".dll", ".so", ".pyc", ".pptx", ".xlsx"):
                continue
            try:
                text = full_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for line_num, line in enumerate(text.splitlines(), start=1):
                found, pattern_name = line_has_secret(line)
                if found and pattern_name:
                    findings.append({
                        "check": "secret_pattern",
                        "file": rel_path,
                        "line": line_num,
                        "pattern": pattern_name,
                        # Never include the actual value
                    })
    except (subprocess.TimeoutExpired, OSError):
        pass
    return findings


def scan_gitignore_completeness() -> list[dict]:
    """Check that .gitignore covers required sensitive patterns."""
    findings = []
    gitignore_path = REPO_ROOT / ".gitignore"
    if not gitignore_path.is_file():
        findings.append({
            "check": "gitignore_missing",
            "file": ".gitignore",
            "detail": ".gitignore file does not exist",
        })
        return findings

    content = gitignore_path.read_text(encoding="utf-8", errors="replace")
    patterns = load_gitignore_patterns(gitignore_path)

    for required in REQUIRED_GITIGNORE_PATTERNS:
        # Check if the pattern or a parent pattern covers it
        covered = False
        clean = required.rstrip("/")
        for pat in patterns:
            pat_clean = pat.rstrip("/")
            if pat_clean == clean:
                covered = True
                break
            # Check if a parent dir pattern covers it (e.g., "data" covers "data/")
            if clean.startswith(pat_clean + "/") or clean.startswith(pat_clean):
                covered = True
                break
            # Check glob match
            if path_matches_gitignore(clean, [pat]):
                covered = True
                break
        if not covered:
            findings.append({
                "check": "gitignore_gap",
                "pattern": required,
                "detail": f"Required pattern '{required}' not covered by .gitignore",
            })
    return findings


def scan_tracked_personal_content() -> list[dict]:
    """Check for personal content files tracked in git."""
    findings = []
    try:
        # Check specific directories
        dirs_to_check = ["memory/", "history/"]
        result = subprocess.run(
            ["git", "ls-files", "--cached"] + dirs_to_check,
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return findings

        tracked = [f.strip() for f in result.stdout.splitlines() if f.strip()]

        # Files that are OK to track (infrastructure, not personal content)
        ok_patterns = [
            ".gitkeep",
            ".gitignore",
            "README.md",
            "memory/work/harness-foundation/",  # PRDs are tracked
        ]

        for f in tracked:
            # Skip infrastructure files
            if any(f.endswith(p) or p in f for p in ok_patterns):
                continue

            # Check against personal content directories
            is_personal = False
            for pdir in PERSONAL_CONTENT_DIRS:
                if f.startswith(pdir + "/"):
                    is_personal = True
                    break

            # Also check TELOS files (except README)
            if f.startswith("memory/work/telos/") and not f.endswith("README.md"):
                is_personal = True

            if is_personal:
                findings.append({
                    "check": "tracked_personal_content",
                    "file": f,
                    "detail": f"Personal content file '{f}' is tracked in git",
                })
    except (subprocess.TimeoutExpired, OSError):
        pass
    return findings


def scan_required_files() -> list[dict]:
    """Check that required security files exist."""
    findings = []
    for rel_path in REQUIRED_FILES:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            findings.append({
                "check": "required_file_missing",
                "file": rel_path,
                "detail": f"Required security file '{rel_path}' does not exist",
            })
    return findings


def scan_settings_permissions() -> list[dict]:
    """Check settings.json for overly permissive configurations."""
    findings = []
    settings_path = REPO_ROOT / ".claude" / "settings.json"
    if not settings_path.is_file():
        return findings

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        allow_list = settings.get("permissions", {}).get("allow", [])

        # Check for dangerous MCP wildcards on mutation-capable servers
        mutation_servers = ["Slack", "Notion", "google-calendar", "google-drive"]
        for entry in allow_list:
            if not isinstance(entry, str):
                continue
            for server in mutation_servers:
                if f"mcp__{server}__*" in entry or f"mcp__claude_ai_{server}__*" in entry:
                    findings.append({
                        "check": "permissive_mcp_wildcard",
                        "setting": entry,
                        "detail": f"Wildcard permission on mutation-capable server '{server}'",
                    })
    except (OSError, json.JSONDecodeError):
        pass
    return findings


def collect_git_hash() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Deterministic security scanner")
    parser.add_argument("--file", action="store_true", help="Also write to data/security_scan_latest.json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    start_time = time.time()
    errors: list[str] = []
    all_findings: list[dict] = []

    # Run all scan passes
    scanners = [
        ("secret_patterns", scan_secrets),
        ("gitignore_completeness", scan_gitignore_completeness),
        ("tracked_personal_content", scan_tracked_personal_content),
        ("required_files", scan_required_files),
        ("settings_permissions", scan_settings_permissions),
    ]

    checks_run = []
    for name, scanner in scanners:
        try:
            findings = scanner()
            all_findings.extend(findings)
            checks_run.append(name)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    elapsed_ms = round((time.time() - start_time) * 1000)

    # Summary counts by check type
    by_check = {}
    for f in all_findings:
        check = f.get("check", "unknown")
        by_check[check] = by_check.get(check, 0) + 1

    output = {
        "_schema_version": SCHEMA_VERSION,
        "_provenance": {
            "script": "tools/scripts/security_scan.py",
            "git_hash": collect_git_hash(),
            "checks_run": checks_run,
            "execution_time_ms": elapsed_ms,
            "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "findings": all_findings,
        "summary": {
            "total_findings": len(all_findings),
            "by_check": by_check,
        },
        "errors": errors,
    }

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, indent=indent, ensure_ascii=True)

    print(json_str)

    if args.file:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json_str, encoding="utf-8")
        print(f"Written to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
