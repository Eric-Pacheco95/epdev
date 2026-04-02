#!/usr/bin/env python3
"""ISC Executor -- deterministic VERIFY phase execution engine.

Parses ISC criteria from a PRD file and dispatches each | Verify: method to
the appropriate handler. Emits a structured JSON report or ASCII markdown table.

Usage:
    python tools/scripts/isc_executor.py --prd PATH
    python tools/scripts/isc_executor.py --prd PATH --json
    python tools/scripts/isc_executor.py --prd PATH --skip-format-gate

Exit codes:
    0 = all non-MANUAL criteria PASS
    1 = one or more criteria FAIL
    2 = executor error (crash, timeout, parse failure)
    3 = MANUAL items present, no FAILs

Output: Structured verification report. Zero LLM tokens consumed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---- import shared utilities from isc_validator ----
# Add scripts dir to path so we can import from sibling script
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from isc_validator import parse_isc_items, _sanitize_ascii  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_VERSION = "1.0.0"

# ---- Secret scrubbing patterns ----
# Applied to all evidence strings before output. Order matters -- most specific first.
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"password\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"api_key\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"token\s*=\s*[A-Za-z0-9_\-\.]{16,}", re.IGNORECASE),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),  # long hex strings (tokens, hashes used as secrets)
]

RECOGNIZED_PREFIXES = ("grep:", "grep!:", "exist:", "read:", "test:", "schema:", "cli:", "review:")


def scrub_secrets(text: str) -> str:
    """Apply SECRET_PATTERNS substitution to remove common secret values."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def collect_git_hash() -> str:
    """Get current git commit hash (short)."""
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


# ---------------------------------------------------------------------------
# Verify handlers
# ---------------------------------------------------------------------------

def _resolve_path(raw: str) -> Path:
    """Resolve a path relative to REPO_ROOT if not absolute."""
    p = Path(raw.strip())
    if not p.is_absolute():
        return REPO_ROOT / p
    return p


def handle_grep(method_body: str, negate: bool = False) -> tuple[str, bool]:
    """Grep: pattern in filepath  OR  Grep: pattern (searches all .py files).

    Returns (evidence, passed).
    Grep  => PASS if match found.
    Grep! => PASS if ZERO matches found (negation, for anti-criteria).
    """
    # Try to parse "pattern in filepath"
    in_match = re.match(r"^(.+?)\s+in\s+(\S+)\s*$", method_body.strip(), re.IGNORECASE)
    if in_match:
        pattern_str = in_match.group(1).strip()
        filepath_str = in_match.group(2).strip()
        target_path = _resolve_path(filepath_str)
        if not target_path.exists():
            return f"File not found: {filepath_str}", False
        try:
            content = target_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Cannot read {filepath_str}: {e}", False
        try:
            match = re.search(pattern_str, content)
        except re.error as e:
            return f"Invalid regex '{pattern_str}': {e}", False
        found = match is not None
        if negate:
            passed = not found
            evidence = (
                f"Grep!: zero matches for '{pattern_str}' in {filepath_str} -- OK"
                if passed
                else f"Grep!: found match for '{pattern_str}' in {filepath_str} -- FAIL"
            )
        else:
            passed = found
            evidence = (
                f"Grep: found '{pattern_str}' in {filepath_str} at char {match.start()}"
                if passed
                else f"Grep: no match for '{pattern_str}' in {filepath_str}"
            )
        return scrub_secrets(evidence), passed
    else:
        # No "in filepath" -- search all .py files under repo
        pattern_str = method_body.strip()
        try:
            compiled = re.compile(pattern_str)
        except re.error as e:
            return f"Invalid regex '{pattern_str}': {e}", False
        matches = []
        for py_file in REPO_ROOT.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                if compiled.search(content):
                    matches.append(str(py_file.relative_to(REPO_ROOT)))
            except Exception:
                continue
        found = len(matches) > 0
        if negate:
            passed = not found
            evidence = (
                f"Grep!: zero matches for '{pattern_str}' across .py files -- OK"
                if passed
                else f"Grep!: found matches in: {', '.join(matches[:5])}"
            )
        else:
            passed = found
            evidence = (
                f"Grep: found '{pattern_str}' in: {', '.join(matches[:5])}"
                if passed
                else f"Grep: no match for '{pattern_str}' across .py files"
            )
        return scrub_secrets(evidence), passed


def handle_exist(method_body: str) -> tuple[str, bool]:
    """Exist: path -- PASS if file/dir exists."""
    target = _resolve_path(method_body.strip())
    exists = target.exists()
    if exists:
        kind = "directory" if target.is_dir() else "file"
        evidence = f"Exist: {kind} found at {method_body.strip()}"
    else:
        evidence = f"Exist: not found: {method_body.strip()}"
    return evidence, exists


