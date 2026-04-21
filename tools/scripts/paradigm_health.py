#!/usr/bin/env python3
"""Paradigm Health Monitor -- SENSE layer for Jarvis infrastructure paradigms.

Measures adherence to the 10 core Jarvis infrastructure paradigms by running
deterministic shell/Python checks. Writes a JSON health report and posts to
Slack when alerts exist. No LLM calls -- runs in seconds.

Usage:
    python tools/scripts/paradigm_health.py              # full report
    python tools/scripts/paradigm_health.py --json       # machine-readable JSON only
    python tools/scripts/paradigm_health.py --test       # self-test

Outputs:
    data/paradigm_health.json     -- structured health report
    stdout                        -- ASCII summary table
    Slack #epdev                  -- alert summary (only when alerts exist)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.isc_templates import isc_paradigm_degraded

OUTPUT_FILE = REPO_ROOT / "data" / "paradigm_health.json"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
HISTORY_DIR = REPO_ROOT / "history"
AGENTS_DIR = REPO_ROOT / "orchestration" / "agents"
PRDS_DIR = REPO_ROOT / "memory" / "work"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# Thresholds: score must be >= threshold to be "healthy"
THRESHOLDS: dict[str, float] = {
    "system_intelligence":    0.5,   # meta: average of others
    "algorithm_adherence":    0.5,
    "isc_driven_development": 0.5,
    "constitutional_security": 0.5,
    "compound_learning":      0.5,
    "immutable_audit_trail":  0.5,
    "skill_first_routing":    0.5,
    "telos_identity_chain":   0.5,
    "sense_decide_act":       0.5,
    "context_routing":        0.5,
}

# Human-readable labels for display
LABELS: dict[str, str] = {
    "system_intelligence":    "System > Intelligence",
    "algorithm_adherence":    "TheAlgorithm Adherence",
    "isc_driven_development": "ISC-Driven Development",
    "constitutional_security": "Constitutional Security",
    "compound_learning":      "Compound Learning",
    "immutable_audit_trail":  "Immutable Audit Trail",
    "skill_first_routing":    "Skill-First Routing",
    "telos_identity_chain":   "TELOS Identity Chain",
    "sense_decide_act":       "SENSE/DECIDE/ACT",
    "context_routing":        "Context Routing",
}


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def _run(cmd: list[str] | str, timeout: int = 10) -> tuple[int, str, str]:
    """Run a command via subprocess. Returns (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            shell=isinstance(cmd, str),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except OSError as exc:
        return -1, "", str(exc)


def _run_python(script: str, args: list[str] = None, timeout: int = 10) -> tuple[int, str, str]:
    """Run a Python script in the repo root using the current interpreter."""
    cmd = [sys.executable, str(REPO_ROOT / script)] + (args or [])
    return _run(cmd, timeout=timeout)


# ---------------------------------------------------------------------------
# Individual paradigm metrics
# ---------------------------------------------------------------------------

def measure_algorithm_adherence() -> tuple[float, str]:
    """Count skills with VERIFY or LEARN section vs total skills.

    Proxy for TheAlgorithm adoption: skills that include verification and
    learning phases are following the 7-phase loop.
    """
    if not SKILLS_DIR.is_dir():
        return 0.0, "skills dir missing"

    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    total = len(skill_files)
    if total == 0:
        return 0.0, "0 skill files found"

    matches = 0
    for sf in skill_files:
        try:
            content = sf.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\bVERIFY\b|\bLEARN\b", content):
                matches += 1
        except OSError:
            pass

    score = matches / total
    return score, f"{matches}/{total} skills have VERIFY/LEARN"


def measure_isc_driven_development() -> tuple[float, str]:
    """Count PRD files that contain '| Verify:' patterns.

    Falls back gracefully -- no batch mode needed.
    """
    prd_files = list(PRDS_DIR.rglob("PRD.md")) + list(PRDS_DIR.rglob("*.prd.md"))
    if not prd_files:
        # Wider search: any .md in memory/work with ISC criteria
        prd_files = [
            f for f in PRDS_DIR.rglob("*.md")
            if "prd" in f.name.lower() or "isc" in f.name.lower()
        ]

    total = len(prd_files)
    if total == 0:
        return 0.0, "no PRD files found"

    compliant = 0
    for prd in prd_files:
        try:
            content = prd.read_text(encoding="utf-8", errors="replace")
            if "| Verify:" in content or "| Verify :" in content:
                compliant += 1
        except OSError:
            pass

    score = compliant / total
    return score, f"{compliant}/{total} PRDs have | Verify: patterns"


def measure_constitutional_security() -> tuple[float, str]:
    """Run the defensive test suite and extract pass rate."""
    defensive_dir = REPO_ROOT / "tests" / "defensive"
    if not defensive_dir.is_dir():
        return 0.0, "tests/defensive/ missing"

    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pytest", str(defensive_dir), "--tb=no", "-q"],
        timeout=30,
    )

    # pytest summary line: "X passed, Y failed in Zs" or "X passed in Zs"
    combined = stdout + stderr
    passed_match = re.search(r"(\d+) passed", combined)
    failed_match = re.search(r"(\d+) failed", combined)
    error_match = re.search(r"(\d+) error", combined)

    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    errors = int(error_match.group(1)) if error_match else 0

    total = passed + failed + errors
    if total == 0:
        # no tests collected -- not an error condition per se
        return 0.5, "no defensive tests collected"

    score = passed / total
    return score, f"{passed}/{total} defensive tests pass"


