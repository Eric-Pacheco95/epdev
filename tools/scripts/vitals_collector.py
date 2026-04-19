#!/usr/bin/env python3
"""Vitals collector -- aggregates all health data into a single JSON blob.

Deterministic data gathering for the /vitals skill. Calls existing sub-scripts
(jarvis_heartbeat.py, skill_usage.py) and reads state files, then outputs
structured JSON that the LLM interprets and formats.

Usage:
    python tools/scripts/vitals_collector.py              # JSON to stdout
    python tools/scripts/vitals_collector.py --file        # also write to data/vitals_latest.json
    python tools/scripts/vitals_collector.py --pretty      # indented JSON

Output contract: tools/schemas/vitals_collector.v1.json
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1.1.0"

# --- Data source paths ---
HEARTBEAT_LATEST = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_latest.json"
HEARTBEAT_HISTORY = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_history.jsonl"
OVERNIGHT_STATE = REPO_ROOT / "data" / "overnight_state.json"
AUTONOMOUS_VALUE = REPO_ROOT / "data" / "autonomous_value.jsonl"
AUTORESEARCH_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
TASKLIST = REPO_ROOT / "orchestration" / "tasklist.md"
MORNING_FEED_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "morning_feed"
EVENTS_DIR = REPO_ROOT / "history" / "events"
ISC_PRODUCER_REPORT = REPO_ROOT / "data" / "isc_producer_report.json"
OUTPUT_FILE = REPO_ROOT / "data" / "vitals_latest.json"


def _run_script(script_path: str, args: list[str]) -> dict | None:
    """Run a Python script and parse JSON output. Returns None on failure."""
    try:
        result = subprocess.run(
            [sys.executable, script_path] + args,
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _read_json(path: Path) -> dict | None:
    """Read a JSON file, return None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl_tail(path: Path, n: int = 5) -> list[dict]:
    """Read last N lines of a JSONL file."""
    entries = []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return entries


def collect_heartbeat() -> tuple[dict | None, str | None]:
    """Return heartbeat snapshot + any error.

    Strategy: prefer the on-disk snapshot written by the hourly Task Scheduler
    run if it is fresh (< 2 h old).  Only invoke the subprocess when the file
    is absent or stale -- the script takes 15-30 s to run and the
    _run_script timeout (10 s) reliably kills it before it completes.
    """
    from datetime import datetime, timezone

    # -- Try on-disk snapshot first ------------------------------------------
    cached = _read_json(HEARTBEAT_LATEST)
    if cached is not None:
        ts_str = cached.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_s = (datetime.now(timezone.utc) - ts).total_seconds()
            if age_s < 7200:  # fresh enough (< 2 h)
                return cached, None
            stale_note = f"heartbeat snapshot is {int(age_s // 60)}m old -- running live"
        except (ValueError, TypeError):
            stale_note = "heartbeat snapshot has unparseable timestamp -- running live"
    else:
        stale_note = None

    # -- Snapshot missing or stale: run live with a generous timeout ----------
    script = str(REPO_ROOT / "tools" / "scripts" / "jarvis_heartbeat.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "--quiet", "--json"],
            capture_output=True, text=True, timeout=60,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout), stale_note
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass

    # -- Last resort: return stale cached data with a warning ----------------
    if cached is not None:
        return cached, "heartbeat script failed -- using cached snapshot"
    return None, "heartbeat script failed and no cached snapshot found"


def collect_skill_usage() -> tuple[dict | None, str | None]:
    """Run skill_usage.py and return data."""
    script = str(REPO_ROOT / "tools" / "scripts" / "skill_usage.py")
    data = _run_script(script, ["--json"])
    if data is None:
        return None, "skill_usage.py failed or returned no output"
    return data, None


def collect_heartbeat_trend() -> list[dict]:
    """Read last 5 heartbeat history entries for trend data."""
    return _read_jsonl_tail(HEARTBEAT_HISTORY, 5)


