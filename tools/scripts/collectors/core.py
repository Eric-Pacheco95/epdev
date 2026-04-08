"""Core collector implementations — stdlib only, no external deps.

Collector types:
  file_count          — count files matching ext in a directory
  file_count_velocity — files/day over a window (uses file mtime)
  checkbox_count      — count open checkboxes in a markdown file
  checkbox_delta      — completed tasks over a window (snapshot diff)
  prd_checkbox        — count ISC checkboxes across PRD files
  derived             — compute from other collector results
  query_events        — pull field from query_events.py --json
  file_recency        — days since newest file was modified
  dir_count           — count subdirectories
  disk_usage          — directory size in MB
  hook_output_size    — run a hook script and measure output chars
  stale_branches      — count stale Jarvis autonomous branches
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _resolve_path(path_str: str, root_dir: Path) -> Path:
    """Resolve a path: absolute passes through, relative resolves to root_dir.
    Validates resolved path stays within root_dir to prevent traversal."""
    p = Path(path_str)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (root_dir / p).resolve()
    # Ensure resolved path is within root_dir (prevent traversal)
    try:
        resolved.relative_to(root_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal blocked: {path_str} resolves outside root_dir")
    return resolved


def _result(name: str, value: Any, unit: str, detail: str = None) -> dict:
    return {"name": name, "value": value, "unit": unit, "detail": detail}


# ── file_count ──────────────────────────────────────────────────────

def collect_file_count(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    ext = cfg.get("ext", ".md")
    recursive = cfg.get("recursive", False)
    if not target.is_dir():
        return _result(name, None, "count", f"directory not found: {cfg['path']}")
    glob_pattern = f"**/*{ext}" if recursive else f"*{ext}"
    count = sum(1 for p in target.glob(glob_pattern) if p.is_file())
    return _result(name, count, "count")


# ── file_count_velocity ─────────────────────────────────────────────

def collect_file_count_velocity(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    ext = cfg.get("ext", ".md")
    window = cfg.get("window_days", 7)
    recursive = cfg.get("recursive", False)
    if not target.is_dir():
        return _result(name, None, "per_day", f"directory not found: {cfg['path']}")
    cutoff = datetime.now(timezone.utc) - timedelta(days=window)
    glob_pattern = f"**/*{ext}" if recursive else f"*{ext}"
    count = 0
    for p in target.glob(glob_pattern):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            count += 1
    velocity = round(count / max(window, 1), 2)
    return _result(name, velocity, "per_day", f"{count} files in last {window}d")


# ── checkbox_count ──────────────────────────────────────────────────

def collect_checkbox_count(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    if not target.is_file():
        return _result(name, None, "count", f"file not found: {cfg['path']}")
    text = target.read_text(encoding="utf-8", errors="replace")
    open_count = len(re.findall(r"^\s*-\s+\[ \]", text, re.MULTILINE))
    return _result(name, open_count, "count")


# ── checkbox_delta ──────────────────────────────────────────────────

def collect_checkbox_delta(cfg: dict, root_dir: Path, prev: dict = None) -> dict:
    """Track completion velocity via snapshot diff of open_task_count."""
    name = cfg["name"]
    if not prev or "open_task_count" not in prev:
        return _result(name, None, "per_day", "no previous snapshot for delta")
    # Current open tasks
    target = _resolve_path(cfg["path"], root_dir)
    if not target.is_file():
        return _result(name, None, "per_day", f"file not found: {cfg['path']}")
    text = target.read_text(encoding="utf-8", errors="replace")
    current_open = len(re.findall(r"^\s*-\s+\[ \]", text, re.MULTILINE))
    prev_open = prev["open_task_count"]
    # Positive delta = tasks were completed (open count went down)
    completed = max(0, prev_open - current_open)
    return _result(name, completed, "per_day", f"prev={prev_open}, now={current_open}")


# ── prd_checkbox ────────────────────────────────────────────────────

def _find_prd_files(root_dir: Path, prd_glob: str) -> list[Path]:
    """Find PRD files matching a simple glob like 'memory/work/*/PRD.md'."""
    parts = prd_glob.split("*")
    if len(parts) != 2:
        full = root_dir / prd_glob
        return [full] if full.is_file() else []
    base_dir = root_dir / parts[0]
    suffix = parts[1].lstrip("/").lstrip("\\")
    if not base_dir.is_dir():
        return []
    results = []
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        candidate = entry / suffix
        if candidate.is_file():
            results.append(candidate)
    return results


def collect_prd_checkbox(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    state = cfg.get("checkbox_state", "open")
    prd_glob = cfg.get("prd_glob", "memory/work/*/PRD.md")
    prd_files = _find_prd_files(root_dir, prd_glob)
    if not prd_files:
        return _result(name, None, "count", f"no PRD files found for {prd_glob}")

    total = 0
    for prd_path in prd_files:
        in_code_block = False
        text = prd_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if state == "open" and re.match(r"^\s*-\s+\[ \]", line):
                total += 1
            elif state == "met" and re.match(r"^\s*-\s+\[[xX]\]", line):
                total += 1
    return _result(name, total, "count", f"{len(prd_files)} PRD files scanned")


# ── derived ─────────────────────────────────────────────────────────

def collect_derived(cfg: dict, _root_dir: Path, _prev: dict = None,
                    current_metrics: dict = None) -> dict:
    """Compute derived metrics from other collector results."""
    name = cfg["name"]
    if current_metrics is None:
        return _result(name, None, "ratio", "no metrics available for derivation")
    # ISC ratio: isc_met / (isc_met + isc_open)
    if name == "isc_ratio":
        met = current_metrics.get("isc_met")
        opn = current_metrics.get("isc_open")
        if met is None or opn is None:
            return _result(name, None, "ratio", "isc_met or isc_open unavailable")
        total = met + opn
        ratio = round(met / total, 4) if total > 0 else 0.0
        return _result(name, ratio, "ratio", f"{met}/{total} met")
    return _result(name, None, "ratio", f"unknown derived formula for {name}")


# ── query_events ────────────────────────────────────────────────────

_query_events_cache: dict | None = None


def _get_query_events_data(root_dir: Path) -> dict | None:
    """Run query_events.py --json once and cache the result."""
    global _query_events_cache
    if _query_events_cache is not None:
        return _query_events_cache
    script = root_dir / "tools" / "scripts" / "query_events.py"
    if not script.is_file():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(root_dir),
        )
        if result.returncode == 0 and result.stdout.strip():
            _query_events_cache = json.loads(result.stdout)
            return _query_events_cache
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def collect_query_events(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    field = cfg.get("field", name)
    data = _get_query_events_data(root_dir)
    if data is None:
        return _result(name, None, "varies", "query_events.py --json failed or unavailable")
    value = data.get(field)
    if value is None:
        return _result(name, None, "varies", f"field '{field}' not in query_events output")
    # top_tools is a list of [tool, count] pairs — keep as-is
    unit = "histogram" if isinstance(value, list) else "varies"
    return _result(name, value, unit)


# ── file_recency ────────────────────────────────────────────────────

def collect_file_recency(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    ext = cfg.get("ext", ".md")

    if target.is_file():
        # Single file recency — clamp to 0 so clock skew or filesystem
        # timestamp rounding never produces a nonsensical negative value.
        mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - mtime).days)
        return _result(name, days, "days_since")

    if not target.is_dir():
        return _result(name, None, "days_since", f"path not found: {cfg['path']}")

    # Directory: find most recent file
    newest_mtime = None
    for p in target.iterdir():
        if not p.is_file() or p.suffix != ext:
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if newest_mtime is None or mtime > newest_mtime:
            newest_mtime = mtime

    if newest_mtime is None:
        return _result(name, None, "days_since", f"no {ext} files found in {cfg['path']}")
    days = max(0, (datetime.now(timezone.utc) - newest_mtime).days)
    return _result(name, days, "days_since")


# ── dir_count ───────────────────────────────────────────────────────

def collect_dir_count(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    if not target.is_dir():
        return _result(name, None, "count", f"directory not found: {cfg['path']}")
    count = sum(1 for p in target.iterdir() if p.is_dir())
    return _result(name, count, "count")


# ── disk_usage ──────────────────────────────────────────────────────

def _dir_size_mb(directory: Path) -> float:
    """Walk directory tree and sum file sizes. Returns MB."""
    total = 0
    try:
        for p in directory.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except (PermissionError, OSError):
        pass
    return round(total / (1024 * 1024), 2)


def collect_disk_usage(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    target = _resolve_path(cfg["path"], root_dir)
    if not target.exists():
        return _result(name, None, "MB", f"path not found: {cfg['path']}")
    if target.is_file():
        size = round(target.stat().st_size / (1024 * 1024), 2)
    else:
        size = _dir_size_mb(target)
    return _result(name, size, "MB")


# ── hook_output_size ────────────────────────────────────────────────

def collect_hook_output_size(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    name = cfg["name"]
    hook_path = cfg.get("hook_script", "")
    if not hook_path:
        return _result(name, None, "chars", "no hook_script configured")
    try:
        script = _resolve_path(hook_path, root_dir)
    except ValueError as exc:
        return _result(name, None, "chars", str(exc))
    if not script.is_file():
        return _result(name, None, "chars", f"hook script not found: {cfg.get('hook_script')}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=15,
            cwd=str(root_dir),
        )
        char_count = len(result.stdout)
        return _result(name, char_count, "chars")
    except (subprocess.TimeoutExpired, OSError) as exc:
        return _result(name, None, "chars", f"hook execution failed: {exc}")


# ── scheduled_tasks ─────────────────────────────────────────────────

def collect_scheduled_tasks(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Check health of Windows Task Scheduler tasks in a given folder."""
    name = cfg["name"]
    task_folder = cfg.get("task_folder", "\\Jarvis\\")

    try:
        # PowerShell: get task name, state, and last result for the folder
        ps_cmd = (
            "Get-ScheduledTask -TaskPath '" + task_folder + "' -ErrorAction Stop "
            "| ForEach-Object { "
            "$info = $_ | Get-ScheduledTaskInfo; "
            "$_.TaskName + ',' + $_.State + ',' + [string]$info.LastTaskResult + ',' + [string]$info.NextRunTime "
            "}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return _result(name, None, "count",
                           f"PowerShell error: {result.stderr.strip()[:200]}")

        lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
        if not lines:
            return _result(name, 0, "count", f"no tasks in {task_folder}")

        total = 0
        unhealthy = 0
        details = []
        for line in lines:
            parts = line.split(",", 3)
            if len(parts) < 3:
                continue
            total += 1
            task_name = parts[0].strip()
            state = parts[1].strip()
            try:
                last_result = int(parts[2].strip())
            except ValueError:
                last_result = -1

            # 0x00041303 = SCHED_S_TASK_HAS_NOT_RUN (waiting for first trigger)
            # 0x00041301 = SCHED_S_TASK_RUNNING (currently executing)
            benign_codes = {0, 0x00041303, 0x00041301}
            healthy = (state in ("Ready", "Running")) and last_result in benign_codes
            if not healthy:
                unhealthy += 1
                status_str = f"{state}/0x{last_result & 0xFFFFFFFF:08X}" if last_result != 0 else state
                details.append(f"{task_name}({status_str})")

        detail_str = f"{total} tasks, {unhealthy} unhealthy"
        if details:
            detail_str += ": " + ", ".join(details)
        return _result(name, unhealthy, "count", detail_str)

    except subprocess.TimeoutExpired:
        return _result(name, None, "count", "PowerShell query timed out")
    except OSError as exc:
        return _result(name, None, "count", f"failed to query tasks: {exc}")