def measure_compound_learning() -> tuple[float, str]:
    """Measure signal recency and synthesis freshness.

    Score = 0.5 * (signals_in_14d / 10 capped at 1.0) +
            0.5 * (synthesis_fresh within 7 days)
    """
    now = datetime.now(timezone.utc)
    cutoff_14d = now - timedelta(days=14)

    # Count recent signal files (skip processed/ subdir)
    recent_signals = 0
    if SIGNALS_DIR.is_dir():
        for f in SIGNALS_DIR.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime >= cutoff_14d:
                    recent_signals += 1
            except OSError:
                pass

    signal_score = min(1.0, recent_signals / 10)

    # Check synthesis freshness (any synthesis file within 7 days)
    cutoff_7d = now - timedelta(days=7)
    synthesis_fresh = False
    if SYNTHESIS_DIR.is_dir():
        for f in SYNTHESIS_DIR.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime >= cutoff_7d:
                    synthesis_fresh = True
                    break
            except OSError:
                pass

    synthesis_score = 1.0 if synthesis_fresh else 0.0
    score = 0.5 * signal_score + 0.5 * synthesis_score

    freshness = "synthesis fresh" if synthesis_fresh else "synthesis stale"
    return score, f"{recent_signals} signals/14d, {freshness}"


def measure_immutable_audit_trail() -> tuple[float, str]:
    """Count history/decisions files that have all required template fields.

    Scoped to history/decisions/ only -- security/, changes/, events/, validations/
    have their own formats and are not expected to follow the decision template.
    Required fields: Date, and (Context or Description), and (Rationale or Action).
    """
    decisions_dir = HISTORY_DIR / "decisions"
    if not decisions_dir.is_dir():
        return 0.0, "history/decisions/ dir missing"

    all_files = list(decisions_dir.glob("*.md"))
    # Exclude README files
    candidate_files = [f for f in all_files if f.name.lower() != "readme.md"]

    if not candidate_files:
        return 0.0, "no history files found"

    compliant = 0
    for f in candidate_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            # Accept both "- **Date**:" and "**Date:**" formats (format evolved over time)
            has_date = bool(re.search(r"(\*\*Date[\*:*]|^- Date:|^Date:)", content, re.MULTILINE | re.IGNORECASE))
            # Accept both explicit Context/Description headers AND ## section headings
            # (older files use ## What Was Built, **Decision:** etc. instead of **Context**)
            has_context = bool(re.search(
                r"(\*\*(Context|Description|Decision|What Was Built|Background)\*\*"
                r"|^- Context:|^- Description:|^## [A-Z])",
                content, re.MULTILINE | re.IGNORECASE
            ))
            has_rationale = bool(re.search(
                r"(\*\*(Rationale|Action|Action Taken|Why|Outcome|Result|Decision|Gate Status|Key Architecture)\*\*"
                r"|^- Rationale:|^- Action Taken:|^- Action:|^- Why:"
                r"|^## (Rationale|Decision|Why|Outcome|Result|Consequences|Gate Status"
                r"|Key Architecture|What Was Built|What Was Implemented|Rules Added"
                r"|Implementation|Applied|Status))",
                content, re.MULTILINE | re.IGNORECASE
            ))
            if has_date and has_context and has_rationale:
                compliant += 1
        except OSError:
            pass

    score = compliant / len(candidate_files)
    return score, f"{compliant}/{len(candidate_files)} decision files have required fields"