def compute_trend_averages(trend_data: list[dict]) -> dict:
    """Compute moving averages for key metrics from heartbeat trend entries."""
    if not trend_data:
        return {}
    key_metrics = [
        "isc_ratio", "signal_velocity", "signal_count",
        "autonomous_signal_rate", "tool_failure_rate",
    ]
    averages = {}
    for metric in key_metrics:
        values = []
        for entry in trend_data:
            metrics = entry.get("metrics", {})
            m = metrics.get(metric, {})
            v = m.get("value") if isinstance(m, dict) else None
            if v is not None and isinstance(v, (int, float)):
                values.append(v)
        if values:
            avg = round(sum(values) / len(values), 4)
            averages[metric] = {
                "avg": avg,
                "min": min(values),
                "max": max(values),
                "samples": len(values),
            }
    return averages


def collect_isc_producer() -> dict:
    """Read ISC producer report for ready-to-mark count and summary."""
    result = {"status": "NO REPORT", "ready_to_mark_count": 0, "summary": None,
              "run_date": None, "prds_scanned": 0}
    if not ISC_PRODUCER_REPORT.is_file():
        return result
    try:
        data = json.loads(ISC_PRODUCER_REPORT.read_text(encoding="utf-8"))
        result["status"] = "OK"
        result["ready_to_mark_count"] = len(data.get("ready_to_mark", []))
        result["summary"] = data.get("summary")
        result["run_date"] = data.get("run_date")
        result["prds_scanned"] = data.get("prds_scanned", 0)
    except (json.JSONDecodeError, OSError):
        result["status"] = "ERROR"
    return result


def collect_overnight_state() -> dict | None:
    """Read overnight self-improvement state."""
    return _read_json(OVERNIGHT_STATE)


def collect_autonomous_value() -> dict:
    """Calculate autonomous value rate from proposals JSONL."""
    result = {"total": 0, "acted_on": 0, "rate_pct": 0.0, "status": "NO DATA"}
    try:
        if not AUTONOMOUS_VALUE.is_file():
            return result
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        lines = AUTONOMOUS_VALUE.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get("ts", ""))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    result["total"] += 1
                    if entry.get("acted_on"):
                        result["acted_on"] += 1
            except (json.JSONDecodeError, ValueError):
                continue
        if result["total"] > 0:
            result["rate_pct"] = round(result["acted_on"] / result["total"] * 100, 1)
            result["status"] = "OK" if result["rate_pct"] >= 20 else "WARN"
    except OSError:
        pass
    return result


def collect_telos_introspection() -> dict:
    """Check TELOS introspection run status."""
    result = {
        "last_run": None,
        "metrics": None,
        "unreviewed_runs": 0,
        "status": "NO RUNS",
    }
    try:
        if not AUTORESEARCH_DIR.is_dir():
            return result
        run_dirs = sorted(
            [d for d in AUTORESEARCH_DIR.iterdir()
             if d.is_dir() and d.name.startswith("run-")],
            key=lambda d: d.name,
            reverse=True,
        )
        if not run_dirs:
            return result
        latest = run_dirs[0]
        result["last_run"] = latest.name.replace("run-", "")
        metrics_file = latest / "metrics.json"
        if metrics_file.is_file():
            result["metrics"] = _read_json(metrics_file)
        # Check for unreviewed runs (older than 7 days with proposals.md)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        for d in run_dirs:
            run_date = d.name.replace("run-", "")
            if run_date < cutoff_date and (d / "proposals.md").is_file():
                result["unreviewed_runs"] += 1
        result["status"] = "WARN" if result["unreviewed_runs"] > 0 else "OK"
    except OSError:
        pass
    return result


