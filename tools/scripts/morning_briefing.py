#!/usr/bin/env python3
"""Morning briefing — Tier 0 Slack surface before first session.

Aggregates:
  - TELOS goals excerpt (memory/work/telos/GOALS.md when present)
  - task_backlog.jsonl: pending + manual_review counts (+ short manual_review list)
  - task_proposals.jsonl: pending proposal count
  - Optional: last financial snapshot summary (does not Read snapshot file in worker
    path that is autonomous-blocked; this script runs Tier-0 and reads locally)

Env:
  SLACK_DM_CHANNEL -- optional channel ID for DM; else posts routine -> #epdev
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKLOG = ROOT / "orchestration" / "task_backlog.jsonl"
GOALS = ROOT / "memory" / "work" / "telos" / "GOALS.md"
SNAPSHOT = ROOT / "data" / "financial" / "snapshot.jsonl"
LOG_DIR = ROOT / "data" / "logs"


def _backlog_counts() -> tuple[Counter, list[dict]]:
    c: Counter = Counter()
    manual: list[dict] = []
    if not BACKLOG.is_file():
        return c, manual
    for line in BACKLOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError:
            continue
        st = str(t.get("status", "unknown"))
        c[st] += 1
        if st == "manual_review":
            manual.append(t)
    return c, manual


def _goals_excerpt(max_lines: int = 25) -> str:
    if not GOALS.is_file():
        return "_GOALS.md not found (ok on fresh checkout)_"
    lines = GOALS.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[:max_lines])


def _financial_blurb() -> str:
    if not SNAPSHOT.is_file():
        return "No financial snapshot yet (run financial_snapshot.py or wait for routine)."
    try:
        last = ""
        for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                last = line
        if not last:
            return "snapshot file empty."
        row = json.loads(last)
        cb = row.get("crypto_bot") or {}
        files = cb.get("files") or {}
        return (
            f"Latest snapshot ts={row.get('ts')} | crypto_root_exists={cb.get('root_exists')} "
            f"| merged_files={len(files)}"
        )
    except (OSError, json.JSONDecodeError) as exc:
        return f"(could not parse snapshot: {exc})"


def _proposal_pending() -> int:
    try:
        from tools.scripts.lib.task_proposals import count_by_status
    except ImportError:
        return 0
    return count_by_status().get("pending", 0)


def main() -> int:
    if os.environ.get("MORNING_BRIEFING_REFRESH_FINANCIAL", "0").strip().lower() not in (
        "0",
        "false",
        "no",
    ):
        try:
            from tools.scripts.financial_snapshot import run as _refresh_financial

            _refresh_financial()
        except Exception as exc:
            print(f"morning_briefing: financial refresh failed: {exc}", file=sys.stderr)

    now = datetime.now(timezone.utc)
    counts, manual = _backlog_counts()
    pending = counts.get("pending", 0)
    mrev = counts.get("manual_review", 0)
    pend_rev = counts.get("pending_review", 0)

    parts = [
        f"*Morning briefing* — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"*Backlog:* pending={pending} manual_review={mrev} pending_review={pend_rev}",
    ]
    if manual:
        parts.append("")
        parts.append("*manual_review (needs you):*")
        for t in manual[:8]:
            tid = t.get("id", "?")
            desc = str(t.get("description", ""))[:120]
            parts.append(f"• `{tid}` {desc}")
        if len(manual) > 8:
            parts.append(f"_…+{len(manual) - 8} more_")

    pp = _proposal_pending()
    parts.append("")
    parts.append(f"*Task proposals (pending):* {pp}")

    parts.append("")
    parts.append("*Financial (snapshot):*")
    parts.append(_financial_blurb())

    parts.append("")
    parts.append("*Goals file (head):*")
    parts.append("```")
    parts.append(_goals_excerpt())
    parts.append("```")

    text = "\n".join(parts)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"morning_briefing_{now.strftime('%Y-%m-%d')}.log"
    log_path.write_text(text + "\n", encoding="utf-8")

    dm = os.environ.get("SLACK_DM_CHANNEL", "").strip()
    try:
        from tools.scripts.slack_notify import EPDEV, notify
    except ImportError:
        print(text)
        print("morning_briefing: slack_notify missing; printed body only", file=sys.stderr)
        return 0

    if dm:
        ok = notify(text, channel=dm, severity="routine")
    else:
        ok = notify(text, severity="routine")
    if not ok and dm:
        notify(text, severity="routine")

    return 0


if __name__ == "__main__":
    sys.exit(main())
