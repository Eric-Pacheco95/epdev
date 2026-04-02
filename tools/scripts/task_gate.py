#!/usr/bin/env python3
"""Task Gate -- unified routing for autonomous vs human-needed work.

Phase 5C: all task proposals flow through this gate before entering
the dispatcher backlog or escalating to Slack for human input.

Routing decides WHERE (backlog vs Slack escalation).
backlog_append() handles HOW (validation, dedup, atomic write).

Usage (from other scripts):
    from tools.scripts.task_gate import propose_task

    result = propose_task(
        description="Run /security-audit and produce findings report",
        project="epdev",
        goal_context="Weekly security posture check",
        skills=["security-audit"],
        isc=["Audit report exists | Verify: test -f memory/learning/signals/*security*"],
        context_files=["security/constitutional-rules.md"],
        source="heartbeat",          # which producer proposed this
    )
    # result.route = "backlog" | "decision" | "skipped"
    # result.reason = why it was routed this way
    # result.task_id = assigned ID if routed to backlog

CLI:
    python -m tools.scripts.task_gate --description "..." --skills security-audit
    python -m tools.scripts.task_gate --self-test
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# -- Paths ------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
AUTONOMY_MAP = REPO_ROOT / "orchestration" / "skill_autonomy_map.json"

# -- Unified backlog write backend ------------------------------------------
from tools.scripts.lib.backlog import backlog_append

# Max tier for autonomous routing (matches dispatcher)
MAX_AUTONOMOUS_TIER = 2

# Keywords that suggest architectural decisions (heuristic for check 3)
_ARCH_KEYWORDS = re.compile(
    r"\b(?:architect|migration|schema|breaking|redesign|refactor.+entire"
    r"|replace.+system|new.+dependency|adopt|deprecat|rewrite)\b",
    re.IGNORECASE,
)





# -- Result type ------------------------------------------------------------

@dataclass
class GateResult:
    """Result of routing a task through the gate."""
    route: str          # "backlog" or "decision"
    reason: str         # human-readable explanation
    task_id: Optional[str] = None   # set if routed to backlog
    check_results: dict = field(default_factory=dict)  # per-check pass/fail


# -- Autonomy map loading ---------------------------------------------------

_autonomy_cache: Optional[dict] = None


def _load_autonomy_map() -> dict:
    """Load skill autonomy map. Cached after first call."""
    global _autonomy_cache
    if _autonomy_cache is not None:
        return _autonomy_cache
    if AUTONOMY_MAP.exists():
        data = json.loads(AUTONOMY_MAP.read_text(encoding="utf-8"))
        # Strip _meta key
        _autonomy_cache = {k: v for k, v in data.items() if not k.startswith("_")}
    else:
        _autonomy_cache = {}
    return _autonomy_cache


# -- ISC validation ----------------------------------------------------------

def _has_verifiable_isc(isc_list: list[str]) -> bool:
    """Check that at least one ISC has a Verify: tag with a command.

    This is a lightweight routing check (does the task HAVE verifiable ISC?).
    Full command-level validation is handled downstream by backlog_append()
    via isc_common.classify_verify_method().
    """
    for criterion in isc_list:
        if "| Verify:" not in criterion and "|Verify:" not in criterion:
            continue
        verify_part = criterion.split("Verify:")[-1].strip()
        if verify_part:
            return True
    return False


# -- Gate checks -------------------------------------------------------------

def _check_has_isc(isc: list[str]) -> tuple[bool, str]:
    """Check 1: Task has at least one verifiable ISC."""
    if not isc:
        return False, "No ISC criteria provided"
    if not _has_verifiable_isc(isc):
        return False, "No ISC has a verifiable command from the allowlist"
    return True, "Has verifiable ISC"


def _check_skill_tier(skills: list[str]) -> tuple[bool, str]:
    """Check 2: All referenced skills are Tier 0-1 and autonomous_safe."""
    if not skills:
        # No skill required -- pure ISC task, that's fine
        return True, "No skill constraint (ISC-only task)"

    autonomy = _load_autonomy_map()
    for skill in skills:
        info = autonomy.get(skill)
        if info is None:
            return False, f"Skill '{skill}' not found in autonomy map"
        tier = info.get("tier", 99)
        if tier > MAX_AUTONOMOUS_TIER:
            return False, f"Skill '{skill}' is Tier {tier} (max autonomous: {MAX_AUTONOMOUS_TIER})"
        if not info.get("autonomous_safe", False):
            return False, f"Skill '{skill}' is not marked autonomous_safe"
    return True, "All skills are Tier 0-1 and autonomous_safe"


def _check_no_arch_keywords(description: str, goal_context: str) -> tuple[bool, str]:
    """Check 3: Heuristic -- description doesn't contain architectural keywords."""
    combined = f"{description} {goal_context}"
    match = _ARCH_KEYWORDS.search(combined)
    if match:
        return False, f"Architectural keyword detected: '{match.group()}'"
    return True, "No architectural keywords detected"