def collect_skill_evolution() -> dict:
    """Score skill maturity across 4 axes."""
    result = {"active": 0, "deprecated": 0, "scores": {}, "upgrade_candidates": []}
    deprecated_markers = ["DEPRECATED", "deprecated"]
    try:
        if not SKILLS_DIR.is_dir():
            return result
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            content = skill_md.read_text(encoding="utf-8")
            name = skill_dir.name
            if any(m in content[:200] for m in deprecated_markers):
                result["deprecated"] += 1
                continue
            result["active"] += 1
            score = 0
            if "# DISCOVERY" in content:
                score += 1
            if "# CONTRACT" in content:
                score += 1
            if "# SKILL CHAIN" in content:
                score += 1
            # Auto-triggers: check if this skill is referenced by other skills
            # (simplified: check if name appears in other SKILL.md files)
            # This is expensive so we skip for the collector — the LLM can do this
            result["scores"][name] = score
        # Find upgrade candidates: lowest scores among active skills
        sorted_scores = sorted(result["scores"].items(), key=lambda x: x[1])
        result["upgrade_candidates"] = [
            {"name": name, "score": f"{score}/3"}
            for name, score in sorted_scores[:3]
            if score < 3
        ]
    except OSError:
        pass
    return result


def collect_overnight_deep_dive() -> dict:
    """Gather detailed overnight data for Slack deep dive report.

    Reads the latest overnight log, autoresearch proposals/contradictions,
    external monitoring report, and overnight branch diff stats.
    """
    result = {
        "log_summary": None,
        "branch_stats": None,
        "autoresearch_proposals": None,
        "autoresearch_contradictions": None,
        "external_monitoring": None,
        "cross_project": None,
    }
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Read latest overnight log
    for date_str in [today, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]:
        log_file = REPO_ROOT / "data" / "logs" / f"overnight_{date_str}.log"
        if log_file.is_file():
            try:
                content = log_file.read_text(encoding="utf-8")
                # Extract dimension results from OVERNIGHT_RESULT lines
                dimensions = []
                for line in content.splitlines():
                    if "completed in" in line and "kept" in line:
                        dimensions.append(line.strip())
                    elif "QUALITY_GATE:" in line or "SECURITY_AUDIT:" in line:
                        dimensions.append(line.strip())
                result["log_summary"] = {
                    "date": date_str,
                    "dimensions": dimensions,
                    "total_lines": len(content.splitlines()),
                }
            except OSError:
                pass
            break

    # 2. Get overnight branch diff stats
    try:
        for date_str in [today, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]:
            branch = f"jarvis/overnight-{date_str}"
            stat_result = subprocess.run(
                ["git", "diff", f"main...{branch}", "--stat", "--stat-width=80"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10, cwd=str(REPO_ROOT),
            )
            if stat_result.returncode == 0 and stat_result.stdout.strip():
                lines = stat_result.stdout.strip().splitlines()
                result["branch_stats"] = {
                    "branch": branch,
                    "summary_line": lines[-1] if lines else "",
                    "top_files": [l.strip() for l in lines[:15]],
                }

                # Commit count
                log_result = subprocess.run(
                    ["git", "log", "--oneline", f"{branch}", "^main"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=10, cwd=str(REPO_ROOT),
                )
                if log_result.returncode == 0 and log_result.stdout:
                    commits = [l.strip() for l in log_result.stdout.strip().splitlines() if l.strip()]
                    result["branch_stats"]["commit_count"] = len(commits)
                    result["branch_stats"]["recent_commits"] = commits[:20]
                break
    except (subprocess.TimeoutExpired, OSError):
        pass

    # 3. Read autoresearch proposals and contradictions (most recent run)
    try:
        if AUTORESEARCH_DIR.is_dir():
            run_dirs = sorted(
                [d for d in AUTORESEARCH_DIR.iterdir()
                 if d.is_dir() and d.name.startswith("run-")],
                key=lambda d: d.name, reverse=True,
            )
            if run_dirs:
                latest = run_dirs[0]
                for fname, key in [("proposals.md", "autoresearch_proposals"),
                                   ("contradictions.md", "autoresearch_contradictions")]:
                    fpath = latest / fname
                    if fpath.is_file():
                        result[key] = fpath.read_text(encoding="utf-8")[:3000]
    except OSError:
        pass

    # 4. Read external monitoring and cross-project reports from overnight
    try:
        for date_str in [today, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]:
            overnight_dir = AUTORESEARCH_DIR / f"overnight-{date_str}"
            if overnight_dir.is_dir():
                for fname, key in [("external_monitoring_report.md", "external_monitoring"),
                                   ("cross_project_report.md", "cross_project")]:
                    fpath = overnight_dir / fname
                    if fpath.is_file():
                        result[key] = fpath.read_text(encoding="utf-8")[:3000]
                break
    except OSError:
        pass

    return result


def collect_unmerged_branches() -> list[str]:
    """Return overnight branches that have commits not in main.

    A branch is only "unmerged" if it has at least one commit that main does not
    contain. Branches whose tip is an ancestor of main (already merged or never
    advanced past their fork point) are excluded so the morning brief does not
    flag dead branches as actionable.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--list", "jarvis/overnight-*"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return []
        branches = [
            b.strip().lstrip("* ").strip()
            for b in result.stdout.strip().splitlines()
            if b.strip()
        ]
        unmerged = []
        for branch in branches:
            count = subprocess.run(
                ["git", "rev-list", "--count", f"main..{branch}"],
                capture_output=True, text=True, timeout=5,
                cwd=str(REPO_ROOT),
            )
            if count.returncode == 0 and count.stdout.strip().isdigit():
                if int(count.stdout.strip()) > 0:
                    unmerged.append(branch)
        return unmerged
    except (subprocess.TimeoutExpired, OSError):
        pass
    return []


def collect_morning_feed() -> dict | None:
    """Read the latest morning_feed file and extract proposals as action items."""
    import re
    if not MORNING_FEED_DIR.is_dir():
        return None
    feed_files = sorted(MORNING_FEED_DIR.glob("*.md"), reverse=True)
    if not feed_files:
        return None
    latest = feed_files[0]
    try:
        content = latest.read_text(encoding="utf-8")
    except OSError:
        return None

    # Extract numbered proposals: only parse after "Proposals:" heading
    proposals = []
    lines = content.splitlines()
    # Find the proposals section start
    i = 0
    while i < len(lines):
        if "Proposals:" in lines[i] or "RATINGS:" in lines[i]:
            i += 1
            break
        i += 1
    # Skip RATINGS line if it comes right after Proposals
    if i < len(lines) and lines[i].strip().startswith("RATINGS:"):
        i += 1
    # Skip blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1
    # Now parse numbered proposals
    while i < len(lines):
        m = re.match(r"^(\d+)\.\s+(.+)", lines[i])
        if m:
            title = m.group(2).strip()
            # Collect description lines until next proposal or end
            desc_lines = []
            telos_tag = ""
            i += 1
            while i < len(lines) and not re.match(r"^\d+\.\s+", lines[i]):
                line = lines[i].strip()
                if line.startswith("TELOS:"):
                    telos_tag = line.replace("TELOS:", "").strip()
                elif line:
                    desc_lines.append(line)
                i += 1
            proposals.append({
                "rank": int(m.group(1)),
                "title": title,
                "telos": telos_tag,
                "description": " ".join(desc_lines)[:300],
            })
        else:
            i += 1

    return {
        "date": latest.stem,
        "file": str(latest.relative_to(REPO_ROOT)),
        "proposal_count": len(proposals),
        "proposals": proposals[:5],
    }


def collect_session_usage() -> dict | None:
    """Aggregate session counts and Gemini usage from event JSONL files."""
    if not EVENTS_DIR.is_dir():
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_dt = datetime.now(timezone.utc).date()

    daily_counts: dict[str, int] = {}
    total_sessions = 0
    session_spans: dict[str, list[str]] = {}  # session_id -> [timestamps]

    # Gemini usage tracking
    gemini_calls = 0
    gemini_tokens = 0
    gemini_daily: dict[str, dict] = {}  # date -> {calls, tokens}

    for f in sorted(EVENTS_DIR.glob("*.jsonl")):
        try:
            for line in f.read_text(encoding="utf-8").strip().splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec_type = rec.get("type", "")
                date_key = rec.get("ts", "")[:10]
                if not date_key:
                    continue
                if rec_type == "session_cost":
                    sid = rec.get("session_id", "")
                    if not sid:
                        # parse_error / empty-session rows — skip totals entirely
                        continue
                    ts = rec.get("ts", "")
                    daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                    total_sessions += 1
                    if ts:
                        session_spans.setdefault(sid, []).append(ts)
                elif rec_type == "gemini_usage":
                    gemini_calls += 1
                    t = rec.get("total_tokens") or 0
                    gemini_tokens += t
                    if date_key not in gemini_daily:
                        gemini_daily[date_key] = {"calls": 0, "tokens": 0}
                    gemini_daily[date_key]["calls"] += 1
                    gemini_daily[date_key]["tokens"] += t
        except OSError:
            continue

    # Compute unique session count and average duration from timestamp spans
    unique_sessions = len(session_spans)
    durations = []
    for sid, timestamps in session_spans.items():
        if len(timestamps) >= 2:
            timestamps.sort()
            try:
                t0 = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
                dur = (t1 - t0).total_seconds()
                if 0 < dur < 86400:  # sanity: under 24h
                    durations.append(dur)
            except (ValueError, TypeError):
                pass
    avg_duration_min = round(sum(durations) / len(durations) / 60, 1) if durations else None

    # Compute weekly and monthly rollups
    week_sessions = sum(
        v for k, v in daily_counts.items()
        if k >= (today_dt - timedelta(days=7)).isoformat()
    )
    month_sessions = sum(
        v for k, v in daily_counts.items()
        if k >= (today_dt - timedelta(days=30)).isoformat()
    )

    # Gemini weekly/monthly
    gemini_week = {"calls": 0, "tokens": 0}
    gemini_month = {"calls": 0, "tokens": 0}
    for k, v in gemini_daily.items():
        if k >= (today_dt - timedelta(days=7)).isoformat():
            gemini_week["calls"] += v["calls"]
            gemini_week["tokens"] += v["tokens"]
        if k >= (today_dt - timedelta(days=30)).isoformat():
            gemini_month["calls"] += v["calls"]
            gemini_month["tokens"] += v["tokens"]

    # Last 7 days as a sparkline-ready array
    last_7 = []
    for i in range(6, -1, -1):
        d = (today_dt - timedelta(days=i)).isoformat()
        last_7.append({"date": d, "sessions": daily_counts.get(d, 0)})

    return {
        "claude": {
            "events_today": daily_counts.get(today, 0),
            "events_week": week_sessions,
            "events_month": month_sessions,
            "events_total": total_sessions,
            "unique_sessions": unique_sessions,
            "avg_duration_min": avg_duration_min,
            "daily_trend": last_7,
            "days_tracked": len(daily_counts),
        },
        "gemini": {
            "total_calls": gemini_calls,
            "total_tokens": gemini_tokens,
            "week": gemini_week,
            "month": gemini_month,
            "today": gemini_daily.get(today, {"calls": 0, "tokens": 0}),
        },
    }


def collect_overnight_streak() -> list[dict]:
    """Compute 7-day overnight run streak from log files."""
    logs_dir = REPO_ROOT / "data" / "logs"
    today_dt = datetime.now(timezone.utc).date()
    streak = []
    for i in range(6, -1, -1):
        d = today_dt - timedelta(days=i)
        date_str = d.isoformat()
        # Check for overnight log file for this date
        log_pattern = f"overnight_*{date_str}*"
        found = list(logs_dir.glob(log_pattern)) if logs_dir.is_dir() else []
        if found:
            # Check if any log indicates failure
            has_fail = False
            for lf in found:
                try:
                    content = lf.read_text(encoding="utf-8", errors="replace")[:500]
                    if "FAIL" in content or "ERROR" in content:
                        has_fail = True
                        break
                except OSError:
                    pass
            streak.append({"date": date_str, "status": "failed" if has_fail else "ran"})
        else:
            streak.append({"date": date_str, "status": "skipped"})
    return streak


def collect_external_monitoring_structured(overnight_deep_dive: dict | None) -> list[dict] | None:
    """Pre-parse external monitoring markdown into structured sections.

    Reads the raw markdown string from overnight_deep_dive.external_monitoring
    and extracts ### headings with their bullet items into structured data.
    """
    import re
    if not overnight_deep_dive:
        return None
    raw_md = overnight_deep_dive.get("external_monitoring")
    if not raw_md or not isinstance(raw_md, str):
        return None

    # Parse sections: ### headings contain source names, bullets contain findings
    sections = []
    current_section = None
    current_items: list[str] = []

    for line in raw_md.splitlines():
        heading_match = re.match(r"^#{2,3}\s+(.+)", line)
        if heading_match:
            heading = heading_match.group(1).strip()
            # Skip meta headings (Summary, Tier labels)
            if any(skip in heading.lower() for skip in ["summary", "tier 1", "tier 2", "tier 3", "overnight run"]):
                # Flush current section if any
                if current_section and current_items:
                    sections.append({
                        "category": current_section,
                        "items": current_items,
                    })
                    current_section = None
                    current_items = []
                continue
            if current_section and current_items:
                sections.append({
                    "category": current_section,
                    "items": current_items,
                })
            current_section = heading
            current_items = []
        elif line.strip().startswith("- **") or line.strip().startswith("- "):
            item = line.strip().lstrip("- ").strip()
            if item and current_section:
                current_items.append(item)

    if current_section and current_items:
        sections.append({
            "category": current_section,
            "items": current_items,
        })

    return sections if sections else None


def collect_contradictions_structured(overnight_deep_dive: dict | None) -> list[dict] | None:
    """Pre-parse autoresearch contradictions markdown into structured data."""
    import re
    if not overnight_deep_dive:
        return None
    raw_md = overnight_deep_dive.get("autoresearch_contradictions")
    if not raw_md or not isinstance(raw_md, str):
        return None

    contradictions = []
    current: dict = {}

    for line in raw_md.splitlines():
        line = line.strip()
        if line.startswith("- TELOS claim:") or line.startswith("- **TELOS claim"):
            if current:
                contradictions.append(current)
            current = {"claim": line.lstrip("- ").replace("TELOS claim:", "").replace("**TELOS claim**:", "").strip().strip('"')}
        elif line.startswith("- Signal evidence:") or line.startswith("- **Signal evidence"):
            current["evidence"] = line.lstrip("- ").replace("Signal evidence:", "").replace("**Signal evidence**:", "").strip()
        elif line.startswith("- Severity:") or line.startswith("- **Severity"):
            sev = line.split(":")[-1].strip().upper()
            current["severity"] = sev if sev in ("HIGH", "MEDIUM", "LOW") else "MEDIUM"

    if current and current.get("claim"):
        contradictions.append(current)

    # Ensure all entries have all fields
    for c in contradictions:
        c.setdefault("evidence", "")
        c.setdefault("severity", "MEDIUM")

    return contradictions if contradictions else None


def collect_proposals_structured(overnight_deep_dive: dict | None) -> list[dict] | None:
    """Pre-parse autoresearch proposals markdown into structured data."""
    import re
    if not overnight_deep_dive:
        return None
    raw_md = overnight_deep_dive.get("autoresearch_proposals")
    if not raw_md or not isinstance(raw_md, str):
        return None

    proposals = []
    current: dict = {}

    for line in raw_md.splitlines():
        line = line.strip()
        if line.startswith("- File:") or line.startswith("- **File"):
            if current:
                proposals.append(current)
            current = {"file": line.split(":", 1)[-1].strip()}
        elif line.startswith("- Change:") or line.startswith("- **Change"):
            current["change"] = line.split(":", 1)[-1].strip()
        elif line.startswith("- Evidence:") or line.startswith("- **Evidence"):
            current["evidence"] = line.split(":", 1)[-1].strip()

    if current and current.get("file"):
        proposals.append(current)

    for p in proposals:
        p.setdefault("change", "")
        p.setdefault("evidence", "")

    return proposals if proposals else None


def collect_git_hash() -> str:
    """Get current git commit hash for provenance."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Collect Jarvis vitals into JSON")
    parser.add_argument("--file", action="store_true", help="Also write to data/vitals_latest.json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    start_time = time.time()
    errors: list[str] = []
    files_scanned: list[str] = []

    # Collect all data sources
    heartbeat_data, heartbeat_err = collect_heartbeat()
    if heartbeat_err:
        errors.append(heartbeat_err)
    if heartbeat_data:
        files_scanned.append("jarvis_heartbeat.py")

    skill_usage_data, skill_err = collect_skill_usage()
    if skill_err:
        errors.append(skill_err)
    if skill_usage_data:
        files_scanned.append("skill_usage.py")

    trend_data = collect_heartbeat_trend()
    trend_averages = compute_trend_averages(trend_data)
    if trend_data:
        files_scanned.append(str(HEARTBEAT_HISTORY))

    overnight_data = collect_overnight_state()
    if overnight_data:
        files_scanned.append(str(OVERNIGHT_STATE))

    autonomous_value = collect_autonomous_value()
    if AUTONOMOUS_VALUE.is_file():
        files_scanned.append(str(AUTONOMOUS_VALUE))

    telos_introspection = collect_telos_introspection()
    if AUTORESEARCH_DIR.is_dir():
        files_scanned.append(str(AUTORESEARCH_DIR))

    skill_evolution = collect_skill_evolution()
    files_scanned.append(str(SKILLS_DIR))

    overnight_deep_dive = collect_overnight_deep_dive()
    files_scanned.append("overnight_deep_dive")

    unmerged_branches = collect_unmerged_branches()

    morning_feed = collect_morning_feed()
    if morning_feed:
        files_scanned.append(str(MORNING_FEED_DIR))

    session_usage = collect_session_usage()
    if session_usage:
        files_scanned.append(str(EVENTS_DIR))

    isc_producer = collect_isc_producer()
    if isc_producer.get("status") == "OK":
        files_scanned.append(str(ISC_PRODUCER_REPORT))

    overnight_streak = collect_overnight_streak()
    external_monitoring_structured = collect_external_monitoring_structured(overnight_deep_dive)
    contradictions_structured = collect_contradictions_structured(overnight_deep_dive)
    proposals_structured = collect_proposals_structured(overnight_deep_dive)

    elapsed_ms = round((time.time() - start_time) * 1000)

    # Build output
    output = {
        "_schema_version": SCHEMA_VERSION,
        "_provenance": {
            "script": "tools/scripts/vitals_collector.py",
            "git_hash": collect_git_hash(),
            "files_scanned": files_scanned,
            "execution_time_ms": elapsed_ms,
            "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "heartbeat": heartbeat_data.get("metrics", {}) if heartbeat_data else {},
        "heartbeat_meta": {
            "ts": heartbeat_data.get("ts") if heartbeat_data else None,
            "version": heartbeat_data.get("version") if heartbeat_data else None,
            "signals": heartbeat_data.get("signals") if heartbeat_data else None,
            "failures": heartbeat_data.get("failures") if heartbeat_data else None,
            "security_events": heartbeat_data.get("security_events") if heartbeat_data else None,
            "open_tasks": heartbeat_data.get("open_tasks") if heartbeat_data else None,
        },
        "skill_usage": skill_usage_data if skill_usage_data else {},
        "heartbeat_trend": trend_data,
        "trend_averages": trend_averages,
        "overnight": overnight_data,
        "autonomous_value": autonomous_value,
        "telos_introspection": telos_introspection,
        "skill_evolution": skill_evolution,
        "unmerged_branches": unmerged_branches,
        "overnight_deep_dive": overnight_deep_dive,
        "morning_feed": morning_feed,
        "session_usage": session_usage,
        "overnight_streak": overnight_streak,
        "external_monitoring_structured": external_monitoring_structured,
        "contradictions_structured": contradictions_structured,
        "proposals_structured": proposals_structured,
        "isc_producer": isc_producer,
        "memory": {},
        "errors": errors,
    }

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, indent=indent, ensure_ascii=True)

    # Write to stdout
    print(json_str)

    # Optionally write to file for dashboard consumption
    if args.file:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json_str, encoding="utf-8")
        print(f"Written to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
