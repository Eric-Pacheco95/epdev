#!/usr/bin/env python3
"""Observability hook: append structured JSONL event records for tool calls and session boundaries.

PAI-aligned event capture — writes to history/events/YYYY-MM-DD.jsonl so a
future dashboard (Langfuse, custom UI, or simple jq queries) can consume them.

Hook types handled:
  - PreToolUse  → intent record (success: null — tool not yet called)
  - PostToolUse → outcome record (success: true/false based on is_error)
  - Stop        → session-end boundary record (tool: "_session")

Wire all three in settings.json. No matcher needed (captures all tools).

Schema per event line:
  {
    "ts":          "2026-03-27T14:30:00Z",  # ISO-8601 UTC
    "hook":        "PostToolUse",
    "session_id":  "...",                   # from Claude Code
    "tool":        "Bash",
    "success":     true | false | null,     # null = intent (PreToolUse), no outcome yet
    "error":       null | "...",            # truncated to 120 chars, PostToolUse only
    "input_len":   42,                      # char length of serialized input (not the input itself)
    "stop_reason": null | "end_turn"        # Stop hook only
  }

Sensitive data (inputs, outputs) is intentionally excluded — length only.
This keeps the log safe to commit and avoids secret leakage.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
EVENTS_DIR = REPO_ROOT / "history" / "events"

# lib imports — insert script dir so lib.* resolves without repo-root prefix
sys.path.insert(0, str(Path(__file__).parent))
from lib.file_lock import locked_append


def main() -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    hook_type = "PostToolUse"
    tool_name = ""
    session_id = ""
    success: bool | None = True
    error_msg = None
    input_len = 0
    stop_reason = None
    read_file_path: str | None = None
    _skill_name = ""
    _advisor_word_count = 0

    try:
        data = json.load(sys.stdin)
        hook_type = data.get("hook_event_name", hook_type)
        tool_name = data.get("tool_name", "")
        session_id = data.get("session_id", "")

        if hook_type == "PreToolUse":
            # Intent record — tool hasn't run yet, no outcome
            success = None
            tool_input = data.get("tool_input", {})
            input_len = len(json.dumps(tool_input))
            # Capture skill name for skill_usage tracking
            if tool_name == "Skill" and isinstance(tool_input, dict):
                _skill_name = tool_input.get("skill", "")

        elif hook_type == "PostToolUse":
            response = data.get("tool_response", {})
            if isinstance(response, dict):
                success = not response.get("is_error", False)
                if not success:
                    content = response.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            c.get("text", "") if isinstance(c, dict) else str(c)
                            for c in content
                        )
                    error_msg = str(content)[:120] if content else "error"
            tool_input = data.get("tool_input", {})
            input_len = len(json.dumps(tool_input))
            # FR-005 whitelist: Read.file_path only; no other tool input captured
            if tool_name == "Read" and isinstance(tool_input, dict):
                fp = tool_input.get("file_path")
                if isinstance(fp, str):
                    read_file_path = fp
            if tool_name == "advisor":
                adv_content = response.get("content", "") if isinstance(response, dict) else ""
                if isinstance(adv_content, list):
                    adv_content = " ".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in adv_content
                    )
                _advisor_word_count = len(str(adv_content).split())

        elif hook_type == "Stop":
            # Session boundary — marks end of a session for aggregation
            tool_name = "_session"
            success = True
            stop_reason = data.get("stop_reason", "end_turn") or "end_turn"

    except (json.JSONDecodeError, EOFError):
        now_utc = datetime.now(timezone.utc)
        error_record: dict = {
            "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": "parse_error",
            "session_id": "",
            "tool": "",
            "success": False,
            "error": "malformed stdin",
            "input_len": 0,
        }
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = EVENTS_DIR / f"{now_utc.strftime('%Y-%m-%d')}.jsonl"
        locked_append(log_path, json.dumps(error_record))
        sys.exit(1)

    now_utc = datetime.now(timezone.utc)
    record: dict = {
        "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook": hook_type,
        "session_id": session_id,
        "tool": tool_name,
        "success": success,
        "error": error_msg,
        "input_len": input_len,
    }
    if stop_reason is not None:
        record["stop_reason"] = stop_reason
    if read_file_path is not None:
        record["file_path"] = read_file_path

    log_path = EVENTS_DIR / f"{now_utc.strftime('%Y-%m-%d')}.jsonl"
    locked_append(log_path, json.dumps(record))

    # Advisor call stub — hook fires before model responds; model appends catch assessment separately
    if tool_name == "advisor" and hook_type == "PostToolUse":
        advisor_log = REPO_ROOT / "data" / "advisor_log.jsonl"
        advisor_log.parent.mkdir(parents=True, exist_ok=True)
        stub = {
            "date": now_utc.strftime("%Y-%m-%d"),
            "session_id": session_id,
            "event": "advisor_called",
            "output_word_count": _advisor_word_count,
            "advisor_changed_plan": None,
            "catch_summary": "PENDING",
        }
        locked_append(advisor_log, json.dumps(stub))

    # Track skill invocations in manifest DB
    if tool_name == "Skill" and hook_type == "PreToolUse" and session_id:
        try:
            if _skill_name:
                from tools.scripts.manifest_db import write_skill_usage
                write_skill_usage(
                    session_id=session_id,
                    skill_name=_skill_name,
                    invoked_at=now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
        except Exception:
            pass  # graceful fallback

    sys.exit(0)


if __name__ == "__main__":
    main()
