#!/usr/bin/env python3
"""Notification hook: push to iPhone via ntfy when Jarvis needs attention.

Fires when:
  - Claude Code is waiting for user permission on a tool call
  - Claude Code has been idle > 60 seconds waiting for input

Reads Claude Code Notification event JSON from stdin.
Posts to ntfy → iPhone ntfy app.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make ntfy_notify importable from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.scripts.ntfy_notify import push  # noqa: E402

_MAX_BODY_LEN = 200
_MIN_ELAPSED_SECONDS = 300  # 5 minutes
_PROMPT_TS_FILE = Path(__file__).resolve().parents[2] / ".claude" / "prompt_ts.json"


def _prompt_elapsed_seconds() -> float:
    """Return seconds since the last UserPromptSubmit, or 0 if unknown."""
    try:
        data = json.loads(_PROMPT_TS_FILE.read_text(encoding="utf-8"))
        return time.time() - float(data["ts"])
    except (OSError, KeyError, ValueError, TypeError):
        return 0.0


def main() -> None:
    # Read Notification event data from stdin
    notification_type = "needs_attention"
    message = ""
    tool_name = ""

    try:
        data = json.load(sys.stdin)
        notification_type = data.get("notification_type", "needs_attention")
        message = data.get("message", "")
        # Tool info lives inside tool_input for some event shapes
        tool_input = data.get("tool_input", {})
        tool_name = data.get("tool_name", tool_input.get("name", ""))
    except (json.JSONDecodeError, EOFError):
        pass

    if notification_type == "permission_request":
        title = f"Jarvis: approve {tool_name or 'tool'}?"
        body = (message or "Waiting for your approval in the terminal.")[:_MAX_BODY_LEN]
        priority = "high"
        tags = ["brain", "warning"]
    else:
        # Idle / completion notification — only fire if prompt ran > 5 minutes
        elapsed = _prompt_elapsed_seconds()
        if elapsed < _MIN_ELAPSED_SECONDS:
            sys.exit(0)
        title = "Jarvis is waiting for you"
        body = (message or "Claude Code is idle — check your terminal.")[:_MAX_BODY_LEN]
        priority = "default"
        tags = ["brain"]

    push(title, body, priority=priority, tags=tags)
    sys.exit(0)


if __name__ == "__main__":
    main()
