#!/usr/bin/env python3
"""review_gate.py -- Post the latest draft to Slack for human review.

Reads the most recent staging/draft_*.md file and posts a review request
to #content-drafts. Logs the review request to staging/review_log.json.

Exit codes:
    0 -- review request sent (or Slack token missing -- logged and exits clean)
    1 -- no draft found or I/O error
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STAGING = Path(__file__).resolve().parent / "staging"
REVIEW_LOG = STAGING / "review_log.json"

# ---------------------------------------------------------------------------
# Slack config
# ---------------------------------------------------------------------------
SLACK_API = "https://slack.com/api/chat.postMessage"
CONTENT_DRAFTS_CHANNEL = "#content-drafts"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_draft() -> Path | None:
    """Return the most recently modified draft_*.md file, or None."""
    drafts = sorted(STAGING.glob("draft_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return drafts[0] if drafts else None


def parse_title_from_draft(content: str) -> str:
    """Extract title from frontmatter or first H1."""
    # Try frontmatter first
    fm_match = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
    if fm_match:
        return fm_match.group(1).strip()
    # Fall back to first H1
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    return "Untitled"


def extract_body_preview(content: str, chars: int = 200) -> str:
    """Return first N chars of the post body (after frontmatter and headers)."""
    # Strip frontmatter block (--- ... ---)
    stripped = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
    # Strip leading H1 and italic subtitle lines
    stripped = re.sub(r"^#\s+.+\n", "", stripped).strip()
    stripped = re.sub(r"^\*.+\*\n", "", stripped).strip()
    # Strip TL;DR block up to the --- divider
    stripped = re.sub(r"^\*\*TL;DR\*\*.*?---\n", "", stripped, flags=re.DOTALL).strip()

    preview = stripped[:chars].replace("\n", " ")
    return preview


def post_to_slack(token: str, channel: str, text: str) -> bool:
    """Post a message to Slack. Returns True on success."""
    payload = json.dumps(
        {"channel": channel, "text": text, "username": "Jarvis"}
    ).encode("utf-8")
    req = urllib.request.Request(
        SLACK_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            if not body.get("ok"):
                print(
                    f"[REVIEW_GATE] Slack API error: {body.get('error')}",
                    file=sys.stderr,
                )
                return False
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"[REVIEW_GATE] Slack request failed: {exc}", file=sys.stderr)
        return False


def load_review_log() -> list:
    """Load existing review log entries."""
    if not REVIEW_LOG.exists():
        return []
    try:
        data = json.loads(REVIEW_LOG.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_review_log(entries: list) -> None:
    """Persist review log to disk."""
    STAGING.mkdir(parents=True, exist_ok=True)
    try:
        REVIEW_LOG.write_text(
            json.dumps(entries, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[REVIEW_GATE] WARN: Could not save review log: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("[REVIEW_GATE] Looking for latest draft...")
    draft_path = find_latest_draft()

    if draft_path is None:
        print("[REVIEW_GATE] ERROR: No draft files found in staging/.", file=sys.stderr)
        return 1

    print(f"[REVIEW_GATE] Found: {draft_path.name}")

    try:
        content = draft_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[REVIEW_GATE] ERROR: Could not read draft: {exc}", file=sys.stderr)
        return 1

    title = parse_title_from_draft(content)
    preview = extract_body_preview(content)

    message = (
        "Weekly Substack draft ready for review\n\n"
        f"Title: {title}\n\n"
        f"Preview:\n{preview}...\n\n"
        f"Full draft: {draft_path}\n\n"
        "Reply 'approve' to mark ready, "
        "'edit {feedback}' to request changes, "
        "'skip' to discard"
    )

    # Log the review request regardless of Slack success
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = {
        "timestamp": timestamp,
        "draft": str(draft_path),
        "title": title,
        "channel": CONTENT_DRAFTS_CHANNEL,
        "slack_sent": False,
        "status": "pending_review",
    }

    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        print(
            "[REVIEW_GATE] SLACK_BOT_TOKEN not set -- skipping Slack post. "
            "Draft is ready locally at: " + str(draft_path),
        )
        entries = load_review_log()
        entries.append(log_entry)
        save_review_log(entries)
        print(f"[REVIEW_GATE] Review request logged (no Slack): {REVIEW_LOG}")
        return 0

    print(f"[REVIEW_GATE] Posting to Slack {CONTENT_DRAFTS_CHANNEL}...")
    sent = post_to_slack(token, CONTENT_DRAFTS_CHANNEL, message)

    log_entry["slack_sent"] = sent
    entries = load_review_log()
    entries.append(log_entry)
    save_review_log(entries)

    if sent:
        print(f"[REVIEW_GATE] Review request sent to {CONTENT_DRAFTS_CHANNEL}")
        print(f"[REVIEW_GATE] Review log updated: {REVIEW_LOG}")
    else:
        print(
            "[REVIEW_GATE] WARN: Slack post failed. "
            f"Draft is ready locally at: {draft_path}",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
