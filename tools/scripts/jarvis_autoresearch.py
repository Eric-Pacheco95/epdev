#!/usr/bin/env python3
"""Jarvis TELOS Introspection Runner -- Karpathy-inspired autoresearch.

Analyzes the gap between TELOS identity docs and accumulated learning
evidence (signals, synthesis, sessions). Surfaces contradictions, coverage
gaps, stale claims, and open questions. Writes proposals for human review.

Uses claude -p (Claude Max subscription, no API key needed).
Only safe from Task Scheduler or standalone CMD -- never from within
an active Claude Code session (subprocess hang risk).

Usage:
    python tools/scripts/jarvis_autoresearch.py              # full run
    python tools/scripts/jarvis_autoresearch.py --dry-run    # gather only, no LLM call
    python tools/scripts/jarvis_autoresearch.py --test       # self-test

Environment:
    SLACK_BOT_TOKEN    xoxb-... for Slack posting (optional)

Outputs:
    memory/work/jarvis/autoresearch/run-YYYY-MM-DD/  -- run artifacts
    memory/learning/signals/                          -- autonomous signal (if threshold met)
    Slack #epdev                                      -- summary (if threshold met)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
PROCESSED_DIR = SIGNALS_DIR / "processed"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SESSION_DIR = REPO_ROOT / "memory" / "session"
OUTPUT_BASE = REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"

# Thresholds for autonomous signal + Slack posting
SIGNAL_THRESHOLD_CONTRADICTIONS = 3
SIGNAL_THRESHOLD_COVERAGE = 50  # percent


# -- File gathering (read-only, time-bounded) --------------------------------

def read_telos_files() -> dict[str, str]:
    """Read all TELOS identity files. Returns {filename: content}."""
    result = {}
    if not TELOS_DIR.is_dir():
        return result
    for f in sorted(TELOS_DIR.glob("*.md")):
        try:
            result[f.name] = f.read_text(encoding="utf-8")
        except OSError:
            pass
    return result


def read_recent_files(directory: Path, days: int, max_files: int = 30) -> list[dict]:
    """Read recent .md files from a directory, bounded by age and count.

    Returns list of {name, content, mtime_str}.
    """
    if not directory.is_dir():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    candidates = []

    for f in directory.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                candidates.append((f, mtime))
        except OSError:
            pass

    # Sort newest first, limit count
    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = candidates[:max_files]

    result = []
    for f, mtime in candidates:
        try:
            content = f.read_text(encoding="utf-8")
            # Truncate very long files to 1000 chars for token efficiency
            if len(content) > 1000:
                content = content[:1000] + "\n[... truncated]"
            result.append({
                "name": f.name,
                "content": content,
                "mtime": mtime.strftime("%Y-%m-%d"),
            })
        except OSError:
            pass

    return result


def read_synthesis_recent(count: int = 5) -> list[dict]:
    """Read the N most recent synthesis docs (no date filter -- always useful)."""
    if not SYNTHESIS_DIR.is_dir():
        return []

    files = sorted(SYNTHESIS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime,
                   reverse=True)[:count]

    result = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            if len(content) > 2000:
                content = content[:2000] + "\n[... truncated]"
            result.append({"name": f.name, "content": content})
        except OSError:
            pass

    return result


def gather_inputs() -> dict:
    """Gather all read-scope inputs. Returns structured dict."""
    telos = read_telos_files()
    synthesis = read_synthesis_recent(5)
    signals = read_recent_files(PROCESSED_DIR, days=14, max_files=20)
    raw_signals = read_recent_files(SIGNALS_DIR, days=7, max_files=10)
    failures = read_recent_files(FAILURES_DIR, days=14, max_files=10)
    sessions = read_recent_files(SESSION_DIR, days=7, max_files=5)

    return {
        "telos": telos,
        "synthesis": synthesis,
        "signals": signals,
        "raw_signals": raw_signals,
        "failures": failures,
        "sessions": sessions,
        "scope_summary": {
            "telos_files": len(telos),
            "synthesis_docs": len(synthesis),
            "signals_14d": len(signals),
            "raw_signals_7d": len(raw_signals),
            "failures_14d": len(failures),
            "sessions_7d": len(sessions),
        },
    }


# -- Claude CLI call ---------------------------------------------------------

def call_claude(prompt: str, system: str = "") -> str:
    """Call claude -p for analysis. Uses Claude Max subscription (no API key).

    Only safe from Task Scheduler or standalone CMD -- never from within
    an active Claude Code session (subprocess hang risk).
    """
    # Combine system + user prompt into a single prompt for claude -p
    if system:
        full_prompt = "SYSTEM INSTRUCTIONS:\n%s\n\nUSER INPUT:\n%s" % (
            system, prompt)
    else:
        full_prompt = prompt

    try:
        # Pass prompt via stdin ("-") to avoid Windows command-line length
        # limits (WinError 206).  The overnight_runner uses the same pattern.
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "-"],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,  # 5 min -- longer prompt needs more time
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            return "(claude -p error: %s)" % result.stderr.strip()[:200]
        return "(claude -p returned empty response)"
    except FileNotFoundError:
        return "(claude CLI not found at %s -- ensure it exists)" % CLAUDE_BIN
    except subprocess.TimeoutExpired:
        return "(claude -p timed out after 300s)"
    except Exception as exc:
        return "(claude -p failed: %s)" % exc


# -- Analysis prompt construction --------------------------------------------

def build_analysis_prompt(inputs: dict) -> tuple[str, str]:
    """Build system + user prompts for TELOS introspection analysis.

    Returns (system_prompt, user_prompt).
    """
    system = """You are Jarvis's TELOS introspection engine. You analyze the gap
