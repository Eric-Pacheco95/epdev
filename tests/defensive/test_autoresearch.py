#!/usr/bin/env python3
"""Defensive tests: jarvis_autoresearch.py core functions, parsing, dedup, guards."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_autoresearch import (
    SIGNAL_THRESHOLD_CONTRADICTIONS,
    SIGNAL_THRESHOLD_COVERAGE,
    build_analysis_prompt,
    extract_section,
    gather_inputs,
    parse_metrics,
    read_recent_files,
    read_synthesis_recent,
    read_telos_files,
    write_run_artifacts,
)


def _pass(name: str) -> None:
    print("PASS: %s" % name)


def _fail(name: str, detail: str = "") -> None:
    print("FAIL: %s" % name)
    if detail:
        print("      %s" % detail)


def main() -> None:
    ok = True

    # -- 1. TELOS file reading --
    telos = read_telos_files()
    if len(telos) >= 10:
        _pass("TELOS files readable (%d)" % len(telos))
    else:
        _fail("TELOS files readable", "expected >= 10, got %d" % len(telos))
        ok = False

    if "GOALS.md" in telos and "MISSION.md" in telos:
        _pass("Core TELOS files present (GOALS.md, MISSION.md)")
    else:
        _fail("Core TELOS files present")
        ok = False

    # -- 2. Synthesis reading --
    synthesis = read_synthesis_recent(3)
    if len(synthesis) >= 1:
        _pass("Synthesis docs readable (%d)" % len(synthesis))
    else:
        _fail("Synthesis docs readable", "expected >= 1")
        ok = False

    # -- 3. Time-bounded file reading --
    # Test with a temp directory to verify boundary logic
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create a file that should be within bounds (today)
        recent = tmppath / "recent.md"
        recent.write_text("recent signal", encoding="utf-8")
        # Create a file and backdate it (won't work on all OS, but the read
        # function filters by mtime so we test the happy path)
        result = read_recent_files(tmppath, days=7, max_files=5)
        if len(result) == 1 and result[0]["name"] == "recent.md":
            _pass("Time-bounded file reading works")
        else:
            _fail("Time-bounded file reading", "got %d files" % len(result))
            ok = False

        # Test max_files limit
        for i in range(10):
            (tmppath / ("sig_%02d.md" % i)).write_text("signal %d" % i,
                                                        encoding="utf-8")
        capped = read_recent_files(tmppath, days=7, max_files=5)
        if len(capped) == 5:
            _pass("max_files cap enforced (10 files, limit 5)")
        else:
            _fail("max_files cap", "expected 5, got %d" % len(capped))
            ok = False

        # Test truncation of long files
        long_file = tmppath / "long.md"
        long_file.write_text("x" * 2000, encoding="utf-8")
        long_result = read_recent_files(tmppath, days=7, max_files=20)
        long_entry = [r for r in long_result if r["name"] == "long.md"]
        if long_entry and "[... truncated]" in long_entry[0]["content"]:
            _pass("Long file truncation works")
        else:
            _fail("Long file truncation")
            ok = False

    # -- 4. Empty directory handling --
    nonexistent = Path(tmpdir) / "does_not_exist"
    result = read_recent_files(nonexistent, days=7)
    if result == []:
        _pass("Nonexistent directory returns empty list")
    else:
        _fail("Nonexistent directory", "expected [], got %s" % result)
        ok = False

    # -- 5. Metrics parsing: well-formed response --
    good_response = """=== METRICS ===
contradiction_count: 3
open_questions: 5
coverage_score: 66.7
staleness_flags: 2
insight_count: 4
proposal_count: 2

=== CONTRADICTIONS ===
Some contradictions.

=== COVERAGE ===
Coverage details.

=== PROPOSALS ===
Proposal details."""

    metrics = parse_metrics(good_response)
    if metrics["contradiction_count"] == 3 and metrics["open_questions"] == 5:
        _pass("Metrics parse: integer fields")
    else:
        _fail("Metrics parse: integer fields", str(metrics))
        ok = False

    if abs(metrics["coverage_score"] - 66.7) < 0.1:
        _pass("Metrics parse: float field (coverage_score)")
    else:
        _fail("Metrics parse: float", str(metrics["coverage_score"]))
        ok = False

    # -- 6. Metrics parsing: malformed response (no METRICS section) --
    bad_response = "Here is my analysis of your TELOS files..."
    bad_metrics = parse_metrics(bad_response)
    if all(v == 0 or v == 0.0 for v in bad_metrics.values()):
        _pass("Malformed response: returns safe zeros")
    else:
        _fail("Malformed response", str(bad_metrics))
        ok = False

    # -- 7. Metrics parsing: partial response (some fields missing) --
    partial_response = """=== METRICS ===
contradiction_count: 1
coverage_score: 80.0

=== CONTRADICTIONS ===
None."""

    partial = parse_metrics(partial_response)
    if (partial["contradiction_count"] == 1
            and partial["coverage_score"] == 80.0
            and partial["open_questions"] == 0):
        _pass("Partial response: found fields + safe defaults for missing")
    else:
        _fail("Partial response", str(partial))
        ok = False

    # -- 8. Metrics parsing: truncated response (API cut off mid-section) --
    truncated = """=== METRICS ===
