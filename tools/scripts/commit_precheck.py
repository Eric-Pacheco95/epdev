#!/usr/bin/env python3
"""Commit pre-check -- deterministic staged file analysis.

Deterministic CLI tool for the /commit skill. Handles everything that
doesn't require LLM judgment: staged file inventory, secret detection,
diff stats, file type classification.

Usage:
    python tools/scripts/commit_precheck.py                # table summary
    python tools/scripts/commit_precheck.py --json         # JSON output
    python tools/scripts/commit_precheck.py --json --pretty
    python tools/scripts/commit_precheck.py --strict       # exit 1 if secrets found
    python tools/scripts/commit_precheck.py --diff-only    # just show diff stats

Output: Structured pre-commit report. Zero LLM tokens consumed.
The LLM only needs to: analyze the diff for commit type + write the message.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Secret patterns (subset of security_scan.py patterns for speed)
SECRET_PATTERNS = [
    (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "API key"),
    (r"(?:secret|password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Secret/password"),
    (r"(?:token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Token"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI/Anthropic key"),
    (r"xoxb-[A-Za-z0-9\-]+", "Slack bot token"),
    (r"xoxp-[A-Za-z0-9\-]+", "Slack user token"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub PAT"),
    (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "Private key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
]

# File types that should never be committed
DANGEROUS_EXTENSIONS = {
    ".env", ".pem", ".key", ".p12", ".pfx", ".jks",
    ".credentials", ".keystore",
}

DANGEROUS_FILENAMES = {
    ".env", ".env.local", ".env.production", "credentials.json",
    "service-account.json", "id_rsa", "id_ed25519",
}

# File type classification
FILE_CATEGORIES = {
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h"},
    "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"},
    "docs": {".md", ".txt", ".rst", ".adoc"},
    "skill": set(),  # detected by path
    "test": set(),   # detected by path
    "script": {".sh", ".bat", ".ps1", ".cmd"},
    "data": {".csv", ".jsonl", ".sql", ".db", ".sqlite"},
}


def _sanitize_ascii(text: str) -> str:
    """Replace common Unicode chars with ASCII for Windows cp1252."""
    replacements = {
        "\u2192": "->", "\u2014": "--", "\u2013": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)
    return text


def run_git(args: list[str]) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT), timeout=15,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_staged_files() -> list[str]:
    """Get list of staged files."""
    output = run_git(["diff", "--cached", "--name-only"])
    if not output:
        return []
    return [f for f in output.splitlines() if f.strip()]


def get_unstaged_files() -> list[str]:
    """Get list of modified but unstaged files."""
    output = run_git(["diff", "--name-only"])
    if not output:
        return []
    return [f for f in output.splitlines() if f.strip()]


def get_untracked_files() -> list[str]:
    """Get list of untracked files (not using -uall for safety)."""
    output = run_git(["status", "--porcelain"])
    if not output:
        return []
    untracked = []
    for line in output.splitlines():
        if line.startswith("?? "):
            untracked.append(line[3:].strip().strip('"'))
    return untracked


def get_diff_stats() -> dict:
    """Get diff statistics for staged changes."""
    output = run_git(["diff", "--cached", "--stat"])
    numstat = run_git(["diff", "--cached", "--numstat"])

    total_added = 0
    total_removed = 0
    file_stats = []

    for line in (numstat or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0] != "-" else 0
            removed = int(parts[1]) if parts[1] != "-" else 0
            total_added += added
            total_removed += removed
            file_stats.append({
                "file": parts[2],
                "added": added,
                "removed": removed,
            })

    return {
        "total_added": total_added,
        "total_removed": total_removed,
        "net_change": total_added - total_removed,
        "files_changed": len(file_stats),
        "files": file_stats,
    }


def classify_file(filepath: str) -> str:
    """Classify a file by category."""
    p = Path(filepath)
    ext = p.suffix.lower()
    name = p.name.lower()

    # Path-based classification first
    if "test" in str(p).lower() or name.startswith("test_"):
        return "test"
    if ".claude/skills/" in filepath.replace("\\", "/"):
        return "skill"
    if "tools/scripts/" in filepath.replace("\\", "/"):
        return "script"

    # Extension-based
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category

    return "other"


def check_secrets_in_diff() -> list[dict]:
    """Scan staged diff for secret patterns."""
    diff = run_git(["diff", "--cached"])
    if not diff:
        return []

    findings = []
    current_file = ""

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added_line = line[1:]
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, added_line, re.IGNORECASE):
                    # Don't flag if it's clearly a variable reference or placeholder
                    if any(
                        placeholder in added_line.lower()
                        for placeholder in [
                            "xxx", "your_", "example", "placeholder",
                            "changeme", "${", "process.env", "os.environ",
                            "getenv",
                        ]
                    ):
                        continue
                    findings.append({
                        "file": current_file,
                        "type": label,
                        "line_preview": added_line[:80].strip(),
                    })

    return findings


def check_dangerous_files(staged: list[str]) -> list[dict]:
    """Check if any staged files are dangerous types."""
    warnings = []
    for f in staged:
        p = Path(f)
        if p.suffix.lower() in DANGEROUS_EXTENSIONS:
            warnings.append({"file": f, "reason": f"Dangerous extension: {p.suffix}"})
        if p.name.lower() in DANGEROUS_FILENAMES:
            warnings.append({"file": f, "reason": f"Sensitive filename: {p.name}"})
    return warnings


def get_recent_commits(n: int = 5) -> list[dict]:
    """Get recent commit messages for style reference."""
    output = run_git(["log", f"-{n}", "--format=%H|%s"])
    if not output:
        return []
    commits = []
    for line in output.splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0][:8], "message": parts[1]})
    return commits


def get_current_branch() -> str:
    """Get current branch name."""
    return run_git(["branch", "--show-current"]) or "unknown"


def run_precheck(strict: bool = False, diff_only: bool = False) -> dict:
    """Run all pre-commit checks."""
    staged = get_staged_files()
    report = {
        "branch": get_current_branch(),
        "staged_count": len(staged),
        "staged_files": staged,
    }

    if not staged:
        report["status"] = "nothing_staged"
        report["unstaged"] = get_unstaged_files()
        report["untracked"] = get_untracked_files()
        return report

    # Diff stats
    report["diff_stats"] = get_diff_stats()

    if diff_only:
        return report

    # File classification
    categories = {}
    for f in staged:
        cat = classify_file(f)
        categories.setdefault(cat, []).append(f)
    report["categories"] = {k: len(v) for k, v in categories.items()}
    report["categories_detail"] = categories

    # Secret detection
    secrets = check_secrets_in_diff()
    report["secrets"] = secrets
    report["secrets_found"] = len(secrets) > 0

    # Dangerous files
    dangerous = check_dangerous_files(staged)
    report["dangerous_files"] = dangerous

    # Recent commits for style reference
    report["recent_commits"] = get_recent_commits()

    # Overall status
    issues = []
    if secrets:
        issues.append(f"{len(secrets)} potential secret(s) in staged diff")
    if dangerous:
        issues.append(f"{len(dangerous)} dangerous file(s) staged")

    report["issues"] = issues
    report["status"] = "blocked" if issues else "ready"

    return report


def format_table(report: dict) -> str:
    """Format as ASCII table."""
    lines = []

    if report.get("status") == "nothing_staged":
        lines.append("Nothing staged for commit.")
        lines.append("")
        if report.get("unstaged"):
            lines.append(f"  Unstaged changes: {len(report['unstaged'])} files")
            for f in report["unstaged"][:10]:
                lines.append(f"    M {f}")
        if report.get("untracked"):
            lines.append(f"  Untracked files: {len(report['untracked'])} files")
            for f in report["untracked"][:10]:
                lines.append(f"    ? {f}")
        return "\n".join(lines)

    branch = report["branch"]
    stats = report.get("diff_stats", {})
    lines.append(f"Branch: {branch} | {report['staged_count']} files staged | +{stats.get('total_added', 0)} -{stats.get('total_removed', 0)} lines")
    lines.append("")

    # Categories
    cats = report.get("categories", {})
    if cats:
        cat_parts = [f"{k}: {v}" for k, v in sorted(cats.items()) if v > 0]
        lines.append(f"  File types: {', '.join(cat_parts)}")
        lines.append("")

    # Staged files with diff stats
    for fs in stats.get("files", []):
        lines.append(f"    +{fs['added']:<4} -{fs['removed']:<4} {fs['file']}")
    lines.append("")

    # Secrets
    if report.get("secrets"):
        lines.append("  !! SECRETS DETECTED:")
        for s in report["secrets"]:
            lines.append(f"    [{s['type']}] {s['file']}: {s['line_preview'][:50]}...")
        lines.append("")

    # Dangerous files
    if report.get("dangerous_files"):
        lines.append("  !! DANGEROUS FILES:")
        for d in report["dangerous_files"]:
            lines.append(f"    {d['file']} -- {d['reason']}")
        lines.append("")

    # Recent commits for style
    if report.get("recent_commits"):
        lines.append("  Recent commit style:")
        for c in report["recent_commits"][:3]:
            lines.append(f"    {c['hash']} {c['message'][:60]}")
        lines.append("")

    # Status
    status = report.get("status", "unknown")
    if status == "ready":
        lines.append("  Status: READY -- no issues found")
    elif status == "blocked":
        lines.append("  Status: BLOCKED")
        for issue in report.get("issues", []):
            lines.append(f"    !! {issue}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-commit deterministic checks"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if secrets found")
    parser.add_argument("--diff-only", action="store_true", help="Only show diff stats")

    args = parser.parse_args()

    report = run_precheck(strict=args.strict, diff_only=args.diff_only)

    if args.json:
        indent = 2 if args.pretty else None
        print(_sanitize_ascii(json.dumps(report, indent=indent, default=str)))
    else:
        print(_sanitize_ascii(format_table(report)))

    if args.strict and report.get("secrets_found"):
        sys.exit(1)


if __name__ == "__main__":
    main()
