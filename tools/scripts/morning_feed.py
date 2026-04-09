#!/usr/bin/env python3
"""Jarvis Morning Feed -- combined briefing to Slack at 9am.

Uses RSS/Atom feeds (stdlib xml.etree) as primary source, with Tavily
HTTP fallback for sources without feeds. Calls claude -p for proposal
rating (S/A/B/C/D), source discovery, and research task generation.

B+ rated items are routed through the task gate for autonomous research.
Discovered sources are logged to data/source_candidates.jsonl for Eric
to approve in a future session.

Usage:
    python tools/scripts/morning_feed.py                # full run
    python tools/scripts/morning_feed.py --dry-run      # preview, no Slack
    python tools/scripts/morning_feed.py --test          # self-test

Environment:
    SLACK_BOT_TOKEN    xoxb-... for Slack posting (required)
    TAVILY_API_KEY     Tavily API key (optional, fallback for non-RSS sources)

Outputs:
    memory/work/jarvis/morning_feed/YYYY-MM-DD.md   -- raw feed for audit
    data/source_candidates.jsonl                     -- discovered source candidates
    Slack #epdev message                             -- combined briefing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

SOURCES_FILE = REPO_ROOT / "memory" / "work" / "jarvis" / "sources.yaml"
STATE_FILE = REPO_ROOT / "data" / "overnight_state.json"
FEED_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "morning_feed"
HEARTBEAT_FILE = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_latest.json"
VALUE_FILE = REPO_ROOT / "data" / "autonomous_value.jsonl"
CONSOLIDATION_DIR = REPO_ROOT / "data" / "overnight_summary"
CANDIDATES_FILE = REPO_ROOT / "data" / "source_candidates.jsonl"
BACKTEST_DIR = REPO_ROOT / "data" / "predictions" / "backtest"

# RSS fetch settings
RSS_TIMEOUT = 15  # seconds per feed
RSS_MAX_ITEMS = 5  # items per source
RSS_USER_AGENT = "Jarvis-MorningFeed/2.0"


# -- Source loading -----------------------------------------------------------

def load_sources(tier: int = 1) -> list:
    """Load sources from sources.yaml for a given tier.

    Uses basic text parsing -- no pyyaml dependency.
    """
    if not SOURCES_FILE.is_file():
        return []

    text = SOURCES_FILE.read_text(encoding="utf-8")
    sources = []
    current = {}

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("- name:"):
            if current and current.get("tier") == tier:
                sources.append(current)
            current = {"name": stripped.split(":", 1)[1].strip().strip('"')}

        elif stripped.startswith("url:") and current:
            current["url"] = stripped.split(":", 1)[1].strip().strip('"')
            # Fix for URLs -- "url:" splits on first colon, losing protocol
            if not current["url"].startswith("http"):
                current["url"] = "https:" + stripped.split(":", 2)[2].strip().strip('"')

        elif stripped.startswith("feed_url:") and current:
            val = stripped.split(":", 1)[1].strip().strip('"')
            if val and not val.startswith("http"):
                val = "https:" + stripped.split(":", 2)[2].strip().strip('"')
            current["feed_url"] = val if val else ""

        elif stripped.startswith("type:") and current:
            current["type"] = stripped.split(":", 1)[1].strip()

        elif stripped.startswith("tier:") and current:
            try:
                current["tier"] = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass

        elif stripped.startswith("frequency:") and current:
            current["frequency"] = stripped.split(":", 1)[1].strip()

    # Don't forget last entry
    if current and current.get("tier") == tier:
        sources.append(current)

    return sources


# -- RSS/Atom fetching --------------------------------------------------------

def fetch_rss(feed_url: str, max_items: int = RSS_MAX_ITEMS) -> list[dict]:
    """Fetch and parse an RSS or Atom feed. Returns list of items.

    Each item: {title, link, published, summary}
    Uses stdlib xml.etree -- no feedparser dependency.
    """
    if not feed_url:
        return []

    try:
        req = urllib.request.Request(
            feed_url,
            headers={
                "User-Agent": RSS_USER_AGENT,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            },
        )
        with urllib.request.urlopen(req, timeout=RSS_TIMEOUT) as resp:
            raw = resp.read()
    except Exception as exc:
        print(f"  RSS fetch failed for {feed_url}: {exc}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(f"  RSS parse failed for {feed_url}: {exc}", file=sys.stderr)
        return []

    items = []

    # Detect feed type by root tag
    tag = root.tag.lower()
    # Strip namespace if present
    if "}" in tag:
        tag = tag.split("}", 1)[1]

    if tag == "rss":
        # RSS 2.0
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:max_items]:
            items.append({
                "title": _text(item, "title"),
                "link": _text(item, "link"),
                "published": _text(item, "pubDate"),
                "summary": _clean_html(_text(item, "description"))[:300],
            })
    elif tag == "feed":
        # Atom
        ns = ""
        if "{" in root.tag:
            ns = root.tag.split("}")[0] + "}"
        for entry in root.findall(f"{ns}entry")[:max_items]:
            link = ""
            link_el = entry.find(f"{ns}link")
            if link_el is not None:
                link = link_el.get("href", "")
            items.append({
                "title": _text(entry, f"{ns}title"),
                "link": link,
                "published": _text(entry, f"{ns}updated") or _text(entry, f"{ns}published"),
                "summary": _clean_html(_text(entry, f"{ns}summary") or _text(entry, f"{ns}content"))[:300],
            })

    return items


def _text(el: ET.Element, tag: str) -> str:
    """Safely extract text from an XML element."""
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _clean_html(text: str) -> str:
    """Strip HTML tags from text (basic)."""
    return re.sub(r"<[^>]+>", "", text).strip()


# -- Tavily fallback ----------------------------------------------------------

def fetch_tavily(url: str, max_items: int = 3) -> list[dict]:
    """Fallback: use Tavily extract API when no RSS feed available.

    Requires TAVILY_API_KEY in environment.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return []

    try:
        payload = json.dumps({
            "api_key": api_key,
            "urls": [url],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/extract",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": RSS_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        results = data.get("results", [])
        items = []
        for r in results[:max_items]:
            raw = r.get("raw_content", "") or r.get("content", "")
            items.append({
                "title": url.split("/")[-1] or url,
                "link": url,
                "published": "",
                "summary": raw[:300],
            })
        return items
    except Exception as exc:
        print(f"  Tavily fallback failed for {url}: {exc}", file=sys.stderr)
        return []


# -- GitHub API (kept for GitHub-type sources) --------------------------------

def check_github_source(url: str) -> list[dict]:
    """Check a GitHub repo for recent activity via API."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
    if not m:
        return []

    owner, repo = m.group(1), m.group(2)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=3"

    try:
        req = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github.v3+json",
                      "User-Agent": RSS_USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            commits = json.loads(resp.read())
            items = []
            for c in commits[:3]:
                date = c.get("commit", {}).get("committer", {}).get("date", "")[:10]
                msg = c.get("commit", {}).get("message", "").split("\n")[0][:120]
                items.append({
                    "title": msg,
                    "link": c.get("html_url", ""),
                    "published": date,
                    "summary": "",
                })
            return items
    except Exception:
        return []


# -- Unified source fetcher ---------------------------------------------------

def fetch_source_content(source: dict) -> list[dict]:
    """Fetch content from a source using the best available method.

    Priority: RSS/Atom feed > GitHub API > Tavily extract
    """
    name = source.get("name", "unknown")

    # 1. Try RSS/Atom feed
    feed_url = source.get("feed_url", "")
    if feed_url:
        items = fetch_rss(feed_url)
        if items:
            print(f"  [{name}] RSS: {len(items)} items")
            return items

    # 2. Try GitHub API for github-type sources
    url = source.get("url", "")
    if "github.com" in url:
        items = check_github_source(url)
        if items:
            print(f"  [{name}] GitHub API: {len(items)} items")
            return items

    # 3. Tavily fallback
    if url:
        items = fetch_tavily(url)
        if items:
            print(f"  [{name}] Tavily: {len(items)} items")
            return items

    print(f"  [{name}] No content fetched")
    return []


# -- Vitals snapshot ----------------------------------------------------------

def get_vitals_snapshot() -> str:
    """Build a quick vitals summary from heartbeat data."""
    lines = []

    # Heartbeat data
    if HEARTBEAT_FILE.is_file():
        try:
            hb = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
            metrics = hb.get("metrics", {})

            # ISC ratio
            isc_pass = metrics.get("isc_pass_count", {}).get("value", "?")
            isc_total = metrics.get("isc_total_count", {}).get("value", "?")
            lines.append(f"ISC: {isc_pass}/{isc_total}")

            # Signal count
            sig = metrics.get("signal_count", {}).get("value", "?")
            lines.append(f"Signals: {sig}")

            # Test health
            test_pass = metrics.get("test_pass_count", {}).get("value", "?")
            lines.append(f"Tests passing: {test_pass}")

        except (json.JSONDecodeError, OSError):
            lines.append("Heartbeat: unavailable")
    else:
        lines.append("Heartbeat: no data")

    # Overnight state
    if STATE_FILE.is_file():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            last_dim = state.get("last_dimension", "none")
            last_date = state.get("last_run_date", "never")
            run_count = state.get("run_count", 0)
            lines.append(f"Overnight: last={last_dim} ({last_date}), total runs={run_count}")
        except (json.JSONDecodeError, OSError):
            lines.append("Overnight: no state")

    return " | ".join(lines)


# -- Overnight report --------------------------------------------------------

def get_overnight_summary() -> str:
    """Read the overnight run report for today's diff summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = (REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"
                  / f"overnight-{today}")

    if not report_dir.is_dir():
        return "No overnight run today."

    report_file = report_dir / "report.md"
    if report_file.is_file():
        text = report_file.read_text(encoding="utf-8")
        if len(text) > 500:
            return text[:500] + "..."
        return text

    logs = list(report_dir.glob("*_raw.log"))
    if logs:
        return f"Overnight ran ({len(logs)} dimensions logged) but no structured report."

    return "Overnight directory exists but no reports found."


# -- Consolidation report ----------------------------------------------------

def get_consolidation_summary() -> str:
    """Read the consolidation summary from the overnight consolidation script."""
    today = datetime.now().strftime("%Y-%m-%d")
    md_path = CONSOLIDATION_DIR / f"{today}.md"

    if md_path.is_file():
        text = md_path.read_text(encoding="utf-8")
        if len(text) > 800:
            return text[:800] + "\n... (truncated, full report in data/overnight_summary/)"
        return text

    json_path = CONSOLIDATION_DIR / f"{today}.json"
    if json_path.is_file():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            merged = data.get("branches_merged", 0)
            found = data.get("branches_found", 0)
            conflicts = data.get("branches_conflicted", 0)
            review = data.get("review_branch", "N/A")
            tasks = data.get("dispatcher_reports", [])
            tasks_done = sum(1 for t in tasks if t.get("status") == "done")

            parts = [f"Branches: {merged}/{found} merged"]
            if conflicts:
                parts.append(f"{conflicts} conflicts")
            if tasks:
                parts.append(f"Tasks: {tasks_done}/{len(tasks)} done")
            if review and merged > 0:
                parts.append(f"Review: `{review}`")

            return " | ".join(parts)
        except (json.JSONDecodeError, OSError):
            return "Consolidation JSON exists but unreadable."

    return "No consolidation report today."


# -- Claude CLI call ----------------------------------------------------------

def call_claude(prompt: str, system: str = "") -> str:
    """Call claude -p for proposal generation. Uses Claude Max (no API key).

    Passes prompt via stdin to avoid Windows 32K command-line limit.
    Only safe from Task Scheduler or standalone CMD -- never from within
    an active Claude Code session (subprocess hang risk).
    """
    import subprocess

    if system:
        full_prompt = "SYSTEM INSTRUCTIONS:\n%s\n\nUSER INPUT:\n%s" % (system, prompt)
    else:
        full_prompt = prompt

    env = os.environ.copy()
    env["JARVIS_SESSION_TYPE"] = "autonomous"
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "-"],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            return "(claude -p error: %s)" % result.stderr.strip()[:200]
        return "(claude -p returned empty response)"
    except FileNotFoundError as exc:
        return "(claude CLI not found: %s)" % exc
    except subprocess.TimeoutExpired:
        return "(claude -p timed out after 120s)"
    except Exception as exc:
        return "(claude -p failed: %s)" % exc


