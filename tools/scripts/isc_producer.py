#!/usr/bin/env python3
"""ISC Producer -- daily automated verification scanner.

Scans all active PRDs for unchecked ISC criteria, runs isc_executor.py on each,
and produces a batch report. Creates backlog tasks for near-miss items.

SENSE-only: never writes to PRD files. Propose-only: never marks [x].

Usage:
    python tools/scripts/isc_producer.py
    python tools/scripts/isc_producer.py --verbose

Exit codes:
    0 = ran successfully (regardless of pass/fail counts)
    1 = no PRDs found or all errored
    2 = producer crash/timeout
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRD_GLOB = "memory/work/*/PRD.md"
ARCHIVED_DIR = REPO_ROOT / "memory" / "work" / "_archived"
REPORT_PATH = REPO_ROOT / "data" / "isc_producer_report.json"
ISC_PD_PATHS_PATH = REPO_ROOT / "data" / "isc_prd_paths.txt"
BACKLOG_PATH = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
EXECUTOR_SCRIPT = REPO_ROOT / "tools" / "scripts" / "isc_executor.py"
GLOBAL_TIMEOUT_S = 300
MAX_BACKLOG_TASKS = 10


def scan_prds() -> list[Path]:
    """Find all active PRDs, excluding archived."""
    prds = sorted(REPO_ROOT.glob(PRD_GLOB))
    return [p for p in prds if not p.is_relative_to(ARCHIVED_DIR)]


def run_executor(prd_path: Path) -> dict | None:
    """Run isc_executor.py on a single PRD and return parsed JSON."""
    try:
        result = subprocess.run(
            [sys.executable, str(EXECUTOR_SCRIPT),
             "--prd", str(prd_path), "--json", "--skip-format-gate"],
            capture_output=True, text=True, timeout=60,
            cwd=str(REPO_ROOT),
        )
        # Parse JSON from stdout (executor may print non-JSON to stderr)
        stdout = result.stdout.strip()
        if not stdout:
            return None
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return None
    except (json.JSONDecodeError, OSError):
        return None


def classify_near_miss(criterion: dict) -> bool:
    """Determine if a FAIL item is a near-miss (close to passing)."""
    if criterion.get("verdict") != "FAIL":
        return False
    evidence = criterion.get("evidence", "").lower()
    # Anti-criterion FAILs (Grep! negation) are regressions, not near-misses
    verify = criterion.get("verify_method", "").lower()
    if verify.startswith("grep!:"):
        return False
    # Near-miss heuristics: evidence shows partial completion
    near_miss_signals = ["file found", "directory found", "exists",
                         "1 match", "2 match"]
    return any(sig in evidence for sig in near_miss_signals)


def criterion_hash(criterion_text: str) -> str:
    """Generate a short hash for dedup."""
    return hashlib.sha256(criterion_text.encode()).hexdigest()[:12]


def load_existing_backlog_hashes() -> set[str]:
    """Load criterion hashes from existing isc-producer backlog tasks."""
    hashes = set()
    if not BACKLOG_PATH.is_file():
        return hashes
    try:
        for line in BACKLOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
                if task.get("source") == "isc-producer" and task.get("status") != "done":
                    h = task.get("criterion_hash", "")
                    if h:
                        hashes.add(h)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return hashes


def create_backlog_tasks(near_misses: list[dict], existing_hashes: set[str]) -> int:
    """Append backlog tasks for near-miss items via lib/backlog.backlog_append.

    Uses backlog_append (not raw file append) for: the read-modify-write
    lock, routine_id dedup, secret-path scrubbing, validation. Returns
    count created.
    """
    if not near_misses:
        return 0

    # Lazy import so the helper module doesn't need to be on sys.path at
    # import time (isc_producer ships as a standalone script).
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.backlog import backlog_append

    created = 0
    for item in near_misses:
        if created >= MAX_BACKLOG_TASKS:
            break
        h = criterion_hash(item["criterion"])
        if h in existing_hashes:
            continue  # skip duplicate
        verify_method = item.get("verify_method", "") or ""
        task = {
            "id": "isc-%s" % h,
            "description": "Fix near-miss ISC: %s" % item["criterion"][:120],
            "project": "epdev",
            "repo_path": str(REPO_ROOT).replace("\\", "/"),
            "tier": 0,
            "priority": 2,
            "goal_context": "ISC completion velocity -- item is close to passing",
            # Synthesize a pending_review-compatible ISC (Review verify method
            # is accepted when status=pending_review, see validate_task).
            "isc": [
                item["criterion"][:200] + " | Verify: Review",
            ],
            "context_files": [item.get("prd_path", "")],
            "skills": ["validation"],
            "model": "sonnet",
            "status": "pending_review",
            "autonomous_safe": False,
            "source": "isc-producer",
            "criterion_hash": h,
            "routine_id": "isc_producer:near_miss:%s" % h,
            "notes": (
                "Auto-generated by isc_producer. Verify method at discovery: %s"
                % (verify_method[:160] if verify_method else "(none)")
            ),
        }
        try:
            result = backlog_append(task)
        except ValueError:
            # Validation failure -- skip this item rather than crash the batch
            continue
        if result is not None:
            created += 1

    return created


def inject_batch_summary(report: dict) -> int:
    """Inject one pending_review row per batch when FAILs or ready_to_mark
    items exist, so the universal queue surfaces ISC state changes for
    human review. Deduped per-day via routine_id.

    Returns count of summary rows injected (0-2).
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.backlog import backlog_append

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary = report.get("summary", {})
    ready = report.get("ready_to_mark", [])
    fail_count = summary.get("fail", 0)
    injected = 0

    # Ready-to-mark batch -- reminds human to check off passing criteria
    if ready:
        task = {
            "description": (
                "[isc-producer] %d ISC items are ready to mark [x] "
                "across %d PRDs" % (len(ready), report.get("prds_scanned", 0))
            ),
            "tier": 0,
            "autonomous_safe": False,
            "status": "pending_review",
            "priority": 3,
            "isc": [
                "All ready_to_mark criteria are checked off in their PRDs "
                "| Verify: Review",
            ],
            "skills": [],
            "source": "isc-producer",
            "routine_id": "isc_producer:ready_to_mark:%s" % today,
            "notes": "See data/isc_producer_report.json for the full list.",
        }
        try:
            if backlog_append(task) is not None:
                injected += 1
        except ValueError:
            pass

    # Fail batch -- surfaces hard regressions (excluding near-misses, which
    # already get their own per-item rows above)
    if fail_count > 0:
        task = {
            "description": (
                "[isc-producer] %d ISC criteria FAIL across %d PRDs" %
                (fail_count, report.get("prds_scanned", 0))
            ),
            "tier": 0,
            "autonomous_safe": False,
            "status": "pending_review",
            "priority": 2,
            "isc": [
                "Each failing criterion is either fixed, marked deferred, "
                "or has its verify method corrected "
                "| Verify: Review",
            ],
            "skills": [],
            "source": "isc-producer",
            "routine_id": "isc_producer:fails:%s" % today,
            "notes": "See data/isc_producer_report.json for per-PRD breakdown.",
        }
        try:
            if backlog_append(task) is not None:
                injected += 1
        except ValueError:
            pass

    return injected


