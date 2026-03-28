#!/usr/bin/env python3
"""
Jarvis Slack Voice Processor — polls #jarvis-voice every 60s.
New messages are processed as voice captures: signals extracted, TELOS queued,
confirmation posted back in-thread.

Usage:
    python tools/scripts/slack_voice_processor.py [--interval 60] [--once]

Environment (from .env):
    SLACK_BOT_TOKEN          xoxb-... bot token
    SLACK_JARVIS_VOICE_ID    channel ID for #jarvis-voice
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parents[2]
STATE_FILE = REPO_ROOT / "data" / "slack_poller_state.json"
SLACK_API  = "https://slack.com/api"

# Voice capture prompt — inline equivalent of /voice-capture skill for headless use
_VOICE_PROMPT = """You are processing a voice capture from Eric via Slack #jarvis-voice.
This is a stream-of-consciousness voice note or typed thought captured away from desktop.
Treat it exactly like a Notion voice inbox capture.

STEPS:
1. Extract signals from the text. For each signal write a file to memory/learning/signals/ using this format:
---
id: {YYYYMMDD}-slack-voice-{slug}
source: slack_voice
rating: {1-10}
type: {insight|idea|pattern|decision|question|anomaly}
signal: {one sentence}
context: {2-3 sentences}
---

2. Check for TELOS relevance (goals, focus, mood shifts) — note any that need telos-update.

3. Reply with a brief confirmation: signal count written, any TELOS items flagged, done.

Voice capture text:
"""


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key not in os.environ:
            os.environ[key] = val.strip()


def _slack_get(endpoint: str, params: dict) -> dict:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    req = urllib.request.Request(
        f"{SLACK_API}/{endpoint}?{qs}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _slack_post(channel: str, text: str, thread_ts: str | None = None) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    payload: dict = {"channel": channel, "text": text, "username": "Jarvis"}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    req = urllib.request.Request(
        f"{SLACK_API}/chat.postMessage",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("ok", False)
    except Exception as exc:
        print(f"[voice] post failed: {exc}", flush=True)
        return False


def _load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _process_voice(text: str) -> str:
    prompt = _VOICE_PROMPT + text
    try:
        result = subprocess.run(
            ["claude", "-p", "--dangerously-skip-permissions", prompt],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        out = result.stdout.strip()
        if not out and result.stderr.strip():
            out = f"[error] {result.stderr.strip()[:500]}"
        return out or "[no output]"
    except subprocess.TimeoutExpired:
        return "[timeout after 120s]"
    except Exception as exc:
        return f"[error: {exc}]"


def _poll_once(channel_id: str, state: dict) -> dict:
    # Use a separate key so voice and inbox states don't collide
    state_key = f"voice:{channel_id}"
    last_ts = state.get(state_key, "0")

    try:
        resp = _slack_get("conversations.history", {
            "channel": channel_id,
            "oldest": last_ts,
            "limit": 10,
            "inclusive": "false",
        })
    except Exception as exc:
        print(f"[voice] fetch failed: {exc}", flush=True)
        return state

    if not resp.get("ok"):
        print(f"[voice] Slack error: {resp.get('error')}", flush=True)
        return state

    messages = sorted(resp.get("messages", []), key=lambda m: float(m.get("ts", "0")))

    for msg in messages:
        ts   = msg.get("ts", "")
        text = msg.get("text", "").strip()

        if msg.get("bot_id") or msg.get("subtype") or not text:
            state[state_key] = ts
            continue

        print(f"[voice] processing capture: {text[:80]}", flush=True)
        result = _process_voice(text)
        _slack_post(channel_id, result, thread_ts=ts)
        print(f"[voice] processed (ts={ts})", flush=True)
        state[state_key] = ts

    _save_state(state)
    return state


def main() -> None:
    _load_env()

    interval = 60
    once = False
    for arg in sys.argv[1:]:
        if arg == "--once":
            once = True
        elif arg.startswith("--interval="):
            interval = int(arg.split("=", 1)[1])

    channel_id = os.environ.get("SLACK_JARVIS_VOICE_ID", "")
    if not channel_id:
        print("[voice] SLACK_JARVIS_VOICE_ID not set", file=sys.stderr)
        sys.exit(1)
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("[voice] SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    print(f"[voice] started  channel={channel_id}  interval={interval}s", flush=True)
    state = _load_state()

    while True:
        try:
            state = _poll_once(channel_id, state)
        except Exception as exc:
            print(f"[voice] cycle error: {exc}", flush=True)
        if once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
