#!/usr/bin/env python3
"""Code Prescan -- deterministic code quality gate for /review-code.

Runs ruff (linting) and security_scan.py (secrets/config) as sub-tools,
producing a unified JSON report with per-tool status fields.

The LLM reviewer receives structured prescan results so it can focus
judgment on non-mechanical issues (logic errors, threat modeling, etc.).

Usage:
    python tools/scripts/code_prescan.py --path PATH              # table output
    python tools/scripts/code_prescan.py --path PATH --json       # JSON output
    python tools/scripts/code_prescan.py --path PATH --pretty     # indented JSON

Exit codes:
    0 = all tools ran and found 0 issues
    1 = one or more tools found issues, or a tool failed

Tool status values:
    pass             = tool ran, 0 findings
    fail             = tool ran, 1+ findings
    tool_unavailable = tool binary not found
    timeout          = tool exceeded 60s limit
    error            = tool crashed or returned invalid output

Output: Structured prescan report. Zero LLM tokens consumed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_VERSION = "1.0.0"
TOOL_TIMEOUT = 60  # seconds per sub-tool


def _sanitize_ascii(text: str) -> str:
    """Replace common Unicode chars with ASCII equivalents for Windows cp1252."""
    replacements = {
        "\u2192": "->", "\u2014": "--", "\u2013": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "*", "\u00d7": "x",
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)
    return text


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


def run_ruff(scan_path: Path) -> dict:
    """Run ruff linter on the given path.

    Returns a tool result dict with status, findings, and metadata.
    """
    # Check if ruff is available
    ruff_path = shutil.which("ruff")
    if ruff_path is None:
        return {
            "tool": "ruff",
            "status": "tool_unavailable",
            "message": "ruff not found in PATH",
        }

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", str(scan_path)],
            capture_output=True, text=True, timeout=TOOL_TIMEOUT,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "tool": "ruff",
            "status": "timeout",
            "message": f"ruff exceeded {TOOL_TIMEOUT}s timeout",
        }
    except OSError as e:
        return {
            "tool": "ruff",
            "status": "error",
            "message": f"Failed to execute ruff: {e}",
        }

    # Parse ruff JSON output
    findings = []
    try:
        if result.stdout.strip():
            raw = json.loads(result.stdout)
            for item in raw:
                findings.append({
                    "file": item.get("filename", ""),
                    "line": item.get("location", {}).get("row", 0),
                    "code": item.get("code", ""),
                    "message": item.get("message", ""),
                    "severity": _ruff_severity(item.get("code", "")),
                })
    except json.JSONDecodeError:
        return {
            "tool": "ruff",
            "status": "error",
            "message": "Failed to parse ruff JSON output",
            "raw_stderr": result.stderr[:500] if result.stderr else "",
        }

    # Get ruff version
    try:
        ver_result = subprocess.run(
            ["ruff", "version"], capture_output=True, text=True, timeout=5,
        )
        ver_str = ver_result.stdout.strip() if ver_result.returncode == 0 else "unknown"
        # ruff version outputs "ruff 0.15.8 (...)" -- extract just the version
        ruff_version = ver_str.replace("ruff ", "").split(" ")[0] if ver_str != "unknown" else "unknown"
    except (subprocess.TimeoutExpired, OSError):
        ruff_version = "unknown"

    status = "pass" if len(findings) == 0 else "fail"
    return {
        "tool": "ruff",
        "version": ruff_version,
        "status": status,
        "finding_count": len(findings),
        "findings": findings,
    }


def _ruff_severity(code: str) -> str:
    """Map ruff rule code to severity level."""
    # Security-relevant rules are high severity
    security_prefixes = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    if any(code.startswith(p) for p in security_prefixes):
        return "high"
    # Error codes are medium
    if code.startswith("E") or code.startswith("F"):
        return "medium"
    # Everything else is low
    return "low"


def run_security_scan() -> dict:
    """Run security_scan.py and capture its JSON output.

    Returns a tool result dict with status and findings summary.
    """
    script_path = REPO_ROOT / "tools" / "scripts" / "security_scan.py"
    if not script_path.exists():
        return {
            "tool": "security_scan",
            "status": "tool_unavailable",
            "message": f"security_scan.py not found at {script_path}",
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--filter-fp"],
            capture_output=True, text=True, timeout=TOOL_TIMEOUT,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "tool": "security_scan",
            "status": "timeout",
            "message": f"security_scan.py exceeded {TOOL_TIMEOUT}s timeout",
        }
    except OSError as e:
        return {
            "tool": "security_scan",
            "status": "error",
            "message": f"Failed to execute security_scan.py: {e}",
        }

    # Parse security scan JSON
    try:
        scan_output = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "tool": "security_scan",
            "status": "error",
            "message": "Failed to parse security_scan.py JSON output",
            "raw_stderr": result.stderr[:500] if result.stderr else "",
        }

    # Validate schema version
    schema_ver = scan_output.get("_schema_version", "")
    if schema_ver != "1.0.0":
        return {
            "tool": "security_scan",
            "status": "error",
            "message": f"Schema version mismatch: expected 1.0.0, got {schema_ver}",
        }

    summary = scan_output.get("summary", {})
    real_findings = summary.get("real_findings", 0)
    errors = scan_output.get("errors", [])

    status = "pass"
    if real_findings > 0:
        status = "fail"
    elif errors:
        status = "partial"

    return {
        "tool": "security_scan",
        "version": schema_ver,
        "status": status,
        "finding_count": real_findings,
        "false_positives": summary.get("false_positives", 0),
        "scan_errors": errors,
        "findings": scan_output.get("findings", [])[:20],  # cap for output size
    }


def run_prescan(scan_path: Path) -> dict:
    """Run all prescan tools and produce unified report."""
    start_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Run tools
    ruff_result = run_ruff(scan_path)
    security_result = run_security_scan()

    elapsed_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - start_ms

    tools = [ruff_result, security_result]

    # Aggregate
    total_findings = sum(
        t.get("finding_count", 0) for t in tools
        if t["status"] in ("pass", "fail")
    )
    all_passed = all(
        t["status"] in ("pass", "tool_unavailable") for t in tools
    )
    any_findings = total_findings > 0

    # Overall: pass only if all tools ran clean
    if all_passed and not any_findings:
        overall = "pass"
    elif any_findings:
        overall = "fail"
    else:
        overall = "error"

    return {
        "_schema_version": "1.0.0",
        "_provenance": {
            "script": "tools/scripts/code_prescan.py",
            "version": SCRIPT_VERSION,
            "git_hash": collect_git_hash(),
            "execution_time_ms": elapsed_ms,
            "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scan_path": str(scan_path),
        },
        "overall_status": overall,
        "total_findings": total_findings,
        "tools": tools,
    }


def format_table(output: dict) -> str:
    """Format output as human-readable ASCII table."""
    lines = []
    lines.append(f"Code Prescan -- {output['_provenance']['scan_path']}")
    lines.append(f"Overall: {output['overall_status'].upper()} | {output['total_findings']} findings")
    lines.append("")

    for tool in output.get("tools", []):
        status = tool["status"].upper()
        name = tool["tool"]
        count = tool.get("finding_count", "-")
        version = tool.get("version", "")
        ver_str = f" v{version}" if version else ""

        lines.append(f"  [{status}] {name}{ver_str}: {count} findings")

        if tool["status"] == "tool_unavailable":
            lines.append(f"         {tool.get('message', '')}")
        elif tool["status"] == "timeout":
            lines.append(f"         {tool.get('message', '')}")
        elif tool["status"] == "error":
            lines.append(f"         ERROR: {tool.get('message', '')}")

        # Show first 5 findings if any
        for f in tool.get("findings", [])[:5]:
            if isinstance(f, dict):
                file_info = f.get("file", f.get("path", ""))
                line_info = f.get("line", "")
                msg = f.get("message", f.get("detail", ""))
                code = f.get("code", "")
                code_str = f" [{code}]" if code else ""
                lines.append(f"         {file_info}:{line_info}{code_str} {msg}")

        remaining = tool.get("finding_count", 0) - 5
        if remaining > 0:
            lines.append(f"         ... and {remaining} more")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Code Prescan -- deterministic quality gate")
    parser.add_argument("--path", type=str, required=True, help="Path to scan")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    scan_path = Path(args.path)
    if not scan_path.is_absolute():
        scan_path = REPO_ROOT / scan_path

    output = run_prescan(scan_path)

    if args.json or args.pretty:
        indent = 2 if args.pretty else None
        print(json.dumps(output, indent=indent, default=str))
    else:
        print(_sanitize_ascii(format_table(output)))

    sys.exit(0 if output["overall_status"] == "pass" else 1)


if __name__ == "__main__":
    main()
