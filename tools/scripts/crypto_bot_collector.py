#!/usr/bin/env python3
"""SENSE collector for crypto-bot: polls REST API, reads logs, writes state, dead-man's switch.

Phase A of Jarvis Crypto-Bot Project Manager (PRD_jarvis_crypto_manager.md).

READ-ONLY: This script NEVER calls POST/PATCH/DELETE endpoints or opens bot.db directly.

Usage:
    python tools/scripts/crypto_bot_collector.py          # single poll
    python tools/scripts/crypto_bot_collector.py --loop    # continuous 15-min polling
    python tools/scripts/crypto_bot_collector.py --status  # print last state summary
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
STATE_FILE = DATA_DIR / "crypto_bot_state.json"
HISTORY_FILE = DATA_DIR / "crypto_bot_history.jsonl"
DMS_STATE_FILE = DATA_DIR / "crypto_bot_dms_state.json"  # dead-man's switch

CRYPTO_BOT_ROOT = Path("C:/Users/ericp/Github/crypto-bot")
LOG_DIR = CRYPTO_BOT_ROOT / "data" / "logs"
ALERTS_FILE = CRYPTO_BOT_ROOT / "data" / "alerts" / "alerts.jsonl"
PATCHES_FILE = CRYPTO_BOT_ROOT / "data" / "patches.jsonl"

API_BASE = "http://localhost:8080"
API_TIMEOUT_S = 10
POLL_INTERVAL_S = 3600  # 60 minutes (synced with Jarvis heartbeat)
LOG_TAIL_LINES = 200

# Dead-man's switch config
DMS_MAX_CONSECUTIVE_FAILURES = 3
DMS_MAX_ALERTS_PER_INCIDENT = 3

# API endpoints -- GET only
ENDPOINTS = {
    "status": "/api/status",
    "portfolio": "/api/portfolio",
    "pipeline_health": "/api/pipeline-health",
    "paper_report": "/api/paper-report",
    "signal_attribution": "/api/signal-attribution",
    "costs": "/api/costs",
}


def _ascii_safe(text: str) -> str:
    """Strip non-ASCII for Windows cp1252 safety."""
    return text.encode("ascii", errors="replace").decode("ascii")


# ---------------------------------------------------------------------------
# API polling (GET only -- never POST/PATCH/DELETE)
# ---------------------------------------------------------------------------
def _poll_endpoint(path: str) -> tuple[bool, Any]:
    """GET a single API endpoint. Returns (success, data_or_error)."""
    import urllib.error
    import urllib.request

    url = f"{API_BASE}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_S) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return True, json.loads(body)
            except json.JSONDecodeError:
                return True, body
    except urllib.error.URLError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)


def poll_all_endpoints() -> dict[str, Any]:
    """Poll all 6 GET endpoints. Returns dict with results and metadata."""
    results: dict[str, Any] = {}
    all_ok = True
    status_ok = False

    for name, path in ENDPOINTS.items():
        ok, data = _poll_endpoint(path)
        results[name] = {"ok": ok, "data": data if ok else None, "error": None if ok else data}
        if not ok:
            all_ok = False
        if name == "status" and ok:
            status_ok = True

    return {
        "endpoints": results,
        "all_ok": all_ok,
        "status_ok": status_ok,
        "poll_timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Log file reading (tail last N lines -- never full reads on 90MB+ files)
# ---------------------------------------------------------------------------
LOG_FILES = ["uvicorn.log", "celery_worker.log", "celery_beat.log", "health_monitor.log"]


def _tail_file(filepath: Path, n: int = LOG_TAIL_LINES) -> list[str]:
    """Read last N lines from a file using seek-to-end approach."""
    if not filepath.is_file():
        return []
    try:
        size = filepath.stat().st_size
        if size == 0:
            return []
        # Read from end -- cap at 256KB to avoid OOM on huge files
        read_size = min(size, 256 * 1024)
        with open(filepath, "rb") as f:
            f.seek(max(0, size - read_size))
            chunk = f.read().decode("utf-8", errors="replace")
        lines = chunk.splitlines()
        return lines[-n:]
    except OSError:
        return []


def read_logs() -> dict[str, list[str]]:
    """Tail last 200 lines from each crypto-bot log file."""
    result = {}
    for name in LOG_FILES:
        lines = _tail_file(LOG_DIR / name)
        result[name] = lines
    return result


# ---------------------------------------------------------------------------
# Alert and patch audit trail reading (new entries since last poll)
# ---------------------------------------------------------------------------
def _read_jsonl_since(filepath: Path, last_offset: int) -> tuple[list[dict], int]:
    """Read new JSONL entries since byte offset. Returns (entries, new_offset)."""
    if not filepath.is_file():
        return [], 0
    try:
        size = filepath.stat().st_size
        if size <= last_offset:
            return [], size
        entries = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(last_offset)
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries, size
    except OSError:
        return [], last_offset


def read_alerts_and_patches(offsets: dict) -> dict:
    """Read new entries from alerts.jsonl and patches.jsonl."""
    alerts, alerts_offset = _read_jsonl_since(
        ALERTS_FILE, offsets.get("alerts_offset", 0)
    )
    patches, patches_offset = _read_jsonl_since(
        PATCHES_FILE, offsets.get("patches_offset", 0)
    )
    return {
        "new_alerts": alerts,
        "new_patches": patches,
        "alerts_offset": alerts_offset,
        "patches_offset": patches_offset,
    }


# ---------------------------------------------------------------------------
# State snapshot (written to data/crypto_bot_state.json)
# ---------------------------------------------------------------------------
def build_state_snapshot(
    api_results: dict,
    logs: dict[str, list[str]],
    audit: dict,
) -> dict:
    """Build consolidated state snapshot from all collected data."""
    now = datetime.now(timezone.utc).isoformat()

    # Extract key metrics from API data
    status_data = api_results["endpoints"].get("status", {}).get("data") or {}
    paper_data = api_results["endpoints"].get("paper_report", {}).get("data") or {}

    # Process health from status endpoint
    processes = {}
    if isinstance(status_data, dict):
        processes = status_data.get("processes", status_data.get("services", {}))

    # Trade counts from paper report
    trade_count_open = 0
    trade_count_closed = 0
    realized_pnl = 0.0
    win_rate = 0.0
    drawdown_pct = 0.0

    if isinstance(paper_data, dict):
        trade_count_open = paper_data.get("open_trades", paper_data.get("open_count", 0))
        trade_count_closed = paper_data.get("closed_trades", paper_data.get("closed_count", 0))
        realized_pnl = paper_data.get("realized_pnl", paper_data.get("total_pnl", 0.0))
        win_rate = paper_data.get("win_rate", 0.0)
        drawdown_pct = paper_data.get("drawdown_pct", paper_data.get("max_drawdown", 0.0))

    # Log error summary -- count ERROR/CRITICAL lines in recent logs
    log_errors: dict[str, int] = {}
    for logname, lines in logs.items():
        err_count = sum(
            1 for line in lines
            if "ERROR" in line or "CRITICAL" in line or "Traceback" in line
        )
        if err_count > 0:
            log_errors[logname] = err_count

    return {
        "timestamp": now,
        "api_reachable": api_results["all_ok"],
        "status_reachable": api_results["status_ok"],
        "processes": processes,
        "trade_count_open": trade_count_open,
        "trade_count_closed": trade_count_closed,
        "realized_pnl": realized_pnl,
        "win_rate": win_rate,
        "drawdown_pct": drawdown_pct,
        "new_alerts_count": len(audit.get("new_alerts", [])),
        "new_patches_count": len(audit.get("new_patches", [])),
        "new_alerts": audit.get("new_alerts", []),
        "new_patches": audit.get("new_patches", []),
        "log_errors": log_errors,
        "alerts_offset": audit.get("alerts_offset", 0),
        "patches_offset": audit.get("patches_offset", 0),
        "raw_api": {
            name: ep.get("data")
            for name, ep in api_results["endpoints"].items()
            if ep.get("ok")
        },
    }


def write_state(snapshot: dict) -> None:
    """Write state snapshot to data/crypto_bot_state.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(snapshot, indent=2, default=str),
        encoding="utf-8",
    )


