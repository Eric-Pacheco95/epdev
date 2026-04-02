"""Backlog health collector -- reads task_backlog.jsonl, outputs metric JSON.

Metrics emitted:
  backlog_pending_count  -- tasks with status == "pending"
  backlog_failed_count   -- tasks with status == "failed"
  backlog_done_count     -- tasks with status == "done"
  backlog_success_rate   -- done / (done + failed), 0.0-1.0; null if no terminal tasks
  backlog_total_count    -- total task records in backlog

Usage (standalone):
  python tools/scripts/collectors/backlog_health.py
  python tools/scripts/collectors/backlog_health.py --path path/to/task_backlog.jsonl

Output: JSON list of metric dicts, one per metric.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Project root is 3 levels above this file: collectors/ -> scripts/ -> tools/ -> root
_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BACKLOG = _ROOT / "orchestration" / "task_backlog.jsonl"


def _result(name: str, value, unit: str, detail: str = None) -> dict:
    return {"name": name, "value": value, "unit": unit, "detail": detail}


def collect_backlog_health(backlog_path: Path = None) -> list:
    """Read task_backlog.jsonl and return list of metric dicts."""
    if backlog_path is None:
        backlog_path = _DEFAULT_BACKLOG

    if not backlog_path.is_file():
        error_detail = "task_backlog.jsonl not found at %s" % backlog_path
        return [
            _result("backlog_pending_count", None, "count", error_detail),
            _result("backlog_failed_count", None, "count", error_detail),
            _result("backlog_done_count", None, "count", error_detail),
            _result("backlog_success_rate", None, "ratio", error_detail),
            _result("backlog_total_count", None, "count", error_detail),
        ]

    counts = {"pending": 0, "failed": 0, "done": 0, "other": 0}
    total = 0

    try:
        with backlog_path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed lines -- do not crash the collector
                    continue
                total += 1
                status = task.get("status", "")
                if status in counts:
                    counts[status] += 1
                else:
                    counts["other"] += 1
    except OSError as exc:
        error_detail = "read error: %s" % exc
        return [
            _result("backlog_pending_count", None, "count", error_detail),
            _result("backlog_failed_count", None, "count", error_detail),
            _result("backlog_done_count", None, "count", error_detail),
            _result("backlog_success_rate", None, "ratio", error_detail),
            _result("backlog_total_count", None, "count", error_detail),
        ]

    terminal = counts["done"] + counts["failed"]
    if terminal > 0:
        success_rate = round(counts["done"] / terminal, 4)
        rate_detail = "%d done, %d failed of %d terminal" % (
            counts["done"], counts["failed"], terminal
        )
    else:
        success_rate = None
        rate_detail = "no terminal tasks yet"

    return [
        _result("backlog_pending_count", counts["pending"], "count",
                "%d tasks pending" % counts["pending"]),
        _result("backlog_failed_count", counts["failed"], "count",
                "%d tasks failed" % counts["failed"]),
        _result("backlog_done_count", counts["done"], "count",
                "%d tasks done" % counts["done"]),
        _result("backlog_success_rate", success_rate, "ratio", rate_detail),
        _result("backlog_total_count", total, "count",
                "%d total tasks in backlog" % total),
    ]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backlog health collector")
    parser.add_argument("--path", default=None,
                        help="Path to task_backlog.jsonl (default: orchestration/task_backlog.jsonl)")
    args = parser.parse_args()

    backlog_path = Path(args.path) if args.path else None
    metrics = collect_backlog_health(backlog_path)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
