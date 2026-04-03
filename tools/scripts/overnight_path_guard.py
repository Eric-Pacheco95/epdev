#!/usr/bin/env python3
"""Path guard for overnight autonomous agents -- stdlib only.

Validates that file write operations stay within allowed directories.
Used by overnight runner wrapper to enforce TELOS protection and
constitutional security rules at the OS level, independent of
LLM system prompt compliance.

Usage:
    from overnight_path_guard import validate_write_path, PathViolation

    # In wrapper script:
    try:
        validate_write_path(filepath, dimension="scaffolding")
    except PathViolation as e:
        log_security_event(str(e))
        sys.exit(1)

    # CLI smoke test:
    python overnight_path_guard.py --test
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# --- NEVER-WRITE paths (constitutional rules, non-negotiable) ---
BLOCKED_PATHS = [
    REPO_ROOT / "memory" / "work" / "telos",
    REPO_ROOT / "history",  # History is sacred -- immutable audit trail
    REPO_ROOT / "security" / "constitutional-rules.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".claude" / "settings.json",
    REPO_ROOT / ".env",
]

BLOCKED_PATTERNS = [
    "*.pem", "*.key", "*credentials*", "*secret*",
    ".ssh", ".aws",
]

# --- PER-DIMENSION allowed write directories ---
DIMENSION_SCOPES = {
    "scaffolding": [
        REPO_ROOT / ".claude" / "skills",
    ],
    "codebase_health": [
        REPO_ROOT / "tools" / "scripts",
        REPO_ROOT / "tests",
    ],
    "knowledge_synthesis": [
        REPO_ROOT / "memory" / "learning" / "synthesis",
    ],
    "external_monitoring": [
        REPO_ROOT / "memory" / "work" / "jarvis",
    ],
    "prompt_quality": [
        REPO_ROOT / ".claude" / "skills",
    ],
    # algorithm_adherence merges into scaffolding scope (.claude/skills/).
    # Kept as an explicit entry so dimension-level checks remain readable
    # and any future split does not silently lose scope enforcement.
    "algorithm_adherence": [
        REPO_ROOT / ".claude" / "skills",
    ],
    "cross_project": [
        # Report-only -- writes go to autoresearch dir only
    ],
}

# Always allowed for all dimensions (run reports, state files)
ALWAYS_ALLOWED = [
    REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch",
    REPO_ROOT / "data",
]


class PathViolation(Exception):
    """Raised when a write path violates overnight safety rules."""
    pass


def validate_write_path(filepath: str | Path, dimension: str = "unknown") -> Path:
    """Validate that a file path is safe for overnight agent writes.

    Args:
        filepath: The path the agent wants to write to.
        dimension: Which overnight dimension is running.

    Returns:
        Resolved absolute path if valid.

    Raises:
        PathViolation: If the path is blocked or out of scope.
    """
    p = Path(filepath).resolve()

    # 1. Must be within repo root (path traversal prevention)
    try:
        p.relative_to(REPO_ROOT)
    except ValueError:
        raise PathViolation(
            f"BLOCKED: path outside repo root: {p}"
        )

    # 2. Check blocked paths (TELOS, constitutional rules, secrets)
    for blocked in BLOCKED_PATHS:
        blocked_resolved = blocked.resolve()
        if p == blocked_resolved or _is_under(p, blocked_resolved):
            raise PathViolation(
                f"BLOCKED: write to protected path: {p} "
                f"(matches: {blocked})"
            )

    # 3. Check blocked patterns
    name_lower = p.name.lower()
    for pattern in BLOCKED_PATTERNS:
        pat = pattern.lower().replace("*", "")
        if pat in name_lower:
            raise PathViolation(
                f"BLOCKED: filename matches protected pattern: {p} "
                f"(pattern: {pattern})"
            )

    # 4. Check dimension-specific scope
    allowed_dirs = DIMENSION_SCOPES.get(dimension, []) + ALWAYS_ALLOWED
    if not allowed_dirs:
        # cross_project has no write dirs except ALWAYS_ALLOWED
        allowed_dirs = ALWAYS_ALLOWED

    for allowed in allowed_dirs:
        allowed_resolved = allowed.resolve()
        if p == allowed_resolved or _is_under(p, allowed_resolved):
            return p

    raise PathViolation(
        f"BLOCKED: path not in allowed scope for dimension '{dimension}': {p} "
        f"(allowed: {[str(d) for d in allowed_dirs]})"
    )


def _is_under(child: Path, parent: Path) -> bool:
    """Check if child path is under parent directory."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def run_self_test() -> bool:
    """Run smoke tests to verify the guard works."""
    passed = 0
    failed = 0

    def expect_blocked(path, dim, label):
        nonlocal passed, failed
        try:
            validate_write_path(path, dim)
            print(f"  FAIL: {label} -- should have been blocked")
            failed += 1
        except PathViolation:
            print(f"  PASS: {label} -- correctly blocked")
            passed += 1

    def expect_allowed(path, dim, label):
        nonlocal passed, failed
        try:
            validate_write_path(path, dim)
            print(f"  PASS: {label} -- correctly allowed")
            passed += 1
        except PathViolation as e:
            print(f"  FAIL: {label} -- should have been allowed: {e}")
            failed += 1

    print("Overnight Path Guard -- Self Test")
    print(f"Repo root: {REPO_ROOT}")
    print()

    # TELOS protection (the #1 security requirement)
    expect_blocked(
        REPO_ROOT / "memory/work/telos/GOALS.md",
        "scaffolding", "TELOS write blocked"
    )
    expect_blocked(
        REPO_ROOT / "memory/work/telos/MISSION.md",
        "knowledge_synthesis", "TELOS write blocked (any dimension)"
    )

    # Constitutional rules protection
    expect_blocked(
        REPO_ROOT / "security/constitutional-rules.md",
        "codebase_health", "Constitutional rules blocked"
    )

    # CLAUDE.md protection
    expect_blocked(
        REPO_ROOT / "CLAUDE.md",
        "scaffolding", "CLAUDE.md blocked"
    )

    # Secret file patterns
    expect_blocked(
        REPO_ROOT / "tools/credentials.json",
        "scaffolding", "Credentials file blocked"
    )
    expect_blocked(
        REPO_ROOT / ".env",
        "scaffolding", ".env blocked"
    )

    # Path traversal
    expect_blocked(
        Path("C:/Users/ericp/.ssh/id_rsa"),
        "scaffolding", "Path outside repo blocked"
    )

    # Allowed writes
    expect_allowed(
        REPO_ROOT / ".claude/skills/autoresearch/SKILL.md",
        "scaffolding", "Skill file write allowed (scaffolding)"
    )
    expect_allowed(
        REPO_ROOT / "memory/work/jarvis/autoresearch/overnight-2026-03-28/report.md",
        "scaffolding", "Autoresearch report always allowed"
    )
    expect_allowed(
        REPO_ROOT / "data/overnight_state.json",
        "scaffolding", "State file always allowed"
    )
    expect_allowed(
        REPO_ROOT / "tools/scripts/some_script.py",
        "codebase_health", "Script write allowed (codebase_health)"
    )

    # Scope enforcement (wrong dimension)
    expect_blocked(
        REPO_ROOT / ".claude/skills/test/SKILL.md",
        "codebase_health", "Skill write blocked (wrong dimension)"
    )
    expect_blocked(
        REPO_ROOT / "tools/scripts/test.py",
        "scaffolding", "Script write blocked (wrong dimension)"
    )

    print()
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    if "--test" in sys.argv:
        success = run_self_test()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python overnight_path_guard.py --test")
        print("Import validate_write_path() for programmatic use.")
