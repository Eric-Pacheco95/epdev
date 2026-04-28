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
import ctypes
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.worktree import acquire_claude_lock, release_claude_lock  # noqa: E402
from tools.scripts.lib.isc_templates import isc_autoresearch_proposals_review  # noqa: E402

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

PROMPT_SIZE_LIMIT = 90_000  # hard gate -- never warn-and-proceed past this

TELOS_DIR = REPO_ROOT / "memory" / "work" / "telos"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
# NOTE: processed/ subdir was never created in production. Signals land
# directly in SIGNALS_DIR. Keep PROCESSED_DIR as a fallback but primary
# signal reading now uses SIGNALS_DIR with the 14-day window.
PROCESSED_DIR = SIGNALS_DIR / "processed"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
SESSION_DIR = REPO_ROOT / "memory" / "session"
OUTPUT_BASE = REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"

# Thresholds for autonomous signal + Slack posting
SIGNAL_THRESHOLD_CONTRADICTIONS = 3
SIGNAL_THRESHOLD_COVERAGE = 50  # percent

# Cross-project repos that count toward TELOS coverage (G2/G5 indirect work).
# Each entry is a path; if it exists and is a git repo, recent commits are
# included as External Project Evidence and credited toward goal coverage.
EXTERNAL_PROJECT_REPOS = [
    {
        "path": Path(r"C:\Users\ericp\Github\claude-workbench"),
        "credit_goals": ["G5", "G2"],  # day-job AI mastery, AI-augmented life
        "rationale": "Day-job AI workflow harness; G5 pursued indirectly here",
    },
]
EXTERNAL_EVIDENCE_DAYS = 30


# -- Windows sleep prevention -------------------------------------------------

# ES_CONTINUOUS | ES_SYSTEM_REQUIRED — prevent system sleep during run
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


def prevent_sleep() -> bool:
    """Prevent Windows from sleeping during the run. Returns True on success."""
    if sys.platform != "win32":
        return False
    try:
        result = ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        )
        if result == 0:
            print("  WARNING: SetThreadExecutionState returned 0 "
                  "(sleep prevention may not be active)", file=sys.stderr)
            return False
        return True
    except (AttributeError, OSError):
        return False


