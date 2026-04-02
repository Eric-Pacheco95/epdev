#!/usr/bin/env python3
"""ISC Validator -- deterministic quality gate for PRD acceptance criteria.

Extracts ISC criteria from PRD files and runs the 6-check quality gate:
1. Count: 3-8 criteria per phase
2. Conciseness: single sentence, no compound "and"
3. State-not-action: describes what IS true, not what to DO
4. Binary-testable: clear pass/fail with no subjective judgment
5. Anti-criteria: at least one criterion states what must NOT happen
6. Verify method: every criterion has a | Verify: suffix

Usage:
    python tools/scripts/isc_validator.py --prd PATH              # table output
    python tools/scripts/isc_validator.py --prd PATH --json       # JSON output
    python tools/scripts/isc_validator.py --prd PATH --pretty     # indented JSON
    python tools/scripts/isc_validator.py --prd PATH --execute    # run verify methods
    python tools/scripts/isc_validator.py --prd PATH --execute --json

Exit codes:
    0 = all quality gate checks pass (and, with --execute, all executed criteria pass)
    1 = one or more checks fail, or no criteria found, or executed criteria fail

Output: Structured validation report. Zero LLM tokens consumed.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.isc_common import (  # noqa: E402
    MANUAL_REQUIRED,
    SECRET_PATH_PATTERNS,
    classify_verify_method,
    sanitize_isc_command,
)

SCRIPT_VERSION = "1.1.0"

# Where execution audit reports are written
VALIDATIONS_DIR = REPO_ROOT / "history" / "validations"

# Git Bash candidates (Windows -- avoid WSL interception from System32)
_GIT_BASH_CANDIDATES = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
]

# Per-command timeout (seconds)
_CMD_TIMEOUT_S = 30
# Aggregate timeout for all --execute verify commands combined
_AGGREGATE_TIMEOUT_S = 120

# Action verbs that suggest "do X" rather than "X is true"
# Used as a heuristic for the state-not-action check (warning, not hard fail)
ACTION_VERBS = [
    "implement", "create", "build", "add", "remove", "delete", "write",
    "update", "install", "configure", "set up", "deploy", "run", "execute",
    "fix", "refactor", "migrate", "enable", "disable", "ensure",
]


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


def _normalize_unicode(text: str) -> str:
    """Normalize Unicode for regex parsing -- smart quotes, dashes, etc."""
    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes
        "\u201c": '"', "\u201d": '"',   # curly double quotes
        "\u2014": "--", "\u2013": "-",  # em/en dashes
        "\u2026": "...",                # ellipsis
        "\u00a0": " ",                  # non-breaking space
        "\u2010": "-", "\u2011": "-",   # hyphens
        "\u2012": "-", "\u2015": "--",  # figure dash, horizontal bar
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


def parse_isc_items(text: str) -> list[dict]:
    """Extract ISC criteria from PRD text.

    Format: - [ ] Criterion text [E] | Verify: method
    Also handles: * [ ], - [x], - [X]
    """
    normalized = _normalize_unicode(text)
    items = []

    for line_num, line in enumerate(normalized.splitlines(), 1):
        m = re.match(
            r"^\s*[-*]\s+\[([ xX])\]\s+(.+?)(?:\s*\|\s*Verify:\s*(.+))?$",
            line.strip(),
        )
        if m:
            checked = m.group(1).lower() == "x"
            criterion = m.group(2).strip()
            verify_method = (m.group(3) or "").strip()

            # Extract confidence tag [E], [I], [R]
            conf_match = re.search(r"\[([EIR])\]", criterion)
            confidence = conf_match.group(1) if conf_match else None

            # Extract verification type [M] or [A]
            vtype_match = re.search(r"\[([MA])\]", criterion)
            verify_type = vtype_match.group(1) if vtype_match else None

            items.append({
                "line": line_num,
                "checked": checked,
                "criterion": criterion,
                "verify_method": verify_method,
                "confidence": confidence,
                "verify_type": verify_type,
            })

    return items


def detect_phases(text: str, items: list[dict]) -> list[dict]:
    """Detect phase groupings from PRD section headers.

    Looks for patterns like: ### Phase 1: ... or ### Phase 2: ...
    Returns list of phases with their criteria.
    """
    normalized = _normalize_unicode(text)
    lines = normalized.splitlines()

    # Find phase/sprint headers and their line numbers
    phase_headers = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^#{2,4}\s+(?:(?:Phase|Sprint)\s+)?(\d+|Anti)[:\s].*", line, re.IGNORECASE)
        if m:
            phase_headers.append({"line": i, "name": line.strip().lstrip("#").strip()})

    if not phase_headers:
        # No phase headers -- treat all items as a single phase
        return [{"name": "all", "items": items}]

    # Assign items to phases based on line numbers
    phases = []
    for idx, header in enumerate(phase_headers):
        start_line = header["line"]
        end_line = phase_headers[idx + 1]["line"] if idx + 1 < len(phase_headers) else float("inf")

        phase_items = [it for it in items if start_line <= it["line"] < end_line]
        if phase_items:
            phases.append({"name": header["name"], "items": phase_items})

    # Catch any items before the first phase header
    if phase_headers:
        first_line = phase_headers[0]["line"]
        orphans = [it for it in items if it["line"] < first_line]
        if orphans:
            phases.insert(0, {"name": "pre-phase", "items": orphans})

    return phases


def check_count(phases: list[dict]) -> list[dict]:
    """Check 1: Each phase has 3-8 criteria."""
    results = []
    for phase in phases:
        count = len(phase["items"])
        passed = 3 <= count <= 8
        results.append({
            "check": "count",
            "phase": phase["name"],
            "value": count,
            "passed": passed,
            "message": f"{count} criteria" + ("" if passed else " (expected 3-8)"),
        })
    return results


def check_conciseness(items: list[dict]) -> list[dict]:
    """Check 2: Single sentence, no compound 'and' joining two criteria."""
    results = []
    # Pattern: two state/action clauses joined by " and "
    compound_pattern = re.compile(
        r"\b(?:and)\b.*\b(?:and)\b"  # two "and"s = likely compound
        r"|"
        r"\.\s+[A-Z]"  # period followed by capital = two sentences
    )
    for item in items:
        crit = item["criterion"]
        # Remove tags like [E], [I], [R], [M], [A] before checking
        clean = re.sub(r"\[[EIRMA]\]", "", crit).strip()
        has_compound = bool(compound_pattern.search(clean))
        results.append({
            "check": "conciseness",
            "criterion": crit[:80],
            "passed": not has_compound,
            "message": "compound criterion detected" if has_compound else "ok",
        })
    return results


def check_state_not_action(items: list[dict]) -> list[dict]:
    """Check 3: Criteria describe state, not action (warning, not hard fail)."""
    results = []
    for item in items:
        crit = item["criterion"]
        # Remove tags before checking
        clean = re.sub(r"\[[EIRMA]\]", "", crit).strip()
        # Check if criterion starts with an action verb
        first_word = clean.split()[0].lower() if clean.split() else ""
        is_action = first_word in ACTION_VERBS
        results.append({
            "check": "state_not_action",
            "criterion": crit[:80],
            "passed": not is_action,
            "severity": "warning",  # not a hard fail
            "message": f"starts with action verb '{first_word}'" if is_action else "ok",
        })
    return results


def check_binary_testable(items: list[dict]) -> list[dict]:
    """Check 4: Criterion has a clear pass/fail (heuristic: has verify method)."""
    results = []
    # Subjective terms that suggest non-binary evaluation
    subjective = ["appropriate", "reasonable", "good enough", "nice",
                   "adequately", "sufficiently", "as needed"]
    for item in items:
        crit = item["criterion"]
        clean = re.sub(r"\[[EIRMA]\]", "", crit).strip().lower()
        has_subjective = any(s in clean for s in subjective)
        has_verify = bool(item["verify_method"])
        passed = has_verify and not has_subjective
        msg = []
        if not has_verify:
            msg.append("no verify method")
        if has_subjective:
            msg.append("contains subjective terms")
        results.append({
            "check": "binary_testable",
            "criterion": crit[:80],
            "passed": passed,
            "message": "; ".join(msg) if msg else "ok",
        })
    return results


def check_anti_criteria(items: list[dict]) -> dict:
    """Check 5: At least one criterion states what must NOT happen."""
    anti_patterns = ["never", "no ", "not ", "neither", "must not", "does not",
                     "cannot", "without", "absent", "zero ", "none "]
    anti_count = 0
    for item in items:
        crit = item["criterion"].lower()
        if any(p in crit for p in anti_patterns):
            anti_count += 1
    return {
        "check": "anti_criteria",
        "passed": anti_count >= 1,
        "anti_count": anti_count,
        "message": f"{anti_count} anti-criteria found" + (
            "" if anti_count >= 1 else " (need at least 1)"
        ),
    }


def check_verify_methods(items: list[dict]) -> list[dict]:
    """Check 6: Every criterion has a | Verify: suffix."""
    results = []
    for item in items:
        has_verify = bool(item["verify_method"])
        results.append({
            "check": "verify_method",
            "criterion": item["criterion"][:80],
            "passed": has_verify,
            "message": "ok" if has_verify else "missing | Verify: suffix",
        })
    return results


def run_quality_gate(prd_path: Path) -> dict:
    """Run the full 6-check quality gate on a PRD file."""
    start_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Handle missing/empty/unreadable files
    errors = []
    if not prd_path.exists():
        errors.append(f"File not found: {prd_path}")
        return _build_output(prd_path, [], [], errors, start_ms)

    try:
        text = prd_path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"Cannot read file: {e}")
        return _build_output(prd_path, [], [], errors, start_ms)

    if not text.strip():
        errors.append("File is empty")
        return _build_output(prd_path, [], [], errors, start_ms)

    # Extract ISC items
    items = parse_isc_items(text)
    if not items:
        errors.append("No ISC criteria found (expected '- [ ] ... | Verify:' format)")
        return _build_output(prd_path, items, [], errors, start_ms)

    # Detect phases
    phases = detect_phases(text, items)

    # Run all 6 checks
    all_checks = []

    # Check 1: Count per phase
    all_checks.extend(check_count(phases))

    # Check 2: Conciseness
    all_checks.extend(check_conciseness(items))

    # Check 3: State-not-action (warnings only)
    all_checks.extend(check_state_not_action(items))

    # Check 4: Binary-testable
    all_checks.extend(check_binary_testable(items))

    # Check 5: Anti-criteria (single result for all items)
    all_checks.append(check_anti_criteria(items))

    # Check 6: Verify methods
    all_checks.extend(check_verify_methods(items))

    return _build_output(prd_path, items, all_checks, errors, start_ms)


def _build_output(
    prd_path: Path,
    items: list[dict],
    checks: list[dict],
    errors: list[str],
    start_ms: int,
) -> dict:
    """Build the structured output dict."""
    elapsed_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - start_ms

    # Separate hard fails from warnings
    hard_fails = [c for c in checks if not c["passed"] and c.get("severity") != "warning"]
    warnings = [c for c in checks if not c["passed"] and c.get("severity") == "warning"]

    # Gate pass = no hard fails and at least 1 criterion found
    gate_passed = len(hard_fails) == 0 and len(items) > 0 and len(errors) == 0

    # Summary by check type
    check_summary = {}
    for c in checks:
        ctype = c["check"]
        if ctype not in check_summary:
            check_summary[ctype] = {"total": 0, "passed": 0, "failed": 0}
        check_summary[ctype]["total"] += 1
        if c["passed"]:
            check_summary[ctype]["passed"] += 1
        else:
            check_summary[ctype]["failed"] += 1

    return {
        "_schema_version": "1.0.0",
        "_provenance": {
            "script": "tools/scripts/isc_validator.py",
            "version": SCRIPT_VERSION,
            "git_hash": collect_git_hash(),
            "execution_time_ms": elapsed_ms,
            "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "prd_path": str(prd_path),
        "extracted_count": len(items),
        "criteria": items,
        "checks": checks,
        "check_summary": check_summary,
        "hard_fails": len(hard_fails),
        "warnings": len(warnings),
        "gate_passed": gate_passed,
        "errors": errors,
    }


def format_table(output: dict) -> str:
    """Format output as human-readable ASCII table."""
    lines = []
    lines.append(f"ISC Validator -- {output['prd_path']}")
    lines.append(f"Extracted: {output['extracted_count']} criteria")
    lines.append("")

    if output["errors"]:
        for err in output["errors"]:
            lines.append(f"  ERROR: {err}")
        lines.append("")

    # Check summary
    lines.append("Quality Gate Checks:")
    for check_name, stats in output.get("check_summary", {}).items():
        status = "PASS" if stats["failed"] == 0 else "FAIL"
        lines.append(f"  [{status}] {check_name}: {stats['passed']}/{stats['total']} passed")

    lines.append("")

    # Hard fails detail
    hard_fails = [c for c in output.get("checks", [])
                  if not c["passed"] and c.get("severity") != "warning"]
    if hard_fails:
        lines.append("Hard Fails:")
        for f in hard_fails:
            crit = f.get("criterion", f.get("phase", ""))
            lines.append(f"  [{f['check']}] {crit}: {f['message']}")
        lines.append("")

    # Warnings
    warnings = [c for c in output.get("checks", [])
                if not c["passed"] and c.get("severity") == "warning"]
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            crit = w.get("criterion", "")
            lines.append(f"  [{w['check']}] {crit}: {w['message']}")
        lines.append("")

    # Overall
    gate = "PASS" if output["gate_passed"] else "FAIL"
    lines.append(f"Gate: {gate} | {output['hard_fails']} fails, {output['warnings']} warnings")

    return "\n".join(lines)


# -- Execution engine (--execute mode) ----------------------------------------

def _find_git_bash() -> str:
    """Return path to Git Bash, avoiding WSL's bash.exe on Windows."""
    for candidate in _GIT_BASH_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which("bash")
    if found and "System32" not in found and "system32" not in found:
        return found
    return _GIT_BASH_CANDIDATES[0]