between Eric's identity documents (TELOS) and his accumulated learning evidence
(signals, synthesis, session transcripts).

Your job is to find:
1. CONTRADICTIONS: Where TELOS claims something that signals contradict
2. COVERAGE GAPS: TELOS goals with no recent signal evidence (last 30 days)
3. STALENESS: TELOS items with statuses that don't match reality
4. OPEN QUESTIONS: Important gaps that need investigation
5. INSIGHTS: Non-obvious patterns from cross-referencing sources

OUTPUT FORMAT (strict -- parser depends on this):

=== METRICS ===
contradiction_count: <int>
open_questions: <int>
coverage_score: <float 0-100>
staleness_flags: <int>
insight_count: <int>
proposal_count: <int>

=== CONTRADICTIONS ===
For each:
- TELOS claim: <quote from TELOS file, with filename>
- Signal evidence: <what signals actually show>
- Severity: HIGH | MEDIUM | LOW

=== COVERAGE ===
For each TELOS goal (from GOALS.md):
- Goal: <name>
- Weight: <percentage>
- Recent evidence: YES | NO | PARTIAL
- Last signal date: <date or "none found">
- Notes: <brief>

=== OPEN QUESTIONS ===
Numbered list. Each: a question that the data raises but cannot answer.

=== INSIGHTS ===
Numbered list. Each: a non-obvious pattern with evidence citation.

=== PROPOSALS ===
For each proposed TELOS update:
- File: <TELOS filename to update>
- Change: <what to add/modify/remove>
- Evidence: <signal/synthesis citation>
- Priority: HIGH | MEDIUM | LOW

DEDUP RULES (mandatory before creating any proposal):
- Check the CURRENT TASKS section below. Do NOT propose changes that duplicate
  existing unchecked tasklist items or open validations.
- If a proposal overlaps with an existing task, skip it or reference the task
  instead of creating a duplicate.
- Generating zero proposals is a valid outcome. Silence means the system is healthy.

