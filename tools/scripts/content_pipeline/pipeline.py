#!/usr/bin/env python3
"""Weekly Substack content pipeline. Run via Task Scheduler.

Orchestrates collect -> transform -> review_gate in sequence.
Each step must succeed before the next runs (except review_gate,
which runs best-effort even if degraded).

Usage:
    python pipeline.py
"""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def run_step(script, label):
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, script)],
        capture_output=True,
        text=True,
    )
    print(f"[{label}] exit={result.returncode}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    if not run_step("collect_sources.py", "COLLECT"):
        sys.exit(1)
    if not run_step("transform_content.py", "TRANSFORM"):
        sys.exit(1)
    run_step("review_gate.py", "REVIEW_GATE")