# -- Backlog I/O (read-only, for dedup + test cleanup) ----------------------

def _read_backlog() -> list[dict]:
    """Read all tasks from JSONL backlog."""
    if not BACKLOG_FILE.exists():
        return []
    tasks = []
    for line in BACKLOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tasks.append(json.loads(line))
    return tasks


# -- Dedup check -------------------------------------------------------------

def _is_duplicate(description: str, tasks: list[dict]) -> bool:
    """Check if a task with the same description already exists and is pending."""
    desc_lower = description.lower().strip()
    for t in tasks:
        if t.get("status") in ("pending", "claimed", "executing"):
            if t.get("description", "").lower().strip() == desc_lower:
                return True
    return False


# -- Main gate function ------------------------------------------------------

def propose_task(
    description: str,
    project: str = "epdev",
    goal_context: str = "",
    skills: Optional[list[str]] = None,
    isc: Optional[list[str]] = None,
    context_files: Optional[list[str]] = None,
    source: str = "unknown",
    tier: Optional[int] = None,
    model: str = "sonnet",
    notify_on_decision: bool = True,
) -> GateResult:
    """Route a task proposal through the gate.

    Returns GateResult with route="backlog" (task added to JSONL)
    or route="decision" (escalated to #jarvis-decisions).
    """
    skills = skills or []
    isc = isc or []
    context_files = context_files or []

    checks: dict[str, dict] = {}

    # -- Check 1: Has verifiable ISC? --
    passed, reason = _check_has_isc(isc)
    checks["has_isc"] = {"passed": passed, "reason": reason}
    if not passed:
        return _route_decision(
            description, reason, checks, source, notify_on_decision
        )

    # -- Check 2: Skills are Tier 0-1 and autonomous_safe? --
    passed, reason = _check_skill_tier(skills)
    checks["skill_tier"] = {"passed": passed, "reason": reason}
    if not passed:
        return _route_decision(
            description, reason, checks, source, notify_on_decision
        )

    # -- Check 3: No architectural keywords? (heuristic) --
    passed, reason = _check_no_arch_keywords(description, goal_context)
    checks["no_arch_keywords"] = {"passed": passed, "reason": reason}
    if not passed:
        return _route_decision(
            description, reason, checks, source, notify_on_decision
        )

    # -- All checks passed: route to backlog --

    # Description-based dedup (heartbeat tasks don't have routine_id)
    backlog = _read_backlog()
    if _is_duplicate(description, backlog):
        return GateResult(
            route="skipped",
            reason="Duplicate: identical pending task already in backlog",
            check_results=checks,
        )

    # Determine tier from skill map if not explicitly provided
    if tier is None:
        autonomy = _load_autonomy_map()
        tier = max(
            (autonomy.get(s, {}).get("tier", 0) for s in skills),
            default=0,
        )

    # Build task dict -- backlog_append() handles: ID generation, auto-fill
    # optional fields, ISC validation, atomic write
    task = {
        "description": description,
        "project": project,
        "repo_path": str(REPO_ROOT) if project == "epdev" else "",
        "tier": tier,
        "priority": 2,  # default medium; dispatcher sorts by priority
        "goal_context": goal_context,
        "isc": isc,
        "context_files": context_files,
        "skills": skills,
        "model": model,
        "autonomous_safe": True,
        "notes": f"Auto-proposed by {source}",
        "source": source,
    }

    try:
        result = backlog_append(task, backlog_path=BACKLOG_FILE)
    except ValueError as exc:
        # backlog_append validation failed -- escalate to human
        return _route_decision(
            description, f"Validation failed: {exc}",
            checks, source, notify_on_decision,
        )

    if result is None:
        # Deduped by backlog_append (routine_id collision)
        return GateResult(
            route="skipped",
            reason="Deduped by backlog_append (routine_id)",
            check_results=checks,
        )

    task_id = result["id"]
    print(f"task_gate: {task_id} -> backlog (source={source})", file=sys.stderr)

    return GateResult(
        route="backlog",
        reason="All checks passed",
        task_id=task_id,
        check_results=checks,
    )


