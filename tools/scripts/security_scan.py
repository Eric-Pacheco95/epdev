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

from tools.scripts.lib.isc_templates import isc_security_scan_review

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


def run_defensive_tests() -> dict:
    """Run pytest tests/defensive/ and return structured results."""
    test_dir = REPO_ROOT / "tests" / "defensive"
    if not test_dir.exists():
        return {"status": "skipped", "reason": "tests/defensive/ not found", "passed": 0, "failed": 0}

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT),
        )
        # Parse pytest output
        output_lines = result.stdout.splitlines()
        passed = failed = errors = 0
        for line in output_lines:
            if " passed" in line:
                import re as _re
                m = _re.search(r"(\d+) passed", line)
                if m:
                    passed = int(m.group(1))
            if " failed" in line:
                import re as _re
                m = _re.search(r"(\d+) failed", line)
                if m:
                    failed = int(m.group(1))
            if " error" in line:
                import re as _re
                m = _re.search(r"(\d+) error", line)
                if m:
                    errors = int(m.group(1))

        return {
            "status": "pass" if result.returncode == 0 else "fail",
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "returncode": result.returncode,
            "output_tail": "\n".join(output_lines[-10:]),
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "passed": 0, "failed": 0, "errors": 0}
    except Exception as exc:
        return {"status": "error", "reason": str(exc), "passed": 0, "failed": 0}


# Known false positive patterns -- findings matching these are tagged but not removed
FALSE_POSITIVE_RULES = [
    # Test fixtures contain intentional secret patterns
    {"check": "secret_pattern", "path_contains": "tests/", "tag": "test_fixture"},
    # Example/template files
    {"check": "secret_pattern", "path_contains": "example", "tag": "example_file"},
    {"check": "secret_pattern", "path_contains": "template", "tag": "template_file"},
    # Fabric upstream patterns
    {"check": "secret_pattern", "path_contains": "fabric-upstream", "tag": "upstream_vendored"},
]


def apply_false_positive_filter(findings: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate findings into real and false positives. Returns (real, false_positives)."""
    real = []
    false_positives = []

    for f in findings:
        is_fp = False
        for rule in FALSE_POSITIVE_RULES:
            match = True
            if "check" in rule and f.get("check") != rule["check"]:
                match = False
            if "path_contains" in rule:
                file_path = f.get("file", "") or f.get("path", "")
                if rule["path_contains"] not in file_path:
                    match = False
            if match:
                f["false_positive"] = True
                f["fp_tag"] = rule["tag"]
                false_positives.append(f)
                is_fp = True
                break
        if not is_fp:
            real.append(f)

    return real, false_positives


def write_audit_log(output: dict, test_results: dict | None = None) -> str:
    """Write timestamped audit log to history/security/."""
    audit_dir = REPO_ROOT / "history" / "security"
    audit_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = f"{now.strftime('%Y-%m-%d')}_audit.md"
    filepath = audit_dir / filename

    total = output["summary"]["total_findings"]
    real_count = output["summary"].get("real_findings", total)
    fp_count = output["summary"].get("false_positives", 0)

    lines = [
        f"# Security Audit - {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"- Scanner: security_scan.py v{SCHEMA_VERSION}",
        f"- Git hash: {output['_provenance']['git_hash']}",
        f"- Total findings: {total} ({real_count} real, {fp_count} false positives)",
        f"- Execution time: {output['_provenance']['execution_time_ms']}ms",
        "",
    ]

    if test_results:
        status = test_results.get("status", "unknown")
        lines.append(f"## Defensive Tests: {status.upper()}")
        lines.append(f"- Passed: {test_results.get('passed', 0)}")
        lines.append(f"- Failed: {test_results.get('failed', 0)}")
        lines.append("")

    if output.get("real_findings"):
        lines.append("## Findings (Real)")
        for f in output["real_findings"]:
            check = f.get("check", "unknown")
            detail = f.get("detail", f.get("pattern", ""))
            file_ref = f.get("file", f.get("path", ""))
            lines.append(f"- [{check}] {file_ref}: {detail}")
        lines.append("")

    if not output.get("real_findings") and not output.get("errors"):
        lines.append("## Result: CLEAN")
        lines.append("No actionable findings.")

    content = "\n".join(lines) + "\n"

    # Append if file exists (multiple runs per day), otherwise create
    if filepath.exists():
        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write("\n---\n\n" + content)
    else:
        filepath.write_text(content, encoding="utf-8")

    return str(filepath)


def emit_backlog_rows(real_findings: list[dict]) -> int:
    """Inject one pending_review backlog row per (check, severity-class) group.

    Deduped per-day via routine_id so a daily scheduled scan does not flood
    the queue. Returns count of rows actually written (post-dedup).

    Never raises -- scan integrity must not depend on backlog availability.
    """
    if not real_findings:
        return 0
    try:
        from tools.scripts.lib.backlog import backlog_append
    except Exception:
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    by_check: dict[str, int] = {}
    for f in real_findings:
        key = f.get("check", "unknown")
        by_check[key] = by_check.get(key, 0) + 1

    written = 0
    for check, count in sorted(by_check.items()):
        task = {
            "description": (
                "[security_scan] %s: %d real finding(s) (%s)"
                % (check, count, today)
            ),
            "tier": 0,
            "autonomous_safe": False,
            "status": "pending_review",
            "priority": 1,
            "isc": isc_security_scan_review(),
            "skills": [],
            "source": "security-scan",
            "routine_id": "security_scan:%s:%s" % (check, today),
            "context_files": ["data/security_scan_latest.json"],
            "notes": (
                "Auto-injected by security_scan --emit-backlog. Review the "
                "full finding detail in data/security_scan_latest.json "
                "(run with --file to persist)."
            ),
        }
        try:
            if backlog_append(task) is not None:
                written += 1
        except Exception:
            continue
    return written


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Deterministic security scanner")
    parser.add_argument("--file", action="store_true", help="Also write to data/security_scan_latest.json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--run-tests", action="store_true", help="Also run pytest tests/defensive/")
    parser.add_argument("--audit-log", action="store_true", help="Write audit log to history/security/")
    parser.add_argument("--filter-fp", action="store_true", help="Apply false positive filter")
    parser.add_argument("--emit-backlog", action="store_true",
                        help="Inject one pending_review backlog row per (check, day) when real findings exist")
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

    # Apply false positive filter
    real_findings = all_findings
    fp_findings = []
    if args.filter_fp:
        real_findings, fp_findings = apply_false_positive_filter(all_findings)

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
            "real_findings": len(real_findings),
            "false_positives": len(fp_findings),
        },
        "errors": errors,
    }

    if args.filter_fp:
        output["real_findings"] = real_findings
        output["false_positive_findings"] = fp_findings

    # Run defensive tests
    test_results = None
    if args.run_tests:
        test_results = run_defensive_tests()
        output["defensive_tests"] = test_results

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, indent=indent, ensure_ascii=True)

    print(json_str)

    if args.file:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json_str, encoding="utf-8")
        print(f"Written to {OUTPUT_FILE}", file=sys.stderr)

    # Write audit log
    if args.audit_log:
        log_path = write_audit_log(output, test_results)
        print(f"Audit log: {log_path}", file=sys.stderr)

    # Inject into universal backlog if requested
    if args.emit_backlog:
        # Only emit for filtered real findings if --filter-fp was used;
        # otherwise emit for all findings.
        rows_written = emit_backlog_rows(
            real_findings if args.filter_fp else all_findings
        )
        print(f"Backlog rows injected: {rows_written}", file=sys.stderr)


if __name__ == "__main__":
    main()