def build_report(prd_results: list[dict], duration_s: float,
                 tasks_created: int, timeout_hit: bool = False,
                 run_date: str | None = None) -> dict:
    """Build the final report JSON."""
    total = {"pass": 0, "fail": 0, "manual": 0, "error": 0}
    ready_to_mark = []
    by_prd = []

    for pr in prd_results:
        prd_path = pr["prd_path"]
        executor_output = pr["executor_output"]
        if executor_output is None:
            by_prd.append({
                "path": prd_path,
                "status": "ERROR",
                "summary": {"pass": 0, "fail": 0, "manual": 0, "error": 0},
                "criteria": [],
            })
            continue

        criteria = executor_output.get("criteria", [])
        prd_summary = {"pass": 0, "fail": 0, "manual": 0, "error": 0}
        prd_criteria = []

        for c in criteria:
            verdict = c.get("verdict", "ERROR").lower()
            prd_summary[verdict] = prd_summary.get(verdict, 0) + 1
            total[verdict] = total.get(verdict, 0) + 1

            entry = {
                "criterion": c.get("criterion", ""),
                "verdict": c.get("verdict", "ERROR"),
                "evidence": c.get("evidence", ""),
                "verify_method": c.get("verify_method", ""),
            }
            prd_criteria.append(entry)

            if verdict == "pass":
                ready_to_mark.append({
                    "prd_path": prd_path,
                    "criterion": c.get("criterion", ""),
                    "evidence": c.get("evidence", ""),
                })

        by_prd.append({
            "path": prd_path,
            "status": "OK",
            "summary": prd_summary,
            "criteria": prd_criteria,
        })

    return {
        "run_date": run_date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_duration_s": round(duration_s, 2),
        "timeout_hit": timeout_hit,
        "summary": total,
        "ready_to_mark": ready_to_mark,
        "near_miss_tasks_created": tasks_created,
        "prds_scanned": len(prd_results),
        "by_prd": by_prd,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="ISC Producer -- daily verification scanner")
    parser.add_argument("--verbose", action="store_true", help="Print per-PRD details")
    args = parser.parse_args()

    start = time.monotonic()
    run_start_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Scan PRDs
    prds = scan_prds()
    if not prds:
        print("ISC Producer: no active PRDs found at %s" % PRD_GLOB)
        return 1

    if args.verbose:
        print("ISC Producer: scanning %d PRDs..." % len(prds))

    # Execute per PRD
    prd_results = []
    near_misses = []
    timeout_hit = False

    for prd in prds:
        elapsed = time.monotonic() - start
        if elapsed > GLOBAL_TIMEOUT_S:
            print("ISC Producer: global timeout (%ds) reached after %d PRDs" % (
                GLOBAL_TIMEOUT_S, len(prd_results)))
            timeout_hit = True
            break

        rel_path = str(prd.relative_to(REPO_ROOT)).replace("\\", "/")
        executor_output = run_executor(prd)
        prd_results.append({
            "prd_path": rel_path,
            "executor_output": executor_output,
        })

        if executor_output and args.verbose:
            summary = executor_output.get("summary", {})
            print("  %s: %d PASS, %d FAIL, %d MANUAL" % (
                rel_path, summary.get("pass", 0),
                summary.get("fail", 0), summary.get("manual", 0)))

        # Collect near-misses
        if executor_output:
            for c in executor_output.get("criteria", []):
                if classify_near_miss(c):
                    near_misses.append({
                        "prd_path": rel_path,
                        "criterion": c.get("criterion", ""),
                        "evidence": c.get("evidence", ""),
                        "verify_method": c.get("verify_method", ""),
                    })

    # Create backlog tasks for near-misses
    existing_hashes = load_existing_backlog_hashes()
    tasks_created = create_backlog_tasks(near_misses, existing_hashes)

    # Build and write report
    duration_s = time.monotonic() - start
    report = build_report(prd_results, duration_s, tasks_created, timeout_hit,
                          run_start_ts)

    # Inject per-day batch summary rows into the universal backlog so
    # FAILs and ready_to_mark items surface through the dispatcher queue
    # (deduped per-day by routine_id).
    summary_rows = inject_batch_summary(report)
    report["batch_summary_rows_injected"] = summary_rows

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    # Write sidecar prd-paths file -- contains only prd_path values with no
    # verify_method or evidence strings, so Grep! anti-criteria targeting this
    # file avoid self-referential false positives from the main report JSON.
    prd_paths_txt = "\n".join(e["path"] for e in report["by_prd"])
    ISC_PD_PATHS_PATH.write_text(prd_paths_txt + "\n", encoding="utf-8")

    # ASCII summary for Task Scheduler log
    s = report["summary"]
    rtm = len(report["ready_to_mark"])
    print("ISC Producer: %d PRDs scanned in %.1fs" % (report["prds_scanned"], duration_s))
    print("  Total: %d PASS, %d FAIL, %d MANUAL, %d ERROR" % (
        s["pass"], s["fail"], s["manual"], s["error"]))
    print("  Ready to mark: %d items" % rtm)
    print("  Near-miss tasks created: %d" % tasks_created)
    print("  Report: %s" % REPORT_PATH)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ISC Producer: fatal error: %s" % exc)
        sys.exit(2)
