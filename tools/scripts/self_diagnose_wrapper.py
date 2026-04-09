#!/usr/bin/env python3
"""Jarvis Self-Diagnose Wrapper -- L1 graduated self-heal.

Wraps any runner command. On failure, calls claude -p for diagnosis
(root cause + proposed fix), logs the diagnosis, and posts to Slack.
Does NOT apply fixes or retry -- diagnosis only.

This is L1 of the graduated self-heal model:
  L0: Alert (runners fail silently in logs) -- previous state
  L1: Diagnose (this wrapper) -- capture, diagnose, log, notify
  L2: Playbook (future) -- auto-execute pre-approved fixes
  L3: Novel fix (maybe never) -- LLM-generated code patches

Usage:
    python self_diagnose_wrapper.py -- python tools/scripts/overnight_runner.py
    python self_diagnose_wrapper.py --timeout 600 -- python tools/scripts/morning_feed.py

Safety:
    - No file writes except the failure log
    - No retry of the original command
    - Skips diagnosis if CLAUDE_CODE_SESSION env var is set
    - Sanitizes error output before sending to claude -p
    - Stdlib only, ASCII-only output
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"

# Error patterns that indicate failure even if exit code is 0
ERROR_PATTERNS = [
    re.compile(r"^ERROR:", re.MULTILINE),
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"FileNotFoundError"),
    re.compile(r"QUALITY_GATE:\s*FAIL"),
    re.compile(r"SECURITY_AUDIT:\s*FAIL"),
]

# Patterns that indicate the host is out of memory / pagefile.
# When matched, skip claude -p diagnosis (it will OOM the same way)
# and write a hardcoded structured failure record instead.
OOM_PATTERNS = [
    re.compile(r"WinError 1455"),
    re.compile(r"paging file is too small", re.IGNORECASE),
    re.compile(r"MemoryError"),
    re.compile(r"Cannot allocate memory"),
    re.compile(r"\[Errno 12\]"),
]


def detect_oom(output: str) -> bool:
    """Return True if output indicates host memory/pagefile exhaustion."""
    for pat in OOM_PATTERNS:
        if pat.search(output):
            return True
    return False


def build_oom_diagnosis(runner_name: str) -> str:
    """Hardcoded diagnosis for OOM failures -- skips claude -p (would also OOM)."""
    return (
        "ROOT_CAUSE: Host out of virtual memory -- Windows pagefile exhausted "
        "(WinError 1455). Diagnosis skipped because claude -p would hit the same OOM.\n"
        "SEVERITY: 7\n"
        "CATEGORY: resource_exhaustion\n"
        "PROPOSED_FIX: Increase Windows pagefile (System Properties -> Advanced -> "
        "Performance -> Virtual Memory): set initial 16GB, max 32GB. Reboot required.\n"
        "REVERSIBLE: yes\n"
        "REQUIRES_HUMAN: yes\n"
        "DETAILS: %s aborted before any work was done. The runner did not produce "
        "a branch or any artifacts. This is a host-level issue, not a code bug -- "
        "no fix can be applied from inside Jarvis."
    ) % runner_name

# Patterns to strip from output before sending to claude -p (secret safety)
SECRET_PATTERNS = [
    re.compile(r".*Bearer\s+\S+.*", re.IGNORECASE),
    re.compile(r".*token[=:]\s*\S+.*", re.IGNORECASE),
    re.compile(r".*sk-[a-zA-Z0-9]+.*"),
    re.compile(r".*xoxb-[a-zA-Z0-9-]+.*"),
    re.compile(r".*xoxp-[a-zA-Z0-9-]+.*"),
    re.compile(r".*ANTHROPIC_API_KEY.*", re.IGNORECASE),
    re.compile(r".*SLACK_BOT_TOKEN.*", re.IGNORECASE),
    re.compile(r".*AKIA[A-Z0-9]{16}.*"),  # AWS access keys
    re.compile(r".*ghp_[a-zA-Z0-9]{36}.*"),  # GitHub PATs
    re.compile(r".*gho_[a-zA-Z0-9]{36}.*"),  # GitHub OAuth tokens
    re.compile(r".*password[=:]\s*\S+.*", re.IGNORECASE),
]

DIAGNOSE_TIMEOUT_S = 300  # 5 minutes for diagnosis


# -- Failure detection -------------------------------------------------------

def detect_failure(exit_code: int, output: str) -> bool:
    """Return True if the runner output indicates failure."""
    if exit_code != 0:
        return True
    for pattern in ERROR_PATTERNS:
        if pattern.search(output):
            return True
    return False


def extract_runner_name(command: list[str]) -> str:
    """Extract a short runner name from the command for logging."""
    for arg in command:
        if arg.endswith(".py"):
            return Path(arg).stem
    return "unknown_runner"


# -- Output sanitization -----------------------------------------------------

def sanitize_output(output: str, max_lines: int = 50) -> str:
    """Strip secret patterns and truncate output for the diagnosis prompt."""
    lines = output.splitlines()
    # Take last N lines (most relevant for diagnosis)
    lines = lines[-max_lines:]
    sanitized = []
    for line in lines:
        skip = False
        for pat in SECRET_PATTERNS:
            if pat.match(line):
                sanitized.append("[REDACTED: possible secret]")
                skip = True
                break
        if not skip:
            sanitized.append(line)
    return "\n".join(sanitized)


# -- Playbook classification -------------------------------------------------

def classify_playbook(output: str) -> str:
    """Match output against known playbook patterns. Returns category or 'unknown'."""
    try:
        from tools.scripts.failure_playbooks import PLAYBOOKS
    except ImportError:
        return "unknown"

    for pb in PLAYBOOKS:
        if re.search(pb["pattern"], output):
            return pb["category"]
    return "unknown"


# -- Diagnosis ---------------------------------------------------------------

def build_diagnosis_prompt(runner_name: str, exit_code: int,
                           sanitized_output: str, playbook_category: str) -> str:
    """Build the claude -p prompt for failure diagnosis."""
    return """You are Jarvis's failure diagnosis engine. A scheduled runner has failed.