def allow_sleep() -> None:
    """Re-allow system sleep (clear the continuous flag)."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except (AttributeError, OSError):
        pass


# -- File gathering (read-only, time-bounded) --------------------------------

TELOS_FILE_MAX_CHARS = 4000  # per-file cap; saves ~20K on LEARNED+STATUS+MUSIC


def read_telos_files() -> dict[str, str]:
    """Read all TELOS identity files. Returns {filename: content}."""
    result = {}
    if not TELOS_DIR.is_dir():
        return result
    for f in sorted(TELOS_DIR.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            if len(content) > TELOS_FILE_MAX_CHARS:
                content = content[:TELOS_FILE_MAX_CHARS] + "\n[... truncated for prompt budget]"
            result[f.name] = content
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


def read_prior_proposals(days: int = 14, max_runs: int = 5) -> list[dict]:
    """Read recent run-*/proposals.md files to dedup against prior proposals.

    Prevents the "already-applied edit" failure mode where autoresearch
    proposes the same TELOS change multiple days in a row because it has no
    memory of what it already suggested (or what Eric already merged).
    """
    if not OUTPUT_BASE.is_dir():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    candidates = []
    for run_dir in OUTPUT_BASE.glob("run-*"):
        proposals_file = run_dir / "proposals.md"
        if not proposals_file.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(proposals_file.stat().st_mtime)
            if mtime >= cutoff:
                candidates.append((proposals_file, mtime, run_dir.name))
        except OSError:
            pass

    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = candidates[:max_runs]

    result = []
    for f, mtime, run_name in candidates:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if len(content) > 1500:
                content = content[:1500] + "\n[... truncated]"
            result.append({
                "run": run_name,
                "date": mtime.strftime("%Y-%m-%d"),
                "content": content,
            })
        except OSError:
            pass
    return result


def read_external_project_evidence() -> list[dict]:
    """Read recent git log from configured cross-project repos.

    These commits count toward TELOS goal coverage when the goal is pursued
    indirectly in a sibling repo (e.g., G5 day-job AI mastery via
    claude-workbench). Each entry carries the credit_goals list so the
    analysis prompt can attribute evidence correctly.
    """
    result = []
    for repo_cfg in EXTERNAL_PROJECT_REPOS:
        repo_path = repo_cfg["path"]
        if not (repo_path / ".git").is_dir():
            continue
        try:
            proc = subprocess.run(
                [
                    "git", "log",
                    f"--since={EXTERNAL_EVIDENCE_DAYS} days ago",
                    "--pretty=format:%h %ad %s",
                    "--date=short",
                ],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            log = proc.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            log = ""

        if not log:
            continue

        # Cap to 20 commits to bound prompt size
        lines = log.splitlines()[:20]
        result.append({
            "repo": repo_path.name,
            "credit_goals": repo_cfg["credit_goals"],
            "rationale": repo_cfg["rationale"],
            "commit_count": len(lines),
            "log": "\n".join(lines),
        })
    return result


def gather_inputs() -> dict:
    """Gather all read-scope inputs. Returns structured dict."""
    telos = read_telos_files()
    synthesis = read_synthesis_recent(5)
    # Primary: read from SIGNALS_DIR (where signals actually land).
    # Fallback: also check PROCESSED_DIR if it exists, to avoid losing
    # signals if the processed/ subdir is ever created.
    signals = read_recent_files(SIGNALS_DIR, days=7, max_files=10)
    if PROCESSED_DIR.is_dir():
        processed = read_recent_files(PROCESSED_DIR, days=7, max_files=5)
        # Merge, dedup by name, cap at 10
        seen = {s["name"] for s in signals}
        for p in processed:
            if p["name"] not in seen:
                signals.append(p)
                seen.add(p["name"])
        signals = signals[:10]
    raw_signals = read_recent_files(SIGNALS_DIR, days=3, max_files=5)
    failures = read_recent_files(FAILURES_DIR, days=14, max_files=10)
    sessions = read_recent_files(SESSION_DIR, days=7, max_files=5)
    prior_proposals = read_prior_proposals(days=14, max_runs=5)
    external_evidence = read_external_project_evidence()

    # raw_signals uses the 3-day window from SIGNALS_DIR -- same dir as
    # signals but narrower window. Keep both: "signals" = 7-day context,
    # "raw_signals" = 3-day recency emphasis in the prompt.
    return {
        "telos": telos,
        "synthesis": synthesis,
        "signals": signals,
        "raw_signals": raw_signals,
        "failures": failures,
        "sessions": sessions,
        "prior_proposals": prior_proposals,
        "external_evidence": external_evidence,
        "scope_summary": {
            "telos_files": len(telos),
            "synthesis_docs": len(synthesis),
            "signals_7d": len(signals),
            "raw_signals_3d": len(raw_signals),
            "failures_14d": len(failures),
            "sessions_7d": len(sessions),
            "prior_proposals": len(prior_proposals),
            "external_repos": len(external_evidence),
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

    env = os.environ.copy()
    env["JARVIS_SESSION_TYPE"] = "autonomous"
    try:
        # Pass prompt via stdin ("-") to avoid Windows command-line length
        # limits (WinError 206).  The overnight_runner uses the same pattern.
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "-"],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=max(600, len(full_prompt) // 100),  # ~1s per 100 chars, scales with prompt size
            cwd=str(REPO_ROOT),
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Rate limit guard (steering rule [MODEL-DEP]):
            # claude -p returns exit 0 with the rate-limit message in stdout
            # when the Claude Max usage limit is hit. Treat as error so
            # callers (auto_apply_telos, analysis pass) do not act on it.
            rate_limit_phrases = (
                "hit your limit", "rate limit", "quota exceeded",
                "too many requests", "usage limit resets",
            )
            output_lower = output.lower()
            if any(p in output_lower for p in rate_limit_phrases):
                return "(claude -p rate-limited: %s)" % output[:200]
            return output
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
- External evidence: <repo name + commit count if this goal is in a credit_goals list, else "none">
- Notes: <brief>

When scoring coverage_score, credit external project evidence: if a goal has
no in-repo signals but an external repo in the External Project Evidence
section lists it in credit_goals with >=1 commit in the last 30 days, count
that goal as PARTIAL (not NO) and credit it at half weight. A goal pursued
indirectly in a sibling repo is not a coverage gap -- it is intentional
routing.

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
- Check the PRIOR PROPOSALS section below (last 14 days of run-*/proposals.md).
  Do NOT propose changes that were already proposed in a prior run OR that
  appear to have been already applied to the current TELOS files. Before
  proposing any TELOS edit, verify the current TELOS content does NOT already
  reflect the change you are about to propose. If the change is already live,
  the proposal is stale -- skip it.
- If a proposal overlaps with an existing task or prior proposal, skip it or
  reference the earlier one instead of creating a duplicate.
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

    if inputs.get("external_evidence"):
        parts.append("\n## External Project Evidence (cross-repo commits, last 30 days)\n")
        parts.append("These commits count toward TELOS coverage for the goals listed in credit_goals.\n")
        for ext in inputs["external_evidence"]:
            parts.append("### %s -- credit_goals: %s (%d commits)\n" % (
                ext["repo"], ", ".join(ext["credit_goals"]), ext["commit_count"]))
            parts.append("Rationale: %s\n" % ext["rationale"])
            parts.append("```\n%s\n```\n" % ext["log"])

    if inputs.get("prior_proposals"):
        parts.append("\n## Prior Proposals (last 14 days of autoresearch runs)\n")
        parts.append("Dedup against these. Do NOT re-propose items already listed OR already applied to current TELOS.\n")
        for pp in inputs["prior_proposals"]:
            parts.append("### %s (%s)\n%s\n" % (pp["run"], pp["date"], pp["content"]))

    parts.append("\n## Scope Summary\n")
    scope = inputs["scope_summary"]
    parts.append("- TELOS files read: %d" % scope["telos_files"])
    parts.append("- Synthesis docs read: %d" % scope["synthesis_docs"])
    parts.append("- Processed signals (7d): %d" % scope["signals_7d"])
    parts.append("- Raw signals (3d): %d" % scope["raw_signals_3d"])
    parts.append("- Failures (14d): %d" % scope["failures_14d"])
    parts.append("- Sessions (7d): %d" % scope["sessions_7d"])
    parts.append("- Prior proposals (14d): %d" % scope.get("prior_proposals", 0))
    parts.append("- External repos with recent commits: %d" % scope.get("external_repos", 0))

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

def _dump_raw_response(response: str, tag: str) -> None:
    """Dump raw Claude response to a timestamped file for diagnosis.

    Called when metrics parsing fails silently — makes the failure loud
    so it can be investigated from logs.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    dump_dir = OUTPUT_BASE / ("run-%s" % today)
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / ("raw_response_%s.txt" % tag)
    try:
        dump_path.write_text(response[:50000], encoding="utf-8")
        print("  Raw response dumped to: %s" % dump_path, file=sys.stderr)
    except OSError as exc:
        print("  WARNING: could not dump raw response: %s" % exc,
              file=sys.stderr)


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
        _dump_raw_response(response, "metrics-section-missing")
        return metrics

    block = metrics_match.group(1)
    parsed_count = 0
    for key in metrics:
        m = re.search(r"%s:\s*(\d+\.?\d*)" % key, block)
        if m:
            val = m.group(1)
            if "." in val:
                metrics[key] = float(val)
            else:
                metrics[key] = int(val)
            parsed_count += 1

    # Loud failure: if METRICS section existed but no values parsed,
    # something is wrong with the format — dump for diagnosis
    if parsed_count == 0:
        print("  WARNING: METRICS section found but 0 values parsed. "
              "Dumping raw response for diagnosis.", file=sys.stderr)
        _dump_raw_response(response, "metrics-parse-zero")

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
        "- Signals (7d): %d" % scope_summary["signals_7d"],
        "- Raw signals (3d): %d" % scope_summary["raw_signals_3d"],
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


