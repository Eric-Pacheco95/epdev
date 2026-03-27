#!/usr/bin/env python3
"""Minimal Slack notifier — stdlib only, no external deps.

Usage (from other scripts):
    from tools.scripts.slack_notify import notify, EPDEV, CRITICAL
    notify("message text")               # → #epdev (default)
    notify("message text", CRITICAL)     # → #general (must-see only)

Environment:
    SLACK_BOT_TOKEN  xoxb-... bot token from ClaudeActivities app (required)

If SLACK_BOT_TOKEN is not set, logs a warning to stderr and returns False silently
so hooks never crash the session on a missing token.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

EPDEV = "C0ANZKK12CD"
CRITICAL = "C0AKR43PDA4"

_API = "https://slack.com/api/chat.postMessage"


def notify(text: str, channel: str = EPDEV, *, username: str = "Jarvis") -> bool:
    """Post text to a Slack channel. Returns True on success."""
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        print(
            "slack_notify: SLACK_BOT_TOKEN not set — skipping Slack post",
            file=sys.stderr,
        )
        return False

    payload = json.dumps(
        {"channel": channel, "text": text, "username": username}
    ).encode()
    req = urllib.request.Request(
        _API,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read())
            if not body.get("ok"):
                print(f"slack_notify: API error — {body.get('error')}", file=sys.stderr)
                return False
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"slack_notify: request failed — {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # Quick smoke-test: python slack_notify.py "hello from Jarvis"
    msg = " ".join(sys.argv[1:]) or "Jarvis slack_notify smoke-test"
    ok = notify(msg)
    sys.exit(0 if ok else 1)
