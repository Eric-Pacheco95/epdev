"""Atomic JSONL append for Phase 6A.1 retrieval instrumentation signals.

Thin wrapper over locked_append (msvcrt.locking on Windows) that serialises
a dict record to a JSON line before writing.  Import this wherever a signal
needs to be appended; never call locked_append directly from signal code.

Usage:
    from tools.scripts.lib.signal_writer import append_signal
    append_signal(path, {"ts": "...", "query": "...", ...})
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.file_lock import locked_append  # noqa: E402


def append_signal(path: str | Path, record: dict) -> None:
    """Atomically append one JSON record to a JSONL signal file.

    Concurrency: msvcrt.locking byte-range lock (Windows); fcntl.flock fallback
    (POSIX); plain append if neither is available.  Safe under 15+ concurrent
    Claude Code sessions.
    """
    p = Path(path) if Path(path).is_absolute() else REPO_ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=True)
    locked_append(p, line)
