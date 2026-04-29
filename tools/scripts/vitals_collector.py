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
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1.3.0"

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
MEMORY_TIMESERIES = REPO_ROOT / "data" / "logs" / "memory_timeseries.jsonl"
OUTPUT_FILE = REPO_ROOT / "data" / "vitals_latest.json"
AI_PRICING = REPO_ROOT / "config" / "ai_pricing.json"
TAVILY_USAGE = REPO_ROOT / "data" / "tavily_usage.jsonl"
CRYPTO_BOT_ROOT = Path(os.environ.get("CRYPTO_BOT_ROOT", r"C:\Users\ericp\Github\crypto-bot"))
MORALIS_CU_LOG = CRYPTO_BOT_ROOT / "data" / "moralis_cu_counter.jsonl"
MORALIS_STATUS_LOG = CRYPTO_BOT_ROOT / "data" / "moralis_stream_status.jsonl"
MORALIS_MONTHLY_CAP_CU = 2_000_000
MORALIS_ALERT_THRESHOLD_PCT = 70
AI_PRICING_STALE_DAYS = 90

# Local clock hours [start, end) for "overnight while sleeping" reporting on scheduled tasks.
# 1 <= hour < 10 == 1:00am through 9:59am local (Task Scheduler times converted from UTC).
SLEEP_WINDOW_LOCAL_START_HOUR = 1
SLEEP_WINDOW_LOCAL_END_HOUR_EXCL = 10

# FR-006 thresholds — ratio of peak commit to pagefile-allocated
MEMORY_WARN_RATIO = 0.70
MEMORY_CRITICAL_RATIO = 0.90

# FR-009 stub message (exact string — tests match this)
FR009_STUB = "not yet available — blocked on [dependency]"


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


def load_ai_pricing(path: Path = AI_PRICING) -> dict | None:
    """Load config/ai_pricing.json. Returns None on missing/invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def check_ai_pricing_staleness(
    pricing: dict | None,
    now: datetime | None = None,
    stale_days: int = AI_PRICING_STALE_DAYS,
) -> str | None:
    """Return error-key string for errors[] or None if pricing is fresh.

    Return values:
      - "ai_pricing_stale"        -- verified_at > stale_days old
      - "ai_pricing_unparseable"  -- verified_at missing or malformed
      - None                      -- fresh
    """
    if not pricing:
        return None
    verified_at = pricing.get("verified_at", "")
    if not verified_at:
        return "ai_pricing_unparseable"
    try:
        dt = datetime.fromisoformat(str(verified_at))
    except (ValueError, TypeError):
        return "ai_pricing_unparseable"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    age_days = ((now or datetime.now(timezone.utc)) - dt).days
    if age_days > stale_days:
        return "ai_pricing_stale"
    return None


def apply_gemini_pricing(gemini: dict | None, pricing: dict | None) -> None:
    """Mutate gemini dict in place: add cost_usd_month, cost_usd_week using Flash output rate.

    Nanobanana image generation is output-dominated; using output rate as an
    upper-bound estimate. Per-token input/output split not available from the
    source events (gemini_usage records total_tokens only).
    """
    if gemini is None or not pricing:
        return
    flash = (pricing.get("gemini") or {}).get("flash") or {}
    output_rate = flash.get("output_per_1m_usd")
    input_rate = flash.get("input_per_1m_usd")
    try:
        rate = float(output_rate)
        _ = float(input_rate)
    except (TypeError, ValueError):
        return
    if rate <= 0:
        return
    tokens_month = int((gemini.get("month") or {}).get("tokens") or 0)
    tokens_week = int((gemini.get("week") or {}).get("tokens") or 0)
    gemini["cost_usd_month"] = round(tokens_month * rate / 1_000_000, 4)
    gemini["cost_usd_week"] = round(tokens_week * rate / 1_000_000, 4)
    gemini["pricing_rate_per_1m_usd"] = rate
    gemini["pricing_assumption"] = "output_rate_upper_bound"


def collect_tavily_usage(
    path: Path = TAVILY_USAGE,
    pricing: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Roll up data/tavily_usage.jsonl into monthly/weekly call counts.

    "Month" = current calendar month (from first of month, UTC). "Week" = last 7 days.
    """
    now = now or datetime.now(timezone.utc)
    today_dt = now.date()
    month_start = today_dt.replace(day=1)
    week_cutoff = today_dt - timedelta(days=7)

    calls_month = 0
    calls_week = 0
    total = 0
    if path.is_file():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = rec.get("ts", "")
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
                except (ValueError, AttributeError, TypeError):
                    continue
                total += 1
                if dt >= month_start:
                    calls_month += 1
                if dt >= week_cutoff:
                    calls_week += 1
        except OSError:
            pass

    free_tier_limit = None
    if pricing:
        try:
            free_tier_limit = (
                (pricing.get("tavily") or {})
                .get("researcher_tier", {})
                .get("monthly_credits")
            )
        except (AttributeError, TypeError):
            free_tier_limit = None

    return {
        "calls_total": total,
        "calls_month": calls_month,
        "calls_week": calls_week,
        "free_tier_limit": free_tier_limit,
    }