# ── auth_health ─────────────────────────────────────────────────────

_AUTH_FAILURE_LOG = Path(__file__).resolve().parents[2] / "data" / "auth_failures.jsonl"


def collect_auth_health(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Test auth token validity for configured services.

    Currently tests:
      - SLACK_BOT_TOKEN via Slack auth.test API

    Returns count of unhealthy tokens. 0 = all healthy.
    Writes to local auth_failures.jsonl as fallback when Slack itself is down.
    """
    name = cfg["name"]
    checks = cfg.get("checks", ["slack"])
    unhealthy = 0
    details = []

    for check in checks:
        if check == "slack":
            token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
            if not token:
                unhealthy += 1
                details.append("slack:missing_token")
                _log_auth_failure(root_dir, "slack", "SLACK_BOT_TOKEN not set")
                continue

            try:
                req = urllib.request.Request(
                    "https://slack.com/api/auth.test",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    data=b"{}",
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    body = json.loads(resp.read())
                    if not body.get("ok"):
                        unhealthy += 1
                        error = body.get("error", "unknown")
                        details.append(f"slack:{error}")
                        _log_auth_failure(root_dir, "slack", error)
                    else:
                        details.append("slack:ok")
            except (urllib.error.URLError, OSError) as exc:
                unhealthy += 1
                details.append("slack:network_error")
                _log_auth_failure(root_dir, "slack", str(exc))

    detail_str = f"{len(checks)} checks, {unhealthy} unhealthy"
    if details:
        detail_str += ": " + ", ".join(details)
    return _result(name, unhealthy, "count", detail_str)


def _log_auth_failure(root_dir: Path, service: str, error: str) -> None:
    """Write auth failure to local JSONL as fallback when Slack is down."""
    log_dir = root_dir / "data"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "auth_failures.jsonl"
        entry = json.dumps({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "service": service,
            "error": error[:200],
        })
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except OSError:
        pass


# ── autonomous_signal_rate ──────────────────────────────────────────

def collect_autonomous_signal_rate(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Count signals with 'Source: autonomous' over last N days, return rate/day."""
    name = cfg.get("name", "autonomous_signal_rate")
    window = cfg.get("window_days", 7)
    signal_dir = _resolve_path(cfg.get("path", "memory/learning/signals"), root_dir)

    if not signal_dir.is_dir():
        return _result(name, None, "per_day", "signal directory not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=window)
    count = 0
    scanned = 0

    # Scan all .md files recursively
    for p in signal_dir.rglob("*.md"):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            continue
        scanned += 1
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                stripped = line.strip().lower()
                if stripped.startswith("- source:") and "autonomous" in stripped:
                    count += 1
                    break
        except OSError:
            continue

    rate = round(count / max(window, 1), 2)
    return _result(name, rate, "per_day", "%d autonomous signals in last %dd (%d scanned)" % (count, window, scanned))


# ── manifest_signal_count ──────────────────────────────────────────

def collect_manifest_signal_count(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Count signals from manifest DB instead of filesystem glob."""
    name = cfg.get("name", "signal_count")
    db_path = root_dir / "data" / "jarvis_index.db"

    if not db_path.exists():
        return _result(name, None, "count", "manifest DB not found")

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        total = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL"
        ).fetchone()[0]
        conn.close()
        return _result(name, total, "count")
    except Exception as exc:
        return _result(name, None, "count", "manifest_signal_count error: %s" % exc)


# ── manifest_signal_velocity ──────────────────────────────────────

def collect_manifest_signal_velocity(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Compute signal velocity from manifest DB date field."""
    name = cfg.get("name", "signal_velocity")
    window = cfg.get("window_days", 7)
    db_path = root_dir / "data" / "jarvis_index.db"

    if not db_path.exists():
        return _result(name, None, "per_day", "manifest DB not found")

    try:
        import sqlite3
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window)).strftime("%Y-%m-%d")
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL AND date >= ?",
            (cutoff,)
        ).fetchone()[0]
        conn.close()
        velocity = round(count / max(window, 1), 2)
        return _result(name, velocity, "per_day", "%d signals in last %dd" % (count, window))
    except Exception as exc:
        return _result(name, None, "per_day", "manifest_signal_velocity error: %s" % exc)