def handle_read(method_body: str) -> tuple[str, bool]:
    """Read: filepath [contains "substring"] -- checks existence and optional content."""
    # Parse optional 'contains "..."' or contains '...'
    contains_match = re.match(
        r'^(\S+)\s+contains\s+["\'](.+)["\']$',
        method_body.strip(),
        re.IGNORECASE,
    )
    if contains_match:
        filepath_str = contains_match.group(1).strip()
        substring = contains_match.group(2).strip()
        target = _resolve_path(filepath_str)
        if not target.exists():
            return f"Read: file not found: {filepath_str}", False
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Read: cannot read {filepath_str}: {e}", False
        found = substring in content
        evidence = (
            f"Read: '{substring}' found in {filepath_str}"
            if found
            else f"Read: '{substring}' NOT found in {filepath_str}"
        )
        return scrub_secrets(evidence), found
    else:
        # Just existence check
        filepath_str = method_body.strip()
        target = _resolve_path(filepath_str)
        exists = target.exists()
        evidence = (
            f"Read: file exists: {filepath_str}"
            if exists
            else f"Read: file not found: {filepath_str}"
        )
        return evidence, exists


def handle_test(method_body: str) -> tuple[str, bool]:
    """Test: command -- PASS if exit code 0. 60-second timeout."""
    command = method_body.strip()
    # shell=True is required to run arbitrary test commands (pytest, python scripts, etc.).
    # CLI-type verify methods are intentionally blocked (routed to MANUAL) to prevent
    # AI-authored shell injection. Test-type is accepted risk -- ISC authors are responsible
    # for only using Test: with safe, idempotent commands. v2 will add an explicit allowlist.
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=60,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        stdout_tail = result.stdout.strip()[-300:] if result.stdout else ""
        stderr_tail = result.stderr.strip()[-200:] if result.stderr else ""
        passed = result.returncode == 0
        combined = " | ".join(filter(None, [stdout_tail, stderr_tail]))
        status = "exit 0 -- PASS" if passed else f"exit {result.returncode} -- FAIL"
        evidence = f"Test: `{command}` -> {status}"
        if combined:
            evidence += f" | output: {combined[:300]}"
        return scrub_secrets(evidence), passed
    except subprocess.TimeoutExpired as e:
        # Explicitly kill on Windows
        if e.process is not None:
            try:
                e.process.kill()
            except Exception:
                pass
        return f"Test: `{command}` timed out after 60s", False
    except Exception as exc:
        return f"Test: `{command}` error: {exc}", False


def handle_schema(method_body: str) -> tuple[str, bool]:
    """Schema: file.json .field [== value] -- field existence or equality check."""
    # Syntax: Schema: path/to/file.json .fieldname [== value]
    eq_match = re.match(
        r'^(\S+)\s+(\.\S+)\s*==\s*(.+)$',
        method_body.strip(),
    )
    field_match = re.match(
        r'^(\S+)\s+(\.\S+)\s*$',
        method_body.strip(),
    )

    if eq_match:
        filepath_str = eq_match.group(1).strip()
        field_path = eq_match.group(2).strip().lstrip(".")
        expected_val = eq_match.group(3).strip().strip('"\'')
    elif field_match:
        filepath_str = field_match.group(1).strip()
        field_path = field_match.group(2).strip().lstrip(".")
        expected_val = None
    else:
        return f"Schema: cannot parse syntax: '{method_body.strip()}'", False

    target = _resolve_path(filepath_str)
    if not target.exists():
        return f"Schema: file not found: {filepath_str}", False
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return f"Schema: invalid JSON in {filepath_str}: {e}", False
    except Exception as e:
        return f"Schema: cannot read {filepath_str}: {e}", False

    # Navigate dotted field path (e.g. "summary.pass" -> data["summary"]["pass"])
    keys = field_path.split(".")
    node = data
    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return f"Schema: field '.{field_path}' not found in {filepath_str}", False

    if expected_val is None:
        # Field existence only
        return f"Schema: field '.{field_path}' exists in {filepath_str} (value: {repr(node)[:60]})", True

    # Equality check -- compare as strings for simplicity
    actual_str = str(node)
    passed = actual_str == expected_val
    evidence = (
        f"Schema: .{field_path} == '{expected_val}' -- {'PASS' if passed else f'FAIL (got {actual_str!r})'}"
    )
    return scrub_secrets(evidence), passed