def collect_moralis_vitals(
    cu_path: Path = MORALIS_CU_LOG,
    status_path: Path = MORALIS_STATUS_LOG,
    now: datetime | None = None,
) -> dict:
    """Roll up Moralis stream-status + local CU counter.

    Ground truth sources (probe 2026-04-19 confirmed no usage/stats API exists):
      - cu_path: JSONL written by dashboard/app.py:/moralis-webhook (event*10 CU)
      - status_path: JSONL written by tools/moralis_stream_monitor.py (hourly)

    Emits `alert_70pct` when month-to-date CU exceeds 70% of the 2M Starter cap.
    Slack alerting at that threshold is the /vitals skill's job, not the
    collector's — the collector only surfaces the flag.
    """
    now = now or datetime.now(timezone.utc)
    today_dt = now.date()
    month_start = today_dt.replace(day=1)

    cu_mtd = 0
    cu_today = 0
    events_mtd = 0
    last_event_ts: str | None = None
    if cu_path.is_file():
        try:
            for line in cu_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    dt = datetime.fromisoformat(
                        str(rec.get("ts", "")).replace("Z", "+00:00")
                    ).date()
                except (ValueError, AttributeError, TypeError):
                    continue
                cu = int(rec.get("cu", 0) or 0)
                ev = int(rec.get("events", 0) or 0)
                if dt >= month_start:
                    cu_mtd += cu
                    events_mtd += ev
                    last_event_ts = rec.get("ts") or last_event_ts
                if dt == today_dt:
                    cu_today += cu
        except OSError:
            pass

    status = "unknown"
    status_msg = ""
    addresses = None
    chain_ids: list[str] = []
    last_poll_ts: str | None = None
    last_poll_age_min: float | None = None
    if status_path.is_file():
        try:
            lines = status_path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                status = rec.get("status", "unknown")
                status_msg = rec.get("statusMessage", "")
                addresses = rec.get("amountOfAddresses")
                chain_ids = rec.get("chainIds", []) or []
                last_poll_ts = rec.get("ts")
                try:
                    poll_dt = datetime.fromisoformat(
                        str(last_poll_ts).replace("Z", "+00:00")
                    )
                    last_poll_age_min = round(
                        (now - poll_dt).total_seconds() / 60, 1
                    )
                except (ValueError, AttributeError, TypeError):
                    pass
                break
        except OSError:
            pass

    cap = MORALIS_MONTHLY_CAP_CU
    pct_used = round((cu_mtd / cap) * 100, 1) if cap else 0.0
    alert_70pct = pct_used >= MORALIS_ALERT_THRESHOLD_PCT

    return {
        "stream_status": status,
        "status_message": status_msg,
        "addresses": addresses,
        "chain_ids": chain_ids,
        "last_poll_ts": last_poll_ts,
        "last_poll_age_min": last_poll_age_min,
        "cu_mtd": cu_mtd,
        "cu_today": cu_today,
        "events_mtd": events_mtd,
        "last_event_ts": last_event_ts,
        "monthly_cap_cu": cap,
        "pct_used": pct_used,
        "alert_70pct": alert_70pct,
        "alert_threshold_pct": MORALIS_ALERT_THRESHOLD_PCT,
    }