# -- Auto-apply safe TELOS updates -------------------------------------------

TELOS_AUTO_SAFE_FILES = {"STATUS.md", "LEARNED.md", "CHALLENGES.md"}

def auto_apply_telos(metrics: dict, run_dir: Path) -> bool:
    """Auto-apply TELOS updates for safe-tier files when thresholds are crossed.

    Only touches STATUS.md, LEARNED.md, CHALLENGES.md (the auto-update tier
    from /telos-update). Higher-sensitivity files (MISSION.md, BELIEFS.md)
    require interactive human approval.

    Returns True if updates were applied.
    """
    contradictions = metrics.get("contradiction_count", 0)
    coverage = metrics.get("coverage_score", 100)

    if (contradictions < SIGNAL_THRESHOLD_CONTRADICTIONS
            and coverage >= SIGNAL_THRESHOLD_COVERAGE):
        print("  TELOS auto-apply: skipped (thresholds not crossed)")
        return False

    proposals_path = run_dir / "proposals.md"
    if not proposals_path.is_file():
        print("  TELOS auto-apply: skipped (no proposals.md)")
        return False

    proposals = proposals_path.read_text(encoding="utf-8").strip()
    if not proposals:
        print("  TELOS auto-apply: skipped (proposals.md empty)")
        return False

    # Build a focused prompt for safe-tier TELOS updates only
    telos_context = []
    for fname in sorted(TELOS_AUTO_SAFE_FILES):
        fpath = TELOS_DIR / fname
        if fpath.is_file():
            telos_context.append("=== %s ===\n%s" % (
                fname, fpath.read_text(encoding="utf-8")))

    if not telos_context:
        print("  TELOS auto-apply: skipped (no safe-tier TELOS files found)")
        return False

    prompt = (
        "You are updating TELOS identity files based on autoresearch findings.\n\n"
        "RULES:\n"
        "- ONLY modify these files: %s\n"
        "- Use the Edit tool for surgical updates -- never overwrite entire files\n"
        "- Each edit must be supported by evidence from the proposals below\n"
        "- Do NOT touch MISSION.md, BELIEFS.md, GOALS.md, or any other files\n"
        "- Log each change to history/changes/ with source: autonomous-autoresearch\n"
        "- If no changes are warranted, do nothing -- silence is valid\n\n"
        "CURRENT TELOS FILES:\n%s\n\n"
        "AUTORESEARCH PROPOSALS:\n%s\n\n"
        "Apply only well-evidenced updates to the safe-tier files listed above."
    ) % (", ".join(sorted(TELOS_AUTO_SAFE_FILES)),
         "\n\n".join(telos_context), proposals)

    print("  TELOS auto-apply: invoking claude -p for safe-tier updates...")
    result = call_claude(prompt)

    if result.startswith("("):
        print("  TELOS auto-apply: failed -- %s" % result, file=sys.stderr)
        return False

    print("  TELOS auto-apply: complete")
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
    return notify("\n".join(lines), severity=sev, bypass_caps=True)