def _route_decision(
    description: str,
    reason: str,
    checks: dict,
    source: str,
    notify: bool,
) -> GateResult:
    """Route a task to #jarvis-decisions via Slack."""
    if notify:
        try:
            from tools.scripts.slack_notify import notify as slack_notify

            msg = (
                f"Task Gate: needs your input\n"
                f"Source: {source}\n"
                f"Task: {description}\n"
                f"Blocked by: {reason}\n"
                f"---\n"
                f"Reply in a session to refine and re-submit."
            )
            slack_notify(msg, severity="decision")
        except Exception as exc:
            print(f"task_gate: Slack notify failed: {exc}", file=sys.stderr)

    print(f"task_gate: -> decision (reason={reason})", file=sys.stderr)

    return GateResult(
        route="decision",
        reason=reason,
        check_results=checks,
    )


# -- Self-test ---------------------------------------------------------------

def self_test() -> bool:
    """Run gate self-tests. Returns True if all pass."""
    print("\n=== Task Gate Self-Test ===\n")
    ok = True

    # Test 1: Task with valid ISC and Tier 0 skill passes
    print("Test 1: Valid Tier 0 task passes gate...")
    result = propose_task(
        description="Run security audit on repo",
        skills=["review-code"],
        isc=["Report exists | Verify: test -f report.md"],
        source="self-test",
        notify_on_decision=False,
    )
    if result.route != "backlog":
        print(f"  FAIL: expected backlog, got {result.route}: {result.reason}")
        ok = False
    else:
        print(f"  PASS: routed to backlog as {result.task_id}")

    # Test 2: Duplicate is skipped
    print("Test 2: Duplicate task is skipped...")
    result2 = propose_task(
        description="Run security audit on repo",
        skills=["review-code"],
        isc=["Report exists | Verify: test -f report.md"],
        source="self-test",
        notify_on_decision=False,
    )
    if result2.route != "skipped":
        print(f"  FAIL: expected skipped, got {result2.route}")
        ok = False
    else:
        print("  PASS: duplicate detected and skipped")

    # Test 3: No ISC -> decision
    print("Test 3: No ISC -> decision...")
    result3 = propose_task(
        description="Do something vague",
        skills=["review-code"],
        isc=[],
        source="self-test",
        notify_on_decision=False,
    )
    if result3.route != "decision":
        print(f"  FAIL: expected decision, got {result3.route}")
        ok = False
    else:
        print(f"  PASS: routed to decision ({result3.reason})")

    # Test 4: Tier 3 skill -> decision
    print("Test 4: Tier 3 skill -> decision...")
    result4 = propose_task(
        description="Update TELOS identity files",
        skills=["telos-update"],
        isc=["TELOS updated | Verify: test -f memory/work/telos/identity.md"],
        source="self-test",
        notify_on_decision=False,
    )
    if result4.route != "decision":
        print(f"  FAIL: expected decision, got {result4.route}")
        ok = False
    else:
        print(f"  PASS: Tier 3 blocked ({result4.reason})")

    # Test 5: Architectural keyword -> decision
    print("Test 5: Architectural keyword -> decision...")
    result5 = propose_task(
        description="Redesign the entire notification system",
        skills=["review-code"],
        isc=["Design doc exists | Verify: test -f design.md"],
        source="self-test",
        notify_on_decision=False,
    )
    if result5.route != "decision":
        print(f"  FAIL: expected decision, got {result5.route}")
        ok = False
    else:
        print(f"  PASS: arch keyword caught ({result5.reason})")

    # Test 6: ISC without Verify command -> decision
    print("Test 6: ISC without verify command -> decision...")
    result6 = propose_task(
        description="Check something",
        skills=["review-code"],
        isc=["Something is true"],
        source="self-test",
        notify_on_decision=False,
    )
    if result6.route != "decision":
        print(f"  FAIL: expected decision, got {result6.route}")
        ok = False
    else:
        print(f"  PASS: unverifiable ISC blocked ({result6.reason})")

    # Test 7: No skill constraint (ISC-only) passes
    print("Test 7: No skill (ISC-only task) passes...")
    result7 = propose_task(
        description="Verify heartbeat snapshot exists",
        skills=[],
        isc=["Snapshot exists | Verify: test -f data/heartbeat_snapshot.json"],
        source="self-test",
        notify_on_decision=False,
    )
    if result7.route != "backlog":
        print(f"  FAIL: expected backlog, got {result7.route}: {result7.reason}")
        ok = False
    else:
        print(f"  PASS: ISC-only task accepted as {result7.task_id}")

    # Test 8: Unknown skill -> decision
    print("Test 8: Unknown skill -> decision...")
    result8 = propose_task(
        description="Run a skill that doesn't exist",
        skills=["nonexistent-skill"],
        isc=["Something | Verify: test -f foo"],
        source="self-test",
        notify_on_decision=False,
    )
    if result8.route != "decision":
        print(f"  FAIL: expected decision, got {result8.route}")
        ok = False
    else:
        print(f"  PASS: unknown skill blocked ({result8.reason})")

    # Cleanup: remove self-test tasks from backlog
    backlog = _read_backlog()
    cleaned = [t for t in backlog if t.get("source") != "self-test"]
    if len(cleaned) < len(backlog):
        BACKLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(BACKLOG_FILE.parent), suffix=".tmp", prefix="backlog_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for t in cleaned:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
            os.replace(tmp_path, str(BACKLOG_FILE))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        print(f"\nCleaned up {len(backlog) - len(cleaned)} self-test tasks from backlog.")

    print(f"\n{'ALL TESTS PASSED' if ok else 'SOME TESTS FAILED'}")
    return ok