def handle_manual(method_body: str, prefix: str) -> tuple[str, str]:
    """Return MANUAL verdict with original instruction text."""
    instruction = f"{prefix}{method_body}".strip() if prefix else method_body.strip()
    return instruction, "MANUAL"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch(verify_method: str) -> tuple[str, str]:
    """Dispatch a verify method string to the correct handler.

    Returns (evidence, verdict) where verdict is PASS|FAIL|ERROR|MANUAL.
    """
    # Strip | model: <annotation> suffix -- /implement-prd adds these to ISC lines for subagent
    # routing (e.g. "| model: sonnet"). They are PRD metadata, not part of the verify command.
    raw = re.sub(r"\s*\|\s*model:\s*\S+\s*$", "", verify_method.strip(), flags=re.IGNORECASE)
    lower = raw.lower()

    if lower.startswith("grep!:"):
        body = raw[6:].strip()
        evidence, passed = handle_grep(body, negate=True)
        return evidence, "PASS" if passed else "FAIL"

    if lower.startswith("grep:"):
        body = raw[5:].strip()
        evidence, passed = handle_grep(body, negate=False)
        return evidence, "PASS" if passed else "FAIL"

    if lower.startswith("exist:"):
        body = raw[6:].strip()
        evidence, passed = handle_exist(body)
        return evidence, "PASS" if passed else "FAIL"

    if lower.startswith("read:"):
        body = raw[5:].strip()
        evidence, passed = handle_read(body)
        return evidence, "PASS" if passed else "FAIL"

    if lower.startswith("test:"):
        body = raw[5:].strip()
        evidence, passed = handle_test(body)
        return evidence, "PASS" if passed else "FAIL"

    if lower.startswith("schema:"):
        body = raw[7:].strip()
        evidence, passed = handle_schema(body)
        return evidence, "PASS" if passed else "FAIL"

    # CLI, Review, or unrecognized prefix -> MANUAL
    if lower.startswith("cli:"):
        instruction, verdict = handle_manual(raw[4:].strip(), "CLI: ")
        return f"Manual action required: {instruction}", verdict

    if lower.startswith("review:"):
        instruction, verdict = handle_manual(raw[7:].strip(), "Review: ")
        return f"Manual review required: {instruction}", verdict

    # Unknown prefix or informal prose -> MANUAL
    if not raw:
        return "No verify method provided", "MANUAL"

    # Check if it looks like an unrecognized prefix (word followed by colon)
    prefix_match = re.match(r"^([A-Za-z]+):\s*", raw)
    if prefix_match and prefix_match.group(1).lower() + ":" not in RECOGNIZED_PREFIXES:
        return f"Unrecognized prefix '{prefix_match.group(1)}:' -- manual action required: {raw}", "MANUAL"

    # Informal prose (no recognized prefix at all)
    return f"Informal verify method -- manual action required: {raw}", "MANUAL"


# ---------------------------------------------------------------------------
# Core executor
# ---------------------------------------------------------------------------

def run_executor(prd_path: Path, skip_format_gate: bool = False) -> dict:
    """Run the full ISC execution on a PRD file. Returns structured output dict."""
    start_ms = int(time.monotonic() * 1000)
    executed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    errors: list[str] = []

    # ---- format gate ----
    if not skip_format_gate:
        try:
            gate_result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "scripts" / "isc_validator.py"),
                    "--prd", str(prd_path),
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(REPO_ROOT),
            )
            if gate_result.returncode != 0:
                errors.append(f"Format gate failed (isc_validator exit {gate_result.returncode})")
                # Still parse and attempt execution; errors will surface in output
        except subprocess.TimeoutExpired as e:
            if e.process is not None:
                try:
                    e.process.kill()
                except Exception:
                    pass
            errors.append("Format gate timed out after 30s")
        except Exception as exc:
            errors.append(f"Format gate error: {exc}")

    # ---- read PRD ----
    if not prd_path.exists():
        errors.append(f"PRD file not found: {prd_path}")
        return _build_output(prd_path, [], errors, start_ms, executed_at)

    try:
        prd_text = prd_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        errors.append(f"Cannot read PRD: {e}")
        return _build_output(prd_path, [], errors, start_ms, executed_at)

    # ---- parse criteria ----
    raw_items = parse_isc_items(prd_text)
    if not raw_items:
        errors.append("No ISC criteria found (expected '- [ ] ... | Verify:' format)")
        return _build_output(prd_path, [], errors, start_ms, executed_at)

    # ---- initialize ALL criteria to ERROR before execution ----
    # Security: no criterion can default to PASS if execution is incomplete.
    criteria: list[dict] = []
    for item in raw_items:
        criteria.append({
            "line": item["line"],
            "criterion": item["criterion"],
            "verify_method": item["verify_method"],
            "verdict": "ERROR",  # initialized to ERROR verdict before execution begins
            "evidence": "Not yet executed",
            "duration_ms": 0,
        })

    # ---- execute each criterion ----
    for record in criteria:
        t0 = int(time.monotonic() * 1000)
        try:
            evidence, verdict = dispatch(record["verify_method"])
            record["verdict"] = verdict
            record["evidence"] = _sanitize_ascii(scrub_secrets(evidence))
        except Exception as exc:
            record["verdict"] = "ERROR"
            record["evidence"] = f"Unexpected executor error: {exc}"
        finally:
            record["duration_ms"] = int(time.monotonic() * 1000) - t0

    return _build_output(prd_path, criteria, errors, start_ms, executed_at)


