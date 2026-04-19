#!/usr/bin/env python3
"""PostToolUse hook: append Tavily tool-call record to data/tavily_usage.jsonl.

Matched by `mcp__tavily__.*` in .claude/settings.json. Non-blocking by design:
any failure (parse, write, permissions) exits 0 so tool execution is never
interrupted. Schema:

    {"ts":"2026-04-19T17:30:00Z","tool":"mcp__tavily__tavily_search",
     "duration_ms":1234,"session_id":"<id>"}
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
USAGE_LOG = REPO_ROOT / "data" / "tavily_usage.jsonl"

sys.path.insert(0, str(Path(__file__).parent))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    try:
        tool_name = data.get("tool_name", "") or ""
        if not tool_name.startswith("mcp__tavily__"):
            sys.exit(0)

        session_id = data.get("session_id", "") or ""

        duration_ms = None
        for key in ("duration_ms", "duration", "elapsed_ms"):
            v = data.get(key)
            if v is not None:
                try:
                    duration_ms = int(v)
                    break
                except (ValueError, TypeError):
                    continue
        if duration_ms is None:
            meta = data.get("tool_response_meta") or data.get("meta") or {}
            if isinstance(meta, dict):
                v = meta.get("duration_ms") or meta.get("duration")
                try:
                    duration_ms = int(v) if v is not None else None
                except (ValueError, TypeError):
                    duration_ms = None

        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": tool_name,
            "duration_ms": duration_ms,
            "session_id": session_id,
        }

        try:
            from lib.file_lock import locked_append  # type: ignore
            USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
            locked_append(USAGE_LOG, json.dumps(record))
        except Exception:
            try:
                USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
                with USAGE_LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
