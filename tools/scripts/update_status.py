#!/usr/bin/env python3
"""update_status.py — Update STATUS.md dynamic sections from the latest session handoff.

Called by the Stop hook. Reads the most recent data/session_handoff_*.md and updates:
  - ## Last Updated (inline header line)
  - ## Queued Next Session (from Pending Efforts)
  - ## Recent Wins (prepend new entry from Done This Session)
  - ## Current Blockers (from Hard Constraints)

Skips if the latest handoff was already processed (state tracked in
data/update_status_state.json to avoid duplicate Recent Wins on repeated runs).

Sections NOT touched: Signal Pipeline Health, Foundation Phase Declaration,
Current Focus, Life Context — those are manually maintained.

Usage:
    python tools/scripts/update_status.py           # run and update STATUS.md
    python tools/scripts/update_status.py --dry-run # print proposed changes, no write

Exit codes:
    0 — updated successfully, skipped (already processed), or error (never blocks session)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_MD = REPO_ROOT / "memory" / "work" / "telos" / "STATUS.md"
HANDOFF_DIR = REPO_ROOT / "data"
STATE_FILE = REPO_ROOT / "data" / "update_status_state.json"

# Sections in STATUS.md to leave untouched (manually maintained)
MANUAL_SECTIONS = {
    "Signal Pipeline Health",
    "Foundation Phase Declaration",
    "Current Focus",
    "Life Context",
}


# ---------------------------------------------------------------------------
# Handoff discovery
# ---------------------------------------------------------------------------

def _latest_handoff() -> Path | None:
    """Return the most recently modified session_handoff_*.md file."""
    files = list(HANDOFF_DIR.glob("session_handoff_*.md"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _last_processed() -> str:
    """Return the name of the last handoff we processed (from state file)."""
    if not STATE_FILE.exists():
        return ""
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_handoff", "")
    except (json.JSONDecodeError, OSError):
        return ""


def _save_processed(handoff_name: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_handoff": handoff_name,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Handoff parsing
# ---------------------------------------------------------------------------

def _parse_section(content: str, section_name: str) -> str:
    """Extract body text of a ## section (stops at next ## or EOF)."""
    pattern = rf'^## {re.escape(section_name)}\n(.*?)(?=^## |\Z)'
    m = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_bullet_items(text: str) -> list[str]:
    """Return lines that start with '- ' from a text block."""
    return [line.strip() for line in text.splitlines() if re.match(r'^- ', line.strip())]


def _pending_efforts_to_bullets(text: str) -> str:
    """Convert ### Effort/Session subsections to STATUS.md-style bullets."""
    # Split on ### boundaries; first chunk is pre-header text (discard)
    blocks = re.split(r'^### ', text, flags=re.MULTILINE)
    bullets: list[str] = []

    for block in blocks[1:]:  # skip pre-header chunk
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        raw_title = lines[0].strip()
        # Strip leading "Effort A — ", "Session B — ", etc.
        title = re.sub(r'^(?:Effort|Session|Task|Step)\s+\S+\s+[—–-]+\s+', '', raw_title)

        state_m = re.search(r'\*\*State:\*\*\s*(.+?)(?:\n|$)', block)
        state = state_m.group(1).strip() if state_m else ""

        blocked_m = re.search(r'\*\*Blocked on:\*\*\s*(.+?)(?:\n|$)', block)
        blocked = blocked_m.group(1).strip() if blocked_m else ""

        bullet = f"- **{title}**"
        if state:
            state_short = (state[:120] + "…") if len(state) > 120 else state
            bullet += f" — {state_short}"
        # Only add blocked note when it's non-trivially blocked
        _unblocked = {"nothing", "nothing — ready to build", "nothing — ready to implement",
                      "nothing — ready."}
        if blocked and blocked.lower().rstrip(".") not in {s.rstrip(".") for s in _unblocked}:
            bullet += f" [blocked: {blocked}]"

        bullets.append(bullet)

    return "\n".join(bullets)


def _first_done_label(done_text: str) -> str:
    """Return a short label from the first Done This Session bullet for Last Updated."""
    items = _extract_bullet_items(done_text)
    if not items:
        return "session complete"
    first = items[0]  # e.g. "- **Phase 5E COMPLETE** — ..."
    m = re.search(r'\*\*(.+?)\*\*', first)
    return m.group(1) if m else first[2:80]


# ---------------------------------------------------------------------------
# STATUS.md section replacement (using callable replacements — safe against
# backreferences in substitution content)
# ---------------------------------------------------------------------------

