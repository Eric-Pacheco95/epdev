#!/usr/bin/env python3
"""followon_pending -- 5E-3 staging for LLM FOLLOW_UP lines (no direct backlog writes).

Worker output may contain lines:
  FOLLOW_UP: {"description": "...", "isc": ["..."]}

Rows append here; humans promote via promote_followon_pending.py -> backlog_append().
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.backlog import _exclusive_file_lock

DEFAULT_DIR = REPO_ROOT / "data" / "followon_pending"
DEFAULT_PATH = DEFAULT_DIR / "followon_pending.jsonl"

_last_id_us: int = 0


def _generate_id() -> str:
    global _last_id_us
    candidate = time.time_ns() // 1_000
    _last_id_us = max(candidate, _last_id_us + 1)
    return f"fp-{_last_id_us}"


def validate_follow_up_payload(payload: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    desc = payload.get("description")
    isc = payload.get("isc")
    has_desc = isinstance(desc, str) and bool(desc.strip())
    has_isc = (
        isinstance(isc, list)
        and len(isc) > 0
        and all(isinstance(x, str) for x in isc)
    )
    if not has_desc and not has_isc:
        errs.append("follow_up needs non-empty 'description' and/or non-empty 'isc' list")
    if isc is not None and not isinstance(isc, list):
        errs.append("'isc' must be a list of strings when present")
    elif isinstance(isc, list):
        for i, x in enumerate(isc):
            if not isinstance(x, str):
                errs.append("isc[%d] must be a string" % i)
    return errs


def followon_pending_append(
    record: dict[str, Any],
    path: Optional[Path] = None,
) -> dict[str, Any]:
    """Append one staging row. Idempotent file create; uses lock."""
    path = path or DEFAULT_PATH
    rec = dict(record)
    if rec.get("follow_up_task") is not None:
        errs = validate_follow_up_payload(rec["follow_up_task"])
        if errs:
            raise ValueError("follow_up_task validation failed:\n" + "\n".join(f"  - {e}" for e in errs))

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


_FOLLOW_UP_LINE = re.compile(
    r"^FOLLOW_UP:\s*(\{.*\})\s*$",
    re.MULTILINE,
)


def capture_follow_up_from_stdout(
    stdout: str,
    source_task_id: str,
    path: Optional[Path] = None,
) -> int:
    """Parse FOLLOW_UP: {...} lines from worker stdout; stage each. Returns count."""
    if not stdout or "FOLLOW_UP:" not in stdout:
        return 0
    count = 0
    for m in _FOLLOW_UP_LINE.finditer(stdout):
        raw_json = m.group(1)
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        errs = validate_follow_up_payload(payload)
        if errs:
            continue
        try:
            followon_pending_append(
                {
                    "source_task_id": source_task_id,
                    "follow_up_task": payload,
                    "raw_json": raw_json[:2000],
                },
                path=path,
            )
            count += 1
        except Exception:
            continue
    return count


def list_pending(path: Optional[Path] = None) -> list[dict[str, Any]]:
    path = path or DEFAULT_PATH
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return [r for r in rows if r.get("status") == "pending"]


def promote_one(
    row_id: str,
    path: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    """Promote a pending row into task_backlog via backlog_append. Returns backlog task or None."""
    from tools.scripts.lib.backlog import backlog_append

    path = path or DEFAULT_PATH
    if not path.is_file():
        return None

    lock_path = path.with_suffix(path.suffix + ".lock")
    with _exclusive_file_lock(lock_path):
        raw_lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        rows: list[dict[str, Any]] = []
        for ln in raw_lines:
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        idx = next(
            (
                i
                for i, r in enumerate(rows)
                if r.get("id") == row_id and r.get("status") == "pending"
            ),
            None,
        )
        if idx is None:
            return None
        target = rows[idx]
        fu = target.get("follow_up_task") or {}
        task = {
            "description": fu.get("description") or "Follow-up from worker FOLLOW_UP line",
            "tier": int(fu.get("tier", 1)),
            "priority": int(fu.get("priority", 5)),
            "autonomous_safe": bool(fu.get("autonomous_safe", False)),
            "status": "pending_review",
            "isc": list(fu.get("isc", [])) or [
                "Follow-up reviewed and promoted | Verify: Review",
            ],
            "context_files": list(fu.get("context_files", [])),
            "skills": list(fu.get("skills", [])),
            "notes": (
                (fu.get("notes") or "")
                + "\n[promoted from followon_pending %s source=%s]"
                % (target["id"], target.get("source_task_id"))
            ).strip(),
            "source": fu.get("source") or "follow_up_staging",
            "project": fu.get("project", "epdev"),
        }
        if fu.get("goal_context"):
            task["goal_context"] = fu["goal_context"]
        result = backlog_append(task)
        if result is None:
            return None
        rows[idx]["status"] = "promoted"
        rows[idx]["promoted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows[idx]["promoted_backlog_id"] = result.get("id")
        out = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
        path.write_text(out, encoding="utf-8")
        return result


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