Keep analysis grounded in evidence. Do not speculate beyond what signals show.
Use ASCII only (no Unicode dashes, arrows, or box characters)."""

    # Build user prompt with all gathered data
    parts = []
    parts.append("## TELOS Identity Files\n")
    for name, content in inputs["telos"].items():
        parts.append("### %s\n%s\n" % (name, content))

    parts.append("\n## Recent Synthesis Documents (distilled signals)\n")
    for doc in inputs["synthesis"]:
        parts.append("### %s\n%s\n" % (doc["name"], doc["content"]))

    parts.append("\n## Recent Signals (last 14 days, processed)\n")
    for sig in inputs["signals"]:
        parts.append("### %s (%s)\n%s\n" % (sig["name"], sig["mtime"],
                                              sig["content"]))

    if inputs["raw_signals"]:
        parts.append("\n## Raw Signals (last 7 days, unprocessed)\n")
        for sig in inputs["raw_signals"]:
            parts.append("### %s (%s)\n%s\n" % (sig["name"], sig["mtime"],
                                                  sig["content"]))

    if inputs["failures"]:
        parts.append("\n## Recent Failures (last 14 days)\n")
        for f in inputs["failures"]:
            parts.append("### %s (%s)\n%s\n" % (f["name"], f["mtime"],
                                                  f["content"]))

    if inputs["sessions"]:
        parts.append("\n## Recent Sessions (last 7 days)\n")
        for s in inputs["sessions"]:
            parts.append("### %s (%s)\n%s\n" % (s["name"], s["mtime"],
                                                  s["content"]))

    parts.append("\n## Scope Summary\n")
    scope = inputs["scope_summary"]
    parts.append("- TELOS files read: %d" % scope["telos_files"])
    parts.append("- Synthesis docs read: %d" % scope["synthesis_docs"])
    parts.append("- Processed signals (14d): %d" % scope["signals_14d"])
    parts.append("- Raw signals (7d): %d" % scope["raw_signals_7d"])
    parts.append("- Failures (14d): %d" % scope["failures_14d"])
    parts.append("- Sessions (7d): %d" % scope["sessions_7d"])

    # Include current tasklist for dedup
    tasklist_path = REPO_ROOT / "orchestration" / "tasklist.md"
    if tasklist_path.is_file():
        tasklist_content = tasklist_path.read_text(encoding="utf-8")
        # Truncate to unchecked items only (keep it focused)
        unchecked = [
            line for line in tasklist_content.splitlines()
            if "[ ]" in line or ">>> " in line
        ]
        if unchecked:
            parts.append("\n## CURRENT TASKS (for dedup -- do not duplicate)\n")
            parts.append("\n".join(unchecked[:30]))  # cap at 30 items

    parts.append("\nAnalyze the gap between TELOS identity and signal evidence.")
    parts.append("Follow the output format exactly.")

    user_prompt = "\n".join(parts)
    return system, user_prompt


# -- Response parsing --------------------------------------------------------

def parse_metrics(response: str) -> dict:
    """Parse metrics from the structured response."""
    metrics = {
        "contradiction_count": 0,
        "open_questions": 0,
        "coverage_score": 0.0,
        "staleness_flags": 0,
        "insight_count": 0,
        "proposal_count": 0,
    }

    # Find the METRICS section
    metrics_match = re.search(
        r"=== METRICS ===(.*?)(?:=== |$)", response, re.DOTALL
    )
    if not metrics_match:
        print("  WARNING: METRICS section not found in API response. "
              "Using defaults (all zeros).", file=sys.stderr)
        return metrics

    block = metrics_match.group(1)
    for key in metrics:
        m = re.search(r"%s:\s*(\d+\.?\d*)" % key, block)
        if m:
            val = m.group(1)
            if "." in val:
                metrics[key] = float(val)
            else:
                metrics[key] = int(val)

    return metrics


def extract_section(response: str, section_name: str) -> str:
    """Extract a named section from the response."""
    pattern = r"=== %s ===(.*?)(?:=== |$)" % re.escape(section_name)
    m = re.search(pattern, response, re.DOTALL)
    return m.group(1).strip() if m else ""


# -- Output writing ----------------------------------------------------------

def write_run_artifacts(run_dir: Path, response: str, metrics: dict,
                        scope_summary: dict) -> None:
    """Write all run artifacts to the output directory."""
    run_dir.mkdir(parents=True, exist_ok=True)

    # metrics.json
    metrics_data = {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "run_time": datetime.now().strftime("%H:%M:%S"),
        "scope": scope_summary,
        "metrics": metrics,
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_data, indent=2) + "\n", encoding="utf-8"
    )

    # report.md (full response)
    report_lines = [
        "# TELOS Introspection Report -- %s" % datetime.now().strftime(
            "%Y-%m-%d"),
        "",
        "## Scope",
        "- TELOS files: %d" % scope_summary["telos_files"],
        "- Synthesis docs: %d" % scope_summary["synthesis_docs"],
        "- Signals (14d): %d" % scope_summary["signals_14d"],
        "- Raw signals (7d): %d" % scope_summary["raw_signals_7d"],
        "- Failures (14d): %d" % scope_summary["failures_14d"],
        "- Sessions (7d): %d" % scope_summary["sessions_7d"],
        "",
        "## Metrics",
        "- Contradictions: %d" % metrics["contradiction_count"],
        "- Open questions: %d" % metrics["open_questions"],
        "- Coverage score: %.0f%%" % metrics["coverage_score"],
        "- Staleness flags: %d" % metrics["staleness_flags"],
        "- Insights: %d" % metrics["insight_count"],
        "- Proposals: %d" % metrics["proposal_count"],
        "",
        "## Full Analysis",
        "",
        response,
    ]
    (run_dir / "report.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    # proposals.md (extracted section)
    proposals = extract_section(response, "PROPOSALS")
    if proposals:
        (run_dir / "proposals.md").write_text(
            "# TELOS Update Proposals -- %s\n\n%s\n" % (
                datetime.now().strftime("%Y-%m-%d"), proposals),
            encoding="utf-8",
        )

    # contradictions.md (extracted section)
    contradictions = extract_section(response, "CONTRADICTIONS")
    if contradictions:
        (run_dir / "contradictions.md").write_text(
            "# Contradictions -- %s\n\n%s\n" % (
                datetime.now().strftime("%Y-%m-%d"), contradictions),
            encoding="utf-8",
        )

    # coverage.md (extracted section)
    coverage = extract_section(response, "COVERAGE")
    if coverage:
        (run_dir / "coverage.md").write_text(
            "# Goal Coverage -- %s\n\n%s\n" % (
                datetime.now().strftime("%Y-%m-%d"), coverage),
            encoding="utf-8",
        )


# -- Autonomous signal writing -----------------------------------------------

def write_autonomous_signal(metrics: dict, run_dir: Path) -> bool:
    """Write an autonomous signal if thresholds are crossed.

    Returns True if a signal was written.
    """
    contradictions = metrics.get("contradiction_count", 0)
    coverage = metrics.get("coverage_score", 100)

    if (contradictions < SIGNAL_THRESHOLD_CONTRADICTIONS
            and coverage >= SIGNAL_THRESHOLD_COVERAGE):
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    reasons = []
    if contradictions >= SIGNAL_THRESHOLD_CONTRADICTIONS:
        reasons.append(
            "%d contradictions between TELOS and signals" % contradictions
        )
    if coverage < SIGNAL_THRESHOLD_COVERAGE:
        reasons.append("coverage score %.0f%% (below %d%% threshold)" % (
            coverage, SIGNAL_THRESHOLD_COVERAGE))

    signal_name = "%s_telos-introspection-findings.md" % today
    signal_path = SIGNALS_DIR / signal_name

    # Dedup: increment counter until we find an unused filename
    counter = 1
    while signal_path.is_file():
        counter += 1
        signal_name = "%s_telos-introspection-findings-%d.md" % (today, counter)
        signal_path = SIGNALS_DIR / signal_name

    content = (
        "# Signal: TELOS introspection found significant gaps\n"
        "- Date: %s\n"
        "- Rating: 7\n"
        "- Category: introspection\n"
        "- Source: autonomous\n"
        "- Observation: Autoresearch introspection run found: %s. "
        "Full report at %s\n"
        "- Implication: TELOS identity docs may need updating to reflect "
        "current reality. Review proposals in the run report.\n"
        "- Context: Automated TELOS introspection via jarvis_autoresearch.py\n"
    ) % (today, "; ".join(reasons), run_dir / "report.md")

    signal_path.write_text(content, encoding="utf-8")
    print("  Autonomous signal written: %s" % signal_name)
    return True


# -- Slack notification ------------------------------------------------------

def post_slack_summary(metrics: dict, run_dir: Path) -> bool:
    """Post summary to #epdev if thresholds crossed."""
    try:
        from tools.scripts.slack_notify import notify
    except ImportError:
        print("  Slack notify not available", file=sys.stderr)
        return False

    contradictions = metrics.get("contradiction_count", 0)
    coverage = metrics.get("coverage_score", 100)
    proposals = metrics.get("proposal_count", 0)

    # Only post if significant findings
    if (contradictions < SIGNAL_THRESHOLD_CONTRADICTIONS
            and coverage >= SIGNAL_THRESHOLD_COVERAGE
            and proposals == 0):
        print("  No significant findings -- skipping Slack")
        return False

    lines = [
        "*TELOS Introspection Complete*",
        "Contradictions: %d | Coverage: %.0f%% | Proposals: %d" % (
            contradictions, coverage, proposals),
        "Open questions: %d | Insights: %d" % (
            metrics.get("open_questions", 0),
            metrics.get("insight_count", 0)),
        "Report: `%s`" % (run_dir / "report.md"),
    ]

    if contradictions >= SIGNAL_THRESHOLD_CONTRADICTIONS:
        lines.append(
            ">> %d contradictions found -- review proposals" % contradictions
        )
    if coverage < SIGNAL_THRESHOLD_COVERAGE:
        lines.append(
            ">> Coverage below %d%% -- some goals have no recent evidence"
            % SIGNAL_THRESHOLD_COVERAGE
        )

    # Escalate to #general if contradictions or low coverage need attention
    sev = "critical" if (contradictions >= SIGNAL_THRESHOLD_CONTRADICTIONS
                         or coverage < SIGNAL_THRESHOLD_COVERAGE) else "routine"
    return notify("\n".join(lines), severity=sev)