def _replace_section_body(status: str, section_name: str, new_body: str) -> str:
    """Replace the body of a ## section while keeping the header line."""
    pattern = rf'^(## {re.escape(section_name)}\n)(.*?)(?=^## |\Z)'

    def replacer(m: re.Match) -> str:
        return m.group(1) + "\n" + new_body + "\n\n"

    return re.sub(pattern, replacer, status, flags=re.MULTILINE | re.DOTALL)


def _prepend_to_section(status: str, section_name: str, new_entry: str) -> str:
    """Prepend new_entry into the body of a ## section, keeping existing content."""
    pattern = rf'^(## {re.escape(section_name)}\n)(.*?)(?=^## |\Z)'

    def replacer(m: re.Match) -> str:
        existing = m.group(2)
        return m.group(1) + "\n" + new_entry + "\n" + existing

    return re.sub(pattern, replacer, status, flags=re.MULTILINE | re.DOTALL)


def _update_last_updated_line(status: str, new_value: str) -> str:
    """Replace the ## Last Updated: inline line."""
    def replacer(m: re.Match) -> str:
        return f"## Last Updated: {new_value}"

    return re.sub(r'^## Last Updated:.*$', replacer, status, flags=re.MULTILINE)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_updated_status(handoff: str, status: str) -> str:
    """Apply all dynamic section updates. Returns modified status content."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    done_text = _parse_section(handoff, "Done This Session")
    constraints_text = _parse_section(handoff, "Hard Constraints")
    pending_text = _parse_section(handoff, "Pending Efforts")

    # 1. Last Updated line
    done_label = _first_done_label(done_text) if done_text else "session complete"
    status = _update_last_updated_line(status, f"{today} — {done_label}")

    # 2. Queued Next Session from Pending Efforts
    if pending_text:
        new_queued = _pending_efforts_to_bullets(pending_text)
        if new_queued:
            status = _replace_section_body(status, "Queued Next Session", new_queued)

    # 3. Prepend to Recent Wins from Done This Session
    if done_text:
        items = _extract_bullet_items(done_text)
        if items:
            first_m = re.search(r'\*\*(.+?)\*\*', items[0])
            win_label = first_m.group(1) if first_m else items[0][2:80]
            extra = len(items) - 1
            if extra > 0:
                win_entry = f"- **{today}**: {win_label} (+{extra} more — see handoff)"
            else:
                win_entry = f"- **{today}**: {win_label}"
            status = _prepend_to_section(status, "Recent Wins", win_entry)

    # 4. Current Blockers from Hard Constraints
    if constraints_text:
        bullets = _extract_bullet_items(constraints_text)
        if bullets:
            status = _replace_section_body(status, "Current Blockers", "\n".join(bullets))

    return status


def main(dry_run: bool = False) -> int:
    handoff_path = _latest_handoff()
    if not handoff_path:
        print("[update_status] No handoff file found — skipping", file=sys.stderr)
        return 0

    last = _last_processed()
    if last == handoff_path.name and not dry_run:
        print(
            f"[update_status] {handoff_path.name} already processed — skipping",
            file=sys.stderr,
        )
        return 0

    try:
        handoff = handoff_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[update_status] Cannot read handoff: {exc}", file=sys.stderr)
        return 0

    try:
        status = STATUS_MD.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[update_status] Cannot read STATUS.md: {exc}", file=sys.stderr)
        return 0

    updated = _build_updated_status(handoff, status)

    if dry_run:
        print(f"[update_status] DRY RUN — source: {handoff_path.name}")
        print("=" * 72)
        print(updated)
        return 0

    # Write backup before overwriting
    backup = STATUS_MD.with_suffix(".md.bak")
    try:
        backup.write_text(status, encoding="utf-8")
    except OSError:
        pass  # backup failure is non-fatal

    try:
        STATUS_MD.write_text(updated, encoding="utf-8")
    except OSError as exc:
        print(f"[update_status] Cannot write STATUS.md: {exc}", file=sys.stderr)
        return 0

    _save_processed(handoff_path.name)
    print(
        f"[update_status] STATUS.md updated from {handoff_path.name}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    # Reconfigure stdout/stderr for UTF-8 on Windows (cp1252 can't encode arrows/em-dashes)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 fallback — reconfigure not available

    dry = "--dry-run" in sys.argv
    try:
        sys.exit(main(dry_run=dry))
    except Exception as exc:  # noqa: BLE001 — never block the session
        print(f"[update_status] Unhandled error: {exc}", file=sys.stderr)
        sys.exit(0)