# ── manifest_autonomous_signal_rate ───────────────────────────────

def collect_manifest_autonomous_signal_rate(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Count autonomous signals from manifest DB source field.

    Returns rate per day plus per-category breakdown so volume spikes
    from specific producers (prediction, heartbeat, overnight) are visible.
    """
    name = cfg.get("name", "autonomous_signal_rate")
    window = cfg.get("window_days", 7)
    db_path = root_dir / "data" / "jarvis_index.db"

    if not db_path.exists():
        return _result(name, None, "per_day", "manifest DB not found")

    try:
        import sqlite3
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window)).strftime("%Y-%m-%d")
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL "
            "AND source = 'autonomous' AND date >= ?",
            (cutoff,)
        ).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL AND date >= ?",
            (cutoff,)
        ).fetchone()[0]

        # Per-category breakdown for autonomous signals (identifies which
        # producer is spiking: prediction-accuracy, heartbeat, etc.)
        cat_rows = conn.execute(
            "SELECT COALESCE(category, 'uncategorized'), COUNT(*) FROM signals "
            "WHERE deleted_at IS NULL AND source = 'autonomous' AND date >= ? "
            "GROUP BY category ORDER BY COUNT(*) DESC LIMIT 5",
            (cutoff,)
        ).fetchall()

        # Also count by filename prefix pattern to catch producer origin
        # (e.g., prediction-*, backtest-*, heartbeat-*)
        prefix_rows = conn.execute(
            "SELECT "
            "  CASE "
            "    WHEN filename LIKE 'prediction-%' OR filename LIKE '%prediction%' THEN 'prediction' "
            "    WHEN filename LIKE 'backtest-%' OR filename LIKE '%backtest%' THEN 'backtest' "
            "    WHEN filename LIKE 'heartbeat-%' OR filename LIKE '%heartbeat%' THEN 'heartbeat' "
            "    WHEN filename LIKE 'overnight-%' OR filename LIKE '%overnight%' THEN 'overnight' "
            "    WHEN filename LIKE 'dispatch-%' OR filename LIKE '%dispatch%' THEN 'dispatcher' "
            "    ELSE 'other' "
            "  END as producer, COUNT(*) "
            "FROM signals WHERE deleted_at IS NULL AND source = 'autonomous' AND date >= ? "
            "GROUP BY producer ORDER BY COUNT(*) DESC",
            (cutoff,)
        ).fetchall()
        conn.close()

        rate = round(count / max(window, 1), 2)
        cat_parts = ["%s=%d" % (c, n) for c, n in cat_rows]
        prod_parts = ["%s=%d" % (p, n) for p, n in prefix_rows if n > 0]
        detail = "%d autonomous in last %dd (%d total), rate=%.1f/day, by_category=[%s], by_producer=[%s]" % (
            count, window, total, rate,
            ", ".join(cat_parts) if cat_parts else "none",
            ", ".join(prod_parts) if prod_parts else "none",
        )
        return _result(name, rate, "per_day", detail)
    except Exception as exc:
        return _result(name, None, "per_day",
                       "manifest_autonomous_signal_rate error: %s" % exc)


# ── signal_volume ──────────────────────────────────────────────────

def collect_signal_volume(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Read signal counts from manifest DB (signals table)."""
    name = cfg.get("name", "signal_volume")
    db_path = root_dir / "data" / "jarvis_index.db"

    if not db_path.exists():
        return _result(name, None, "count", "manifest DB not found")

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")

        # Total signals (not soft-deleted)
        total = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL"
        ).fetchone()[0]

        # By processed status
        processed = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE deleted_at IS NULL AND processed = 1"
        ).fetchone()[0]
        unprocessed = total - processed

        # By source (top sources)
        source_rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM signals "
            "WHERE deleted_at IS NULL GROUP BY source ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        conn.close()

        source_parts = ["%s=%d" % (s or "unknown", c) for s, c in source_rows]
        detail = "total=%d processed=%d unprocessed=%d sources=[%s]" % (
            total, processed, unprocessed, ", ".join(source_parts)
        )
        return _result(name, total, "count", detail)

    except Exception as exc:
        return _result(name, None, "count", "signal_volume error: %s" % exc)