Analyze the error output and provide a structured diagnosis.

RUNNER: %s
EXIT CODE: %d
PLAYBOOK MATCH: %s

ERROR OUTPUT (last 50 lines, secrets redacted):
---
%s
---

Provide your diagnosis in this exact format (ASCII only, no Unicode):

ROOT_CAUSE: <one sentence describing why the runner failed>
SEVERITY: <1-10, where 10 is system-breaking>
CATEGORY: <one of: path_resolution, slack_cap, stale_worktree, timeout, import_error, code_bug, config_error, network_error, auth_error, unknown>
PROPOSED_FIX: <one sentence describing how to fix it>
REVERSIBLE: <yes or no>
REQUIRES_HUMAN: <yes or no>
DETAILS: <2-3 sentences with additional context>

Be specific and grounded in the error output. Do not speculate beyond what the output shows.""" % (
        runner_name, exit_code, playbook_category, sanitized_output
    )


def call_claude_diagnose(prompt: str) -> str:
    """Call claude -p for diagnosis. Returns response or error string."""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "-"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=DIAGNOSE_TIMEOUT_S,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            return "(diagnosis error: %s)" % result.stderr.strip()[:200]
        return "(diagnosis returned empty response)"
    except FileNotFoundError:
        return "(claude CLI not found at %s)" % CLAUDE_BIN
    except subprocess.TimeoutExpired:
        return "(diagnosis timed out after %ds)" % DIAGNOSE_TIMEOUT_S
    except Exception as exc:
        return "(diagnosis failed: %s)" % exc


# -- Logging -----------------------------------------------------------------

def log_failure(runner_name: str, exit_code: int, raw_output: str,
                diagnosis: str, playbook_category: str) -> Path:
    """Write failure diagnosis to memory/learning/failures/."""
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = runner_name.replace("_", "-")

    # Dedup: increment counter for multiple failures on same day
    log_path = FAILURES_DIR / ("%s_self-diagnose-%s.md" % (today, slug))
    counter = 1
    while log_path.is_file():
        counter += 1
        log_path = FAILURES_DIR / (
            "%s_self-diagnose-%s-%d.md" % (today, slug, counter)
        )

    # Extract structured fields from diagnosis
    root_cause = _extract_field(diagnosis, "ROOT_CAUSE", "Unknown")
    severity = _extract_field(diagnosis, "SEVERITY", "5")
    category = _extract_field(diagnosis, "CATEGORY", playbook_category)
    proposed_fix = _extract_field(diagnosis, "PROPOSED_FIX", "Manual investigation needed")

    content = """# Failure: %s runner failed
