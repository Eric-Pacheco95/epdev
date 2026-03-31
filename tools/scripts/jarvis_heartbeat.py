#!/usr/bin/env python3
"""Jarvis ISC Engine heartbeat — config-driven, self-improving vitals.

Phase 3E upgrade: replaces basic file counter with 19 collectors,
diff engine, auto-signal writing, and modular alert routing.

Usage:
    python tools/scripts/jarvis_heartbeat.py                  # full run
    python tools/scripts/jarvis_heartbeat.py --quiet           # no alerts
    python tools/scripts/jarvis_heartbeat.py --json            # JSON output
    python tools/scripts/jarvis_heartbeat.py --session-end     # from Stop hook
    python tools/scripts/jarvis_heartbeat.py --config path.json # custom config

Environment:
    SLACK_BOT_TOKEN  xoxb-... for Slack alerts (optional)
    NTFY_TOPIC       ntfy topic for push notifications (optional)

Outputs:
    memory/work/isce/heartbeat_latest.json   -- latest snapshot
    memory/work/isce/heartbeat_history.jsonl  -- append-only log
    memory/learning/signals/                  -- auto-signals on WARN/CRIT
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.collectors.core import (  # noqa: E402
    run_collector, reset_query_cache,
)

DEFAULT_CONFIG = REPO_ROOT / "heartbeat_config.json"
SEVERITY_ORDER = {"OK": 0, "INFO": 1, "WARN": 2, "CRIT": 3}
SEVERITY_RATING = {"INFO": 4, "WARN": 6, "CRIT": 8}


# ── Config ──────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    """Load and validate heartbeat config."""
    if not config_path.is_file():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print("Create heartbeat_config.json or use --config to specify path.", file=sys.stderr)
        print("See heartbeat_config.json.example for a template.", file=sys.stderr)
        sys.exit(1)
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in config: {exc}", file=sys.stderr)
        sys.exit(1)
    if "collectors" not in cfg:
        print("ERROR: Config missing 'collectors' key.", file=sys.stderr)
        sys.exit(1)
    return cfg


def resolve_root(cfg: dict) -> Path:
    """Resolve root_dir from config. Relative paths resolve to repo root."""
    raw = cfg.get("root_dir", ".")
    p = Path(raw)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


# ── Snapshot ────────────────────────────────────────────────────────

def collect_snapshot(cfg: dict, root_dir: Path, prev_metrics: dict = None) -> dict:
    """Run all collectors and build snapshot."""
    now = datetime.now(timezone.utc)
    reset_query_cache()

    metrics = {}
    collector_results = []

    # First pass: non-derived collectors
    for entry in cfg["collectors"]:
        if entry.get("type") == "derived":
            continue
        result = run_collector(entry, root_dir, prev_metrics)
        collector_results.append(result)
        if result["value"] is not None:
            metrics[result["name"]] = result["value"]

    # Second pass: derived collectors (need first-pass results)
    for entry in cfg["collectors"]:
        if entry.get("type") != "derived":
            continue
        result = run_collector(entry, root_dir, prev_metrics, current_metrics=metrics)
        collector_results.append(result)
        if result["value"] is not None:
            metrics[result["name"]] = result["value"]

    # Build snapshot with backward-compatible top-level fields
    snapshot = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": cfg.get("version", 1),
        # Backward compatibility: old heartbeat fields at top level
        "signals": metrics.get("signal_count", 0),
        "failures": metrics.get("failure_count", 0),
        "security_events": metrics.get("security_event_count", 0),
        "open_tasks": metrics.get("open_task_count", 0),
        # New: full metrics dict
        "metrics": {},
    }

    for result in collector_results:
        snapshot["metrics"][result["name"]] = {
            "value": result["value"],
            "unit": result["unit"],
        }
        if result["detail"]:
            snapshot["metrics"][result["name"]]["detail"] = result["detail"]

    return snapshot


# ── Diff Engine ─────────────────────────────────────────────────────

def diff_snapshots(current: dict, previous: dict, cfg: dict) -> list[dict]:
    """Compare two snapshots, evaluate thresholds, return list of changes."""
    if not previous:
        return []

    changes = []
    prev_metrics = previous.get("metrics", {})
    curr_metrics = current.get("metrics", {})

    # Build threshold lookup from config
    threshold_map = {}
    for entry in cfg.get("collectors", []):
        threshold_map[entry["name"]] = entry.get("thresholds", {})

    # Build isc_ref lookup from config
    isc_ref_map = {}
    for entry in cfg.get("collectors", []):
        if entry.get("isc_ref"):
            isc_ref_map[entry["name"]] = entry["isc_ref"]

    for name, curr_data in curr_metrics.items():
        curr_val = curr_data.get("value")
        if curr_val is None:
            continue
        # Skip non-numeric values (like top_tools histogram)
        if not isinstance(curr_val, (int, float)):
            continue

        prev_data = prev_metrics.get(name, {})
        prev_val = prev_data.get("value")
        if prev_val is None or not isinstance(prev_val, (int, float)):
            continue

        delta = round(curr_val - prev_val, 4)
        delta_pct = round((delta / prev_val) * 100, 1) if prev_val != 0 else 0.0

        # Evaluate severity from thresholds
        thresholds = threshold_map.get(name, {})
        severity = _evaluate_severity(curr_val, thresholds)

        change = {
            "metric": name,
            "previous": prev_val,
            "current": curr_val,
            "delta": delta,
            "delta_pct": delta_pct,
            "severity": severity,
        }
        if name in isc_ref_map:
            change["isc_ref"] = isc_ref_map[name]
        changes.append(change)

    return changes


def _evaluate_severity(value: float, thresholds: dict) -> str:
    """Evaluate severity based on threshold config."""
    if not thresholds:
        return "OK"
    # Check CRIT first (highest priority)
    if "crit_above" in thresholds and value >= thresholds["crit_above"]:
        return "CRIT"
    if "crit_below" in thresholds and value <= thresholds["crit_below"]:
        return "CRIT"
    # Then WARN
    if "warn_above" in thresholds and value >= thresholds["warn_above"]:
        return "WARN"
    if "warn_below" in thresholds and value <= thresholds["warn_below"]:
        return "WARN"
    return "OK"


# ── Persistence ─────────────────────────────────────────────────────

def get_snapshot_paths(cfg: dict, root_dir: Path) -> tuple[Path, Path]:
    """Return (latest_path, history_path) from config."""
    snap_dir = root_dir / cfg.get("snapshot_dir", "memory/work/isce")
    snap_dir.mkdir(parents=True, exist_ok=True)
    return snap_dir / "heartbeat_latest.json", snap_dir / "heartbeat_history.jsonl"


def load_previous(latest_path: Path) -> dict | None:
    if not latest_path.is_file():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_snapshot(snap: dict, latest_path: Path, history_path: Path) -> None:
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap) + "\n")


# ── Auto-Signal Writing ────────────────────────────────────────────

def _load_cooldown_state(snap_dir: Path) -> dict:
    """Load cooldown tracker: {metric_name: last_signal_ts_iso}."""
    path = snap_dir / "cooldown_state.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cooldown_state(snap_dir: Path, state: dict) -> None:
    path = snap_dir / "cooldown_state.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _is_cooled_down(metric: str, cooldown_state: dict, cooldown_minutes: int) -> bool:
    """Check if enough time has passed since last signal for this metric."""
    last_ts = cooldown_state.get(metric)
    if not last_ts:
        return True
    try:
        last = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
        return elapsed >= cooldown_minutes
    except (ValueError, TypeError):
        return True


def write_auto_signal(change: dict, cfg: dict, root_dir: Path,
                      cooldown_state: dict) -> bool:
    """Write a learning signal for a threshold crossing. Returns True if written."""
    metric = change["metric"]
    severity = change["severity"]
    cooldown_min = cfg.get("cooldown_minutes", 60)

    if not _is_cooled_down(metric, cooldown_state, cooldown_min):
        return False

    rating = SEVERITY_RATING.get(severity, 6)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    signal_dir = root_dir / cfg.get("signal_output_dir", "memory/learning/signals")
    signal_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize metric name for filename safety
    safe_metric = re.sub(r"[^a-zA-Z0-9_-]", "_", metric)
    base_name = f"{date_str}_heartbeat-{safe_metric}"
    signal_path = signal_dir / f"{base_name}.md"
    counter = 2
    while signal_path.exists():
        signal_path = signal_dir / f"{base_name}_{counter}.md"
        counter += 1

    prev_val = change.get("previous", "N/A")
    curr_val = change.get("current", "N/A")
    delta_pct = change.get("delta_pct", 0)

    direction = "dropped" if change.get("delta", 0) < 0 else "increased"
    isc_ref = change.get("isc_ref", "")
    isc_frontmatter = f"\nisc_ref: \"{isc_ref}\"" if isc_ref else ""
    isc_body = f"\n**ISC Reference**: {isc_ref}" if isc_ref else ""
    content = f"""---