# ── producer_health ──────────────────────────────────────────────────

def collect_producer_health(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Check producer_runs manifest table for stale or failed producers."""
    name = cfg.get("name", "producer_health")
    max_age_hours = cfg.get("max_age_hours", 26)
    try:
        sys.path.insert(0, str(root_dir))
        from tools.scripts.manifest_db import query_producer_health
        issues = query_producer_health(max_age_hours=max_age_hours)
        if not issues:
            return _result(name, 0, "count", "all producers healthy")
        detail_parts = []
        for iss in issues:
            detail_parts.append(
                "%s: %s (%.0fh ago, last: %s)" % (
                    iss["producer"], iss["issue"],
                    iss["hours_ago"], iss["last_status"]
                )
            )
        return _result(name, len(issues), "count", "; ".join(detail_parts))
    except Exception as exc:
        return _result(name, None, "count", "producer_health error: %s" % exc)


# ── producer_recency ────────────────────────────────────────────────

def _parse_datetime_utc(value: str) -> "datetime":
    """Parse a date string ('2026-04-04') or ISO datetime to a timezone-aware UTC datetime."""
    value = value.strip()
    # Date-only: YYYY-MM-DD -- use end-of-day (23:59:59 UTC) to give producer benefit of the doubt
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    # ISO datetime with trailing Z
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    # Python 3.7+ fromisoformat handles +HH:MM offsets
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def collect_producer_recency(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Check each producer in orchestration/producers.json for staleness.

    For each producer:
      - Determines last-run time via state_type (json_key, file_mtime, dir_latest)
      - Skips producers still within first_run_grace_until_utc
      - Emits a WARN detail entry when age_hours > alert_threshold_hours
      - Writes a sentinel file to data/producers/{name}.suspend for stale producers

    Returns a single result: value = count of stale/missing producers.
    """
    name = cfg.get("name", "producer_recency")
    producers_path = root_dir / "orchestration" / "producers.json"

    if not producers_path.is_file():
        return _result(name, None, "count", "producers.json not found: orchestration/producers.json")

    try:
        producers = json.loads(producers_path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as exc:
        return _result(name, None, "count", "failed to read producers.json: %s" % exc)

    now_utc = datetime.now(timezone.utc)
    issues = []
    stale_count = 0

    for entry in producers:
        entry_name = entry.get("name", "unknown")
        try:
            # Grace period check
            grace_str = entry.get("first_run_grace_until_utc")
            if grace_str:
                try:
                    grace_until = _parse_datetime_utc(grace_str)
                    if grace_until > now_utc:
                        continue
                except (ValueError, TypeError):
                    # Malformed grace field -- skip staleness check conservatively
                    issues.append("malformed grace period for %s: %s" % (entry_name, grace_str))
                    continue

            state_type = entry.get("state_type", "json_key")
            state_file_str = entry.get("state_file", "")
            state_key = entry.get("state_key")
            alert_threshold_hours = entry.get("alert_threshold_hours", 26)

            if not state_file_str:
                issues.append("state file not found: (empty) [%s]" % entry_name)
                stale_count += 1
                continue

            state_path = _resolve_path(state_file_str, root_dir)
            last_run_utc = None

            if state_type == "json_key":
                if not state_path.is_file():
                    issues.append("state file not found: %s [%s]" % (state_file_str, entry_name))
                    stale_count += 1
                    continue
                try:
                    data = json.loads(state_path.read_text(encoding="utf-8", errors="replace"))
                    raw_value = data.get(state_key) if state_key else None
                    if raw_value is None:
                        issues.append("state key '%s' not found in %s [%s]" % (
                            state_key, state_file_str, entry_name))
                        stale_count += 1
                        continue
                    last_run_utc = _parse_datetime_utc(str(raw_value))
                except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                    issues.append("error reading state for %s: %s" % (entry_name, exc))
                    stale_count += 1
                    continue

            elif state_type == "file_mtime":
                if not state_path.exists():
                    issues.append("state file not found: %s [%s]" % (state_file_str, entry_name))
                    stale_count += 1
                    continue
                mtime = state_path.stat().st_mtime
                last_run_utc = datetime.fromtimestamp(mtime, tz=timezone.utc)

            elif state_type == "dir_latest":
                if not state_path.is_dir():
                    issues.append("state file not found: %s [%s]" % (state_file_str, entry_name))
                    stale_count += 1
                    continue
                newest_mtime = None
                try:
                    for child in state_path.iterdir():
                        # Check files first; fall back to subdir mtime if no files exist
                        if child.is_file() or child.is_dir():
                            child_mtime = child.stat().st_mtime
                            if newest_mtime is None or child_mtime > newest_mtime:
                                newest_mtime = child_mtime
                except OSError as exc:
                    issues.append("error scanning dir %s [%s]: %s" % (
                        state_file_str, entry_name, exc))
                    stale_count += 1
                    continue
                if newest_mtime is None:
                    issues.append("dir is empty: %s [%s]" % (state_file_str, entry_name))
                    stale_count += 1
                    continue
                last_run_utc = datetime.fromtimestamp(newest_mtime, tz=timezone.utc)

            else:
                issues.append("unknown state_type '%s' [%s]" % (state_type, entry_name))
                stale_count += 1
                continue

            # Compare age against threshold
            if last_run_utc is not None:
                age_hours = (now_utc - last_run_utc).total_seconds() / 3600
                if age_hours > alert_threshold_hours:
                    stale_count += 1
                    issues.append("%s stale: %.1fh (threshold: %sh)" % (
                        entry_name, age_hours, alert_threshold_hours))
                    # Write sentinel file (idempotent -- preserves mtime of first suspension)
                    try:
                        sentinel_dir = root_dir / "data" / "producers"
                        sentinel_dir.mkdir(parents=True, exist_ok=True)
                        sentinel_path = sentinel_dir / ("%s.suspend" % entry_name)
                        if not sentinel_path.exists():
                            sentinel_msg = (
                                "suspended by producer_recency watchdog at %s" %
                                now_utc.isoformat()
                            )
                            sentinel_path.write_text(sentinel_msg, encoding="ascii")
                    except OSError as exc:
                        issues.append("failed to write sentinel for %s: %s" % (entry_name, exc))

        except Exception as exc:
            issues.append("error: %s [%s]" % (exc, entry_name))

    detail = "; ".join(issues) if issues else None
    return _result(name, stale_count, "count", detail)


# ── backlog_health ─────────────────────────────────────────────────

# Cache for backlog_health results to avoid repeated file reads in a single snapshot
_backlog_health_cache: dict | None = None


def _get_backlog_health_data(root_dir: Path) -> list[dict]:
    """Call backlog_health.collect_backlog_health() once and cache results."""
    global _backlog_health_cache
    if _backlog_health_cache is not None:
        return _backlog_health_cache
    try:
        sys.path.insert(0, str(root_dir))
        from tools.scripts.collectors.backlog_health import collect_backlog_health
        metrics = collect_backlog_health(None)  # Uses default path
        _backlog_health_cache = metrics
        return metrics
    except Exception as exc:
        # Return error results for all 5 metrics
        _backlog_health_cache = [
            _result("backlog_pending_count", None, "count", f"backlog_health error: {exc}"),
            _result("backlog_pending_review_count", None, "count", f"backlog_health error: {exc}"),
            _result("backlog_manual_review_count", None, "count", f"backlog_health error: {exc}"),
            _result("backlog_failed_count", None, "count", f"backlog_health error: {exc}"),
            _result("backlog_done_count", None, "count", f"backlog_health error: {exc}"),
            _result("backlog_success_rate", None, "ratio", f"backlog_health error: {exc}"),
            _result("backlog_total_count", None, "count", f"backlog_health error: {exc}"),
        ]
        return _backlog_health_cache


def collect_backlog_health_metric(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Extract a single metric from backlog_health output by name."""
    metric_name = cfg.get("metric", "")
    if not metric_name:
        return _result(cfg.get("name", "backlog_unknown"), None, "unknown",
                      "backlog_health_metric: no 'metric' field in config")

    all_metrics = _get_backlog_health_data(root_dir)
    for metric in all_metrics:
        if metric["name"] == metric_name:
            return metric

    # Metric not found in backlog results
    return _result(metric_name, None, "unknown",
                  f"metric '{metric_name}' not found in backlog_health output")


# ── system_resources ───────────────────────────────────────────────

def collect_system_resources(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Count Claude/node processes and HTTPS connections.

    Returns a composite score: total HTTPS connections.
    Detail includes breakdown by process type.
    """
    name = cfg.get("name", "system_resources")

    claude_count = 0
    node_count = 0
    https_connections = 0

    # Count claude.exe processes
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq claude.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0:
            claude_count = sum(
                1 for ln in result.stdout.strip().splitlines()
                if "claude.exe" in ln.lower()
            )
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Count node.exe processes
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq node.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0:
            node_count = sum(
                1 for ln in result.stdout.strip().splitlines()
                if "node.exe" in ln.lower()
            )
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Count established TCP connections + identify top process holders.
    # Per-process attribution prevents the "blame Claude" misattribution bug
    # where a leaking dev server triggered "close idle Claude sessions" alerts
    # while Claude itself was holding only ~5 connections (2026-04-08 incident).
    top_holders_str = "no per-process data"
    try:
        from tools.scripts.lib.net_util import get_https_summary, format_top_holders
        ps_total, holders = get_https_summary(top_n=3)
        if ps_total is not None:
            https_connections = ps_total
            top_holders_str = format_top_holders(holders)
        else:
            # Fallback to legacy netstat-only count if PowerShell unavailable
            result = subprocess.run(
                ["netstat", "-n"],
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            if result.returncode == 0:
                for ln in result.stdout.splitlines():
                    if "ESTABLISHED" in ln and ":443" in ln:
                        https_connections += 1
    except (OSError, subprocess.TimeoutExpired, ImportError):
        pass

    detail = "claude=%d, node=%d, total=%d; top: %s" % (
        claude_count, node_count, https_connections, top_holders_str
    )
    return _result(name, https_connections, "count", detail)


# ── stale_branches ─────────────────────────────────────────────────

def _collect_stale_branches(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Thin wrapper — delegates to branch_lifecycle.collect_stale_branches()."""
    try:
        sys.path.insert(0, str(root_dir))
        from tools.scripts.branch_lifecycle import collect_stale_branches
        return collect_stale_branches(cfg, root_dir, _prev)
    except Exception as exc:
        return _result(cfg.get("name", "stale_branches"), None, "count",
                       "stale_branches import error: %s" % exc)


# ── Dispatcher ──────────────────────────────────────────────────────

COLLECTOR_TYPES = {
    "file_count": collect_file_count,
    "file_count_velocity": collect_file_count_velocity,
    "checkbox_count": collect_checkbox_count,
    "checkbox_delta": collect_checkbox_delta,
    "prd_checkbox": collect_prd_checkbox,
    "derived": collect_derived,
    "query_events": collect_query_events,
    "file_recency": collect_file_recency,
    "dir_count": collect_dir_count,
    "disk_usage": collect_disk_usage,
    "hook_output_size": collect_hook_output_size,
    "scheduled_tasks": collect_scheduled_tasks,
    "auth_health": collect_auth_health,
    "producer_health": collect_producer_health,
    "producer_recency": collect_producer_recency,
    "autonomous_signal_rate": collect_autonomous_signal_rate,
    "signal_volume": collect_signal_volume,
    "manifest_signal_count": collect_manifest_signal_count,
    "manifest_signal_velocity": collect_manifest_signal_velocity,
    "manifest_autonomous_signal_rate": collect_manifest_autonomous_signal_rate,
    "backlog_health_metric": collect_backlog_health_metric,
    "system_resources": collect_system_resources,
    "stale_branches": _collect_stale_branches,
}


def run_collector(cfg: dict, root_dir: Path, prev_metrics: dict = None,
                  current_metrics: dict = None) -> dict:
    """Dispatch to the right collector by type. Returns result dict."""
    ctype = cfg.get("type", "")
    fn = COLLECTOR_TYPES.get(ctype)
    if fn is None:
        return _result(cfg.get("name", "unknown"), None, "unknown",
                       f"unknown collector type: {ctype}")
    if ctype == "derived":
        return fn(cfg, root_dir, prev_metrics, current_metrics=current_metrics)
    return fn(cfg, root_dir, prev_metrics)


def reset_query_cache():
    """Clear the query_events and backlog_health subprocess caches between runs."""
    global _query_events_cache, _backlog_health_cache
    _query_events_cache = None
    _backlog_health_cache = None