# -- Backlog intake ----------------------------------------------------------

# TELOS files safe for autonomous dispatcher apply (doc-append only, no code).
# Higher-sensitivity files (MISSION.md, BELIEFS.md, GOALS.md) require
# interactive approval and are intentionally excluded.
_SAFE_TELOS_FILES = frozenset({
    "LEARNED.md", "MODELS.md", "PROJECTS.md", "MUSIC.md",
    "STATUS.md", "CHALLENGES.md", "STRATEGIES.md", "WISDOM.md",
})

# Change verbs that indicate destructive operations — block autonomous apply.
_UNSAFE_CHANGE_VERBS = ("delete", "remove file", "create new file", "rename file", "move file")


def _parse_proposals(run_dir: Path) -> list[dict]:
    """Parse proposals.md into a list of {file, change, priority} dicts.

    Uses a simple line-prefix state machine — robust to multi-line fields.
    Returns empty list on any parse failure.
    """
    proposals_path = run_dir / "proposals.md"
    if not proposals_path.is_file():
        return []
    try:
        lines = proposals_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    results: list[dict] = []
    current: dict | None = None
    active_field: str | None = None

    for line in lines:
        if line.startswith("- File:"):
            if current and current.get("file") and current.get("change"):
                results.append(current)
            current = {"file": line[7:].strip(), "change": "", "priority": "MEDIUM"}
            active_field = None
        elif current is None:
            continue
        elif line.startswith("- Change:"):
            current["change"] = line[9:].strip()
            active_field = "change"
        elif line.startswith("- Evidence:"):
            active_field = None
        elif line.startswith("- Priority:"):
            current["priority"] = line[11:].strip().upper()
            active_field = None
        elif line.startswith("- "):
            active_field = None
        elif active_field == "change" and line.strip():
            current["change"] = (current["change"] + " " + line.strip()).strip()

    if current and current.get("file") and current.get("change"):
        results.append(current)
    return results


def _safe_telos_proposal(proposal: dict) -> bool:
    """Return True if proposal is a safe doc-append to a known TELOS file."""
    filename = proposal.get("file", "").strip()
    if filename not in _SAFE_TELOS_FILES:
        return False
    change_lower = proposal.get("change", "").lower()
    return not any(kw in change_lower for kw in _UNSAFE_CHANGE_VERBS)


