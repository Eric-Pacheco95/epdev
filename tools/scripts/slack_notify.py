#!/usr/bin/env python3
"""Unified Slack notifier — severity routing, dedup, daily caps.

Phase 4C: all Jarvis Slack traffic flows through this module.

Usage (from other scripts):
    from tools.scripts.slack_notify import notify, EPDEV, CRITICAL
    notify("message text")                          # routine -> #epdev
    notify("message text", severity="critical")     # must-see -> #general
    notify("message text", CRITICAL)                # legacy channel override

Severity routing (per slack-routing.md):
    "routine"  -> #epdev   (C0ANZKK12CD) — default
    "critical" -> #general (C0AKR43PDA4) — auth failures, security, blocks

Daily caps (file-based, resets at midnight):
    routine:  20 messages/day
    critical:  5 messages/day

Dedup: identical messages within 1hr are silently dropped.

Environment:
    SLACK_BOT_TOKEN  xoxb-... bot token from ClaudeActivities app (required)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

EPDEV = "C0ANZKK12CD"
CRITICAL = "C0AKR43PDA4"

_API = "https://slack.com/api/chat.postMessage"

# Routing: severity -> channel ID
_SEVERITY_CHANNEL = {
    "routine": EPDEV,
    "critical": CRITICAL,
}

# Daily caps per severity
_DAILY_CAPS = {
    "routine": 20,
    "critical": 5,
}

# Dedup window in seconds
_DEDUP_WINDOW_S = 3600  # 1 hour

# State file for caps + dedup (next to this script)
_STATE_DIR = Path(__file__).resolve().parent / ".notify_state"


def _state_path() -> Path:
    """Return path to today's state file."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    return _STATE_DIR / f"{today}.json"


def _load_state() -> dict:
    """Load today's state (counts + dedup hashes). Auto-resets daily."""
    path = _state_path()
    if not path.is_file():
        return {"date": path.stem, "counts": {"routine": 0, "critical": 0}, "recent": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Verify it's today's state
        if data.get("date") != path.stem:
            return {"date": path.stem, "counts": {"routine": 0, "critical": 0}, "recent": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"date": path.stem, "counts": {"routine": 0, "critical": 0}, "recent": []}


def _save_state(state: dict) -> None:
    """Persist state to disk."""
    path = _state_path()
    try:
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"slack_notify: failed to save state -- {exc}", file=sys.stderr)

    # Clean up old state files (keep last 3 days)
    try:
        for old in sorted(_STATE_DIR.glob("*.json"))[:-3]:
            old.unlink(missing_ok=True)
    except OSError:
        pass


def _msg_hash(text: str) -> str:
    """Short hash of message text for dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _is_duplicate(state: dict, text: str) -> bool:
    """Check if an identical message was sent within the dedup window."""
    h = _msg_hash(text)
    now_ts = datetime.now(timezone.utc).timestamp()
    # Clean expired entries while checking
    active = []
    found = False
    for entry in state.get("recent", []):
        if now_ts - entry.get("ts", 0) < _DEDUP_WINDOW_S:
            active.append(entry)
            if entry.get("hash") == h:
                found = True
    state["recent"] = active
    return found


def _record_message(state: dict, text: str, severity: str) -> None:
    """Record a sent message for dedup + cap tracking."""
    state["counts"][severity] = state["counts"].get(severity, 0) + 1
    state["recent"].append({
        "hash": _msg_hash(text),
        "ts": datetime.now(timezone.utc).timestamp(),
        "severity": severity,
    })


def notify(
    text: str,
    channel: Optional[str] = None,
    *,
    severity: str = "routine",
    username: str = "Jarvis",
    bypass_caps: bool = False,
) -> bool:
    """Post text to Slack with severity routing, dedup, and daily caps.

    Args:
        text: Message content.
        channel: Explicit channel override (bypasses severity routing).
                 Use EPDEV or CRITICAL constants, or pass severity instead.
        severity: "routine" (default) or "critical". Determines channel
                  when no explicit channel is given.
        username: Bot display name.
        bypass_caps: Skip cap/dedup checks (for testing only).

    Returns True on successful post, False otherwise.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        print(
            "slack_notify: SLACK_BOT_TOKEN not set -- skipping Slack post",
            file=sys.stderr,
        )
        return False

    # Resolve channel: explicit override wins, otherwise route by severity
    if channel is None:
        channel = _SEVERITY_CHANNEL.get(severity, EPDEV)
    elif channel == CRITICAL and severity == "routine":
        # Caller passed CRITICAL channel explicitly — treat as critical severity
        severity = "critical"

    if not bypass_caps:
        state = _load_state()

        # Dedup check
        if _is_duplicate(state, text):
            print("slack_notify: duplicate message within dedup window -- skipped",
                  file=sys.stderr)
            return False

        # Daily cap check
        cap = _DAILY_CAPS.get(severity, 20)
        current = state["counts"].get(severity, 0)
        if current >= cap:
            print(f"slack_notify: daily {severity} cap reached ({cap}) -- skipped",
                  file=sys.stderr)
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
                print(f"slack_notify: API error -- {body.get('error')}", file=sys.stderr)
                return False

        if not bypass_caps:
            _record_message(state, text, severity)
            _save_state(state)

        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"slack_notify: request failed -- {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slack notifier with severity routing")
    parser.add_argument("message", nargs="*", default=["Jarvis slack_notify smoke-test"])
    parser.add_argument("--severity", choices=["routine", "critical"], default="routine")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without posting")
    args = parser.parse_args()

    msg = " ".join(args.message)

    if args.dry_run:
        channel = _SEVERITY_CHANNEL.get(args.severity, EPDEV)
        channel_name = "#epdev" if channel == EPDEV else "#general"
        state = _load_state()
        cap = _DAILY_CAPS.get(args.severity, 20)
        current = state["counts"].get(args.severity, 0)
        is_dup = _is_duplicate(state, msg)
        print(f"Severity:  {args.severity}")
        print(f"Channel:   {channel_name} ({channel})")
        print(f"Daily cap: {current}/{cap}")
        print(f"Duplicate: {is_dup}")
        print(f"Message:   {msg[:80]}...")
        print(f"Would post: {not is_dup and current < cap}")
        sys.exit(0)

    ok = notify(msg, severity=args.severity)
    sys.exit(0 if ok else 1)
