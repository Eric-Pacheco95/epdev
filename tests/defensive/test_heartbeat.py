#!/usr/bin/env python3
"""Defensive tests: jarvis_heartbeat.py core functions, config loading, severity eval, ASCII output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT_SCRIPT = REPO_ROOT / "tools" / "scripts" / "jarvis_heartbeat.py"
HEARTBEAT_CONFIG = REPO_ROOT / "heartbeat_config.json"

# Add repo root to path for imports
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _pass(name: str) -> None:
    print(f"PASS: {name}")


def _fail(name: str, detail: str = "") -> None:
    print(f"FAIL: {name}")
    if detail:
        print(f"      {detail}")


def main() -> None:
    ok = True

    # 1. Heartbeat script exists
    if HEARTBEAT_SCRIPT.is_file():
        _pass("jarvis_heartbeat.py exists")
    else:
        _fail("jarvis_heartbeat.py exists")
        print("Cannot continue without heartbeat script.")
        sys.exit(1)

    # 2. Heartbeat config exists and is valid JSON
    if HEARTBEAT_CONFIG.is_file():
        _pass("heartbeat_config.json exists")
        try:
            cfg = json.loads(HEARTBEAT_CONFIG.read_text(encoding="utf-8"))
            _pass("heartbeat_config.json is valid JSON")
            if "collectors" in cfg:
                _pass("heartbeat_config.json has 'collectors' key")
            else:
                ok = False
                _fail("heartbeat_config.json has 'collectors' key")
        except json.JSONDecodeError as e:
            ok = False
            _fail("heartbeat_config.json is valid JSON", str(e))
            cfg = None
    else:
        ok = False
        _fail("heartbeat_config.json exists")
        cfg = None

    # 3. Heartbeat --help exits 0
    result = subprocess.run(
        [sys.executable, str(HEARTBEAT_SCRIPT), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        _pass("jarvis_heartbeat.py --help exits 0")
    else:
        ok = False
        _fail("jarvis_heartbeat.py --help exits 0", f"exit={result.returncode}")

    # 4. Heartbeat --json --quiet runs and produces valid JSON
    result = subprocess.run(
        [sys.executable, str(HEARTBEAT_SCRIPT), "--json", "--quiet"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        _pass("jarvis_heartbeat.py --json --quiet exits 0")
    else:
        ok = False
        _fail("jarvis_heartbeat.py --json --quiet exits 0",
              f"exit={result.returncode} stderr={result.stderr[:200]}")

    if result.returncode == 0 and result.stdout.strip():
        try:
            snap = json.loads(result.stdout)
            _pass("heartbeat JSON output is valid")

            # 5. Snapshot has required keys
            required_keys = ["ts", "metrics"]
            for key in required_keys:
                if key in snap:
                    _pass(f"snapshot has '{key}' key")
                else:
                    ok = False
                    _fail(f"snapshot has '{key}' key")

            # 6. Metrics dict is non-empty
            metrics = snap.get("metrics", {})
            if len(metrics) > 0:
                _pass(f"snapshot has {len(metrics)} metrics")
            else:
                ok = False
                _fail("snapshot has metrics", "metrics dict is empty")

            # 7. Key metrics present
            expected_metrics = ["signal_count", "failure_count", "open_task_count"]
            for m in expected_metrics:
                if m in metrics:
                    _pass(f"metric '{m}' present")
                else:
                    ok = False
                    _fail(f"metric '{m}' present")

        except json.JSONDecodeError as e:
            ok = False
            _fail("heartbeat JSON output is valid", str(e))
    else:
        # Skip JSON validation tests if heartbeat didn't produce output
        if result.returncode == 0:
            ok = False
            _fail("heartbeat JSON output is valid", "empty stdout")

    # 8. Heartbeat human-readable output is ASCII-only
    result_text = subprocess.run(
        [sys.executable, str(HEARTBEAT_SCRIPT), "--quiet"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result_text.returncode == 0:
        non_ascii = [c for c in result_text.stdout if ord(c) > 127]
        if not non_ascii:
            _pass("heartbeat text output is ASCII-only")
        else:
            ok = False
            _fail("heartbeat text output is ASCII-only", f"found {len(non_ascii)} non-ASCII chars")
    else:
        ok = False
        _fail("heartbeat text output runs", f"exit={result_text.returncode}")

    # 9. Severity evaluation function works correctly
    try:
        from tools.scripts.jarvis_heartbeat import _evaluate_severity

        # Test: value above warn threshold
        sev = _evaluate_severity(15, {"warn_above": 10, "crit_above": 20})
        if sev == "WARN":
            _pass("_evaluate_severity: warn_above correct")
        else:
            ok = False
            _fail("_evaluate_severity: warn_above correct", f"got {sev}")

        # Test: value above crit threshold
        sev = _evaluate_severity(25, {"warn_above": 10, "crit_above": 20})
        if sev == "CRIT":
            _pass("_evaluate_severity: crit_above correct")
        else:
            ok = False
            _fail("_evaluate_severity: crit_above correct", f"got {sev}")

        # Test: value OK (below all thresholds)
        sev = _evaluate_severity(5, {"warn_above": 10, "crit_above": 20})
        if sev == "OK":
            _pass("_evaluate_severity: OK correct")
        else:
            ok = False
            _fail("_evaluate_severity: OK correct", f"got {sev}")

        # Test: empty thresholds returns OK
        sev = _evaluate_severity(100, {})
        if sev == "OK":
            _pass("_evaluate_severity: empty thresholds = OK")
        else:
            ok = False
            _fail("_evaluate_severity: empty thresholds = OK", f"got {sev}")

        # Test: below threshold (crit_below)
        sev = _evaluate_severity(0.1, {"crit_below": 0.5, "warn_below": 0.8})
        if sev == "CRIT":
            _pass("_evaluate_severity: crit_below correct")
        else:
            ok = False
            _fail("_evaluate_severity: crit_below correct", f"got {sev}")

    except ImportError as e:
        ok = False
        _fail("import _evaluate_severity", str(e))

    # 10. Diff engine produces expected output
    try:
        from tools.scripts.jarvis_heartbeat import diff_snapshots

        current = {
            "metrics": {
                "signal_count": {"value": 20},
                "failure_count": {"value": 5},
            }
        }
        previous = {
            "metrics": {
                "signal_count": {"value": 15},
                "failure_count": {"value": 5},
            }
        }
        test_cfg = {
            "collectors": [
                {"name": "signal_count", "thresholds": {"warn_above": 25}},
                {"name": "failure_count", "thresholds": {"warn_above": 10}},
            ]
        }
        changes = diff_snapshots(current, previous, test_cfg)
        signal_change = next((c for c in changes if c["metric"] == "signal_count"), None)
        if signal_change and signal_change["delta"] == 5:
            _pass("diff_snapshots: detects delta correctly")
        else:
            ok = False
            _fail("diff_snapshots: detects delta correctly", str(changes))

        # No change should produce delta 0
        no_change = next((c for c in changes if c["metric"] == "failure_count"), None)
        if no_change and no_change["delta"] == 0:
            _pass("diff_snapshots: zero delta for unchanged metric")
        else:
            ok = False
            _fail("diff_snapshots: zero delta for unchanged metric", str(changes))

    except ImportError as e:
        ok = False
        _fail("import diff_snapshots", str(e))

    # 11. Latest snapshot file exists (from previous heartbeat runs)
    latest = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_latest.json"
    if latest.is_file():
        _pass("heartbeat_latest.json exists")
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            if "ts" in data and "metrics" in data:
                _pass("heartbeat_latest.json has valid structure")
            else:
                ok = False
                _fail("heartbeat_latest.json has valid structure")
        except json.JSONDecodeError:
            ok = False
            _fail("heartbeat_latest.json is valid JSON")
    else:
        # Not a failure — may be first run
        _pass("heartbeat_latest.json check (not yet created — OK for first run)")

    if not ok:
        sys.exit(1)
    print("\nAll heartbeat tests passed.")


if __name__ == "__main__":
    main()