def _task_scheduler_result_label(last_result: int) -> str:
    """Map Windows Task Scheduler LastTaskResult to a short ASCII label."""
    code = last_result & 0xFFFFFFFF
    # https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-and-success-constants
    known = {
        0: "SUCCESS",
        0x00041300: "SCHED_S_TASK_READY",
        0x00041301: "SCHED_S_TASK_RUNNING",
        0x00041302: "SCHED_S_TASK_DISABLED",
        0x00041303: "SCHED_S_TASK_HAS_NOT_RUN",
        0x00041304: "SCHED_S_TASK_NO_MORE_RUNS",
        0x00041305: "SCHED_S_TASK_NOT_SCHEDULED",
        0x00041306: "SCHED_S_TASK_TERMINATED",
    }
    if code in known:
        return known[code]
    if code != 0:
        return f"HRESULT_0x{code:08X}"
    return "SUCCESS"


def _summarize_overnight_log(content: str) -> tuple[str, int | None, str]:
    """Return (status, exit_code_or_none, failure_hint_ascii).

    status is 'ran' (completed success) or 'failed' (log present but unsuccessful)
    or 'skipped' when called with empty content (unused here).
    """
    if not content.strip():
        return "skipped", None, ""

    tail = content[-16384:] if len(content) > 16384 else content
    exit_code: int | None = None
    for line in reversed(tail.splitlines()):
        lower = line.lower()
        if "complete (exit code:" in lower or "exit code:" in lower:
            idx = lower.rfind("exit code:")
            if idx >= 0:
                rest = line[idx + len("exit code:") :].strip()
                for token in rest.replace(")", " ").split():
                    try:
                        exit_code = int(token)
                        break
                    except ValueError:
                        continue
            break

    fail_markers = (
        "error:",
        "critical:",
        "traceback",
        "exception:",
        "failed to",
        "aborting",
        "winerror",
    )
    lower_tail = tail.lower()
    has_fail_line = any(m in lower_tail for m in fail_markers)

    if exit_code is not None:
        status = "failed" if exit_code != 0 else "ran"
    elif has_fail_line:
        status = "failed"
    else:
        status = "ran"

    hint = ""
    if status == "failed":
        for ln in reversed(tail.splitlines()):
            raw = ln.strip()
            low = raw.lower()
            if any(low.startswith(m.rstrip(":")) or low.startswith(m) for m in ("error", "critical", "traceback")):
                hint = raw[:240]
                break
            if "winerror" in low or "failed to" in low:
                hint = raw[:240]
                break
        if not hint:
            # last non-empty line
            for ln in reversed(tail.splitlines()):
                s = ln.strip()
                if s:
                    hint = s[:240]
                    break

    # ASCII-safe for terminal / Slack cp1252
    hint = hint.encode("ascii", "replace").decode("ascii")

    return status, exit_code, hint


def collect_overnight_streak() -> list[dict]:
    """Compute 7-day overnight run streak from log files with exit code and failure hint."""
    logs_dir = REPO_ROOT / "data" / "logs"
    today_dt = datetime.now(timezone.utc).date()
    streak: list[dict] = []
    for i in range(6, -1, -1):
        d = today_dt - timedelta(days=i)
        date_str = d.isoformat()
        log_pattern = f"overnight_*{date_str}*"
        def _mtime(p: Path) -> float:
            try:
                return p.stat().st_mtime if p.is_file() else 0.0
            except OSError:
                return 0.0

        found = sorted(logs_dir.glob(log_pattern), key=_mtime, reverse=True) if logs_dir.is_dir() else []
        if not found:
            streak.append({"date": date_str, "status": "skipped"})
            continue

        primary = found[0]
        rel = str(primary.relative_to(REPO_ROOT)).replace("\\", "/")
        try:
            full = primary.read_text(encoding="utf-8", errors="replace")
        except OSError:
            streak.append({"date": date_str, "status": "skipped", "log_file": rel, "failure_hint": "could not read log"})
            continue

        status, exit_code, hint = _summarize_overnight_log(full)
        entry: dict = {"date": date_str, "status": status, "log_file": rel}
        if exit_code is not None:
            entry["exit_code"] = exit_code
        if hint:
            entry["failure_hint"] = hint
        streak.append(entry)
    return streak