def measure_skill_first_routing() -> tuple[float, str]:
    """Count skills with ## One-liner section vs total skills."""
    if not SKILLS_DIR.is_dir():
        return 0.0, "skills dir missing"

    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    total = len(skill_files)
    if total == 0:
        return 0.0, "0 skill files found"

    with_oneliner = 0
    for sf in skill_files:
        try:
            content = sf.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^## One-liner", content, re.MULTILINE):
                with_oneliner += 1
        except OSError:
            pass

    score = with_oneliner / total
    return score, f"{with_oneliner}/{total} skills have ## One-liner"


def measure_telos_identity_chain() -> tuple[float, str]:
    """Count TELOS files modified in last 30 days."""
    if not TELOS_DIR.is_dir():
        return 0.0, "memory/work/telos/ missing"

    telos_files = [f for f in TELOS_DIR.glob("*.md") if f.name != "README.md"]
    total = len(telos_files)
    if total == 0:
        return 0.0, "no TELOS files found"

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    fresh = 0
    for f in telos_files:
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                fresh += 1
        except OSError:
            pass

    score = fresh / total
    return score, f"{fresh}/{total} TELOS files updated in last 30 days"


def measure_sense_decide_act() -> tuple[float, str]:
    """Count agent files that have all 6 required sections.

    Uses same section detection logic as validate_agents.py.
    """
    if not AGENTS_DIR.is_dir():
        return 0.0, "orchestration/agents/ missing"

    required_sections = [
        "Identity", "Mission", "Critical Rules",
        "Deliverables", "Workflow", "Success Metrics",
    ]
    agent_files = list(AGENTS_DIR.glob("*.md"))
    total = len(agent_files)
    if total == 0:
        return 0.0, "no agent files found"

    compliant = 0
    for af in agent_files:
        try:
            content = af.read_text(encoding="utf-8", errors="replace")
            headings = re.findall(r"^## (.+)$", content, re.MULTILINE)
            headings = [h.strip() for h in headings]
            all_present = all(
                any(req.lower() in h.lower() for h in headings)
                for req in required_sections
            )
            if all_present:
                compliant += 1
        except OSError:
            pass

    score = compliant / total
    return score, f"{compliant}/{total} agents have all 6 sections"


def measure_context_routing() -> tuple[float, str]:
    """Check that all context routing table entries in CLAUDE.md point to existing files."""
    if not CLAUDE_MD.is_file():
        return 0.0, "CLAUDE.md missing"

    try:
        content = CLAUDE_MD.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0.0, "cannot read CLAUDE.md"

    # Extract backtick-quoted paths from the context routing table
    # Matches lines like: | Topic | `path/to/file` |
    routing_paths = re.findall(r"`([^`]+\.md[^`]*)`", content)
    # Only keep paths that look like relative file/dir paths (no spaces, no code snippets)
    routing_paths = [p for p in routing_paths if "/" in p and " " not in p]

    if not routing_paths:
        return 0.5, "no routing paths found in CLAUDE.md"

    # Deduplicate
    routing_paths = list(dict.fromkeys(routing_paths))

    existing = 0
    for rel_path in routing_paths:
        target = REPO_ROOT / rel_path
        if target.exists():
            existing += 1

    score = existing / len(routing_paths)
    return score, f"{existing}/{len(routing_paths)} context routing paths exist"


# ---------------------------------------------------------------------------
# Measurement dispatcher
# ---------------------------------------------------------------------------