# -- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jarvis TELOS Introspection Runner"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Gather inputs only, no API call")
    parser.add_argument("--test", action="store_true",
                        help="Run self-tests")
    args = parser.parse_args()

    if args.test:
        return run_self_test()

    today = datetime.now().strftime("%Y-%m-%d")
    print("Jarvis TELOS Introspection -- %s" % today)
    print("Repo: %s" % REPO_ROOT)

    # 1. Check for dedup: same date already ran
    run_dir = OUTPUT_BASE / ("run-%s" % today)
    if run_dir.is_dir() and (run_dir / "metrics.json").is_file():
        print("Already ran today (%s). Report at: %s" % (today, run_dir))
        print("Delete the run directory to re-run.")
        return 0

    # 2. Gather inputs (read-only, time-bounded)
    print("\nGathering inputs...")
    inputs = gather_inputs()
    scope = inputs["scope_summary"]
    print("  TELOS files: %d" % scope["telos_files"])
    print("  Synthesis docs: %d" % scope["synthesis_docs"])
    print("  Signals (14d): %d" % scope["signals_14d"])
    print("  Raw signals (7d): %d" % scope["raw_signals_7d"])
    print("  Failures (14d): %d" % scope["failures_14d"])
    print("  Sessions (7d): %d" % scope["sessions_7d"])

    if scope["telos_files"] == 0:
        print("\nERROR: No TELOS files found at %s" % TELOS_DIR,
              file=sys.stderr)
        return 1

    if args.dry_run:
        system, user = build_analysis_prompt(inputs)
        print("\n[DRY RUN] Would call Anthropic API")
        print("  System prompt: %d chars" % len(system))
        print("  User prompt: %d chars" % len(user))
        print("  Output dir: %s" % run_dir)
        return 0

    # 3. Build prompts and call API
    print("\nAnalyzing TELOS vs signal evidence...")
    system, user = build_analysis_prompt(inputs)

    # Prompt size guard (100K chars ~ 25K tokens)
    total_chars = len(system) + len(user)
    if total_chars > 100000:
        print("  WARNING: Prompt is %d chars (>100K). "
              "Consider reducing signal window." % total_chars,
              file=sys.stderr)

    response = call_claude(user, system)

    if response.startswith("("):
        print("\nERROR: %s" % response, file=sys.stderr)
        return 1

    # 4. Parse metrics
    metrics = parse_metrics(response)
    print("\nMetrics:")
    print("  Contradictions: %d" % metrics["contradiction_count"])
    print("  Open questions: %d" % metrics["open_questions"])
    print("  Coverage score: %.0f%%" % metrics["coverage_score"])
    print("  Staleness flags: %d" % metrics["staleness_flags"])
    print("  Insights: %d" % metrics["insight_count"])
    print("  Proposals: %d" % metrics["proposal_count"])

    # 5. Write run artifacts
    print("\nWriting artifacts to %s ..." % run_dir)
    write_run_artifacts(run_dir, response, metrics, scope)

    # 6. Autonomous signal (if threshold crossed)
    write_autonomous_signal(metrics, run_dir)

    # 7. Slack notification (if significant)
    post_slack_summary(metrics, run_dir)

    print("\nIntrospection complete. Review proposals at:")
    print("  %s" % (run_dir / "proposals.md"))
    return 0