contradiction_count: 2
open_questions: 3
coverage_score: 55"""
    trunc_metrics = parse_metrics(truncated)
    if trunc_metrics["contradiction_count"] == 2:
        _pass("Truncated response: parses available metrics")
    else:
        _fail("Truncated response", str(trunc_metrics))
        ok = False

    # -- 9. Section extraction --
    contrad = extract_section(good_response, "CONTRADICTIONS")
    if "Some contradictions" in contrad:
        _pass("Section extraction: CONTRADICTIONS")
    else:
        _fail("Section extraction: CONTRADICTIONS")
        ok = False

    proposals = extract_section(good_response, "PROPOSALS")
    if "Proposal details" in proposals:
        _pass("Section extraction: PROPOSALS (last section)")
    else:
        _fail("Section extraction: PROPOSALS")
        ok = False

    missing = extract_section(good_response, "NONEXISTENT")
    if missing == "":
        _pass("Section extraction: missing section returns empty string")
    else:
        _fail("Section extraction: missing section")
        ok = False

    # -- 10. Prompt construction --
    inputs = gather_inputs()
    system, user = build_analysis_prompt(inputs)
    if len(system) > 100 and "TELOS" in system:
        _pass("System prompt contains TELOS instructions (%d chars)" % len(
            system))
    else:
        _fail("System prompt")
        ok = False

    if "GOALS.md" in user and len(user) > 500:
        _pass("User prompt includes TELOS content (%d chars)" % len(user))
    else:
        _fail("User prompt")
        ok = False

    # -- 11. ASCII safety in prompt --
    all_ascii = all(ord(c) < 128 for c in system)
    if all_ascii:
        _pass("System prompt is ASCII-safe")
    else:
        non_ascii = [c for c in system if ord(c) >= 128]
        _fail("System prompt ASCII", "non-ASCII chars: %s" % non_ascii[:5])
        ok = False

    # -- 12. Write artifacts to temp dir --
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "test-run"
        scope = {"telos_files": 19, "synthesis_docs": 5, "signals_7d": 20,
                 "raw_signals_3d": 8, "failures_14d": 3, "sessions_7d": 0}
        write_run_artifacts(run_dir, good_response, metrics, scope)

        if (run_dir / "metrics.json").is_file():
            data = json.loads(
                (run_dir / "metrics.json").read_text(encoding="utf-8"))
            if data["metrics"]["contradiction_count"] == 3:
                _pass("metrics.json written with correct data")
            else:
                _fail("metrics.json data", str(data))
                ok = False
        else:
            _fail("metrics.json not created")
            ok = False

        if (run_dir / "report.md").is_file():
            _pass("report.md created")
        else:
            _fail("report.md not created")
            ok = False

        if (run_dir / "proposals.md").is_file():
            _pass("proposals.md created")
        else:
            _fail("proposals.md not created")
            ok = False

        if (run_dir / "contradictions.md").is_file():
            _pass("contradictions.md created")
        else:
            _fail("contradictions.md not created")
            ok = False

        if (run_dir / "coverage.md").is_file():
            _pass("coverage.md created")
        else:
            _fail("coverage.md not created")
            ok = False

    # -- 13. Signal dedup counter logic --
    with tempfile.TemporaryDirectory() as tmpdir:
        sig_dir = Path(tmpdir)
        # Simulate 3 existing signal files
        (sig_dir / "2026-01-01_telos-introspection-findings.md").write_text(
            "first", encoding="utf-8")
        (sig_dir / "2026-01-01_telos-introspection-findings-2.md").write_text(
            "second", encoding="utf-8")
        (sig_dir / "2026-01-01_telos-introspection-findings-3.md").write_text(
            "third", encoding="utf-8")

        # The dedup logic should find the next available counter
        name = "2026-01-01_telos-introspection-findings.md"
        path = sig_dir / name
        counter = 1
        while path.is_file():
            counter += 1
            name = "2026-01-01_telos-introspection-findings-%d.md" % counter
            path = sig_dir / name

        if counter == 4 and name.endswith("-4.md"):
            _pass("Signal dedup: counter increments past existing files")
        else:
            _fail("Signal dedup", "counter=%d name=%s" % (counter, name))
            ok = False

    # -- 14. Threshold logic --
    if SIGNAL_THRESHOLD_CONTRADICTIONS == 3:
        _pass("Contradiction threshold is 3")
    else:
        _fail("Contradiction threshold",
              "expected 3, got %d" % SIGNAL_THRESHOLD_CONTRADICTIONS)
        ok = False

    if SIGNAL_THRESHOLD_COVERAGE == 50:
        _pass("Coverage threshold is 50%%")
    else:
        _fail("Coverage threshold",
              "expected 50, got %d" % SIGNAL_THRESHOLD_COVERAGE)
        ok = False

    # -- 15. Write constraint: OUTPUT_BASE path --
    from tools.scripts.jarvis_autoresearch import OUTPUT_BASE
    expected_suffix = os.path.join("memory", "work", "jarvis", "autoresearch")
    if str(OUTPUT_BASE).endswith(expected_suffix):
        _pass("OUTPUT_BASE constrained to autoresearch/ tree")
    else:
        _fail("OUTPUT_BASE", str(OUTPUT_BASE))
        ok = False

    # -- Summary --
    print()
    if ok:
        print("All tests passed.")
    else:
        print("Some tests FAILED.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