def append_history(snapshot: dict) -> None:
    """Append summary row to data/crypto_bot_history.jsonl (FR-007)."""
    row = {
        "timestamp": snapshot["timestamp"],
        "trade_count_open": snapshot["trade_count_open"],
        "trade_count_closed": snapshot["trade_count_closed"],
        "realized_pnl": snapshot["realized_pnl"],
        "win_rate": snapshot["win_rate"],
        "drawdown_pct": snapshot["drawdown_pct"],
        "processes_alive": snapshot.get("status_reachable", False),
        "alerts_fired_count": snapshot["new_alerts_count"],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


# ---------------------------------------------------------------------------
# Dead-man's switch (FR-002)
# ---------------------------------------------------------------------------
def _load_dms_state() -> dict:
    """Load dead-man's switch state."""
    if DMS_STATE_FILE.is_file():
        try:
            return json.loads(DMS_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"consecutive_failures": 0, "alerts_sent": 0, "incident_active": False, "last_success": None}


def _save_dms_state(state: dict) -> None:
    """Save dead-man's switch state."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DMS_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def dead_mans_switch(status_ok: bool, snapshot: dict) -> None:
    """Check dead-man's switch and send Slack alerts if needed.

    Rules:
    - 3 consecutive /api/status failures -> Slack alert
    - Max 3 alerts per incident
    - Reset counter on recovery; send recovery message
    """
    dms = _load_dms_state()

    if status_ok:
        # Recovery
        if dms.get("incident_active"):
            _send_dms_alert(
                "RECOVERY: crypto-bot back online",
                f"API responding again. Last failure streak: {dms['consecutive_failures']} polls.",
                severity="routine",
            )
            dms = {"consecutive_failures": 0, "alerts_sent": 0, "incident_active": False,
                   "last_success": datetime.now(timezone.utc).isoformat()}
        else:
            dms["consecutive_failures"] = 0
            dms["last_success"] = datetime.now(timezone.utc).isoformat()
    else:
        dms["consecutive_failures"] = dms.get("consecutive_failures", 0) + 1

        if dms["consecutive_failures"] >= DMS_MAX_CONSECUTIVE_FAILURES:
            if not dms.get("incident_active"):
                dms["incident_active"] = True
                dms["alerts_sent"] = 0

            if dms.get("alerts_sent", 0) < DMS_MAX_ALERTS_PER_INCIDENT:
                last_success = dms.get("last_success", "unknown")
                _send_dms_alert(
                    "ALERT: crypto-bot API unreachable",
                    (
                        f"GET /api/status failed {dms['consecutive_failures']} consecutive times.\n"
                        f"Last successful poll: {last_success}\n"
                        f"Alert {dms['alerts_sent'] + 1}/{DMS_MAX_ALERTS_PER_INCIDENT}"
                    ),
                    severity="critical",
                )
                dms["alerts_sent"] = dms.get("alerts_sent", 0) + 1

    _save_dms_state(dms)


def _send_dms_alert(title: str, body: str, severity: str = "critical") -> None:
    """Send dead-man's switch alert via Slack."""
    try:
        # Import from sibling module
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from tools.scripts.slack_notify import notify
        msg = _ascii_safe(f"[crypto-bot] {title}\n{body}")
        notify(msg, severity=severity)
    except Exception as exc:
        print(f"DMS alert failed: {_ascii_safe(str(exc))}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main poll cycle
# ---------------------------------------------------------------------------
def run_poll() -> dict:
    """Execute a single poll cycle. Returns the state snapshot."""
    # Load previous offsets for incremental JSONL reads
    prev_state = {}
    if STATE_FILE.is_file():
        try:
            prev_state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    offsets = {
        "alerts_offset": prev_state.get("alerts_offset", 0),
        "patches_offset": prev_state.get("patches_offset", 0),
    }

    # 1. Poll API endpoints (GET only)
    api_results = poll_all_endpoints()

    # 2. Read log tails
    logs = read_logs()

    # 3. Read new alerts/patches
    audit = read_alerts_and_patches(offsets)

    # 4. Build and write state
    snapshot = build_state_snapshot(api_results, logs, audit)
    write_state(snapshot)

    # 5. Append history row
    append_history(snapshot)

    # 6. Dead-man's switch
    dead_mans_switch(api_results["status_ok"], snapshot)

    return snapshot


def print_status() -> None:
    """Print last known state summary."""
    if not STATE_FILE.is_file():
        print("No state file found. Run a poll first.")
        return
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading state: {exc}")
        return

    ts = state.get("timestamp", "unknown")
    api_ok = state.get("api_reachable", False)
    trades_open = state.get("trade_count_open", 0)
    trades_closed = state.get("trade_count_closed", 0)
    pnl = state.get("realized_pnl", 0.0)
    wr = state.get("win_rate", 0.0)
    dd = state.get("drawdown_pct", 0.0)

    print(_ascii_safe(f"Crypto-bot state as of {ts}"))
    print(f"  API reachable: {api_ok}")
    print(f"  Trades: {trades_open} open, {trades_closed} closed")
    print(f"  Realized P&L: ${pnl:.2f}")
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Drawdown: {dd:.1f}%")

    errs = state.get("log_errors", {})
    if errs:
        print("  Log errors:")
        for logname, count in errs.items():
            print(f"    {logname}: {count} errors")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto-bot SENSE collector")
    parser.add_argument("--loop", action="store_true", help="Continuous polling every 15 min")
    parser.add_argument("--status", action="store_true", help="Print last state summary")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.loop:
        print(_ascii_safe(f"Starting continuous polling (every {POLL_INTERVAL_S}s)..."))
        while True:
            try:
                snapshot = run_poll()
                api_ok = snapshot.get("api_reachable", False)
                ts = snapshot.get("timestamp", "")
                print(_ascii_safe(f"[{ts}] Poll complete. API: {'OK' if api_ok else 'FAIL'}"))
            except Exception as exc:
                print(_ascii_safe(f"Poll error: {str(exc)}"), file=sys.stderr)
            time.sleep(POLL_INTERVAL_S)
    else:
        snapshot = run_poll()
        api_ok = snapshot.get("api_reachable", False)
        print(_ascii_safe(f"Poll complete. API: {'OK' if api_ok else 'FAIL'}"))
        print_status()


if __name__ == "__main__":
    main()
