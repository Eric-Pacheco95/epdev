#!/usr/bin/env python3
"""Lightweight ntfy push notifier — stdlib only, no external deps.

Usage (from other scripts):
    from tools.scripts.ntfy_notify import push
    push("Jarvis needs you", body="Tool permission waiting")
    push("Session ended", priority="low")

Environment:
    NTFY_TOPIC   your private ntfy topic name (required — keep secret)
    NTFY_SERVER  ntfy server base URL (default: https://ntfy.sh)

If NTFY_TOPIC is not set, logs a warning to stderr and returns False silently
so hooks never crash the session on a missing env var.

Priority levels: max, high, default, low, min
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

_DEFAULT_SERVER = "https://ntfy.sh"


def push(
    title: str,
    body: str = "",
    *,
    priority: str = "default",
    tags: list[str] | None = None,
) -> bool:
    """Send a push notification via ntfy. Returns True on success."""
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print(
            "ntfy_notify: NTFY_TOPIC not set — skipping ntfy push",
            file=sys.stderr,
        )
        return False

    server = os.environ.get("NTFY_SERVER", _DEFAULT_SERVER).rstrip("/")
    url = f"{server}/{topic}"

    payload: dict = {"topic": topic, "title": title, "priority": priority}
    if body:
        payload["message"] = body
    if tags:
        payload["tags"] = tags

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"ntfy_notify: request failed — {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # Smoke-test: python ntfy_notify.py "Test title" "Test body"
    args = sys.argv[1:]
    title_ = args[0] if args else "Jarvis ntfy smoke-test"
    body_ = args[1] if len(args) > 1 else ""
    ok = push(title_, body_)
    sys.exit(0 if ok else 1)
