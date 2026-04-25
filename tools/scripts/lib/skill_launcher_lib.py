"""Helpers for skill_launcher.py: watchdog, prompt building, verifier, park-gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"
_PARK_GATE_DIR = _REPO_ROOT / "memory" / "work" / "skill-launcher-autoresearch" / "park_gates"
_RUN_LOG_DIR = _REPO_ROOT / "memory" / "work" / "skill-launcher-autoresearch" / "run_logs"
_PRICING_PATH = _REPO_ROOT / "config" / "ai_pricing.json"
_GENERATOR_MODEL = "claude-sonnet-4-6"
_QUALITY_GATE_MODEL = "claude-opus-4-7"


class WatchdogThread(threading.Thread):
    """Poll knowledge_dir for new .md files; kill proc after N consecutive empty checks.

    Also checks SKILL.md hash-pin; sets kill_reason='hash_pin_mismatch' on mutation.
    """

    def __init__(
        self,
        knowledge_dir: Path,
        proc: subprocess.Popen,
        n_consecutive: int = 10,
        check_interval_s: float = 60.0,
        skill_md_path: Path | None = None,
        initial_hash: str | None = None,
    ) -> None:
        super().__init__(name="skill-launcher-watchdog", daemon=True)
        self.knowledge_dir = Path(knowledge_dir)
        self.proc = proc
        self.n_consecutive = n_consecutive
        self.check_interval_s = check_interval_s
        self.skill_md_path = skill_md_path
        self.initial_hash = initial_hash
        self.killed = False
        self.kill_reason: str | None = None

    def _count_files(self) -> int:
        if not self.knowledge_dir.is_dir():
            return 0
        return sum(1 for _ in self.knowledge_dir.rglob("*.md"))

    def _hash_current_skill(self) -> str | None:
        if not self.skill_md_path or not self.initial_hash:
            return None
        try:
            content = self.skill_md_path.read_text(encoding="utf-8")
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except OSError:
            return None

    def run(self) -> None:
        last_count = self._count_files()
        consecutive_empty = 0
        while self.proc.poll() is None:
            time.sleep(self.check_interval_s)
            if self.proc.poll() is not None:
                return
            current_hash = self._hash_current_skill()
            if current_hash is not None and current_hash != self.initial_hash:
                self.proc.terminate()
                self.killed = True
                self.kill_reason = "hash_pin_mismatch"
                return
            current_count = self._count_files()
            if current_count > last_count:
                last_count = current_count
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                if consecutive_empty >= self.n_consecutive:
                    self.proc.terminate()
                    self.killed = True
                    self.kill_reason = "watchdog_null_signal"
                    return


def parse_tokens_from_stream_json(text: str) -> tuple[int, str]:
    """Return (total_tokens, detected_model) from claude -p --output-format stream-json."""
    total, model = 0, _GENERATOR_MODEL
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
        if isinstance(msg.get("model"), str):
            model = msg["model"]
        usage = msg.get("usage") if isinstance(msg, dict) else None
        if isinstance(usage, dict):
            total += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    return total, model


def estimate_cost_usd(tokens: int, model: str) -> float:
    try:
        rates = (
            json.loads(_PRICING_PATH.read_text(encoding="utf-8"))
            .get("claude", {}).get("models", {}).get(model, {})
        )
        return tokens * rates.get("output_per_mtok", 15.0) / 1_000_000
    except Exception:
        return 0.0


def build_prompt(skill: str, args_str: str, max_cost: float) -> str:
    skill_md = _SKILLS_DIR / skill / "SKILL.md"
    skill_text = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
    return (
        f"<command-name>/{skill}</command-name>\n\n"
        f"Running autonomously in isolated worktree. Cost cap: ${max_cost} USD.\n"
        f"Write all output to memory/knowledge/.\n\n"
        f"SKILL DEFINITION:\n{skill_text}\n\nINPUT:\n{args_str}\n"
    )[:90_000]


def run_verifier(verifier: Path, knowledge_dir: Path, tokens: int, started_at: str) -> int:
    import sys
    cmd = [sys.executable, str(verifier),
           "--knowledge-dir", str(knowledge_dir), "--since-time", started_at]
    if tokens > 0:
        cmd += ["--tokens-spent", str(tokens)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        import sys as _sys
        print(r.stderr, file=_sys.stderr)
    return r.returncode


def spawn_quality_gate(claude_bin: str, branch: str, topic: str, worktree: Path) -> tuple[bool, str]:
    """Run Opus quality-gate review; return (passed, session_id)."""
    diff = subprocess.run(
        ["git", "diff", "--stat", f"main...{branch}"],
        capture_output=True, text=True, cwd=str(worktree),
    ).stdout or "(no diff)"
    prompt = (
        "Quality-gate review for autoresearch output.\n\n"
        f"Diff summary:\n{diff[:4000]}\n\nTopic: {topic}\n\n"
        "Check: real knowledge content (not stub), citations present, >300 words. "
        "Reply with exactly: QUALITY_GATE_PASS or QUALITY_GATE_FAIL <reason>"
    )
    r = subprocess.run(
        [claude_bin, "-p", "--output-format", "stream-json", "--model", _QUALITY_GATE_MODEL, "-"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    session_id = f"{branch}-qg"
    for line in (r.stdout or "").splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj.get("session_id"), str):
                session_id = obj["session_id"]
        except json.JSONDecodeError:
            pass
    return "QUALITY_GATE_PASS" in (r.stdout or ""), session_id


def open_pr_via_claude(claude_bin: str, branch: str, topic: str) -> bool:
    """Instruct Claude to open a PR so the PreToolUse gh-allowlist hook fires.

    Launcher never calls gh directly — command is assembled here and passed
    as prompt text to a claude subprocess running under hook supervision.
    (Kept in lib so skill_launcher.py has no 'gh' string — ISC-7.)
    """
    _parts = ["pr", "create", "--repo", "epdev/epdev",
               "--head", branch, "--base", "main",
               "--title", json.dumps("autoresearch: " + topic[:55]),
               "--body", "Autonomous autoresearch run. Verified by Tier 1 + Opus quality-gate."]
    prompt = "Run this command:\n" + " ".join(["gh"] + _parts) + "\nThen print DONE."
    r = subprocess.run(
        [claude_bin, "-p", "--verbose", "-"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    return "DONE" in (r.stdout or "")


def write_park_gate(park_gate_dir: Path, run_id: str, skill: str, topic: str,
                    exit_reason: str, resume_cmd: str, started_at: str,
                    tokens: int, cost: float) -> Path:
    park_gate_dir.mkdir(parents=True, exist_ok=True)
    path = park_gate_dir / f"{run_id}.json"
    path.write_text(json.dumps({
        "skill": skill, "run_id": run_id, "topic": topic,
        "exit_reason": exit_reason, "resume_command": resume_cmd,
        "started_at": started_at, "ended_at": datetime.now(timezone.utc).isoformat(),
        "tokens_spent": tokens, "cost_usd": round(cost, 4),
    }, indent=2), encoding="utf-8")
    return path


def write_run_log(run_log_dir: Path, run_id: str, gen_model: str,
                  qg_model: str, gen_session: str, qg_session: str) -> None:
    run_log_dir.mkdir(parents=True, exist_ok=True)
    (run_log_dir / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id,
        "generator_model": gen_model, "generator_session": gen_session,
        "quality_gate_model": qg_model, "quality_gate_session": qg_session,
    }, indent=2), encoding="utf-8")


def send_park_alert(repo_root: Path, topic: str, exit_reason: str, park_path: Path) -> None:
    import sys
    try:
        sys.path.insert(0, str(repo_root))
        from tools.scripts.slack_notify import notify
        notify(
            f":warning: skill-launcher parked | reason: `{exit_reason}` | topic: {topic[:60]} | {park_path.name}",
            severity="routine",
        )
    except Exception as exc:
        print(f"Slack alert failed: {exc}", file=sys.stderr)