def _build_output(
    prd_path: Path,
    criteria: list[dict],
    errors: list[str],
    start_ms: int,
    executed_at: str,
) -> dict:
    """Build the structured output dict."""
    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    summary = {"pass": 0, "fail": 0, "error": 0, "manual": 0}
    for c in criteria:
        v = c.get("verdict", "ERROR").lower()
        if v == "pass":
            summary["pass"] += 1
        elif v == "fail":
            summary["fail"] += 1
        elif v == "manual":
            summary["manual"] += 1
        else:
            summary["error"] += 1

    # gate_passed: all non-MANUAL criteria are PASS (no FAILs, no ERRORs, and no executor errors)
    gate_passed = (
        summary["fail"] == 0
        and summary["error"] == 0
        and len(criteria) > 0
        and len(errors) == 0
    )

    return {
        "_schema_version": "1.0.0",
        "_provenance": {
            "script": "tools/scripts/isc_executor.py",
            "version": SCRIPT_VERSION,
            "git_hash": collect_git_hash(),
            "execution_time_ms": elapsed_ms,
            "executed_at": executed_at,
        },
        "prd_path": str(prd_path),
        "criteria_count": len(criteria),
        "criteria": criteria,
        "summary": summary,
        "gate_passed": gate_passed,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_table(output: dict) -> str:
    """Format output as human-readable ASCII markdown table."""
    lines = []
    prd_display = output.get("prd_path", "unknown")
    lines.append(f"ISC Executor -- {prd_display}")
    lines.append(f"Executed: {output.get('criteria_count', 0)} criteria")
    lines.append("")

    if output.get("errors"):
        for err in output["errors"]:
            lines.append(f"  ERROR: {err}")
        lines.append("")

    for c in output.get("criteria", []):
        verdict = c.get("verdict", "ERROR")
        crit_text = c.get("criterion", "")[:60]
        verify_raw = c.get("verify_method", "")
        evidence = c.get("evidence", "")

        lines.append(f"  [{verdict}] {crit_text}")
        if verdict == "MANUAL":
            lines.append(f"         Action required: {verify_raw}")
        elif verdict in ("PASS", "FAIL", "ERROR"):
            lines.append(f"         Verify: {verify_raw[:80]} | Evidence: {evidence[:120]}")
        lines.append("")

    s = output.get("summary", {})
    gate = "PASS" if output.get("gate_passed") else "FAIL"
    lines.append(
        f"Gate: {gate} | {s.get('pass', 0)} pass, {s.get('fail', 0)} fail, "
        f"{s.get('manual', 0)} manual, {s.get('error', 0)} error"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Exit code determination
# ---------------------------------------------------------------------------

def determine_exit_code(output: dict) -> int:
    """Determine exit code from execution output.

    0 = all non-MANUAL criteria PASS
    1 = one or more criteria FAIL
    2 = executor error (crash, timeout, parse failure)
    3 = MANUAL items present, no FAILs
    """
    errors = output.get("errors", [])
    if errors and not output.get("criteria"):
        # Fundamental failure -- no criteria could be processed
        return 2

    s = output.get("summary", {})
    fail_count = s.get("fail", 0)
    error_count = s.get("error", 0)
    manual_count = s.get("manual", 0)

    if fail_count > 0:
        return 1
    if error_count > 0:
        return 2
    if manual_count > 0:
        return 3
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ISC Executor -- deterministic VERIFY phase execution engine"
    )
    parser.add_argument("--prd", type=str, required=True, help="Path to PRD file")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Emit machine-readable JSON instead of markdown table")
    parser.add_argument("--skip-format-gate", action="store_true",
                        help="Skip isc_validator.py pre-check (for testing)")
    args = parser.parse_args()

    prd_path = Path(args.prd)
    if not prd_path.is_absolute():
        prd_path = REPO_ROOT / prd_path

    output = run_executor(prd_path, skip_format_gate=args.skip_format_gate)

    if args.json_output:
        print(json.dumps(output, indent=2, default=str))
    else:
        print(_sanitize_ascii(format_table(output)))

    sys.exit(determine_exit_code(output))


if __name__ == "__main__":
    main()