def _local_hour_from_utc_iso(iso_ts: str | None) -> int | None:
    """Return local wall-clock hour (0-23) for a UTC ISO8601 string, or None."""
    if not iso_ts or not isinstance(iso_ts, str):
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone().hour)
    except (ValueError, TypeError, OSError):
        return None


def _scheduled_task_touches_sleep_window(last_run: str | None, next_run: str | None) -> bool:
    """True if last or next run (converted to system local time) falls in sleep window."""
    for ts in (last_run, next_run):
        h = _local_hour_from_utc_iso(ts)
        if h is None:
            continue
        if SLEEP_WINDOW_LOCAL_START_HOUR <= h < SLEEP_WINDOW_LOCAL_END_HOUR_EXCL:
            return True
    return False


def _heartbeat_scheduled_task_folder() -> str:
    cfg = _read_json(REPO_ROOT / "heartbeat_config.json")
    if not isinstance(cfg, dict):
        return "\\Jarvis\\"
    for c in cfg.get("collectors") or []:
        if not isinstance(c, dict):
            continue
        if c.get("name") == "scheduled_tasks_unhealthy" and c.get("type") == "scheduled_tasks":
            return str(c.get("task_folder") or "\\Jarvis\\")
    return "\\Jarvis\\"


def collect_scheduled_tasks_detail() -> dict:
    """Per-task Windows Task Scheduler snapshot for vitals dashboard.

    Fields align with Get-ScheduledTaskInfo: last/next run, result code, missed runs.
    """
    import platform

    sleep_meta = {
        "local_start_hour_inclusive": SLEEP_WINDOW_LOCAL_START_HOUR,
        "local_end_hour_exclusive": SLEEP_WINDOW_LOCAL_END_HOUR_EXCL,
        "note": "last_run_time/next_run_time are UTC from Task Scheduler; hours use system local TZ",
        "task_names": [],
    }

    if platform.system() != "Windows":
        return {
            "platform": "non-windows",
            "task_folder": None,
            "query_error": None,
            "tasks": [],
            "healthy_count": 0,
            "unhealthy_count": 0,
            "total_count": 0,
            "sleep_window": sleep_meta,
        }

    task_folder = _heartbeat_scheduled_task_folder()
    ps = (
        "$tasks = @(); "
        "Get-ScheduledTask -TaskPath $env:JARVIS_TASK_PATH -ErrorAction Stop | ForEach-Object { "
        "$inf = $_ | Get-ScheduledTaskInfo; "
        "$tasks += [pscustomobject]@{ "
        "TaskName = $_.TaskName; "
        "State = [string]$_.State; "
        "LastTaskResult = [int]$inf.LastTaskResult; "
        "LastRunTime = if ($null -ne $inf.LastRunTime -and $inf.LastRunTime.Year -ge 2000) "
        "{ $inf.LastRunTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') } else { $null }; "
        "NextRunTime = if ($null -ne $inf.NextRunTime -and $inf.NextRunTime.Year -ge 2000) "
        "{ $inf.NextRunTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') } else { $null }; "
        "MissedRuns = [int]$inf.NumberOfMissedRuns "
        "} }; "
        "$tasks | ConvertTo-Json -Depth 4 -Compress"
    )
    child_env = {**os.environ, "JARVIS_TASK_PATH": task_folder}

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            env=child_env,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "platform": "windows",
            "task_folder": task_folder,
            "query_error": str(exc)[:300],
            "tasks": [],
            "healthy_count": 0,
            "unhealthy_count": 0,
            "total_count": 0,
            "sleep_window": sleep_meta,
        }

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[:400]
        return {
            "platform": "windows",
            "task_folder": task_folder,
            "query_error": err or f"powershell exit {result.returncode}",
            "tasks": [],
            "healthy_count": 0,
            "unhealthy_count": 0,
            "total_count": 0,
            "sleep_window": sleep_meta,
        }

    raw = (result.stdout or "").strip()
    if not raw:
        return {
            "platform": "windows",
            "task_folder": task_folder,
            "query_error": None,
            "tasks": [],
            "healthy_count": 0,
            "unhealthy_count": 0,
            "total_count": 0,
            "sleep_window": sleep_meta,
        }

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "platform": "windows",
            "task_folder": task_folder,
            "query_error": f"invalid json from powershell: {exc}",
            "tasks": [],
            "healthy_count": 0,
            "unhealthy_count": 0,
            "total_count": 0,
            "sleep_window": sleep_meta,
        }

    rows = parsed if isinstance(parsed, list) else [parsed]
    benign = {0, 0x00041303, 0x00041301}
    tasks_out: list[dict] = []
    healthy = 0
    unhealthy = 0
    now = datetime.now(timezone.utc)

    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("TaskName") or "").strip()
        state = str(row.get("State") or "").strip()
        try:
            last_result = int(row.get("LastTaskResult", -1))
        except (TypeError, ValueError):
            last_result = -1
        last_run = row.get("LastRunTime")
        next_run = row.get("NextRunTime")
        try:
            missed = int(row.get("MissedRuns", 0))
        except (TypeError, ValueError):
            missed = 0

        is_healthy = (state in ("Ready", "Running")) and (last_result in benign)
        if is_healthy:
            healthy += 1
        else:
            unhealthy += 1

        outcome = "unknown"
        if state.lower() == "disabled":
            outcome = "disabled"
        elif last_result == 0x00041303 and missed == 0:
            outcome = "never_ran_yet"
        elif last_result == 0x00041301:
            outcome = "running"
        elif last_result == 0:
            outcome = "completed_ok"
        elif last_result in benign:
            outcome = "benign_nonzero"
        else:
            outcome = "failed"

        should_note: list[str] = []
        if missed > 0:
            should_note.append(f"missed_runs={missed}")
        if next_run and isinstance(next_run, str):
            try:
                nxt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                if nxt < now and last_result not in (0, 0x00041301):
                    should_note.append("next_run_in_past")
            except (ValueError, TypeError):
                pass

        sleep_touch = _scheduled_task_touches_sleep_window(
            last_run if isinstance(last_run, str) else None,
            next_run if isinstance(next_run, str) else None,
        )

        tasks_out.append(
            {
                "task_name": name,
                "state": state,
                "last_task_result": last_result,
                "last_result_label": _task_scheduler_result_label(last_result),
                "last_run_time": last_run,
                "next_run_time": next_run,
                "missed_runs": missed,
                "healthy": is_healthy,
                "outcome": outcome,
                "schedule_flags": should_note,
                "sleep_window_touch": sleep_touch,
            }
        )

    tasks_out.sort(key=lambda r: r.get("task_name") or "")

    sleep_names = [t["task_name"] for t in tasks_out if t.get("sleep_window_touch")]

    return {
        "platform": "windows",
        "task_folder": task_folder,
        "query_error": None,
        "tasks": tasks_out,
        "healthy_count": healthy,
        "unhealthy_count": unhealthy,
        "total_count": len(tasks_out),
        "sleep_window": {
            "local_start_hour_inclusive": SLEEP_WINDOW_LOCAL_START_HOUR,
            "local_end_hour_exclusive": SLEEP_WINDOW_LOCAL_END_HOUR_EXCL,
            "note": "last_run_time/next_run_time are UTC from Task Scheduler; hours use system local TZ",
            "task_names": sleep_names,
        },
    }


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