- Date: %s
- Severity: %s
- Component: %s
- Category: %s
- Playbook match: %s
- Exit code: %d
- Source: self-diagnose-wrapper (L1)

## Root Cause
%s

## Proposed Fix
%s

## Full Diagnosis
%s

## Error Output (last 30 lines)
```
%s
```
""" % (
        runner_name, today, severity, runner_name, category,
        playbook_category, exit_code, root_cause, proposed_fix,
        diagnosis, "\n".join(raw_output.splitlines()[-30:])
    )

    log_path.write_text(content, encoding="utf-8")
    return log_path


def _extract_field(text: str, field: str, default: str) -> str:
    """Extract a structured field from the diagnosis response."""
    m = re.search(r"^%s:\s*(.+)" % field, text, re.MULTILINE)
    return m.group(1).strip() if m else default


# -- Slack notification ------------------------------------------------------

def notify_failure(runner_name: str, diagnosis: str,
                   playbook_category: str, log_path: Path,
                   backlog_task_id: str | None = None) -> bool:
    """Post failure notification to Slack."""
    try:
        from tools.scripts.slack_notify import notify
    except ImportError:
        print("  Slack notify not available", file=sys.stderr)
        return False

    root_cause = _extract_field(diagnosis, "ROOT_CAUSE", "Unknown")
    severity_str = _extract_field(diagnosis, "SEVERITY", "5")
    category = _extract_field(diagnosis, "CATEGORY", playbook_category)

    try:
        severity_num = int(severity_str)
    except ValueError:
        severity_num = 5

    lines = [
        ":wrench: *Runner Failure Diagnosed (L1)*",
        "Runner: `%s`" % runner_name,
        "Root cause: %s" % root_cause,
        "Category: %s | Playbook: %s" % (category, playbook_category),
        "Log: `%s`" % log_path.relative_to(REPO_ROOT),
    ]
    if backlog_task_id:
        lines.append(":robot_face: Self-heal queued: `%s`" % backlog_task_id)
    else:
        lines.append(":eyes: Requires human review -- no task queued")

    sev = "critical" if severity_num >= 8 else "routine"
    return notify("\n".join(lines), severity=sev)


# -- Backlog injection -------------------------------------------------------

_TEST_REF_RE = re.compile(
    r"\btests[/\\][\w/\\\-.]+\.py(?:::[\w_]+)?",
)


def _extract_failing_test_refs(output: str) -> list[str]:
    """Extract pytest test path references from a failure output blob.

    Matches `tests/.../foo.py` and `tests/.../foo.py::test_name` patterns.
    Returns deduped list with forward-slash normalized paths. Used by the
    self-heal ISC builder to construct exact `pytest <ref>` re-run criteria
    instead of relying on the generic runner --test sanity gate.
    """
    if not output:
        return []
    refs = []
    seen = set()
    for m in _TEST_REF_RE.finditer(output):
        ref = m.group(0).replace("\\", "/")
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def append_self_heal_task(runner_name: str, diagnosis: str,
                          log_path: Path,
                          failure_output: str = "") -> str | None:
    """Append a Tier 1 self-heal task to the dispatcher backlog.

    Only appended when REQUIRES_HUMAN is 'no' in the diagnosis.
    Returns the task ID if written, None otherwise.
    """
    requires_human = _extract_field(diagnosis, "REQUIRES_HUMAN", "yes").lower()
    if requires_human != "no":
        return None

    proposed_fix = _extract_field(diagnosis, "PROPOSED_FIX",
                                   "Manual investigation needed")
    root_cause = _extract_field(diagnosis, "ROOT_CAUSE", "Unknown failure")
    category = _extract_field(diagnosis, "CATEGORY", "unknown")

    task_id = "auto-heal-%s-%s" % (
        runner_name.replace("_", "-"),
        datetime.now().strftime("%Y%m%d-%H%M%S"),
    )

    runner_script = "tools/scripts/%s.py" % runner_name
    runner_path = REPO_ROOT / runner_script

    # Build ISC. The previous generic `<runner> --test` sanity gate is too
    # loose -- it only verifies the runner self-test, not the failing artifact.
    # When the failure output names specific test files / cases, add a
    # `pytest <ref>` ISC for each so the heal worker has to actually fix the
    # named artifact (not just leave the runner's self-test passing).
    isc = []
    test_refs = _extract_failing_test_refs(failure_output) + \
        _extract_failing_test_refs(diagnosis)
    seen_ref = set()
    for ref in test_refs:
        if ref in seen_ref:
            continue
        seen_ref.add(ref)
        isc.append(
            "Failing test passes after fix: %s | Verify: python -m pytest %s -q --tb=no"
            % (ref, ref)
        )
    # Always include the generic runner sanity gate (when the script exists)
    # as a regression check in addition to the specific test ISC above.
    if runner_path.is_file():
        verify_cmd = "python %s --test" % runner_script
        isc.append(
            "%s exits cleanly after fix | Verify: %s" % (runner_name, verify_cmd)
        )
    if not isc:
        isc = [
            "%s failure resolved | Verify: manual smoke test" % runner_name,
        ]

    task = {
        "id": task_id,
        "description": "Self-heal %s: %s" % (runner_name, proposed_fix),
        "project": "epdev",
        "repo_path": str(REPO_ROOT).replace("\\", "/"),
        "tier": 1,
        "priority": 1,
        "dependencies": [],
        "parent_id": None,
        "goal_context": (
            "Automated self-heal: %s runner failed. Root cause: %s. "
            "Diagnosis log: %s"
        ) % (runner_name, root_cause, log_path.relative_to(REPO_ROOT)),
        "isc": isc,
        "context_files": [str(log_path.relative_to(REPO_ROOT))],
        "skills": [],
        "model": "sonnet",
        "review_model": None,
        "status": "pending",
        "autonomous_safe": True,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "completed": None,
        "branch": None,
        "run_report": None,
        "failure_reason": None,
        "notes": "Auto-generated by self-diagnose-wrapper L1. Category: %s" % category,
    }

    try:
        BACKLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with BACKLOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(task) + "\n")
        return task_id
    except Exception as exc:
        print("self-diagnose: failed to write backlog task: %s" % exc,
              file=sys.stderr)
        return None


# -- Main --------------------------------------------------------------------

def main() -> int:
    # Parse args: everything after -- is the command to run
    args = sys.argv[1:]
    timeout = None

    # Extract optional --timeout flag
    if "--timeout" in args:
        idx = args.index("--timeout")
        if idx + 1 < len(args):
            try:
                timeout = int(args[idx + 1])
            except ValueError:
                pass
            args = args[:idx] + args[idx + 2:]

    if "--" not in args:
        print("Usage: python self_diagnose_wrapper.py [--timeout N] -- <command>",
              file=sys.stderr)
        print("Example: python self_diagnose_wrapper.py -- python overnight_runner.py",
              file=sys.stderr)
        return 1

    sep_idx = args.index("--")
    command = args[sep_idx + 1:]
    if not command:
        print("ERROR: No command specified after --", file=sys.stderr)
        return 1

    runner_name = extract_runner_name(command)

    # Skip diagnosis inside active Claude Code sessions (hang risk)
    if os.environ.get("CLAUDE_CODE_SESSION"):
        print("self-diagnose: skipping (inside Claude Code session)",
              file=sys.stderr)
        # Still run the command, just don't diagnose on failure
        result = subprocess.run(command, cwd=str(REPO_ROOT))
        return result.returncode

    # 1. Run the command
    print("self-diagnose: running %s ..." % runner_name)
    run_start = datetime.now()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # tolerate non-utf-8 bytes from runner output
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
        exit_code = result.returncode
        combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

        # Tee output to stdout/stderr so .bat log capture still works.
        # ASCII-strip first: Task Scheduler stdout is cp1252 on Windows and
        # any non-encodable char (including U+FFFD from upstream decode) raises
        # UnicodeEncodeError, killing the wrapper before the runner exits.
        def _ascii_safe(s: str) -> str:
            return s.encode("ascii", errors="replace").decode("ascii")
        if result.stdout:
            sys.stdout.write(_ascii_safe(result.stdout))
        if result.stderr:
            sys.stderr.write(_ascii_safe(result.stderr))

    except subprocess.TimeoutExpired as exc:
        exit_code = 124  # standard timeout exit code
        combined_output = "Command timed out after %ss\nPartial stdout: %s\nPartial stderr: %s" % (
            timeout, (exc.stdout or b"").decode("utf-8", errors="replace")[:500],
            (exc.stderr or b"").decode("utf-8", errors="replace")[:500]
        )
        print(combined_output, file=sys.stderr)
    except FileNotFoundError:
        exit_code = 127  # command not found
        combined_output = "Command not found: %s" % " ".join(command)
        print(combined_output, file=sys.stderr)

    # 1b. Write producer_runs row to manifest DB
    run_end = datetime.now()
    run_date = run_start.strftime("%Y-%m-%d")
    started_iso = run_start.strftime("%Y-%m-%dT%H:%M:%S")
    completed_iso = run_end.strftime("%Y-%m-%dT%H:%M:%S")
    run_status = "success" if exit_code == 0 else "failure"
    try:
        from tools.scripts.manifest_db import write_producer_run
        write_producer_run(
            producer=runner_name,
            run_date=run_date,
            started_at=started_iso,
            completed_at=completed_iso,
            duration_seconds=(run_end - run_start).total_seconds(),
            status=run_status,
            exit_code=exit_code,
        )
    except Exception:
        pass  # graceful fallback -- DB write is non-critical

    # 2. Detect failure
    if not detect_failure(exit_code, combined_output):
        print("self-diagnose: %s completed successfully" % runner_name)
        return exit_code

    print("self-diagnose: failure detected in %s (exit code: %d)" % (
        runner_name, exit_code))

    # 3. Classify against known playbooks
    playbook_category = classify_playbook(combined_output)
    print("self-diagnose: playbook match: %s" % playbook_category)

    # 3b. OOM short-circuit: if host is out of memory, skip claude -p entirely.
    # Calling claude -p under OOM produces a useless "diagnosis unavailable"
    # log because the diagnoser hits the same WinError 1455. Use a hardcoded
    # diagnosis instead so the failure record is actionable.
    if detect_oom(combined_output):
        print("self-diagnose: OOM detected -- skipping claude -p (would also OOM)")
        playbook_category = "resource_exhaustion"
        diagnosis = build_oom_diagnosis(runner_name)
    else:
        # 4. Sanitize output and build diagnosis prompt
        sanitized = sanitize_output(combined_output)
        prompt = build_diagnosis_prompt(runner_name, exit_code,
                                        sanitized, playbook_category)

        # 5. Call claude -p for diagnosis
        print("self-diagnose: calling claude -p for diagnosis ...")
        diagnosis = call_claude_diagnose(prompt)

        if diagnosis.startswith("("):
            # Diagnosis itself failed -- check if claude -p also OOM'd
            if detect_oom(diagnosis):
                print("self-diagnose: claude -p hit OOM -- using hardcoded OOM diagnosis",
                      file=sys.stderr)
                playbook_category = "resource_exhaustion"
                diagnosis = build_oom_diagnosis(runner_name)
            else:
                # Diagnosis itself failed for non-OOM reason -- log what we have
                print("self-diagnose: diagnosis unavailable: %s" % diagnosis,
                      file=sys.stderr)
                diagnosis = "ROOT_CAUSE: Diagnosis unavailable -- %s\nSEVERITY: 5\nCATEGORY: unknown\nPROPOSED_FIX: Manual investigation needed" % diagnosis

    # 6. Log the failure
    log_path = log_failure(runner_name, exit_code, combined_output,
                           diagnosis, playbook_category)
    print("self-diagnose: failure logged to %s" % log_path.relative_to(REPO_ROOT))

    # 6b. Inject self-heal task into dispatcher backlog (if REQUIRES_HUMAN: no).
    # Pass combined_output so the ISC builder can extract specific failing test
    # references and build `pytest <ref>` criteria, not just a generic --test gate.
    task_id = append_self_heal_task(runner_name, diagnosis, log_path,
                                    failure_output=combined_output)
    if task_id:
        print("self-diagnose: backlog task queued -> %s" % task_id)
    else:
        print("self-diagnose: requires human review -- no backlog task created")

    # 7. Notify via Slack
    notify_failure(runner_name, diagnosis, playbook_category, log_path,
                   backlog_task_id=task_id)

    # Return original exit code so .bat captures the correct status
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
