#!/usr/bin/env python3
"""Research Producer -- SENSE layer for autonomous domain knowledge accrual.

Three topic sources (all deterministic, no LLM calls):
  1. Static watchlist  -- orchestration/research_topics.json (manually curated baseline)
  2. TELOS gap scan    -- reads TELOS GOALS.md + knowledge/index.md; injects topics for
                          goal domains with no recent KB coverage
  3. Signal clustering -- reads jarvis_index.db signals; topics mentioned 3+ times in
                          recent signal titles become one-off research tasks

All injected tasks go directly to dispatcher (pending + autonomous_safe=true).
Slack notification sent to #epdev summarizing what was queued and why.

Usage:
    python tools/scripts/research_producer.py              # normal run
    python tools/scripts/research_producer.py --dry-run    # show what would be injected
    python tools/scripts/research_producer.py --force SLUG # force-inject specific topic
    python tools/scripts/research_producer.py --status     # show per-topic coverage table

Outputs:
    orchestration/task_backlog.jsonl        -- research tasks appended (pending)
    data/research_producer_state.json       -- last_run + per-topic injected dates
    data/logs/research_producer_{date}.log  -- run log
    Slack #epdev                            -- injection summary (when tasks added)
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

TOPICS_FILE   = REPO_ROOT / "orchestration" / "research_topics.json"
STATE_FILE    = REPO_ROOT / "data" / "research_producer_state.json"
KNOWLEDGE_DIR = REPO_ROOT / "memory" / "knowledge"
TELOS_DIR     = REPO_ROOT / "memory" / "work" / "telos"
LOGS_DIR      = REPO_ROOT / "data" / "logs"
DB_PATH       = REPO_ROOT / "data" / "jarvis_index.db"

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# TELOS → domain mapping
# Keyword groups that map goal language to knowledge domains.
# ---------------------------------------------------------------------------

_TELOS_DOMAIN_MAP: list[tuple[list[str], str, str]] = [
    # (keywords, domain, default_type)
    (["financial independence", "business", "side hustle", "revenue", "income",
      "consulting", "freelance", "client"], "fintech", "market"),
    (["ai system", "jarvis", "ai brain", "ai tool", "ai infrastructure",
      "orchestration", "agent", "autonomous", "claude", "anthropic",
      "fabric", "pai"], "ai-infra", "technical"),
    (["guitar", "music", "song", "jazz", "funk", "dead", "mayer",
      "practice", "composition", "ear training"], "general", "technical"),
    (["health", "gym", "fitness", "physical", "workout", "streak"], "general", "technical"),
    (["bank", "corporate", "automate", "day job", "workflow", "automation"], "fintech", "technical"),
    (["crypto", "trading", "defi", "bitcoin", "ethereum", "market",
      "algorithmic", "bot", "strategy"], "crypto", "market"),
    (["prediction", "forecast", "calibration", "metaculus",
      "manifold", "polymarket"], "ai-infra", "technical"),
    (["security", "threat", "vulnerability", "prompt injection",
      "attack", "defense"], "security", "technical"),
]

# Minimum days before auto-injecting a TELOS-derived topic again
_TELOS_TOPIC_INTERVAL = 21

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
# Knowledge base helpers
# ---------------------------------------------------------------------------

def _kb_articles_by_domain() -> dict[str, list[str]]:
    """Return {domain: [date_str, ...]} for all knowledge articles."""
    result: dict[str, list[str]] = {}
    if not KNOWLEDGE_DIR.is_dir():
        return result
    for domain_dir in KNOWLEDGE_DIR.iterdir():
        if not domain_dir.is_dir():
            continue
        dates = []
        for md in domain_dir.glob("*.md"):
            name = md.stem
            if len(name) >= 10 and name[:10].count("-") == 2:
                try:
                    date.fromisoformat(name[:10])
                    dates.append(name[:10])
                except ValueError:
                    pass
        if dates:
            result[domain_dir.name] = sorted(dates)
    return result


def latest_article_date(domain: str) -> str | None:
    """Most recent knowledge article date for a domain, or None."""
    articles = _kb_articles_by_domain()
    dates = articles.get(domain, [])
    return dates[-1] if dates else None


def is_static_due(topic: dict, state: dict) -> bool:
    """Return True if a static topic needs a new research run."""
    slug = topic["slug"]
    interval = topic.get("interval_days", 14)

    kb_date = latest_article_date(topic["domain"])
    if kb_date:
        try:
            if (date.today() - date.fromisoformat(kb_date)).days < interval:
                return False
        except ValueError:
            pass

    last_injected = state.get("topics", {}).get(slug, {}).get("last_injected")
    if last_injected:
        try:
            if (date.today() - date.fromisoformat(last_injected)).days < interval:
                return False
        except ValueError:
            pass

    return True


# ---------------------------------------------------------------------------
# Source 2: TELOS gap scan
# ---------------------------------------------------------------------------

def _read_telos_goals() -> str:
    """Return raw text of GOALS.md (and STATUS.md if present)."""
    text = ""
    for fname in ("GOALS.md", "STATUS.md", "PROJECTS.md"):
        p = TELOS_DIR / fname
        if p.exists():
            try:
                text += p.read_text(encoding="utf-8") + "\n"
            except OSError:
                pass
    return text.lower()


def scan_telos_gaps(state: dict) -> list[dict]:
    """Find TELOS goal domains with stale KB coverage.

    Returns list of auto-topic dicts ready for injection.
    """
    goals_text = _read_telos_goals()
    if not goals_text:
        return []

    kb = _kb_articles_by_domain()
    candidates = []
    seen_domains: set[str] = set()

    for keywords, domain, research_type in _TELOS_DOMAIN_MAP:
        if domain in seen_domains:
            continue

        # Check if any goal keyword appears in TELOS text
        matched_kw = next((kw for kw in keywords if kw in goals_text), None)
        if not matched_kw:
            continue

        # Check KB coverage
        domain_dates = kb.get(domain, [])
        latest = domain_dates[-1] if domain_dates else None
        days_stale = (date.today() - date.fromisoformat(latest)).days if latest else 9999

        # Must be stale enough to warrant a new pass
        if days_stale < _TELOS_TOPIC_INTERVAL:
            continue

        # Check state: was a TELOS-derived topic for this domain injected recently?
        telos_key = f"_telos_{domain}"
        last_injected = state.get("topics", {}).get(telos_key, {}).get("last_injected")
        if last_injected:
            try:
                if (date.today() - date.fromisoformat(last_injected)).days < _TELOS_TOPIC_INTERVAL:
                    continue
            except ValueError:
                pass

        # Build a topic for this domain gap
        slug = f"telos-gap-{domain}-{TODAY}"
        topic_title = _domain_to_title(domain, matched_kw, days_stale)
        candidates.append({
            "slug": slug,
            "routine_id": f"telos_gap_{domain}",
            "title": topic_title,
            "type": research_type,
            "domain": domain,
            "depth": "default",
            "interval_days": _TELOS_TOPIC_INTERVAL,
            "priority": 2,
            "tags": keywords[:4],
            "_state_key": telos_key,
            "_source": "telos_gap",
            "_reason": f"TELOS goal '{matched_kw}' — {domain} KB last updated {latest or 'never'} ({days_stale}d ago)",
        })
        seen_domains.add(domain)

    return candidates


def _domain_to_title(domain: str, matched_kw: str, days_stale: int) -> str:
    """Generate a research title from a domain gap."""
    titles = {
        "fintech": "Fintech and AI consulting market -- revenue opportunities for solo operators 2026",
        "ai-infra": "AI infrastructure and agentic patterns -- latest developments and Jarvis relevance",
        "crypto": "Crypto algorithmic trading and DeFi market structure -- current opportunities",
        "security": "AI-specific security threats and defensive patterns -- prompt injection and agentic attacks",
        "general": f"State of the art: {matched_kw} -- tools, frameworks, and best practices 2026",
        "automotive": "EV market update -- pricing, incentives, new models",
    }
    return titles.get(domain, f"Domain knowledge update: {domain} ({matched_kw})")


# ---------------------------------------------------------------------------
# Source 3: Signal topic clustering
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "this", "that", "it", "as", "at", "via", "per", "re", "new", "update",
    "signal", "session", "note", "learning", "capture", "jarvis", "phase",
    "add", "fix", "run", "check", "test", "build", "use", "set", "get",
})

_DOMAIN_KEYWORDS: dict[str, str] = {
    "claude": "ai-infra", "anthropic": "ai-infra", "llm": "ai-infra",
    "agent": "ai-infra", "mcp": "ai-infra", "autonomous": "ai-infra",
    "langchain": "ai-infra", "langgraph": "ai-infra", "embedding": "ai-infra",
    "bitcoin": "crypto", "ethereum": "crypto", "defi": "crypto",
    "trading": "crypto", "crypto": "crypto", "blockchain": "crypto",
    "bank": "fintech", "fintech": "fintech", "payment": "fintech",
    "security": "security", "injection": "security", "vulnerability": "security",
    "guitar": "general", "music": "general", "health": "general", "gym": "general",
    "prediction": "ai-infra", "forecast": "ai-infra", "calibration": "ai-infra",
}

_MIN_SIGNAL_MENTIONS = 3   # keyword must appear in this many recent signal titles
_SIGNAL_WINDOW_DAYS  = 14  # look back window


def scan_signal_topics(state: dict) -> list[dict]:
    """Find topics repeated in recent signal titles.

    Returns list of auto-topic dicts for high-frequency terms.
    """
    if not DB_PATH.exists():
        return []

    cutoff = (date.today() - timedelta(days=_SIGNAL_WINDOW_DAYS)).isoformat()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT title FROM signals WHERE deleted_at IS NULL AND date >= ?",
            (cutoff,),
        ).fetchall()
        conn.close()
    except Exception:
        return []

    # Tokenise titles
    word_counts: Counter = Counter()
    for (title,) in rows:
        if not title:
            continue
        words = re.findall(r"[a-zA-Z]{4,}", title.lower())
        word_counts.update(w for w in words if w not in _STOP_WORDS)

    # Find words that appear frequently AND map to a domain
    candidates = []
    injected_domains: set[str] = set()

    for word, count in word_counts.most_common(30):
        if count < _MIN_SIGNAL_MENTIONS:
            break
        domain = _DOMAIN_KEYWORDS.get(word)
        if not domain or domain in injected_domains:
            continue

        # Check if static watchlist already covers this domain recently
        latest = latest_article_date(domain)
        if latest:
            try:
                if (date.today() - date.fromisoformat(latest)).days < 14:
                    continue
            except ValueError:
                pass

        # Check state for this signal cluster
        sig_key = f"_signal_{domain}"
        last_injected = state.get("topics", {}).get(sig_key, {}).get("last_injected")
        if last_injected:
            try:
                if (date.today() - date.fromisoformat(last_injected)).days < 14:
                    continue
            except ValueError:
                pass

        slug = f"signal-cluster-{domain}-{TODAY}"
        candidates.append({
            "slug": slug,
            "routine_id": f"signal_cluster_{domain}",
            "title": f"Signal-driven research: {domain} -- topic '{word}' mentioned {count}x in recent signals",
            "type": "technical" if domain in ("ai-infra", "security") else "market",
            "domain": domain,
            "depth": "quick",
            "interval_days": 14,
            "priority": 3,
            "tags": [word, domain],
            "_state_key": sig_key,
            "_source": "signal_cluster",
            "_reason": f"Keyword '{word}' appeared {count}x in last {_SIGNAL_WINDOW_DAYS}d of signals",
        })
        injected_domains.add(domain)

    return candidates


# ---------------------------------------------------------------------------
# Task injection (shared)
# ---------------------------------------------------------------------------

def _build_worker_notes(topic: dict) -> str:
    depth = topic["depth"]
    sub_q_range = "2-3" if depth == "quick" else ("5-7" if depth == "default" else "8-12")
    return (
        f"AUTONOMOUS RESEARCH TASK -- skip interactive confirmations.\n"
        f"Topic: {topic['title']}\n"
        f"Type: {topic['type']} (pre-classified)\n"
        f"Depth: {depth}\n"
        f"Domain: {topic['domain']}\n"
        f"Source: {topic.get('_source', 'watchlist')} -- {topic.get('_reason', '')}\n"
        f"Output paths:\n"
        f"  Brief:     memory/work/{topic['slug']}/research_brief.md\n"
        f"  Knowledge: memory/knowledge/{topic['domain']}/{{date}}_{topic['slug']}.md\n"
        f"  Signals:   memory/learning/signals/ (1-2 signals, source=autonomous)\n"
        f"Execute phases in order:\n"
        f"  Phase 0.5: scan memory/knowledge/index.md for prior articles on {topic['domain']}\n"
        f"  Phase 1:   generate {sub_q_range} sub-questions (no confirmation needed)\n"
        f"  Phase 2:   search with Tavily (type={topic['type']})\n"
        f"  Phase 3:   write research brief + domain knowledge article\n"
        f"  Phase 3.5: file to memory/knowledge/{topic['domain']}/ and append to memory/knowledge/index.md\n"
        f"Tags: {', '.join(topic.get('tags', []))}"
    )


def inject_topic(topic: dict, dry_run: bool = False) -> dict | None:
    """Build and inject a dispatcher task. Returns task if injected, None if deduped."""
    from tools.scripts.lib.backlog import backlog_append

    slug   = topic["slug"]
    domain = topic["domain"]

    task = {
        "description": f"Research ({topic['type']}): {topic['title']}",
        "project": "epdev",
        "repo_path": str(REPO_ROOT).replace("\\", "/"),
        "tier": 1,
        "priority": topic.get("priority", 3),
        "autonomous_safe": True,
        "goal_context": (
            f"Domain knowledge accrual -- '{domain}' KB needs a fresh {topic['type']} pass. "
            f"Source: {topic.get('_source','watchlist')}. "
            f"Output feeds knowledge index and generates learning signals."
        ),
        "isc": [
            f"Research brief exists | Verify: test -f memory/work/{slug}/research_brief.md",
            f"Domain knowledge article filed | Verify: find memory/knowledge/{domain} -name '*{slug[:30]}*.md'",
        ],
        "context_files": [
            "memory/knowledge/index.md",
            f"memory/knowledge/{domain}/",
            ".claude/skills/research/SKILL.md",
        ],
        "skills": ["research"],
        "model": "sonnet",
        "routine_id": topic.get("routine_id", f"research_{slug}"),
        "source": "research_producer",
        "notes": _build_worker_notes(topic),
    }

    if dry_run:
        src = topic.get("_source", "watchlist")
        reason = topic.get("_reason", "")
        print(f"  [DRY RUN] {src}: {topic['title'][:70]}")
        if reason:
            print(f"    Why: {reason}")
        return task

    result = backlog_append(task)
    if result is None:
        print(f"  Dedup: {topic.get('routine_id','?')}")
        return None

    src = topic.get("_source", "watchlist")
    print(f"  [{src}] Injected: {slug}")
    return result


# ---------------------------------------------------------------------------
# DB: producer_runs
# ---------------------------------------------------------------------------

def record_producer_run(tasks_generated: int, status: str = "success") -> None:
    if not DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO producer_runs
               (producer, run_date, started_at, completed_at, status, exit_code, artifact_count, log_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("research_producer", TODAY, now, now, status,
             0 if status == "success" else 1, tasks_generated,
             f"data/logs/research_producer_{TODAY}.log"),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"  WARN: producer_runs write failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------

def notify_slack(injected: list[dict]) -> None:
    """Post research queue summary to #epdev."""
    try:
        from tools.scripts.slack_notify import notify
    except ImportError:
        return

    if not injected:
        return

    lines = [f"Research producer queued {len(injected)} topic(s) for autonomous research:\n"]
    for t in injected:
        src = t.get("_source", "watchlist")
        icon = {"watchlist": "📋", "telos_gap": "🎯", "signal_cluster": "📡"}.get(src, "•")
        reason = t.get("_reason", "")
        lines.append(f"{icon} *{t['title'][:80]}*")
        if reason:
            lines.append(f"  _{reason}_")

    lines.append("\nResults will appear in memory/knowledge/ after dispatcher runs (~5:30am).")
    try:
        notify("\n".join(lines), severity="routine")
    except Exception as exc:
        print(f"  WARN: Slack notify failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def print_status(static_topics: list[dict], state: dict) -> None:
    kb = _kb_articles_by_domain()
    print(f"\n{'Source':<12} {'Slug':<35} {'Domain':<10} {'KB Latest':<12} {'Injected':<12} Due?")
    print("-" * 95)

    for t in static_topics:
        if not t.get("enabled", True):
            continue
        domain_dates = kb.get(t["domain"], [])
        kb_latest = domain_dates[-1] if domain_dates else "never"
        injected = state.get("topics", {}).get(t["slug"], {}).get("last_injected", "never")
        due = "YES" if is_static_due(t, state) else "no"
        print(f"  {'watchlist':<10} {t['slug']:<35} {t['domain']:<10} {kb_latest:<12} {injected:<12} {due}")

    # Show TELOS gap state
    for _, domain, _ in _TELOS_DOMAIN_MAP:
        telos_key = f"_telos_{domain}"
        if telos_key in state.get("topics", {}):
            injected = state["topics"][telos_key].get("last_injected", "never")
            domain_dates = kb.get(domain, [])
            kb_latest = domain_dates[-1] if domain_dates else "never"
            print(f"  {'telos_gap':<10} {telos_key:<35} {domain:<10} {kb_latest:<12} {injected:<12}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Research Producer -- autonomous domain knowledge accrual")
    parser.add_argument("--dry-run",  action="store_true", help="Show what would be injected, no writes")
    parser.add_argument("--force",    metavar="SLUG",      help="Force-inject specific static topic slug")
    parser.add_argument("--status",   action="store_true", help="Show topic coverage table and exit")
    parser.add_argument("--no-telos", action="store_true", help="Skip TELOS gap scan")
    parser.add_argument("--no-signals", action="store_true", help="Skip signal cluster scan")
    args = parser.parse_args()

    print(f"=== Research Producer === {datetime.now().isoformat()}")

    if not TOPICS_FILE.exists():
        print(f"ERROR: Topics file not found: {TOPICS_FILE}", file=sys.stderr)
        return 1

    try:
        config = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in topics file: {exc}", file=sys.stderr)
        return 1

    static_topics = [t for t in config.get("topics", []) if t.get("enabled", True)]
    state = load_state()

    if args.status:
        print_status(static_topics, state)
        return 0

    all_candidates: list[dict] = []

    # -- Source 1: Static watchlist --
    if args.force:
        targets = [t for t in static_topics if t["slug"] == args.force]
        if not targets:
            print(f"ERROR: Topic '{args.force}' not found in watchlist.")
            return 1
        for t in targets:
            t["_source"] = "watchlist"
            t["_reason"] = "force-injected"
        all_candidates.extend(targets)
    else:
        for t in static_topics:
            if is_static_due(t, state):
                t["_source"] = "watchlist"
                t["_reason"] = f"interval {t['interval_days']}d elapsed since last KB article"
                all_candidates.append(t)

    # -- Source 2: TELOS gap scan --
    if not args.no_telos and not args.force:
        telos_gaps = scan_telos_gaps(state)
        if telos_gaps:
            print(f"  TELOS gaps found: {len(telos_gaps)}")
        all_candidates.extend(telos_gaps)

    # -- Source 3: Signal clustering --
    if not args.no_signals and not args.force:
        signal_topics = scan_signal_topics(state)
        if signal_topics:
            print(f"  Signal clusters found: {len(signal_topics)}")
        all_candidates.extend(signal_topics)

    if not all_candidates:
        print(f"  All topics current. Idle Is Success.")
        state["last_run"] = TODAY
        if not args.dry_run:
            save_state(state)
            record_producer_run(0)
        return 0

    # -- Deduplicate by domain: one task per domain per run AND cross-run backlog check --
    # Read active backlog tasks to avoid duplicating across sources or runs.
    backlog_active_domains: set[str] = set()
    backlog_path = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
    if backlog_path.exists():
        for line in backlog_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
                if (t.get("source") == "research_producer"
                        and t.get("status") in ("pending", "executing", "verifying")):
                    # Extract domain from goal_context or notes
                    gc = t.get("goal_context", "") or ""
                    for dm in ("ai-infra", "fintech", "crypto", "security", "general", "automotive"):
                        if f"'{dm}'" in gc or f'"{dm}"' in gc:
                            backlog_active_domains.add(dm)
                            break
            except (json.JSONDecodeError, KeyError):
                pass

    seen_domains: set[str] = set(backlog_active_domains)
    deduped: list[dict] = []
    for t in sorted(all_candidates, key=lambda x: x.get("priority", 9)):
        domain = t["domain"]
        if domain in seen_domains:
            continue
        deduped.append(t)
        seen_domains.add(domain)

    src_counts = {}
    for t in deduped:
        src_counts[t.get("_source","?")] = src_counts.get(t.get("_source","?"),0) + 1
    print(f"  Candidates: {len(deduped)} topics ({src_counts})")

    injected: list[dict] = []
    for topic in deduped:
        result = inject_topic(topic, dry_run=args.dry_run)
        if result is not None:
            injected.append(topic)
            if not args.dry_run:
                state_key = topic.get("_state_key", topic["slug"])
                state.setdefault("topics", {}).setdefault(state_key, {})["last_injected"] = TODAY

    if not args.dry_run:
        state["last_run"] = TODAY
        save_state(state)
        record_producer_run(len(injected))

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"research_producer_{TODAY}.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | injected={len(injected)} | candidates={len(deduped)}\n")
            for t in deduped:
                status = "injected" if t in injected else "dedup/skipped"
                f.write(f"  {t.get('_source','?')}: {t['slug']} -> {status}\n")

        # Slack notification -- only when tasks were actually added
        if injected:
            notify_slack(injected)

    print(f"  Done. {len(injected)} task(s) injected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