def _parse_ts(ts: str) -> datetime | None:
    """Parse ISO-8601 Z timestamp used by sampler + hook_events."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def load_memory_ticks(path: Path, since_hours: int, now: datetime | None = None) -> list[dict]:
    """Return ticks from memory_timeseries.jsonl within the last `since_hours` window."""
    if not path.exists():
        return []
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=since_hours)
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                tick = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(tick.get("ts", ""))
            if ts is not None and ts >= cutoff:
                out.append(tick)
    except OSError:
        return []
    return out


def _commit_limit_bytes() -> int:
    """Return Windows commit limit (RAM + pagefile) in bytes.

    Uses Win32_OperatingSystem.TotalVirtualMemorySize (KB) — authoritative
    on Windows. Falls back to psutil RAM+swap sum if WMI unavailable.
    """
    try:
        import subprocess as _sp
        r = _sp.run(
            ["powershell", "-NonInteractive", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).TotalVirtualMemorySize"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return int(r.stdout.strip()) * 1024
    except Exception:
        pass
    try:
        import psutil
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return int(vm.total) + int(sw.total)
    except Exception:
        return 0


def _pagefile_bytes() -> int:
    """Return raw pagefile size (swap only, not RAM) in bytes."""
    try:
        import psutil
        return int(psutil.swap_memory().total)
    except Exception:
        return 0


def build_memory_summary(
    ticks: list[dict],
    commit_limit_bytes: int,
    pagefile_bytes: int = 0,
    window_hours: int = 24,
) -> dict:
    """FR-006 summary: peak commit + ratio + top-1 consumer at peak + completion rate.

    commit_limit_bytes: RAM + pagefile (Windows commit limit); denominator for peak_ratio.
    pagefile_bytes: raw pagefile size only; denominator for pagefile_pressure.

    Expected ticks in 24h window per PRD:
      night (22:00–08:00, 2-min cadence) = 10 * 30 = 300
      day   (08:00–22:00, 10-min cadence) = 14 * 6 = 84
      total = 384
    """
    expected_ticks_24h = 384
    expected = int(expected_ticks_24h * (window_hours / 24))

    if pagefile_bytes:
        pf_total_gb = pagefile_bytes / 1024 ** 3
        peak_pf_used_gb = max(
            (max(0.0, pf_total_gb - float(t.get("pagefile_free_gb") or pf_total_gb))
             for t in ticks),
            default=0.0,
        )
        pagefile_pressure = round(peak_pf_used_gb / pf_total_gb, 4) if pf_total_gb else 0.0
    else:
        pagefile_pressure = 0.0

    if not ticks:
        return {
            "status": "NO_DATA",
            "window_hours": window_hours,
            "tick_count": 0,
            "expected_ticks": expected,
            "tick_completion_rate": 0.0,
            "peak_commit_bytes": 0,
            "peak_commit_gb": 0.0,
            "peak_ratio": 0.0,
            "pagefile_pressure": pagefile_pressure,
            "top1_consumer_at_peak": None,
            "commit_limit_bytes": commit_limit_bytes,
            "warn_threshold_ratio": MEMORY_WARN_RATIO,
            "critical_threshold_ratio": MEMORY_CRITICAL_RATIO,
        }

    peak_tick = max(ticks, key=lambda t: int(t.get("commit_bytes_sum") or 0))
    peak_bytes = int(peak_tick.get("commit_bytes_sum") or 0)
    peak_ratio = (peak_bytes / commit_limit_bytes) if commit_limit_bytes else 0.0

    top5 = peak_tick.get("top5_procs") or []
    top1_name = top5[0].get("name") if top5 and isinstance(top5[0], dict) else None

    if peak_ratio >= MEMORY_CRITICAL_RATIO:
        status = "CRITICAL"
    elif peak_ratio >= MEMORY_WARN_RATIO:
        status = "WARN"
    else:
        status = "HEALTHY"

    completion_rate = min(1.0, len(ticks) / expected) if expected else 0.0

    return {
        "status": status,
        "window_hours": window_hours,
        "tick_count": len(ticks),
        "expected_ticks": expected,
        "tick_completion_rate": round(completion_rate, 4),
        "peak_commit_bytes": peak_bytes,
        "peak_commit_gb": round(peak_bytes / (1024 ** 3), 2),
        "peak_ratio": round(peak_ratio, 4),
        "pagefile_pressure": pagefile_pressure,
        "top1_consumer_at_peak": top1_name,
        "commit_limit_bytes": commit_limit_bytes,
        "warn_threshold_ratio": MEMORY_WARN_RATIO,
        "critical_threshold_ratio": MEMORY_CRITICAL_RATIO,
    }


def build_memory_detail(
    ticks: list[dict],
    commit_limit_bytes: int,
    pagefile_bytes: int = 0,
    window_hours: int = 24,
) -> dict:
    """FR-007 detail: hourly buckets (max/avg) + top-5 consumer histogram + over-commit crossings."""
    from collections import defaultdict

    summary = build_memory_summary(ticks, commit_limit_bytes, pagefile_bytes, window_hours)

    buckets: dict[str, list[int]] = defaultdict(list)
    histogram: dict[str, dict[str, float]] = {}
    overcommits: list[dict] = []

    for t in ticks:
        ts = _parse_ts(t.get("ts", ""))
        commit = int(t.get("commit_bytes_sum") or 0)
        if ts is not None:
            bucket = ts.strftime("%Y-%m-%dT%H:00Z")
            buckets[bucket].append(commit)
        if commit_limit_bytes and commit > commit_limit_bytes:
            overcommits.append({
                "ts": t.get("ts"),
                "commit_gb": round(commit / (1024 ** 3), 2),
                "commit_limit_gb": round(commit_limit_bytes / (1024 ** 3), 2),
                "ratio": round(commit / commit_limit_bytes, 4),
            })
        for proc in t.get("top5_procs") or []:
            if not isinstance(proc, dict):
                continue
            name = proc.get("name") or "unknown"
            paged_mb = float(proc.get("paged_mb") or 0)
            entry = histogram.setdefault(name, {"occurrences": 0, "total_paged_mb": 0.0})
            entry["occurrences"] += 1
            entry["total_paged_mb"] += paged_mb

    hourly = [
        {
            "hour": bucket,
            "tick_count": len(vals),
            "max_gb": round(max(vals) / (1024 ** 3), 2),
            "avg_gb": round((sum(vals) / len(vals)) / (1024 ** 3), 2),
        }
        for bucket, vals in sorted(buckets.items())
    ]

    top5_histogram = sorted(
        (
            {
                "name": name,
                "occurrences": int(entry["occurrences"]),
                "avg_paged_mb": round(entry["total_paged_mb"] / entry["occurrences"], 1),
            }
            for name, entry in histogram.items()
        ),
        key=lambda x: x["occurrences"],
        reverse=True,
    )[:5]

    return {
        "summary": summary,
        "hourly_buckets": hourly,
        "top5_histogram": top5_histogram,
        "overcommit_crossings": overcommits,
    }


def load_context_file_counts(
    events_dir: Path,
    days: int = 7,
    top_n: int = 20,
    now: datetime | None = None,
) -> list[dict]:
    """FR-008: aggregate Read.file_path occurrences from hook_events JSONL, filter .md, top-N by count."""
    if not events_dir.exists():
        return []
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    counts: dict[str, int] = {}

    for jsonl in events_dir.glob("*.jsonl"):
        try:
            lines = jsonl.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("tool") != "Read" or rec.get("hook") != "PostToolUse":
                continue
            fp = rec.get("file_path")
            if not isinstance(fp, str) or not fp.lower().endswith(".md"):
                continue
            ts = _parse_ts(rec.get("ts", ""))
            if ts is None or ts < cutoff:
                continue
            counts[fp] = counts.get(fp, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return [{"file_path": fp, "count": c} for fp, c in ranked]


def collect_memory_summary() -> dict:
    """Wrapper for main() default path — window = 24h."""
    ticks = load_memory_ticks(MEMORY_TIMESERIES, since_hours=24)
    return build_memory_summary(
        ticks,
        commit_limit_bytes=_commit_limit_bytes(),
        pagefile_bytes=_pagefile_bytes(),
        window_hours=24,
    )


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Collect Jarvis vitals into JSON")
    parser.add_argument("--file", action="store_true", help="Also write to data/vitals_latest.json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--memory", action="store_true", help="FR-007: emit detailed memory panel (hourly buckets, top-5 histogram, over-commit crossings) and exit")
    parser.add_argument("--context-files", action="store_true", help="FR-008: emit top-20 .md files Read in last 7 days and exit")
    parser.add_argument("--token-costs", action="store_true", help="FR-009 stub: print blocked-on message and exit")
    parser.add_argument("--reaper-log", action="store_true", help="FR-009 stub: print blocked-on message and exit")
    parser.add_argument("--tavily-log-file", default=None, help="Override path to tavily_usage.jsonl (defaults to data/tavily_usage.jsonl)")
    parser.add_argument("--ai-pricing-file", default=None, help="Override path to config/ai_pricing.json (defaults to config/ai_pricing.json)")
    args = parser.parse_args()

    # FR-009 stubs — fast path, no full collection.
    # Write bytes directly so the em dash survives Windows cp1252 stdout default.
    if args.token_costs or args.reaper_log:
        sys.stdout.buffer.write((FR009_STUB + "\n").encode("utf-8"))
        sys.stdout.flush()
        sys.exit(0)

    # FR-007 detailed memory panel — fast path
    if args.memory:
        ticks = load_memory_ticks(MEMORY_TIMESERIES, since_hours=24)
        detail = build_memory_detail(
            ticks,
            commit_limit_bytes=_commit_limit_bytes(),
            pagefile_bytes=_pagefile_bytes(),
            window_hours=24,
        )
        indent = 2 if args.pretty else None
        print(json.dumps(detail, indent=indent, ensure_ascii=True))
        sys.exit(0)

    # FR-008 context-files — fast path
    if args.context_files:
        rows = load_context_file_counts(EVENTS_DIR, days=7, top_n=20)
        indent = 2 if args.pretty else None
        print(json.dumps({"context_files": rows, "window_days": 7}, indent=indent, ensure_ascii=True))
        sys.exit(0)

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

    # --- AI pricing + Tavily rollup (B2b) ---
    pricing_path = Path(args.ai_pricing_file) if args.ai_pricing_file else AI_PRICING
    tavily_path = Path(args.tavily_log_file) if args.tavily_log_file else TAVILY_USAGE
    ai_pricing = load_ai_pricing(pricing_path)
    if ai_pricing is not None:
        files_scanned.append(str(pricing_path))
        stale_key = check_ai_pricing_staleness(ai_pricing)
        if stale_key:
            errors.append(stale_key)
    if session_usage is None:
        session_usage = {"claude": {}, "gemini": {}}
    apply_gemini_pricing(session_usage.get("gemini"), ai_pricing)
    session_usage["tavily"] = collect_tavily_usage(tavily_path, ai_pricing)
    if tavily_path.is_file():
        files_scanned.append(str(tavily_path))

    moralis_vitals = collect_moralis_vitals()
    if MORALIS_CU_LOG.is_file():
        files_scanned.append(str(MORALIS_CU_LOG))
    if MORALIS_STATUS_LOG.is_file():
        files_scanned.append(str(MORALIS_STATUS_LOG))

    isc_producer = collect_isc_producer()
    if isc_producer.get("status") == "OK":
        files_scanned.append(str(ISC_PRODUCER_REPORT))

    overnight_streak = collect_overnight_streak()
    scheduled_tasks_detail = collect_scheduled_tasks_detail()
    if scheduled_tasks_detail.get("platform") == "windows" and not scheduled_tasks_detail.get("query_error"):
        files_scanned.append("scheduled_tasks (powershell)")
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
        "moralis_vitals": moralis_vitals,
        "overnight_streak": overnight_streak,
        "scheduled_tasks_detail": scheduled_tasks_detail,
        "external_monitoring_structured": external_monitoring_structured,
        "contradictions_structured": contradictions_structured,
        "proposals_structured": proposals_structured,
        "isc_producer": isc_producer,
        "memory": collect_memory_summary(),
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