def _check_uncommitted_changes() -> bool:
    """Return True if working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _run_single_cmd(cmd: str) -> dict:
    """Execute one verify command and return a result dict."""
    try:
        if os.name == "nt":
            shell_cmd = [_find_git_bash(), "-c", cmd]
        else:
            shell_cmd = ["bash", "-c", cmd]
        result = subprocess.run(
            shell_cmd,
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
            timeout=_CMD_TIMEOUT_S,
        )
        output = (result.stdout + result.stderr)[:500]
        return {
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "output": output,
        }
    except subprocess.TimeoutExpired:
        return {"status": "fail", "exit_code": -1, "output": f"timeout after {_CMD_TIMEOUT_S}s"}
    except Exception as exc:
        return {"status": "fail", "exit_code": -1, "output": str(exc)[:200]}


def _redact_secrets(text: str) -> str:
    """Redact lines that look like secret key-value pairs or secret paths.

    Applied to report content before writing to disk.
    """
    lines = text.splitlines()
    redacted = []
    for line in lines:
        # Redact KEY=value patterns (env-var style secrets); threshold 4+ chars
        # to catch short tokens like TOKEN=abc123 as well as long API keys.
        if re.search(r"\b[A-Z][A-Z0-9_]{3,}\s*=\s*\S{4,}", line):
            redacted.append("[REDACTED -- possible secret value]")
        # Redact lines containing secret-path patterns
        elif SECRET_PATH_PATTERNS.search(line):
            redacted.append("[REDACTED -- protected path]")
        else:
            redacted.append(line)
    return "\n".join(redacted)


def run_execution(items: list[dict]) -> list[dict]:
    """Execute ISC verify methods for all criteria.

    Uses a ThreadPoolExecutor with _AGGREGATE_TIMEOUT_S total budget.
    Each command gets at most _CMD_TIMEOUT_S.

    Returns list of execution result dicts.
    """
    results = []

    def _execute_item(item: dict) -> dict:
        verify_method = item.get("verify_method", "")
        criterion = item.get("criterion", "")[:80]

        if not verify_method:
            return {
                "criterion": criterion,
                "status": MANUAL_REQUIRED,
                "command": None,
                "exit_code": None,
                "output": "no verify method",
                "elapsed_ms": 0,
            }

        # Classify first — never execute blocked or manual items
        full_isc = f"{criterion} | Verify: {verify_method}"
        classification = classify_verify_method(full_isc)

        if classification == MANUAL_REQUIRED:
            return {
                "criterion": criterion,
                "status": MANUAL_REQUIRED,
                "command": None,
                "exit_code": None,
                "output": "requires human or LLM judgment",
                "elapsed_ms": 0,
            }

        if classification == "blocked":
            return {
                "criterion": criterion,
                "status": "blocked",
                "command": verify_method,
                "exit_code": None,
                "output": "blocked: dangerous command pattern",
                "elapsed_ms": 0,
            }

        # executable -- sanitize then run
        cmd = sanitize_isc_command(full_isc)
        if cmd is None:
            return {
                "criterion": criterion,
                "status": "blocked",
                "command": verify_method,
                "exit_code": None,
                "output": "blocked: failed sanitization",
                "elapsed_ms": 0,
            }

        t0 = datetime.now(timezone.utc).timestamp()
        run_result = _run_single_cmd(cmd)
        elapsed_ms = int((datetime.now(timezone.utc).timestamp() - t0) * 1000)

        return {
            "criterion": criterion,
            "status": run_result["status"],
            "command": cmd,
            "exit_code": run_result["exit_code"],
            "output": run_result["output"],
            "elapsed_ms": elapsed_ms,
        }

    # Submit all items; enforce aggregate budget via as_completed timeout.
    # TimeoutError from as_completed is raised at the iterator level (not inside
    # the loop body), so it must be caught around the for loop, not inside it.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_execute_item, item): item for item in items}
        try:
            for future in concurrent.futures.as_completed(futures, timeout=_AGGREGATE_TIMEOUT_S):
                try:
                    results.append(future.result())
                except Exception as exc:
                    item = futures[future]
                    results.append({
                        "criterion": item.get("criterion", "")[:80],
                        "status": "fail",
                        "command": item.get("verify_method", ""),
                        "exit_code": -1,
                        "output": str(exc)[:200],
                        "elapsed_ms": 0,
                    })
        except concurrent.futures.TimeoutError:
            # Aggregate budget exceeded -- cancel remaining and record failures
            for future, item in futures.items():
                if not future.done():
                    future.cancel()
                    results.append({
                        "criterion": item.get("criterion", "")[:80],
                        "status": "fail",
                        "command": item.get("verify_method", ""),
                        "exit_code": -1,
                        "output": f"aggregate timeout ({_AGGREGATE_TIMEOUT_S}s) exceeded",
                        "elapsed_ms": _AGGREGATE_TIMEOUT_S * 1000,
                    })

    return results


def write_validation_report(prd_path: Path, output: dict) -> Path:
    """Write a timestamped Markdown report to history/validations/.

    Secret-scans output before writing. Returns the report path.
    """
    VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    slug = prd_path.parent.name
    report_path = VALIDATIONS_DIR / f"{timestamp}_{slug}.md"

    exec_results = output.get("execution_results", [])
    executed = [r for r in exec_results if r["status"] in ("pass", "fail")]
    passed = [r for r in exec_results if r["status"] == "pass"]
    failed = [r for r in exec_results if r["status"] == "fail"]
    manual = [r for r in exec_results if r["status"] == MANUAL_REQUIRED]
    blocked = [r for r in exec_results if r["status"] == "blocked"]

    lines = [
        "# ISC Validation Report",
        "",
        f"**PRD**: {prd_path}",
        f"**Timestamp**: {timestamp.replace('_', ' ')}",
        "",
        f"Executed: {len(executed)} | Passed: {len(passed)} | Failed: {len(failed)} | Manual required: {len(manual)} | Blocked: {len(blocked)}",
        "",
        "## Results",
        "",
    ]

    for r in exec_results:
        status = r["status"].upper()
        cmd_str = f"`{r['command']}`" if r["command"] else "_none_"
        output_str = r.get("output", "") or ""
        lines.append(f"### [{status}] {r['criterion']}")
        lines.append(f"- Command: {cmd_str}")
        if r.get("exit_code") is not None:
            lines.append(f"- Exit code: {r['exit_code']}")
        if output_str:
            lines.append(f"- Output: `{output_str[:200]}`")
        lines.append("")

    content = "\n".join(lines)
    content = _redact_secrets(content)
    report_path.write_text(content, encoding="utf-8")
    return report_path


def format_execution_table(exec_results: list[dict]) -> str:
    """Format execution results as ASCII table."""
    lines = []
    counts = {
        "pass": sum(1 for r in exec_results if r["status"] == "pass"),
        "fail": sum(1 for r in exec_results if r["status"] == "fail"),
        MANUAL_REQUIRED: sum(1 for r in exec_results if r["status"] == MANUAL_REQUIRED),
        "blocked": sum(1 for r in exec_results if r["status"] == "blocked"),
    }
    executed = counts["pass"] + counts["fail"] + counts["blocked"]
    lines.append(
        f"Executed: {executed} | Passed: {counts['pass']} | "
        f"Failed: {counts['fail']} | "
        f"Manual required: {counts[MANUAL_REQUIRED]} | "
        f"Blocked: {counts['blocked']}"
    )
    lines.append("")
    for r in exec_results:
        sym = {"pass": "[PASS]", "fail": "[FAIL]", MANUAL_REQUIRED: "[MANUAL]", "blocked": "[BLOCKED]"}.get(
            r["status"], f"[{r['status'].upper()}]"
        )
        crit = r["criterion"][:60]
        lines.append(f"  {sym} {crit}")
        if r["status"] in ("fail", "blocked") and r.get("output"):
            lines.append(f"         {r['output'][:80]}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ISC Validator -- quality gate for PRD criteria")
    parser.add_argument("--prd", type=str, required=True, help="Path to PRD file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument(
        "--execute", action="store_true",
        help="Execute verify methods after quality gate; write audit report to history/validations/",
    )
    args = parser.parse_args()

    prd_path = Path(args.prd)
    if not prd_path.is_absolute():
        prd_path = REPO_ROOT / prd_path

    output = run_quality_gate(prd_path)

    if args.execute:
        # Guard against recursive --execute calls (e.g. when a verify method
        # invokes isc_validator.py --execute itself). Inner calls run quality
        # gate only; execution is skipped to prevent infinite recursion.
        if os.environ.get("ISC_VALIDATOR_EXECUTING"):
            args.execute = False
        else:
            os.environ["ISC_VALIDATOR_EXECUTING"] = "1"

    if args.execute:
        # Warn on uncommitted changes that could skew verify results
        if _check_uncommitted_changes():
            print(
                _sanitize_ascii(
                    "WARNING: working tree has uncommitted changes -- "
                    "verify results may not reflect committed state"
                ),
                file=sys.stderr,
            )

        items = output.get("criteria", [])
        exec_results = run_execution(items)
        output["execution_results"] = exec_results

        # Write audit report (secret-scanned)
        report_path = write_validation_report(prd_path, output)
        output["validation_report"] = str(report_path)

        # Execution gate: fail only on actual test failures.
        # 'blocked' and 'manual_required' are deferred to human review --
        # they don't indicate broken implementation, only unautomatable checks.
        exec_failed = any(r["status"] == "fail" for r in exec_results)
        if exec_failed:
            output["gate_passed"] = False

    if args.json or args.pretty:
        indent = 2 if args.pretty else None
        print(json.dumps(output, indent=indent, default=str))
    else:
        table = format_table(output)
        if args.execute:
            exec_results = output.get("execution_results", [])
            table += "\n\nExecution Results:\n" + format_execution_table(exec_results)
            report = output.get("validation_report", "")
            if report:
                table += f"\n\nReport: {report}"
        print(_sanitize_ascii(table))

    sys.exit(0 if output["gate_passed"] else 1)


if __name__ == "__main__":
    main()
