#!/usr/bin/env python3
"""
voice_inbox_sync.py — Watches iCloud Shortcuts folder (primary) or OneDrive/jarvis-voice/
(fallback) for new voice transcripts and copies them into memory/work/inbox/voice/
for processing by /voice-capture.

Transport: iOS Shortcut → iCloud Drive/Shortcuts/pai-voice-recording → iCloud for Windows sync
Fallback:  iOS Shortcut → OneDrive/jarvis-voice/ (if iCloud not available)

Run manually or schedule via Windows Task Scheduler every 5 minutes.
Usage: python tools/scripts/voice_inbox_sync.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Primary: iCloud for Windows sync path (set up iCloud for Windows, sign in with Apple ID)
ICLOUD_SHORTCUTS = Path.home() / "iCloudDrive" / "Shortcuts"
ICLOUD_FILE = ICLOUD_SHORTCUTS / "pai-voice-recording"  # file written by iOS Shortcut

# Fallback: OneDrive folder (read-only on iOS, usable if writing from another method)
ONEDRIVE_WATCH = Path.home() / "OneDrive" / "jarvis-voice"

INBOX_DIR = REPO_ROOT / "memory" / "work" / "inbox" / "voice"
PROCESSED_MARKER = INBOX_DIR / "processed"


def _resolve_watch_dir() -> tuple[Path | None, str]:
    """Return (watch_dir_or_file, transport_name) for the first available source."""
    if ICLOUD_SHORTCUTS.exists():
        return ICLOUD_SHORTCUTS, "iCloud Shortcuts"
    if ONEDRIVE_WATCH.exists():
        return ONEDRIVE_WATCH, "OneDrive jarvis-voice"
    return None, "none"


def sync() -> int:
    watch, transport = _resolve_watch_dir()
    if watch is None:
        print("No watch source found. Set up one of:")
        print(f"  iCloud:   install iCloud for Windows → sign in → {ICLOUD_SHORTCUTS}")
        print(f"  OneDrive: create 'jarvis-voice' folder at OneDrive root")
        return 0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Watching {transport}: {watch}")

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_MARKER.mkdir(parents=True, exist_ok=True)

    copied = 0
    candidates = list(watch.glob("*.md")) + list(watch.glob("*.txt"))
    # iCloud Shortcuts stores the file without extension — check for it too
    if ICLOUD_FILE.exists() and not ICLOUD_FILE.suffix:
        candidates.append(ICLOUD_FILE)

    for src in sorted(candidates):
        # Give iCloud file a stable name in the inbox
        dest_name = src.name if src.suffix else f"pai-voice-recording.md"
        dest = INBOX_DIR / dest_name
        if dest.exists() and src.stat().st_mtime <= dest.stat().st_mtime:
            continue

        shutil.copy2(src, dest)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Copied: {src.name} → {dest_name}")
        copied += 1

    if copied == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No new transcripts found.")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Synced {copied} file(s). Run /voice-capture to process.")

    return copied


if __name__ == "__main__":
    synced = sync()
    sys.exit(0)