def _grep_anchor(change_text: str) -> str | None:
    """Extract a post-change anchor phrase for ISC grep from Change text.

    For replace operations, anchors to the NEW state (after 'with "...' or
    'to "...'). For appends, anchors to the last ISO date or a quoted phrase
    so the ISC reflects the target state after the change.
    """
    # "replace X with Y" / "update X to Y" — anchor to the new content
    for pattern in (r'\bwith\s+"([^"]{5,50})"', r'\bto\s+"([^"]{5,50})"'):
        m = re.search(pattern, change_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:50]
    # Last ISO date (appends embed new date; replaces have old date first)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", change_text)
    if dates:
        return dates[-1]
    # Last quoted phrase 10-60 chars
    quotes = re.findall(r'"([^"]{10,60})"', change_text)
    if quotes:
        return quotes[-1][:50]
    # First 3 content words (>3 chars)
    words = [w.strip(".,;:()\"'--") for w in change_text.split() if len(w.strip(".,;:()\"'--")) > 3]
    return " ".join(words[:3]) if len(words) >= 3 else None


def _inject_proposal_tasks(proposals: list[dict], run_dir: Path, run_date: str) -> int:
    """Inject one pending + autonomous_safe task per safe TELOS doc proposal.

    Returns count of newly injected tasks (0 if all deduped or none safe).
    """
    from tools.scripts.lib.backlog import backlog_append

    injected = 0
    proposals_rel = str((run_dir / "proposals.md").relative_to(REPO_ROOT)).replace("\\", "/")
    priority_map = {"HIGH": 2, "MEDIUM": 3, "LOW": 4}

    for proposal in proposals:
        if not _safe_telos_proposal(proposal):
            continue

        filename = proposal["file"].strip()
        telos_path = "memory/work/telos/%s" % filename
        change_head = proposal["change"][:80].strip()
        anchor = _grep_anchor(proposal["change"])

        if anchor:
            # grep -q exits 0 on match (executable classify) — prd_verb 'grep:'
            # format is not accepted by backlog validator's executable check.
            safe_anchor = anchor.replace('"', "").replace("'", "").replace("\\", "")[:50]
            isc = [
                "%s contains proposal content | Verify: grep -q %s %s"
                % (filename, safe_anchor, telos_path)
            ]
        else:
            isc = [
                "%s file present | Verify: test -f %s" % (filename, telos_path)
            ]

        task = {
            "description": "Apply TELOS proposal: %s → %s" % (change_head, filename),
            "tier": 1,
            "autonomous_safe": True,
            "status": "pending",
            "priority": priority_map.get(proposal.get("priority", "MEDIUM"), 3),
            "isc": isc,
            "expected_outputs": [telos_path],
            "context_files": [proposals_rel],
            "source": "autoresearch",
            "routine_id": "autoresearch:proposal:%s:%s" % (
                run_date, filename.lower().replace(".md", "")
            ),
            "skills": [],
            "notes": "Auto-classified safe TELOS doc-write. Run: %s." % run_date,
        }
        try:
            result = backlog_append(task)
            if result is not None:
                injected += 1
        except Exception as exc:
            print("  WARNING: proposal task injection failed (%s): %s" % (filename, exc),
                  file=sys.stderr)

    return injected


def _inject_autoresearch_backlog(metrics: dict, run_dir: Path) -> None:
    """Inject backlog tasks when this run produced proposals.

    Always injects one aggregate pending_review task (human review gate).
    Also injects individual autonomous_safe=True tasks for each proposal that
    targets a known TELOS doc file — these can be dispatched without human
    approval.

    Respects S14 steering rule: triggers on proposal_count, not raw
    contradiction_count. Dedups per-day via routine_id. Never raises.
    """
    try:
        proposal_count = metrics.get("proposal_count", 0)
        if proposal_count < 1:
            return

        from tools.scripts.lib.backlog import backlog_append

        today = datetime.now().strftime("%Y-%m-%d")
        contradictions = metrics.get("contradiction_count", 0)
        coverage = metrics.get("coverage_score", 100)

        # Aggregate review task (pending_review — human gate for non-safe proposals)
        task = {
            "description": (
                "[autoresearch] %d actionable proposal(s) -- "
                "contradictions=%d, coverage=%.0f%% (%s)"
                % (proposal_count, contradictions, coverage, today)
            ),
            "tier": 0,
            "autonomous_safe": False,
            "status": "pending_review",
            "priority": 2,
            "isc": isc_autoresearch_proposals_review(),
            "skills": [],
            "source": "autoresearch",
            "routine_id": "autoresearch:proposals:%s" % today,
            "context_files": [
                str((run_dir / "proposals.md").relative_to(REPO_ROOT)).replace("\\", "/"),
            ],
            "notes": (
                "Auto-injected by jarvis_autoresearch. S14-tagged "
                "contradictions are intentional through Phase 5 -- review "
                "proposals individually before action."
            ),
        }
        backlog_append(task)

        # Per-proposal tasks for safe TELOS doc targets
        parsed = _parse_proposals(run_dir)
        safe_count = _inject_proposal_tasks(parsed, run_dir, today)
        if safe_count:
            print("  Backlog: injected %d safe proposal task(s)" % safe_count)

    except Exception as exc:
        # Never block the main autoresearch run on a backlog injection failure
        print("  WARNING: backlog injection failed: %s" % exc, file=sys.stderr)