date: {date_str}
rating: {rating}
category: system-health
source: heartbeat-auto
severity: {severity}
metric: {metric}{isc_frontmatter}
---

# ISC Gap: {metric} {direction} {abs(delta_pct):.1f}%

**Metric**: {metric}
**Previous**: {prev_val}
**Current**: {curr_val}
**Severity**: {severity}{isc_body}

**Context**: Detected by ISC engine heartbeat at {ts_str}.

**Suggested action**: Review {metric} and consider adjusting thresholds if this is expected.
"""
    signal_path.write_text(content, encoding="utf-8")

    # Update cooldown state
    cooldown_state[metric] = ts_str

    # Update _signal_meta.json
    meta_path = signal_dir.parent / "_signal_meta.json"
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    signal_count = sum(1 for p in signal_dir.iterdir() if p.is_file() and p.suffix == ".md")
    meta["signal_file_count"] = signal_count
    meta["updated_at_utc"] = ts_str
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return True


# ── Alert Routing ───────────────────────────────────────────────────

def _load_alert_counts(snap_dir: Path) -> dict:
    """Load daily alert count tracker."""
    path = snap_dir / "alert_counts.json"
    if not path.is_file():
        return {"date": "", "counts": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"date": "", "counts": {}}


def _save_alert_counts(snap_dir: Path, state: dict) -> None:
    path = snap_dir / "alert_counts.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def route_alerts(changes: list[dict], cfg: dict, root_dir: Path, quiet: bool = False) -> None:
    """Send alerts based on severity and routing config."""
    routing = cfg.get("alert_routing", {})
    caps = cfg.get("daily_alert_caps", {})
    snap_dir = root_dir / cfg.get("snapshot_dir", "memory/work/isce")

    # Load daily alert counts
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    alert_state = _load_alert_counts(snap_dir)
    if alert_state.get("date") != today:
        alert_state = {"date": today, "counts": {}}

    actionable = [c for c in changes if SEVERITY_ORDER.get(c["severity"], 0) >= SEVERITY_ORDER["WARN"]]
    if not actionable:
        return

    # stdout always
    if not quiet:
        stdout_min = SEVERITY_ORDER.get(routing.get("stdout", {}).get("min_severity", "INFO"), 0)
        for c in changes:
            if SEVERITY_ORDER.get(c["severity"], 0) >= stdout_min:
                print(f"  [{c['severity']}] {c['metric']}: {c['previous']} -> {c['current']} "
                      f"(delta: {c['delta']:+.2f}, {c['delta_pct']:+.1f}%)")

    # Slack
    slack_cfg = routing.get("slack", {})
    if slack_cfg and not quiet:
        slack_min = SEVERITY_ORDER.get(slack_cfg.get("min_severity", "WARN"), 0)
        slack_changes = [c for c in changes if SEVERITY_ORDER.get(c["severity"], 0) >= slack_min
                         and c.get("delta", 0) != 0]
        slack_count = alert_state.get("counts", {}).get("slack", 0)
        slack_cap = caps.get("slack", 20)

        if slack_changes and slack_count < slack_cap:
            try:
                from tools.scripts.slack_notify import notify  # noqa: E402
                # Route by max severity: CRIT -> #general, WARN -> #epdev
                max_sev = max(SEVERITY_ORDER.get(c["severity"], 0) for c in slack_changes)
                sev = "critical" if max_sev >= SEVERITY_ORDER["CRIT"] else "routine"
                lines = [":heartbeat: *Jarvis ISC Engine Alert*"]
                for c in slack_changes[:5]:  # max 5 metrics per message
                    lines.append(f"[{c['severity']}] `{c['metric']}`: {c['previous']} -> "
                                 f"{c['current']} ({c['delta_pct']:+.1f}%)")
                notify("\n".join(lines), severity=sev)
                alert_state.setdefault("counts", {})["slack"] = slack_count + 1
            except (ImportError, ConnectionError, TimeoutError, OSError) as exc:
                print(f"  Slack alert skipped: {exc}", file=sys.stderr)

    # ntfy
    ntfy_cfg = routing.get("ntfy", {})
    if ntfy_cfg and not quiet:
        ntfy_min = SEVERITY_ORDER.get(ntfy_cfg.get("min_severity", "CRIT"), 0)
        ntfy_changes = [c for c in changes if SEVERITY_ORDER.get(c["severity"], 0) >= ntfy_min]
        ntfy_count = alert_state.get("counts", {}).get("ntfy", 0)
        ntfy_cap = caps.get("ntfy", 5)

        if ntfy_changes and ntfy_count < ntfy_cap:
            try:
                from tools.scripts.ntfy_notify import push  # noqa: E402
                titles = [f"[{c['severity']}] {c['metric']}" for c in ntfy_changes[:3]]
                push("Jarvis ISC Alert", body="; ".join(titles), priority="high")
                alert_state.setdefault("counts", {})["ntfy"] = ntfy_count + 1
            except (ImportError, ConnectionError, TimeoutError, OSError) as exc:
                print(f"  ntfy alert skipped: {exc}", file=sys.stderr)

    _save_alert_counts(snap_dir, alert_state)


# ── Human-Readable Output ──────────────────────────────────────────

def build_message(snap: dict, prev: dict | None, changes: list[dict]) -> str:
    """Build a human-readable heartbeat message (ASCII-safe)."""
    ts = snap["ts"]
    lines = [f"Jarvis ISC Engine Heartbeat -- {ts}"]
    lines.append("-" * 50)

    # Key metrics summary
    m = snap.get("metrics", {})
    sig = m.get("signal_count", {}).get("value", "?")
    sig_vel = m.get("signal_velocity", {}).get("value", "?")
    fail = m.get("failure_count", {}).get("value", "?")
    tasks = m.get("open_task_count", {}).get("value", "?")
    isc_r = m.get("isc_ratio", {}).get("value")
    isc_r_str = f"{isc_r:.1%}" if isinstance(isc_r, (int, float)) else "?"
    sess = m.get("sessions_per_day", {}).get("value", "?")
    synth = m.get("learning_loop_health", {}).get("value")
    synth_str = f"{synth}d ago" if isinstance(synth, (int, float)) else "?"

    lines.append(f"Signals: {sig} ({sig_vel}/day)  |  Failures: {fail}  |  Open tasks: {tasks}")
    sched = m.get("scheduled_tasks_unhealthy", {})
    sched_val = sched.get("value")
    sched_str = str(sched_val) if sched_val is not None else "?"
    lines.append(f"ISC ratio: {isc_r_str}  |  Sessions/day: {sess}  |  Last synthesis: {synth_str}")
    lines.append(f"Scheduled tasks unhealthy: {sched_str}"
                 + (f"  ({sched.get('detail', '')})" if sched_val and sched_val > 0 else ""))

    # Collector null check (NFR-006)
    null_collectors = [name for name, data in m.items() if data.get("value") is None]
    if null_collectors:
        lines.append(f"Collectors returning null: {', '.join(null_collectors)}")

    # Changes
    if changes:
        actionable = [c for c in changes if c["severity"] in ("WARN", "CRIT")]
        if actionable:
            lines.append("")
            lines.append("Threshold crossings:")
            for c in actionable:
                lines.append(f"  [{c['severity']}] {c['metric']}: "
                             f"{c['previous']} -> {c['current']} ({c['delta_pct']:+.1f}%)")
    elif prev:
        lines.append("No threshold crossings since last run.")
    else:
        lines.append("First heartbeat run -- no previous snapshot to diff.")

    lines.append("-" * 50)

    # Overall status
    severities = [c["severity"] for c in changes] if changes else []
    if "CRIT" in severities:
        status = "CRITICAL"
    elif "WARN" in severities:
        status = "WARN"
    else:
        status = "HEALTHY"
    lines.append(f"Status: {status}")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis ISC Engine heartbeat")
    parser.add_argument("--quiet", action="store_true", help="Suppress alerts (still writes snapshot)")
    parser.add_argument("--json", action="store_true", help="Output snapshot as JSON")
    parser.add_argument("--session-end", action="store_true", help="Session-end mode (from Stop hook)")
    parser.add_argument("--config", type=str, default=None, help="Path to config file")
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    cfg = load_config(config_path)
    root_dir = resolve_root(cfg)

    # Paths
    latest_path, history_path = get_snapshot_paths(cfg, root_dir)

    # Load previous snapshot
    prev = load_previous(latest_path)
    prev_metrics = {}
    if prev:
        for name, data in prev.get("metrics", {}).items():
            if data.get("value") is not None:
                prev_metrics[name] = data["value"]

    # Collect current snapshot
    snap = collect_snapshot(cfg, root_dir, prev_metrics)

    # Diff
    changes = diff_snapshots(snap, prev, cfg)

    # Meta-alert: detect collectors returning null (monitoring blind spots)
    null_collectors = [
        name for name, data in snap.get("metrics", {}).items()
        if data.get("value") is None
    ]
    if null_collectors:
        # Inject synthetic change entry so it flows through alert routing
        null_severity = "CRIT" if len(null_collectors) >= 3 else "WARN"
        changes.append({
            "metric": "_collector_health",
            "previous": 0,
            "current": len(null_collectors),
            "delta": len(null_collectors),
            "delta_pct": 0.0,
            "severity": null_severity,
            "detail": f"Null collectors: {', '.join(null_collectors)}",
        })

    # Save snapshot
    save_snapshot(snap, latest_path, history_path)

    # Auto-signal writing for WARN/CRIT
    snap_dir = root_dir / cfg.get("snapshot_dir", "memory/work/isce")
    cooldown_state = _load_cooldown_state(snap_dir)
    signals_written = 0
    for change in changes:
        if change["severity"] in ("WARN", "CRIT") and change.get("delta", 0) != 0:
            if write_auto_signal(change, cfg, root_dir, cooldown_state):
                signals_written += 1
    if signals_written > 0:
        _save_cooldown_state(snap_dir, cooldown_state)

    # Output
    if args.json:
        print(json.dumps(snap, indent=2))
    else:
        msg = build_message(snap, prev, changes)
        print(msg)

    # Alert routing
    if not args.quiet:
        route_alerts(changes, cfg, root_dir, quiet=args.quiet)

    sys.exit(0)


if __name__ == "__main__":
    main()