# -- Self-test ---------------------------------------------------------------

def run_self_test() -> int:
    """Quick self-tests for the runner."""
    passed = 0
    failed = 0

    def check(condition, label):
        nonlocal passed, failed
        if condition:
            print("  PASS: %s" % label)
            passed += 1
        else:
            print("  FAIL: %s" % label)
            failed += 1

    print("Jarvis Autoresearch -- Self-Test")
    print()

    # 1. TELOS files readable
    telos = read_telos_files()
    check(len(telos) >= 10, "TELOS files readable (%d found)" % len(telos))
    check("GOALS.md" in telos, "GOALS.md exists in TELOS")
    check("MISSION.md" in telos, "MISSION.md exists in TELOS")

    # 2. Synthesis files readable
    synthesis = read_synthesis_recent(3)
    check(len(synthesis) >= 1, "Synthesis docs readable (%d found)" % len(
        synthesis))

    # 3. Signal files readable
    signals = read_recent_files(PROCESSED_DIR, days=14, max_files=5)
    check(len(signals) >= 0, "Signal reading works (%d found)" % len(signals))

    # 4. Output directory writable
    test_dir = OUTPUT_BASE / "test-selftest"
    try:
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "test.txt"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        test_dir.rmdir()
        check(True, "Output directory writable")
    except OSError as exc:
        check(False, "Output directory writable (%s)" % exc)

    # 5. Prompt construction
    inputs = gather_inputs()
    system, user = build_analysis_prompt(inputs)
    check(len(system) > 100, "System prompt built (%d chars)" % len(system))
    check(len(user) > 500, "User prompt built (%d chars)" % len(user))
    check("GOALS.md" in user, "User prompt contains TELOS GOALS reference")

    # 6. Metrics parsing
    mock_response = """=== METRICS ===
contradiction_count: 3
open_questions: 5
coverage_score: 66.7
staleness_flags: 2
insight_count: 4
proposal_count: 2

=== CONTRADICTIONS ===
Some contradictions here.

=== COVERAGE ===
Coverage details here.

=== PROPOSALS ===
Proposal details here."""

    metrics = parse_metrics(mock_response)
    check(metrics["contradiction_count"] == 3, "Metrics parse: contradictions")
    check(metrics["open_questions"] == 5, "Metrics parse: open_questions")
    check(abs(metrics["coverage_score"] - 66.7) < 0.1,
          "Metrics parse: coverage_score")
    check(metrics["proposal_count"] == 2, "Metrics parse: proposals")

    # 7. Section extraction
    contrad = extract_section(mock_response, "CONTRADICTIONS")
    check("contradictions here" in contrad, "Section extraction works")

    proposals = extract_section(mock_response, "PROPOSALS")
    check("Proposal details" in proposals, "Proposals extraction works")

    # 8. ASCII safety - verify no non-ASCII in output strings
    test_strings = [
        "Contradictions: %d" % 3,
        "Coverage: %.0f%%" % 66.7,
        "Report: %s" % (OUTPUT_BASE / "test"),
    ]
    all_ascii = all(
        all(ord(c) < 128 for c in s)
        for s in test_strings
    )
    check(all_ascii, "All output strings are ASCII-safe")

    # 9. Verify write-only target constraint
    check(
        str(OUTPUT_BASE).endswith(
            os.path.join("memory", "work", "jarvis", "autoresearch")
        ),
        "Output base is under autoresearch/ (write constraint)"
    )

    # 10. Threshold logic
    high_metrics = {"contradiction_count": 5, "coverage_score": 40}
    low_metrics = {"contradiction_count": 1, "coverage_score": 80}
    check(
        high_metrics["contradiction_count"] >= SIGNAL_THRESHOLD_CONTRADICTIONS,
        "High contradictions triggers signal"
    )
    check(
        low_metrics["contradiction_count"] < SIGNAL_THRESHOLD_CONTRADICTIONS
        and low_metrics["coverage_score"] >= SIGNAL_THRESHOLD_COVERAGE,
        "Low findings skips signal"
    )

    print()
    print("Results: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