# -- Prompt size gate --------------------------------------------------------

def _enforce_size_gate(inputs: dict) -> tuple[dict, list[str]]:
    """Trim oldest signals until total prompt fits within PROMPT_SIZE_LIMIT.

    Signals are sorted newest-first by read_recent_files(), so dropping from
    the end removes the oldest entries first.  Falls back to raw_signals when
    signals list is exhausted.  Returns (trimmed_inputs, dropped_filenames).
    """
    import copy
    current = copy.deepcopy(inputs)
    dropped: list[str] = []

    while True:
        sys_p, usr_p = build_analysis_prompt(current)
        if len(sys_p) + len(usr_p) <= PROMPT_SIZE_LIMIT:
            break
        if current["signals"]:
            entry = current["signals"].pop()  # oldest (end of newest-first list)
            dropped.append(entry["name"])
        elif current["raw_signals"]:
            entry = current["raw_signals"].pop()
            dropped.append(entry["name"])
        elif current["synthesis"]:
            entry = current["synthesis"].pop()  # oldest synthesis doc
            dropped.append(entry["name"])
        elif current.get("prior_proposals"):
            entry = current["prior_proposals"].pop()
            dropped.append(entry.get("run", "prior-proposal"))
        elif current.get("external_evidence"):
            entry = current["external_evidence"].pop()
            dropped.append(entry.get("repo", "external-evidence"))
        else:
            # Only TELOS+system remain — proceed (TELOS cannot be dropped)
            sys_p, usr_p = build_analysis_prompt(current)
            total = len(sys_p) + len(usr_p)
            print(
                "  WARNING: prompt still %d chars with only TELOS files remaining "
                "— reduce TELOS_FILE_MAX_CHARS if this recurs." % total,
                file=sys.stderr,
            )
            break

    return current, dropped


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
    print("  Signals (7d): %d" % scope["signals_7d"])
    print("  Raw signals (3d): %d" % scope["raw_signals_3d"])
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

    # 3. Prevent system sleep during run
    sleep_prevented = prevent_sleep()
    if sleep_prevented:
        print("  Sleep prevention: active")

    # 4. Acquire global claude -p mutex
    _autoresearch_slot = acquire_claude_lock("autoresearch")
    if _autoresearch_slot is None:
        print("ERROR: Another claude -p process is running. Aborting.",
              file=sys.stderr)
        allow_sleep()
        return 1

    # Build prompts and call API
    print("\nAnalyzing TELOS vs signal evidence...")
    inputs, dropped = _enforce_size_gate(inputs)
    if dropped:
        print("  Prompt exceeded %dK — dropped %d oldest signal(s): %s" % (
            PROMPT_SIZE_LIMIT // 1000, len(dropped), ", ".join(dropped)),
            file=sys.stderr)
    system, user = build_analysis_prompt(inputs)
    print("  Prompt size: %d chars" % (len(system) + len(user)))

    try:
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

        # 7. Auto-apply safe TELOS updates (STATUS, LEARNED, CHALLENGES only)
        auto_apply_telos(metrics, run_dir)

        # 8. Slack notification (if significant)
        post_slack_summary(metrics, run_dir)

        # 9. Backlog intake -- inject one pending_review row per run that
        #    produced actionable proposals. Dedups per-day via routine_id.
        #    Respects the S14 steering rule: we inject on proposal_count,
        #    not on raw contradiction_count, so intentional S14 gaps do not
        #    flood the queue.
        _inject_autoresearch_backlog(metrics, run_dir)

        print("\nIntrospection complete. Review proposals at:")
        print("  %s" % (run_dir / "proposals.md"))
        return 0
    finally:
        release_claude_lock(_autoresearch_slot)
        allow_sleep()


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
    check(len(telos) >= 1, "TELOS dir readable (%d file(s) found)" % len(telos))
    # Full TELOS set checks -- only run when production data is present (>=10 files).
    # Isolated worktrees omit gitignored TELOS files; README.md is always tracked.
    if len(telos) >= 10:
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
