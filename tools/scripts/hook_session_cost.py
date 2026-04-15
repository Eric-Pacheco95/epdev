#!/usr/bin/env python3
"""Stop hook: capture session cost record to JSONL event log.

Writes a session_cost event to history/events/YYYY-MM-DD.jsonl.
Claude Code does not currently expose token counts in the Stop payload,
so this script records what IS available (session_id, stop_reason, timestamp)
and leaves token/cost fields as null placeholders.

When Claude Code eventually exposes token data in the Stop payload,
update the _extract_token_data() function -- the schema stays the same.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = REPO_ROOT / "history" / "events"

sys.path.insert(0, str(Path(__file__).parent))
from lib.file_lock import locked_append


def _extract_token_data(data: dict) -> dict:
    """Extract token/cost data from the Stop payload or environment.

    Currently returns all nulls because Claude Code does not expose
    token counts. This is the single function to update when that changes.
    """
    result = {
        "cost_usd": None,
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
    }

    # Future: check data keys for token fields
    for key in ("input_tokens", "output_tokens", "cache_read_tokens"):
        val = data.get(key)
        if val is not None:
            try:
                result[key] = int(val)
            except (ValueError, TypeError):
                pass

    cost = data.get("cost_usd") or data.get("total_cost")
    if cost is not None:
        try:
            result["cost_usd"] = float(cost)
        except (ValueError, TypeError):
            pass

    # Future: check environment variables
    for env_key, field in [
        ("CLAUDE_SESSION_INPUT_TOKENS", "input_tokens"),
        ("CLAUDE_SESSION_OUTPUT_TOKENS", "output_tokens"),
        ("CLAUDE_SESSION_COST_USD", "cost_usd"),
    ]:
        val = os.environ.get(env_key)
        if val is not None and result[field] is None:
            try:
                result[field] = float(val) if field == "cost_usd" else int(val)
            except (ValueError, TypeError):
                pass

    return result


def build_cost_record(data: dict) -> dict:
    """Build a session_cost event record from Stop hook payload."""
    now_utc = datetime.now(timezone.utc)
    session_id = data.get("session_id", "")
    stop_reason = data.get("stop_reason", "end_turn") or "end_turn"

    token_data = _extract_token_data(data)

    has_any_token_data = any(v is not None for v in token_data.values())
    note = None if has_any_token_data else (
        "token counts unavailable -- Claude Code does not expose in Stop payload"
    )

    record = {
        "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook": "Stop",
        "type": "session_cost",
        "session_id": session_id,
        "stop_reason": stop_reason,
        "cost_usd": token_data["cost_usd"],
        "input_tokens": token_data["input_tokens"],
        "output_tokens": token_data["output_tokens"],
        "cache_read_tokens": token_data["cache_read_tokens"],
    }
    if note:
        record["note"] = note

    return record


def write_cost_record(record: dict) -> Path:
    """Write a cost record to the daily JSONL file with file locking. Returns the file path."""
    ts = record.get("ts", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    date_str = ts[:10]  # YYYY-MM-DD from ISO timestamp
    log_path = EVENTS_DIR / f"{date_str}.jsonl"
    locked_append(log_path, json.dumps(record))
    return log_path


def main() -> None:
    data = {}
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        now_utc = datetime.now(timezone.utc)
        error_record = {
            "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": "Stop",
            "type": "session_cost",
            "session_id": "",
            "stop_reason": "parse_error",
            "cost_usd": None,
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "parse_error": True,
            "success": False,
        }
        write_cost_record(error_record)
        sys.exit(1)

    record = build_cost_record(data)
    write_cost_record(record)
    sys.exit(0)


if __name__ == "__main__":
    main()
