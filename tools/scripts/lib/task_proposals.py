#!/usr/bin/env python3
"""task_proposals -- append-only queue for human-approved backlog promotion.

Autonomous systems MUST NOT write to task_backlog.jsonl directly (PRD_phase5).
They may append structured proposals here when JARVIS_TASK_PROPOSALS_ENABLED=true.
Eric batch-reviews and promotes accepted rows into orchestration/task_backlog.jsonl.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reuse backlog lock primitive (same sidecar pattern).
from tools.scripts.lib.backlog import _exclusive_file_lock
DEFAULT_PATH = REPO_ROOT / "orchestration" / "task_proposals.jsonl"

_last_id_us: int = 0


def _generate_id() -> str:
    global _last_id_us
    candidate = time.time_ns() // 1_000
    _last_id_us = max(candidate, _last_id_us + 1)
    return f"proposal-{_last_id_us}"


def validate_proposal(rec: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not isinstance(rec.get("title"), str) or not rec["title"].strip():
        errs.append("'title' must be a non-empty string")
    if not isinstance(rec.get("rationale"), str) or not str(rec["rationale"]).strip():
        errs.append("'rationale' must be a non-empty string")
    st = rec.get("source", "unknown")
    if not isinstance(st, str):
        errs.append("'source' must be a string")
    sug = rec.get("suggested_task")
    if sug is not None and not isinstance(sug, dict):
        errs.append("'suggested_task' must be a dict or omitted")
    return errs


def proposal_append(
    record: dict[str, Any],
    path: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    """Append one proposal row. Returns the stored record, or None if skipped.

    Skips (returns None) when JARVIS_TASK_PROPOSALS_ENABLED is unset/false/0.
    """
    if os.environ.get("JARVIS_TASK_PROPOSALS_ENABLED", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        print(
            "task_proposals: JARVIS_TASK_PROPOSALS_ENABLED not set -- skip append",
            file=sys.stderr,
        )
        return None

    path = path or DEFAULT_PATH
    rec = dict(record)
    errs = validate_proposal(rec)
    if errs:
        raise ValueError("proposal validation failed:\n" + "\n".join(f"  - {e}" for e in errs))

    if not rec.get("id"):
        rec["id"] = _generate_id()
    if not rec.get("created"):
        rec["created"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "status" not in rec:
        rec["status"] = "pending"

    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    lock_path = path.with_suffix(path.suffix + ".lock")

    with _exclusive_file_lock(lock_path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

    return rec


def count_by_status(path: Optional[Path] = None) -> dict[str, int]:
    path = path or DEFAULT_PATH
    counts: dict[str, int] = {}
    if not path.is_file():
        return counts
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        st = str(row.get("status", "unknown"))
        counts[st] = counts.get(st, 0) + 1
    return counts