# -- Source candidate tracking ------------------------------------------------

def log_source_candidate(candidate: dict) -> None:
    """Append a discovered source candidate to data/source_candidates.jsonl.

    Each candidate: {name, url, type, discovered_from, discovered_date,
                     reason, engagement_count}
    Deduplicates by URL.
    """
    CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing candidate with same URL
    if CANDIDATES_FILE.is_file():
        for line in CANDIDATES_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
                if existing.get("url") == candidate.get("url"):
                    return  # Already tracked
            except json.JSONDecodeError:
                continue

    entry = {
        "name": candidate.get("name", ""),
        "url": candidate.get("url", ""),
        "type": candidate.get("type", "unknown"),
        "feed_url": candidate.get("feed_url", ""),
        "discovered_from": candidate.get("discovered_from", ""),
        "discovered_date": datetime.now().strftime("%Y-%m-%d"),
        "reason": candidate.get("reason", ""),
        "engagement_count": 0,
    }
    with open(CANDIDATES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_discovered_sources(llm_response: str) -> list[dict]:
    """Parse source candidates from the LLM discovery response.

    Expected format in response:
    DISCOVERED_SOURCES:
    - name: "Source Name" | url: "https://..." | type: ai_engineering | reason: "why"
    """
    candidates = []
    in_discovery = False

    for line in llm_response.splitlines():
        stripped = line.strip()
        if "DISCOVERED_SOURCES:" in stripped:
            in_discovery = True
            continue
        if in_discovery and stripped.startswith("- "):
            parts = {}
            for segment in stripped[2:].split("|"):
                segment = segment.strip()
                if ":" in segment:
                    key, val = segment.split(":", 1)
                    parts[key.strip()] = val.strip().strip('"')
            if parts.get("url"):
                candidates.append(parts)
        elif in_discovery and not stripped.startswith("-"):
            in_discovery = False

    return candidates


# -- Task gate integration ---------------------------------------------------

def propose_research_tasks(proposals_text: str, dry_run: bool = False) -> int:
    """Parse B+ rated proposals and route through the task gate.

    Returns number of tasks proposed.
    """
    if dry_run:
        return 0

    try:
        from tools.scripts.task_gate import propose_task
    except ImportError:
        print("  WARNING: task_gate not available, skipping research proposals",
              file=sys.stderr)
        return 0

    # Parse numbered proposals from LLM output
    # Look for lines like: 1. Title - description...
    proposals = re.findall(
        r"^\d+\.\s*\*?\*?(.+?)(?:\*?\*?)?\s*[-:](.+?)(?:\n|$)",
        proposals_text,
        re.MULTILINE,
    )

    count = 0
    for title, body in proposals:
        title = title.strip().strip("*")
        body = body.strip()
        description = f"Research: {title} -- {body[:200]}"

        result = propose_task(
            description=description,
            skills=["research"],
            isc=[
                f"Research brief exists in memory/work/ for topic: {title}",
                "At least 3 sources cited in the brief",
                "Brief includes Jarvis integration notes or TELOS relevance",
            ],
            source="morning_feed",
            model="sonnet",
            notify_on_decision=False,
        )
        if result.route == "backlog":
            count += 1
            print(f"  -> Research task queued: {title[:60]}")

    return count


# -- Pending backtest count ---------------------------------------------------

def _count_pending_backtests() -> int:
    """Count backtest prediction files with status: pending_review."""
    if not BACKTEST_DIR.is_dir():
        return 0
    count = 0
    for f in BACKTEST_DIR.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            if "status: pending_review" in text:
                count += 1
        except OSError:
            pass
    return count


# -- Research digest ----------------------------------------------------------

def _build_research_digest() -> str:
    """Build a short research status block for the morning brief.

    Shows: articles filed this week, topics queued in backlog, next due dates.
    Returns empty string if nothing to report (keeps brief clean on quiet days).
    """
    try:
        import json as _json
        from datetime import date as _date, timedelta as _timedelta
        from pathlib import Path as _Path

        repo = _Path(__file__).resolve().parents[2]
        kb_index = repo / "memory" / "knowledge" / "index.md"
        backlog_path = repo / "orchestration" / "task_backlog.jsonl"
        cutoff = (_date.today() - _timedelta(days=7)).isoformat()

        # Articles filed in last 7 days
        recent_articles = []
        if kb_index.exists():
            for line in kb_index.read_text(encoding="utf-8").splitlines():
                # Format: | YYYY-MM-DD | topic | finding | path |
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4 and len(parts[0]) == 10:
                    try:
                        _date.fromisoformat(parts[0])
                        if parts[0] >= cutoff:
                            recent_articles.append(f"{parts[0]} {parts[1][:50]}")
                    except ValueError:
                        pass

        # Research tasks currently pending in backlog
        queued = []
        if backlog_path.exists():
            for line in backlog_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    t = _json.loads(line)
                    if (t.get("source") == "research_producer"
                            and t.get("status") in ("pending", "executing")):
                        desc = t.get("description", "")
                        # Strip "Research (type): " prefix for brevity
                        desc = desc.split("): ", 1)[-1] if "): " in desc else desc
                        queued.append(desc[:60])
                except (_json.JSONDecodeError, KeyError):
                    pass

        if not recent_articles and not queued:
            return ""

        parts = ["*Research Digest:*"]
        if recent_articles:
            parts.append(f"  Filed this week ({len(recent_articles)}): " + " | ".join(recent_articles[:3]))
        if queued:
            parts.append(f"  Queued for research ({len(queued)}): " + ", ".join(queued[:3]))
        return "\n".join(parts)

    except Exception:
        return ""


# -- Feed generation ---------------------------------------------------------

def generate_feed(dry_run: bool = False) -> str:
    """Generate the full morning feed content."""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")

    # Determine which tiers to check today
    tiers_to_check = [1]  # Always check Tier 1
    day_of_week = datetime.now().weekday()  # 0=Monday
    if day_of_week == 0:  # Monday: check weekly sources
        tiers_to_check.append(2)
    if datetime.now().day == 1:  # 1st of month: check monthly sources
        tiers_to_check.append(3)

    # 1. Fetch content from all relevant sources
    print(f"Checking tiers: {tiers_to_check}")
    all_updates = []
    sources_checked = 0

    for tier in tiers_to_check:
        sources = load_sources(tier=tier)
        for src in sources:
            sources_checked += 1
            items = fetch_source_content(src)
            for item in items:
                all_updates.append({
                    "source": src["name"],
                    "source_type": src.get("type", "unknown"),
                    "tier": tier,
                    **item,
                })

    print(f"Fetched {len(all_updates)} items from {sources_checked} sources")

    # 2. Vitals snapshot
    vitals = get_vitals_snapshot()

    # 3. Overnight + consolidation summaries
    overnight = get_overnight_summary()
    consolidation = get_consolidation_summary()

    # 4. Format source updates for LLM
    if all_updates:
        source_lines = []
        for u in all_updates:
            line = f"[{u['source']}] {u['title']}"
            if u.get("summary"):
                line += f" -- {u['summary'][:150]}"
            if u.get("published"):
                line += f" ({u['published']})"
            source_lines.append(line)
        source_context = "\n".join(source_lines)
    else:
        source_context = "No content fetched from any sources today."

    # Read TELOS goals for cross-referencing
    telos_file = REPO_ROOT / "memory" / "work" / "TELOS.md"
    telos_summary = ""
    if telos_file.is_file():
        telos_text = telos_file.read_text(encoding="utf-8")
        telos_summary = telos_text[:500]

    # 5. Call claude -p to rate, propose, and discover
    system_prompt = """You are Jarvis, an AI assistant generating a morning briefing for Eric.

TASK: Review source updates and overnight results. Do three things:
1. Rate each source update
2. Generate proposals from the best items
3. Discover new sources worth following

RATING SYSTEM (apply to each source update):
Rate each item S/A/B/C/D based on:
- S (exceptional): paradigm-shifting, directly enables a TELOS goal breakthrough
- A (high signal): concrete, actionable, clearly relevant to active projects or goals
- B (solid): useful context or pattern, worth knowing but not urgent
- C (filler): incremental update, no new insight
- D (noise): irrelevant or redundant

QUALITY GATE: Only propose items rated B+ or higher (S, A, or B). Drop C and D entirely.

OUTPUT FORMAT (plain text, no markdown headers or bold):

RATINGS:
[S] item1 (source)
[A] item2 (source)
[B] item3 (source)
[C] item4 (source) -- dropped
...

PROPOSALS (from B+ items only, 1-3 numbered):
Each proposal must have:
- A title
- Which TELOS goal it connects to
- 2-3 sentences making the idea interesting and actionable

SOURCE DISCOVERY (0-2 new sources):
Based on the content you read, identify 0-2 new sources that would be high-signal for Eric's goals. These must be specific URLs, not generic suggestions.

DISCOVERED_SOURCES:
- name: "Source Name" | url: "https://exact-url" | type: category | reason: "why this is valuable"

If no new sources are worth adding, write:
DISCOVERED_SOURCES:
(none today)

If no items pass B+ for proposals, say: "No high-signal items today. Sources checked: N"

Keep total response under 400 words. Do not fabricate updates or source URLs."""

    user_prompt = f"""Generate morning briefing for {today} ({weekday}).

Source updates ({len(all_updates)} items from {sources_checked} sources):
{source_context}

Overnight research:
{overnight}

Autonomous work (dispatcher + consolidation):
{consolidation}

TELOS goals context:
{telos_summary}

If source updates are thin today, suggest 1 idea based on overnight results or current project gaps instead."""

    if dry_run:
        proposals = f"[DRY RUN] Would call claude -p with {len(user_prompt)} char prompt ({len(all_updates)} source items)"
    else:
        proposals = call_claude(user_prompt, system_prompt)

    # 6. Parse discovered sources and log candidates
    if not dry_run:
        candidates = parse_discovered_sources(proposals)
        for c in candidates:
            c["discovered_from"] = "morning_feed"
            log_source_candidate(c)
            print(f"  -> Source candidate logged: {c.get('name', '?')}")

    # 7. Route B+ proposals through the task gate
    tasks_proposed = propose_research_tasks(proposals, dry_run=dry_run)
    if tasks_proposed:
        print(f"  -> {tasks_proposed} research task(s) proposed to gate")

    # 8. Pending backtest count for morning review prompt
    backtest_pending = _count_pending_backtests()

    # 9. Research digest -- articles filed this week + topics queued
    research_digest = _build_research_digest()

    # 10. Assemble combined message
    lines = [
        f"*Jarvis Morning Briefing -- {today}*",
        "",
        f"*Vitals:* {vitals}",
        "",
    ]

    if backtest_pending > 0:
        lines.append(f"*Backtests pending review:* {backtest_pending} -- run `/backtest-review`")
        lines.append("")

    lines.extend([
        f"*Autonomous Work:*",
        consolidation,
        "",
        f"*Sources checked:* {sources_checked} (tiers: {', '.join(str(t) for t in tiers_to_check)}) | {len(all_updates)} items fetched",
        "",
        "*Today's Proposals:*",
        proposals,
    ])

    if tasks_proposed:
        lines.append(f"\n({tasks_proposed} research task(s) queued for autonomous execution)")

    if research_digest:
        lines.append("")
        lines.append(research_digest)

    return "\n".join(lines)


# -- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis Morning Feed")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview feed without posting to Slack")
    parser.add_argument("--test", action="store_true",
                        help="Run self-tests")
    args = parser.parse_args()

    if args.test:
        return run_self_test()

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Jarvis Morning Feed -- {today}")

    # Dedup check: skip if already ran today (NFR-006)
    feed_file = FEED_DIR / f"{today}.md"
    if feed_file.is_file() and not args.dry_run:
        print(f"Already ran today ({today}). Feed exists at: {feed_file}")
        print("Use --dry-run to preview without posting.")
        return 0

    # Generate feed
    feed_content = generate_feed(dry_run=args.dry_run)

    # Save to audit file
    FEED_DIR.mkdir(parents=True, exist_ok=True)
    feed_file = FEED_DIR / f"{today}.md"
    feed_file.write_text(feed_content, encoding="utf-8")
    print(f"Feed saved to: {feed_file}")

    if args.dry_run:
        print("\n--- PREVIEW ---")
        print(feed_content)
        print("--- END PREVIEW ---")
        return 0

    # Post to Slack
    try:
        from tools.scripts.slack_notify import notify
        ok = notify(feed_content, bypass_caps=True)
        if ok:
            print("Posted to #epdev Slack")
        else:
            print("Failed to post to Slack", file=sys.stderr)
    except ImportError:
        print("slack_notify not available", file=sys.stderr)

    # Track proposal IDs for value tracking
    track_proposals(today, feed_content)

    print("Morning feed complete.")
    return 0


def track_proposals(date: str, content: str) -> None:
    """Write proposal IDs to autonomous_value.jsonl for tracking."""
    proposals = re.findall(r"^\d+\.", content, re.MULTILINE)
    VALUE_FILE.parent.mkdir(parents=True, exist_ok=True)

    for i, _ in enumerate(proposals, 1):
        entry = {
            "proposal_id": f"feed-{date}-{i:03d}",
            "date": date,
            "acted_on": False,
            "reference_session": None,
        }
        with open(VALUE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# -- Self-test ---------------------------------------------------------------

def run_self_test() -> int:
    """Quick self-tests."""
    passed = 0
    failed = 0

    def check(condition, label):
        nonlocal passed, failed
        if condition:
            print(f"  PASS: {label}")
            passed += 1
        else:
            print(f"  FAIL: {label}")
            failed += 1

    print("Morning Feed -- Self-Test")
    print()

    # Source loading
    sources = load_sources(tier=1)
    check(len(sources) >= 3, f"Tier 1 sources >= 3 ({len(sources)} found)")

    tier2 = load_sources(tier=2)
    check(len(tier2) >= 5, f"Tier 2 sources >= 5 ({len(tier2)} found)")

    # Source fields
    if sources:
        src = sources[0]
        check("name" in src, "Source has name field")
        check("url" in src, "Source has url field")
        check("feed_url" in src, "Source has feed_url field")
        check("type" in src, "Source has type field")

    # RSS fetch (live test -- Hacker News RSS is reliable)
    hn_items = fetch_rss("https://news.ycombinator.com/rss", max_items=3)
    check(len(hn_items) > 0, f"RSS fetch (HN): {len(hn_items)} items")
    if hn_items:
        check("title" in hn_items[0], "RSS item has title")
        check("link" in hn_items[0], "RSS item has link")

    # Atom fetch (GitHub releases)
    atom_items = fetch_rss(
        "https://github.com/anthropics/claude-code/releases.atom", max_items=2
    )
    check(len(atom_items) > 0, f"Atom fetch (Claude Code): {len(atom_items)} items")

    # Source candidate parsing
    test_response = """Some ratings here...
DISCOVERED_SOURCES:
- name: "Test Blog" | url: "https://test.example.com" | type: ai_engineering | reason: "testing"
- name: "Another" | url: "https://another.example.com" | type: security | reason: "also testing"
"""
    candidates = parse_discovered_sources(test_response)
    check(len(candidates) == 2, f"Parse discovered sources: {len(candidates)} found")
    if candidates:
        check(candidates[0].get("url") == "https://test.example.com",
              "Candidate URL parsed correctly")

    # Vitals snapshot
    vitals = get_vitals_snapshot()
    check(len(vitals) > 0, "Vitals snapshot produces output")

    # File existence
    check(SOURCES_FILE.is_file(), "sources.yaml exists")

    print()
    print(f"Results: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