def run_all_metrics() -> dict[str, dict]:
    """Run all paradigm metrics. Returns raw results dict."""
    measurements = {}

    paradigm_funcs = [
        ("algorithm_adherence",    measure_algorithm_adherence),
        ("isc_driven_development", measure_isc_driven_development),
        ("constitutional_security", measure_constitutional_security),
        ("compound_learning",      measure_compound_learning),
        ("immutable_audit_trail",  measure_immutable_audit_trail),
        ("skill_first_routing",    measure_skill_first_routing),
        ("telos_identity_chain",   measure_telos_identity_chain),
        ("sense_decide_act",       measure_sense_decide_act),
        ("context_routing",        measure_context_routing),
    ]

    for key, func in paradigm_funcs:
        try:
            score, metric = func()
        except Exception as exc:  # noqa: BLE001
            score = 0.0
            metric = f"error: {exc}"

        threshold = THRESHOLDS.get(key, 0.5)
        status = "healthy" if score >= threshold else "degraded"
        measurements[key] = {
            "score": round(score, 4),
            "metric": metric,
            "threshold": threshold,
            "status": status,
        }

    # meta: system_intelligence = average of all others
    other_scores = [v["score"] for v in measurements.values()]
    overall = sum(other_scores) / len(other_scores) if other_scores else 0.0
    meta_threshold = THRESHOLDS.get("system_intelligence", 0.5)
    measurements["system_intelligence"] = {
        "score": round(overall, 4),
        "metric": f"avg of {len(other_scores)} paradigms",
        "threshold": meta_threshold,
        "status": "healthy" if overall >= meta_threshold else "degraded",
    }

    return measurements


def build_report(measurements: dict[str, dict]) -> dict:
    """Build the final JSON report structure."""
    other_scores = [
        v["score"] for k, v in measurements.items()
        if k != "system_intelligence"
    ]
    overall = sum(other_scores) / len(other_scores) if other_scores else 0.0

    alerts = [
        f"{LABELS.get(k, k)}: {v['metric']} (score {v['score']:.2f} < threshold {v['threshold']:.2f})"
        for k, v in measurements.items()
        if v["status"] == "degraded"
    ]

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "paradigms": measurements,
        "overall_score": round(overall, 4),
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _status_char(status: str) -> str:
    """ASCII status indicator."""
    return "OK" if status == "healthy" else "!!"