# -- CLI ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Gate -- route proposals")
    parser.add_argument("--self-test", action="store_true", help="Run self-tests")
    parser.add_argument("--description", type=str, help="Task description")
    parser.add_argument("--project", type=str, default="epdev")
    parser.add_argument("--goal-context", type=str, default="")
    parser.add_argument("--skills", type=str, nargs="*", default=[])
    parser.add_argument("--isc", type=str, nargs="*", default=[])
    parser.add_argument("--context-files", type=str, nargs="*", default=[])
    parser.add_argument("--source", type=str, default="cli")
    parser.add_argument("--model", type=str, default="sonnet")
    parser.add_argument("--dry-run", action="store_true", help="Check gate without writing")

    args = parser.parse_args()

    if args.self_test:
        success = self_test()
        sys.exit(0 if success else 1)

    if not args.description:
        parser.print_help()
        sys.exit(1)

    result = propose_task(
        description=args.description,
        project=args.project,
        goal_context=args.goal_context,
        skills=args.skills,
        isc=args.isc,
        context_files=args.context_files,
        source=args.source,
        model=args.model,
        notify_on_decision=not args.dry_run,
    )

    print(json.dumps({
        "route": result.route,
        "reason": result.reason,
        "task_id": result.task_id,
        "checks": result.check_results,
    }, indent=2))
