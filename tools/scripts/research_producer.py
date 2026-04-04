#!/usr/bin/env python3
"""Research Producer -- SENSE layer for autonomous domain knowledge accrual.

Reads orchestration/research_topics.json, checks which topics are overdue for
research based on knowledge base article dates, and injects dispatcher-eligible
tasks into task_backlog.jsonl.

SENSE-ONLY: this script never executes research itself. It only decides what
to research and injects tasks. The dispatcher worker executes the research.

Usage:
    python tools/scripts/research_producer.py              # normal run
    python tools/scripts/research_producer.py --dry-run    # show what would be injected
    python tools/scripts/research_producer.py --force SLUG # force-inject specific topic
    python tools/scripts/research_producer.py --status     # show last_researched per topic

Outputs:
    orchestration/task_backlog.jsonl        -- new research tasks appended (via backlog_append)
    data/research_producer_state.json       -- updated last_checked + per-topic injected dates
    data/logs/research_producer_{date}.log  -- run log
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

TOPICS_FILE   = REPO_ROOT / "orchestration" / "research_topics.json"
STATE_FILE    = REPO_ROOT / "data" / "research_producer_state.json"
KNOWLEDGE_DIR = REPO_ROOT / "memory" / "knowledge"
WORK_DIR      = REPO_ROOT / "memory" / "work"
LOGS_DIR      = REPO_ROOT / "data" / "logs"
DB_PATH       = REPO_ROOT / "data" / "jarvis_index.db"

TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "topics": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Knowledge base scan
# ---------------------------------------------------------------------------

def latest_article_date(domain: str, tags: list[str]) -> str | None:
    """Return ISO date string of the most recent knowledge article for this domain.

    Scans memory/knowledge/{domain}/ for .md files whose names match YYYY-MM-DD_*.
    Falls back to reading frontmatter 'date:' field if filename date is absent.
    Returns None if no articles exist.
    """
    domain_dir = KNOWLEDGE_DIR / domain
    if not domain_dir.is_dir():
        return None

    latest: str | None = None
    for md in domain_dir.glob("*.md"):
        # Try filename date first: YYYY-MM-DD_*.md
        name = md.stem
        if len(name) >= 10 and name[:10].count("-") == 2:
            try:
                date.fromisoformat(name[:10])
                article_date = name[:10]
            except ValueError:
                article_date = None
        else:
            article_date = None

        # Fall back to frontmatter date: field
        if article_date is None:
            try:
                content = md.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("date:"):
                        article_date = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break
            except OSError:
                pass

        if article_date and (latest is None or article_date > latest):
            latest = article_date

    return latest


def is_due(topic: dict, state: dict) -> bool:
    """Return True if this topic needs a new research run."""
    slug = topic["slug"]
    interval = topic.get("interval_days", 14)

    # 1. Check knowledge base: any article within interval_days?
    kb_date = latest_article_date(topic["domain"], topic.get("tags", []))
    if kb_date:
        try:
            days_since_kb = (date.today() - date.fromisoformat(kb_date)).days
            if days_since_kb < interval:
                return False
        except ValueError:
            pass

    # 2. Check state: was a task injected recently?
    topic_state = state.get("topics", {}).get(slug, {})
    last_injected = topic_state.get("last_injected")
    if last_injected:
        try:
            days_since_inject = (date.today() - date.fromisoformat(last_injected)).days
            if days_since_inject < interval:
                return False
        except ValueError:
            pass

    return True


# ---------------------------------------------------------------------------
# Task injection
# ---------------------------------------------------------------------------

def _build_worker_notes(topic: dict) -> str:
    """Build the notes field that tells the dispatcher worker how to execute research."""
    return (
        f"AUTONOMOUS RESEARCH TASK -- skip interactive confirmations.\n"
        f"Topic: {topic['title']}\n"
        f"Type: {topic['type']} (pre-classified -- do not re-classify or ask for confirmation)\n"
        f"Depth: {topic['depth']} (pre-specified)\n"
        f"Domain: {topic['domain']}\n"
        f"Output paths:\n"
        f"  Brief:    memory/work/{topic['slug']}/research_brief.md\n"
        f"  Knowledge: memory/knowledge/{topic['domain']}/{{date}}_{topic['slug']}.md\n"
        f"  Signals:  memory/learning/signals/ (1-2 signals, source=autonomous)\n"
        f"Execute phases in order:\n"
        f"  Phase 0.5: scan memory/knowledge/index.md for prior articles on {topic['domain']}\n"
        f"  Phase 1:   generate {3 if topic['depth'] == 'quick' else 5}-{5 if topic['depth'] == 'quick' else 7} sub-questions (no confirmation needed)\n"
        f"  Phase 2:   search with Tavily (type={topic['type']})\n"
        f"  Phase 3:   write research brief + domain knowledge article\n"
        f"  Phase 3.5: file to memory/knowledge/{topic['domain']}/ and append to memory/knowledge/index.md\n"
        f"Tags: {', '.join(topic.get('tags', []))}"
    )


def inject_task(topic: dict, dry_run: bool = False) -> dict | None:
    """Build and inject a dispatcher task for this research topic."""
    from tools.scripts.lib.backlog import backlog_append

    slug = topic["slug"]
    domain = topic["domain"]
    research_type = topic["type"]
    depth = topic["depth"]

    task = {
        "description": f"Research ({research_type}): {topic['title']}",
        "project": "epdev",
        "repo_path": str(REPO_ROOT).replace("\\", "/"),
        "tier": 1,
        "priority": topic.get("priority", 3),
        "autonomous_safe": True,
        "goal_context": (
            f"Domain knowledge accrual -- Jarvis knowledge base for '{domain}' needs a fresh "
            f"{research_type} research pass on: {topic['title']}. "
            f"Output feeds the knowledge index (/research Phase 3.5) and generates learning signals."
        ),
        "isc": [
            f"Research brief exists at memory/work/{slug}/research_brief.md | Verify: test -f memory/work/{slug}/research_brief.md",
            f"Domain knowledge article filed in memory/knowledge/{domain}/ | Verify: find memory/knowledge/{domain} -name '*{slug}*.md'",
        ],
        "context_files": [
            "memory/knowledge/index.md",
            f"memory/knowledge/{domain}/",
            ".claude/skills/research/SKILL.md",
        ],
        "skills": ["research"],
        "model": "sonnet",
        "routine_id": f"research_{slug}",
        "source": "research_producer",
        "notes": _build_worker_notes(topic),
    }

    if dry_run:
        print(f"  [DRY RUN] Would inject: {task['description']}")
        print(f"    routine_id: {task['routine_id']}")
        print(f"    ISC[0]: {task['isc'][0][:80]}")
        return task

    result = backlog_append(task)
    if result is None:
        print(f"  Skipped (dedup): {slug}")
        return None

    print(f"  Injected: {slug} (priority={task['priority']}, interval={topic['interval_days']}d)")
    return result


# ---------------------------------------------------------------------------
# DB: producer_runs registration
# ---------------------------------------------------------------------------

def record_producer_run(tasks_generated: int, status: str = "success") -> None:
    """Record this producer run in jarvis_index.db producer_runs table."""
    if not DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO producer_runs
               (producer, run_date, started_at, completed_at, status, exit_code, artifact_count, log_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "research_producer",
                TODAY,
                now,
                now,
                status,
                0 if status == "success" else 1,
                tasks_generated,
                f"data/logs/research_producer_{TODAY}.log",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"  WARN: could not record producer run: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def print_status(topics: list[dict], state: dict) -> None:
    """Print ASCII table of topic status."""
    print(f"\n{'Topic':<32} {'Domain':<10} {'Interval':<10} {'KB Latest':<12} {'Injected':<12} {'Due?'}")
    print("-" * 90)
    for t in topics:
        if not t.get("enabled", True):
            continue
        kb_date = latest_article_date(t["domain"], t.get("tags", [])) or "never"
        injected = state.get("topics", {}).get(t["slug"], {}).get("last_injected", "never")
        due = "YES" if is_due(t, state) else "no"
        print(f"  {t['slug']:<30} {t['domain']:<10} {t['interval_days']:<10} {kb_date:<12} {injected:<12} {due}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Research Producer -- injects research tasks into dispatcher backlog")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be injected without writing")
    parser.add_argument("--force", metavar="SLUG", help="Force-inject specific topic (bypasses interval check)")
    parser.add_argument("--status", action="store_true", help="Show topic status table and exit")
    args = parser.parse_args()

    print(f"=== Research Producer === {datetime.now().isoformat()}")

    # Load config and state
    if not TOPICS_FILE.exists():
        print(f"ERROR: Topics file not found: {TOPICS_FILE}", file=sys.stderr)
        return 1

    try:
        config = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in topics file: {exc}", file=sys.stderr)
        return 1

    topics = [t for t in config.get("topics", []) if t.get("enabled", True)]
    state = load_state()

    if args.status:
        print_status(topics, state)
        return 0

    # Determine which topics to process
    if args.force:
        targets = [t for t in topics if t["slug"] == args.force]
        if not targets:
            print(f"ERROR: Topic '{args.force}' not found. Available: {[t['slug'] for t in topics]}")
            return 1
        print(f"  Force-injecting: {args.force}")
    else:
        targets = [t for t in topics if is_due(t, state)]

    if not targets:
        print(f"  All {len(topics)} topics are current. Idle Is Success.")
        state["last_run"] = TODAY
        if not args.dry_run:
            save_state(state)
            record_producer_run(0)
        return 0

    print(f"  Due topics: {len(targets)} of {len(topics)}")

    injected = 0
    for topic in targets:
        result = inject_task(topic, dry_run=args.dry_run)
        if result is not None:
            injected += 1
            if not args.dry_run:
                topic_state = state.setdefault("topics", {}).setdefault(topic["slug"], {})
                topic_state["last_injected"] = TODAY

    if not args.dry_run:
        state["last_run"] = TODAY
        save_state(state)
        record_producer_run(injected)

        # Write log
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"research_producer_{TODAY}.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | injected={injected} | topics_due={len(targets)}\n")
            for t in targets:
                f.write(f"  {t['slug']}: {'injected' if injected > 0 else 'dedup/skipped'}\n")

    print(f"  Done. {injected} task(s) injected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