def print_summary(report: dict) -> None:
    """Print compact ASCII summary table to stdout."""
    overall = report["overall_score"]
    alerts = report["alerts"]
    timestamp = report.get("timestamp", "unknown")

    print(f"Paradigm Health Report -- {timestamp}")
    print(f"Overall Score: {overall:.2f}")
    print("-" * 72)
    print(f"{'Status':<6} {'Score':<6} {'Paradigm':<28} {'Metric'}")
    print("-" * 72)

    # Print system_intelligence last
    ordered_keys = [k for k in LABELS if k != "system_intelligence"] + ["system_intelligence"]
    paradigms = report["paradigms"]

    for key in ordered_keys:
        if key not in paradigms:
            continue
        p = paradigms[key]
        label = LABELS.get(key, key)
        status_str = _status_char(p["status"])
        metric = p["metric"]
        # Truncate long metrics for table fit
        if len(metric) > 35:
            metric = metric[:32] + "..."
        print(f"[{status_str}]  {p['score']:.2f}   {label:<28} {metric}")

    print("-" * 72)

    if alerts:
        print(f"\nALERTS ({len(alerts)}):")
        for alert in alerts:
            print(f"  !! {alert}")
    else:
        print("\nAll paradigms healthy.")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    """Smoke test: verify all metric functions return valid (score, metric) tuples."""
    print("Running paradigm_health self-test...")
    failures = []

    metric_funcs = [
        ("algorithm_adherence",    measure_algorithm_adherence),
        ("isc_driven_development", measure_isc_driven_development),
        ("constitutional_security", measure_constitutional_security),
        ("compound_learning",      measure_compound_learning),
        ("immutable_audit_trail",  measure_immutable_audit_trail),
        ("skill_first_routing",    measure_skill_first_routing),
        ("telos_identity_chain",   measure_telos_identity_chain),
        ("sense_decide_act",       measure_sense_decide_act),
        ("context_routing",        measure_context_routing),
    ]

    for name, func in metric_funcs:
        try:
            score, metric = func()
            assert isinstance(score, float), f"score not float: {type(score)}"
            assert 0.0 <= score <= 1.0, f"score out of range: {score}"
            assert isinstance(metric, str), f"metric not str: {type(metric)}"
            assert len(metric) > 0, "metric is empty string"
            print(f"  PASS  {name}: {score:.2f} -- {metric}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            print(f"  FAIL  {name}: {exc}")

    # Verify report structure
    measurements = run_all_metrics()
    report = build_report(measurements)
    required_keys = {"timestamp", "paradigms", "overall_score", "alerts"}
    missing_keys = required_keys - set(report.keys())
    if missing_keys:
        failures.append(f"report missing keys: {missing_keys}")
        print(f"  FAIL  report structure: missing {missing_keys}")
    else:
        print(f"  PASS  report structure: all keys present")

    # Verify JSON serializable
    try:
        json.dumps(report)
        print(f"  PASS  JSON serializable")
    except (TypeError, ValueError) as exc:
        failures.append(f"JSON serialization: {exc}")
        print(f"  FAIL  JSON serialization: {exc}")

    print()
    if failures:
        print(f"FAIL -- {len(failures)} test(s) failed")
        return 1
    else:
        print(f"PASS -- all self-tests passed")
        return 0


# ---------------------------------------------------------------------------
# Task injection (SENSE -> backlog producer)
# ---------------------------------------------------------------------------

def inject_paradigm_tasks(report: dict) -> list[dict]:
    """Inject pending_review tasks for degraded paradigms into the backlog.

    Uses routine_id dedup so the same paradigm won't generate duplicate tasks
    while it remains degraded. Returns list of injected task dicts.
    """
    try:
        from tools.scripts.lib.backlog import backlog_append
    except ImportError:
        return []

    injected = []
    for key, p in report["paradigms"].items():
        if p["status"] != "degraded":
            continue
        label = LABELS.get(key, key)
        task = {
            "description": (
                f"Investigate degraded paradigm: {label} "
                f"(score {p['score']:.2f} < {p['threshold']:.2f})"
            ),
            "tier": 1,
            "priority": 4,
            "autonomous_safe": False,
            "status": "pending_review",
            "routine_id": f"paradigm_health_{key}",
            "isc": isc_paradigm_degraded(label, float(p["threshold"])),
            "notes": (
                f"Auto-generated by paradigm_health.py. "
                f"Metric: {p['metric']}. "
                f"Score {p['score']:.2f} below threshold {p['threshold']:.2f}."
            ),
            "context_files": [
                "tools/scripts/paradigm_health.py",
                "data/paradigm_health.json",
            ],
        }
        result = backlog_append(task)
        if result is not None:
            injected.append(result)

    return injected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Paradigm health monitor -- SENSE layer for Jarvis paradigms."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output only (suppress ASCII summary)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run self-test and exit",
    )
    args = parser.parse_args()

    if args.test:
        return run_self_test()

    # Run all metrics
    measurements = run_all_metrics()
    report = build_report(measurements)

    # Write JSON output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    # ASCII summary
    print_summary(report)
    print(f"\nReport written to: {OUTPUT_FILE}")

    # Post to Slack only when alerts exist
    if report["alerts"]:
        alert_count = len(report["alerts"])
        overall = report["overall_score"]
        alert_lines = "\n".join(f"  !! {a}" for a in report["alerts"])
        msg = (
            f"[Paradigm Health] {alert_count} alert(s) -- overall {overall:.2f}\n"
            f"{alert_lines}"
        )
        try:
            from tools.scripts.slack_notify import notify
            notify(msg, severity="routine")
        except ImportError:
            pass  # Slack notify not available -- skip silently

    # Inject pending_review tasks for degraded paradigms
    injected = inject_paradigm_tasks(report)
    degraded_count = len(report["alerts"])
    if injected:
        print(f"\nBacklog: {len(injected)} new task(s) injected for degraded paradigm(s).")
    elif degraded_count:
        print(f"\nBacklog: {degraded_count} degraded paradigm(s) -- tasks already queued (deduped).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
