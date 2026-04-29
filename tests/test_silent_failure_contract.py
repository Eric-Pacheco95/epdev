"""Contract tests against the silent-failure pattern.

Two enforcement layers:

1. Producer contract (Python): domain_knowledge_consolidator.run_consolidation()
   must return non-zero whenever it records status="failure" via manifest_db.

2. Wrapper contract (.bat lint): every tools/scripts/run_*.bat that runs a Python
   producer must capture %ERRORLEVEL% before any subsequent `echo` (which always
   resets ERRORLEVEL to 0) and exit with the captured code so Task Scheduler
   sees the real result.

Why: 2026-04-26 DomainKnowledgeConsolidator wrote a "failure" producer_runs row
but Task Scheduler recorded last_task_result=0. Root cause: the trailing
`echo ... %ERRORLEVEL%` in run_domain_consolidator.bat clobbered the Python
exit code (echo always succeeds). /vitals showed "failed (53h ago)" while
Eric saw Task Scheduler green -- the two states disagreed silently.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Layer 1: Python producer contract
# ---------------------------------------------------------------------------
class TestDomainConsolidatorExitCodeContract:
    """run_consolidation must return non-zero whenever it writes a failure row."""

    def test_returns_nonzero_when_llm_synthesis_fails(self, tmp_path, monkeypatch):
        """When _call_llm returns None for any domain, the script must exit non-zero
        AND write status='failure' -- never the silent 'failure-row + exit-0' combo."""
        import tools.scripts.domain_knowledge_consolidator as dkc

        # Set up a minimal knowledge dir with one domain that has new sources.
        # REPO_ROOT must contain KNOWLEDGE_DIR so source paths resolve to a relative path.
        repo = tmp_path / "repo"
        repo.mkdir()
        knowledge = repo / "knowledge"
        domain_dir = knowledge / "test_domain"
        domain_dir.mkdir(parents=True)
        (domain_dir / "2026-04-01_seed.md").write_text("# seed article\n", encoding="utf-8")

        monkeypatch.setattr(dkc, "REPO_ROOT", repo)
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", knowledge)
        monkeypatch.setattr(dkc, "STATE_FILE", tmp_path / "state.json")
        monkeypatch.setattr(dkc, "ABSORBED_DIR", tmp_path / "absorbed_missing")
        monkeypatch.setattr(dkc, "PREDICTIONS_DIR", tmp_path / "predictions_missing")
        monkeypatch.setattr(dkc, "SYNTHESIS_DIR", tmp_path / "synthesis_missing")
        monkeypatch.setattr(dkc, "SIGNALS_DIR", tmp_path / "signals")
        # Force LLM call to fail
        monkeypatch.setattr(dkc, "_call_llm", lambda *a, **kw: None)
        # Avoid Slack and DB side effects
        monkeypatch.setattr(dkc, "_send_slack", lambda *a, **kw: None)

        emitted = []

        def fake_emit_producer_run(status, n):
            emitted.append(status)

        monkeypatch.setattr(dkc, "_emit_producer_run", fake_emit_producer_run)
        # Skip worktree creation -- run in dry_run=True path instead, but we still
        # need to verify the exit-code/status pairing on the actual production path
        # by stubbing worktree.
        monkeypatch.setattr(dkc, "_create_worktree", lambda: tmp_path / "wt")
        (tmp_path / "wt").mkdir()

        rc = dkc.run_consolidation(dry_run=False, autonomous=True)

        assert rc != 0, "run_consolidation must return non-zero when LLM synthesis fails"
        assert "failure" in emitted, (
            "When run_consolidation returns non-zero, it must also have written "
            "status='failure' to producer_runs (the failing-row + exit-0 silent "
            "failure was the 2026-04-26 regression)"
        )

    def test_returns_zero_on_clean_run(self, tmp_path, monkeypatch):
        """Clean dry-run with no domains returns 0 -- the contract only fires when
        a failure row is actually written."""
        import tools.scripts.domain_knowledge_consolidator as dkc

        empty_knowledge = tmp_path / "knowledge"
        empty_knowledge.mkdir()
        monkeypatch.setattr(dkc, "KNOWLEDGE_DIR", empty_knowledge)
        monkeypatch.setattr(dkc, "STATE_FILE", tmp_path / "state.json")
        monkeypatch.setattr(dkc, "ABSORBED_DIR", tmp_path / "absorbed_missing")

        rc = dkc.run_consolidation(dry_run=True)
        assert rc == 0


# ---------------------------------------------------------------------------
# Layer 2: .bat wrapper exit-propagation lint
# ---------------------------------------------------------------------------
# .bat files in this set are intentionally exempt from the lint:
#   run_hook.bat              -- generic launcher; already correct (template).
#   run_remote_control.bat    -- restart-loop wrapper, never exits normally.
#   run_event_rotation.bat    -- last command IS the python invocation (natural).
#   run_heartbeat_rotation.bat -- last command IS the python invocation.
#   run_isc_producer.bat      -- last command IS the python invocation.
#   run_memory_sampler.bat    -- last command IS the python invocation.
#   run_moralis_monitor.bat   -- last command IS the python invocation (cd + .venv).
#   run_morning_summary.bat   -- last command IS the python invocation.
#   run_signal_compression.bat -- last command IS the python invocation.
_BAT_LINT_EXEMPT = frozenset({
    "run_hook.bat",
    "run_remote_control.bat",
    "run_event_rotation.bat",
    "run_heartbeat_rotation.bat",
    "run_isc_producer.bat",
    "run_memory_sampler.bat",
    "run_moralis_monitor.bat",
    "run_morning_summary.bat",
    "run_signal_compression.bat",
})


def _strip_comments_and_blanks(lines: list[str]) -> list[str]:
    """Return non-blank, non-REM lines (case-insensitive)."""
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.lower().startswith("rem ") or s.lower() == "rem":
            continue
        out.append(s)
    return out


def _last_meaningful_line(content: str) -> str:
    return _strip_comments_and_blanks(content.splitlines())[-1]


def _runs_python_or_claude(content: str) -> bool:
    """Heuristic: does this .bat invoke python.exe or claude(.exe) at all?"""
    return bool(re.search(r"python\.exe|claude(\.exe)?\b|\\python\b", content, re.IGNORECASE))


class TestBatExitPropagationLint:
    """Every run_*.bat must end with `exit /b %RC%` (or equivalent) when it
    runs a python/claude invocation followed by any echo. Otherwise a trailing
    echo silently resets ERRORLEVEL to 0 and Task Scheduler reports success
    on a failed run."""

    @pytest.mark.parametrize(
        "bat_path",
        [p for p in sorted((REPO_ROOT / "tools" / "scripts").glob("run_*.bat"))
         if p.name not in _BAT_LINT_EXEMPT],
        ids=lambda p: p.name,
    )
    def test_bat_propagates_exit_code(self, bat_path):
        content = bat_path.read_text(encoding="utf-8", errors="replace")
        if not _runs_python_or_claude(content):
            pytest.skip(f"{bat_path.name} does not invoke python/claude")

        last = _last_meaningful_line(content)
        # Accept any of: `exit /b %RC%`, `exit /b %ERRORLEVEL%`, `exit /b 0`
        # (the latter only allowed if the .bat has captured RC earlier and
        # this is a watchdog-suspend path -- but the LAST line should still
        # be a propagating exit).
        is_exit = re.match(
            r"^exit\s+/b\s+(%RC%|%ERRORLEVEL%|%WORST_RC%|\d+)\s*$",
            last,
            re.IGNORECASE,
        )
        assert is_exit, (
            f"{bat_path.name} must end with `exit /b %RC%` (or %WORST_RC% / "
            f"%ERRORLEVEL%) so Task Scheduler sees the real Python exit code. "
            f"Last meaningful line was: {last!r}. "
            f"Without this, a trailing `echo ... %ERRORLEVEL%` resets the exit "
            f"code to 0 and silently masks producer failures."
        )

    @pytest.mark.parametrize(
        "bat_path",
        [p for p in sorted((REPO_ROOT / "tools" / "scripts").glob("run_*.bat"))
         if p.name not in _BAT_LINT_EXEMPT],
        ids=lambda p: p.name,
    )
    def test_bat_captures_rc_before_echo(self, bat_path):
        """For .bat files that have an `echo ... ERRORLEVEL` AFTER a python/claude
        call, ensure %ERRORLEVEL% is captured into a variable BEFORE that echo
        (otherwise the captured value is whatever the prior `echo` returned, i.e.
        zero)."""
        content = bat_path.read_text(encoding="utf-8", errors="replace")
        if not _runs_python_or_claude(content):
            pytest.skip(f"{bat_path.name} does not invoke python/claude")

        # Find every echo line that references %ERRORLEVEL%
        bad = []
        lines = content.splitlines()
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped.lower().startswith("rem"):
                continue
            if stripped.lower().startswith("echo") and "%ERRORLEVEL%" in stripped.upper():
                bad.append((i + 1, stripped))

        assert not bad, (
            f"{bat_path.name} references %ERRORLEVEL% directly inside an `echo` "
            f"after a python/claude call. The shell evaluates %ERRORLEVEL% AFTER "
            f"the previous command -- if that previous command was another echo, "
            f"%ERRORLEVEL% is already 0 and the log lies. Capture into RC first: "
            f"`set \"RC=%ERRORLEVEL%\"; echo ... (exit code: %RC%)`. "
            f"Offending lines: {bad}"
        )
