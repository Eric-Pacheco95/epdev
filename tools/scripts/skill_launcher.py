#!/usr/bin/env python3
"""Autonomous skill launcher — runs /autoresearch in an isolated git worktree.

Usage:
  python tools/scripts/skill_launcher.py \\
    --skill autoresearch \\
    --args "topic to research" \\
    --max-runtime 7200 \\
    --max-cost 15 \\
    --verifier tools/scripts/verify_autoresearch_outcome.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
PARK_GATE_DIR = REPO_ROOT / "memory" / "work" / "skill-launcher-autoresearch" / "park_gates"
RUN_LOG_DIR = REPO_ROOT / "memory" / "work" / "skill-launcher-autoresearch" / "run_logs"

_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

GENERATOR_MODEL = "claude-sonnet-4-6"
QUALITY_GATE_MODEL = "claude-opus-4-7"


def check_skill_safety(skill_md_path: Path) -> tuple[bool, str]:
    """Read SKILL.md; return (is_autonomous_safe, content). False if field absent or false."""
    if not skill_md_path.is_file():
        return False, ""
    content = skill_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "## autonomous_safe" and i + 1 < len(lines):
            return lines[i + 1].strip().lower() == "true", content
        if "autonomous_safe" in line.lower() and ":" in line:
            return line.split(":", 1)[1].strip().lower() == "true", content
    return False, content


def hash_skill(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous skill launcher (v1: autoresearch)")
    parser.add_argument("--skill", default="autoresearch")
    parser.add_argument("--args", required=True, dest="skill_args")
    parser.add_argument("--max-runtime", type=int, default=7200)
    parser.add_argument("--max-cost", type=float, default=15.0)
    parser.add_argument("--verifier", default="tools/scripts/verify_autoresearch_outcome.py")
    parser.add_argument("--watchdog-n", type=int, default=10)
    args = parser.parse_args()

    run_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(timezone.utc).isoformat()
    skill_md_path = SKILLS_DIR / args.skill / "SKILL.md"
    verifier_path = REPO_ROOT / args.verifier
    resume_cmd = (
        f"python tools/scripts/skill_launcher.py "
        f"--skill {args.skill} --args {json.dumps(args.skill_args)}"
    )

    is_safe, skill_content = check_skill_safety(skill_md_path)
    if not is_safe:
        print(f"ABORT: {args.skill}/SKILL.md autonomous_safe is false or absent", file=sys.stderr)
        return 1

    initial_hash = hash_skill(skill_content)

    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.worktree import (
        acquire_claude_lock, release_claude_lock, worktree_setup, worktree_cleanup,
    )
    from tools.scripts.lib.skill_launcher_lib import (
        WatchdogThread, build_prompt, estimate_cost_usd, open_pr_via_claude,
        parse_tokens_from_stream_json, run_verifier, send_park_alert,
        spawn_quality_gate, write_park_gate, write_run_log,
    )

    _launcher_slot = acquire_claude_lock("skill-launcher")
    if _launcher_slot is None:
        print("ERROR: claude lock held — another autonomous process running", file=sys.stderr)
        return 1

    branch = f"jarvis/skill-launcher-{args.skill}-{run_id}"
    slug_dir = REPO_ROOT.parent / f"epdev-worktree-{run_id}"
    worktree = worktree_setup(branch, worktree_dir=slug_dir)

    tokens, cost, exit_reason, gen_model = 0, 0.0, "unknown", GENERATOR_MODEL
    gen_session = f"{run_id}-gen"

    try:
        if worktree is None:
            exit_reason = "worktree_setup_failed"
            park = write_park_gate(PARK_GATE_DIR, run_id, args.skill, args.skill_args,
                                   exit_reason, resume_cmd, started_at, 0, 0.0)
            send_park_alert(REPO_ROOT, args.skill_args, exit_reason, park)
            return 1

        # Writes flow through the worktree junction to the main repo — scan main
        # repo directly to avoid Windows junction directory-listing cache lag.
        knowledge_dir = REPO_ROOT / "memory" / "knowledge"
        env = os.environ.copy()
        env["JARVIS_SESSION_TYPE"] = "autonomous"
        env["JARVIS_WORKTREE_ROOT"] = str(worktree)

        proc = subprocess.Popen(
            [CLAUDE_BIN, "-p", "--output-format", "stream-json", "--verbose", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", cwd=str(worktree), env=env,
        )
        proc.stdin.write(build_prompt(args.skill, args.skill_args, args.max_cost))
        proc.stdin.close()

        watchdog = WatchdogThread(
            knowledge_dir, proc, n_consecutive=args.watchdog_n,
            skill_md_path=skill_md_path, initial_hash=initial_hash,
        )
        watchdog.start()

        try:
            stdout, _ = proc.communicate(timeout=args.max_runtime)
        except subprocess.TimeoutExpired:
            proc.terminate()
            stdout, _ = proc.communicate()
            exit_reason = "timeout"

        tokens, gen_model = parse_tokens_from_stream_json(stdout)
        cost = estimate_cost_usd(tokens, gen_model)

        # Write raw stdout to a log so failed runs can be diagnosed.
        run_log_raw = RUN_LOG_DIR / f"{run_id}_raw.txt"
        RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
        run_log_raw.write_text(stdout or "", encoding="utf-8", errors="replace")
        print(f"  Agent output logged -> {run_log_raw}")

        if watchdog.killed:
            exit_reason = watchdog.kill_reason or "watchdog_null_signal"
        elif exit_reason == "unknown":
            if proc.returncode != 0:
                exit_reason = "agent_error"
            else:
                rc = run_verifier(verifier_path, knowledge_dir, tokens, started_at)
                if rc != 0:
                    exit_reason = "verifier_failed"
                else:
                    qg_passed, qg_session = spawn_quality_gate(
                        CLAUDE_BIN, branch, args.skill_args, worktree,
                        knowledge_dir=knowledge_dir, started_at=started_at,
                    )
                    write_run_log(RUN_LOG_DIR, run_id, gen_model, QUALITY_GATE_MODEL,
                                  gen_session, qg_session)
                    exit_reason = "success" if qg_passed else "quality_gate_failed"
                    if qg_passed:
                        # PR is best-effort — knowledge files are gitignored so branch
                        # has no committed diff; skip if Claude can't open one.
                        pr_ok = open_pr_via_claude(CLAUDE_BIN, branch, args.skill_args)
                        if not pr_ok:
                            print("  PR open skipped or failed (non-fatal for gitignored output)")

        if exit_reason != "success":
            park = write_park_gate(PARK_GATE_DIR, run_id, args.skill, args.skill_args,
                                   exit_reason, resume_cmd, started_at, tokens, cost)
            send_park_alert(REPO_ROOT, args.skill_args, exit_reason, park)
            return 1

        print(f"SUCCESS: run_id={run_id} branch={branch}")
        return 0

    finally:
        worktree_cleanup(slug_dir)
        release_claude_lock(_launcher_slot)


if __name__ == "__main__":
    sys.exit(main())
