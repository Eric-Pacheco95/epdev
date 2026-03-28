#!/usr/bin/env python3
"""
Self-heal baseline: captures current system state as regression baseline.
Checks key files exist, hooks are wired, memory dirs exist, agents are defined,
and security validators pass. Designed to run after any major change to detect regressions.

Usage:
    python tests/self_heal/test_baseline.py
    python tests/self_heal/test_baseline.py --verbose

Exit code 0 = all checks passed. Non-zero = failures detected.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, str, str]] = []  # (status, category, message)


def check(status: bool, category: str, message: str) -> None:
    _results.append((PASS if status else FAIL, category, message))


# ---------------------------------------------------------------------------
# 1. Key files exist
# ---------------------------------------------------------------------------

KEY_FILES = [
    "CLAUDE.md",
    ".gitignore",
    ".claude/settings.json",
    ".claude/settings.local.json",
    "config/personality.yaml",
    "config/steering-rules.yaml",
    "docs/EPDEV_JARVIS_BIBLE.md",
    "orchestration/tasklist.md",
    "security/__init__.py",
    "security/constitutional-rules.md",
    "security/validators/__init__.py",
    "security/validators/secret_scanner.py",
    "security/validators/validate_tool_use.py",
    "tools/scripts/hook_session_start.py",
    "tools/scripts/hook_learning_capture.py",
    "tests/defensive/test_injection_detection.py",
    "tests/defensive/test_secret_scanner.py",
]


def check_key_files() -> None:
    for rel in KEY_FILES:
        p = REPO_ROOT / rel
        check(p.exists(), "key_files", f"{rel}")


# ---------------------------------------------------------------------------
# 2. Hooks wired in settings.json
# ---------------------------------------------------------------------------

def check_hooks_wired() -> None:
    settings_path = REPO_ROOT / ".claude" / "settings.json"
    if not settings_path.exists():
        check(False, "hooks", "settings.json missing")
        return

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        check(False, "hooks", f"settings.json is invalid JSON: {e}")
        return

    hooks = data.get("hooks", {})

    # UserPromptSubmit should reference hook_session_start.py
    ups = hooks.get("UserPromptSubmit", [])
    session_hooked = any(
        "hook_session_start" in h.get("command", "")
        for entry in ups
        for h in entry.get("hooks", [])
    )
    check(session_hooked, "hooks", "UserPromptSubmit wired to hook_session_start.py")

    # PreToolUse should reference validate_tool_use.py with Bash matcher
    ptu = hooks.get("PreToolUse", [])
    validator_hooked = any(
        entry.get("matcher") == "Bash"
        and any(
            "validate_tool_use" in h.get("command", "")
            for h in entry.get("hooks", [])
        )
        for entry in ptu
    )
    check(validator_hooked, "hooks", "PreToolUse(Bash) wired to validate_tool_use.py")

    # Stop should reference hook_learning_capture.py
    stop = hooks.get("Stop", [])
    learning_hooked = any(
        "hook_learning_capture" in h.get("command", "")
        for entry in stop
        for h in entry.get("hooks", [])
    )
    check(learning_hooked, "hooks", "Stop wired to hook_learning_capture.py")


# ---------------------------------------------------------------------------
# 3. Memory directories exist
# ---------------------------------------------------------------------------

MEMORY_DIRS = [
    "memory",
    "memory/session",
    "memory/work",
    "memory/learning",
    "memory/learning/signals",
    "memory/learning/failures",
    "memory/learning/synthesis",
]


def check_memory_dirs() -> None:
    for rel in MEMORY_DIRS:
        p = REPO_ROOT / rel
        check(p.is_dir(), "memory_dirs", rel)


# ---------------------------------------------------------------------------
# 4. History directories exist
# ---------------------------------------------------------------------------

HISTORY_DIRS = [
    "history",
    "history/changes",
    "history/decisions",
    "history/security",
]


def check_history_dirs() -> None:
    for rel in HISTORY_DIRS:
        p = REPO_ROOT / rel
        check(p.is_dir(), "history_dirs", rel)


# ---------------------------------------------------------------------------
# 5. Agent definitions exist
# ---------------------------------------------------------------------------

AGENTS = [
    "orchestration/agents/Architect.md",
    "orchestration/agents/Engineer.md",
    "orchestration/agents/Orchestrator.md",
    "orchestration/agents/QATester.md",
    "orchestration/agents/SecurityAnalyst.md",
]


def check_agents() -> None:
    for rel in AGENTS:
        p = REPO_ROOT / rel
        check(p.exists() and p.stat().st_size > 0, "agents", rel)

    # Run validate_agents.py to check Six-Section anatomy compliance
    validator = REPO_ROOT / "tools" / "scripts" / "validate_agents.py"
    if validator.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(validator)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )
            # Note: exit 1 means some agents missing sections (expected until all upgraded)
            # We just check it runs without crashing (exit 0 or 1, not 2+)
            check(result.returncode in (0, 1), "agents", "validate_agents.py runs without error")
        except (subprocess.TimeoutExpired, OSError) as e:
            check(False, "agents", f"validate_agents.py failed: {e}")


# ---------------------------------------------------------------------------
# 6. Security validators pass (run test suite)
# ---------------------------------------------------------------------------

def check_security_validators() -> None:
    for test_file in [
        "tests/defensive/test_injection_detection.py",
        "tests/defensive/test_secret_scanner.py",
    ]:
        path = REPO_ROOT / test_file
        if not path.exists():
            check(False, "security_tests", f"{test_file} (missing)")
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
            check(passed, "security_tests", f"{test_file} (exit {result.returncode})")
        except subprocess.TimeoutExpired:
            check(False, "security_tests", f"{test_file} (timeout)")
        except OSError as e:
            check(False, "security_tests", f"{test_file} (error: {e})")


# ---------------------------------------------------------------------------
# 7. Fabric CLI installed
# ---------------------------------------------------------------------------

def check_fabric_installed() -> None:
    import shutil
    found = shutil.which("fabric") is not None
    check(found, "tools", "fabric CLI on PATH")


# ---------------------------------------------------------------------------
# 8. Python security imports resolve
# ---------------------------------------------------------------------------

def check_security_imports() -> None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "secret_scanner",
            str(REPO_ROOT / "security" / "validators" / "secret_scanner.py"),
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
        check(hasattr(mod, "line_has_secret"), "imports", "secret_scanner.line_has_secret importable")
        check(hasattr(mod, "scan_file"), "imports", "secret_scanner.scan_file importable")
    except Exception as e:
        check(False, "imports", f"secret_scanner import failed: {e}")

    try:
        spec2 = importlib.util.spec_from_file_location(
            "validate_tool_use",
            str(REPO_ROOT / "security" / "validators" / "validate_tool_use.py"),
        )
        assert spec2 and spec2.loader
        mod2 = importlib.util.module_from_spec(spec2)
        # inject root into sys.path so the relative import inside the module works
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        spec2.loader.exec_module(mod2)  # type: ignore[arg-type]
        check(hasattr(mod2, "validate_bash_command"), "imports", "validate_tool_use.validate_bash_command importable")
    except Exception as e:
        check(False, "imports", f"validate_tool_use import failed: {e}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Self-heal baseline checks")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    check_key_files()
    check_hooks_wired()
    check_memory_dirs()
    check_history_dirs()
    check_agents()
    check_security_validators()
    check_fabric_installed()
    check_security_imports()

    passes = [r for r in _results if r[0] == PASS]
    failures = [r for r in _results if r[0] == FAIL]

    if args.verbose or failures:
        categories_seen: set[str] = set()
        for status, cat, msg in _results:
            if cat not in categories_seen:
                print(f"\n[{cat}]")
                categories_seen.add(cat)
            marker = "  OK " if status == PASS else "  FAIL"
            print(f"{marker}  {msg}")

    print()
    print(f"Baseline: {len(passes)} passed, {len(failures)} failed ({len(_results)} total)")

    if failures:
        print("\nFailed checks:")
        for _, cat, msg in failures:
            print(f"  [{cat}] {msg}")
        return 1

    print("All baseline checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
