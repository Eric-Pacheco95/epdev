"""Tests for verify_orphan_streak -- load_entries and main() exit code logic."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_orphan_streak as vos
from tools.scripts.verify_orphan_streak import load_entries, THRESHOLD, REQUIRED_STREAK

SCRIPT = REPO_ROOT / "tools" / "scripts" / "verify_orphan_streak.py"


def _make_log(tmp_path: Path, entries: list[dict]) -> Path:
    log = tmp_path / "orphan_python_snapshot.jsonl"
    lines = [json.dumps(e) for e in entries]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log


def _run(log_path: Path) -> int:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True,
        env={**__import__("os").environ},
    )
    return result.returncode


class TestLoadEntries:
    def test_returns_empty_for_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vos, "LOG_FILE", tmp_path / "nonexistent.jsonl")
        assert load_entries() == []

    def test_parses_jsonl_entries(self, tmp_path, monkeypatch):
        entries = [{"date": "2026-01-01", "count": 5}, {"date": "2026-01-02", "count": 3}]
        log = _make_log(tmp_path, entries)
        monkeypatch.setattr(vos, "LOG_FILE", log)
        result = load_entries()
        assert len(result) == 2
        assert result[0]["count"] == 5

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        log = tmp_path / "snap.jsonl"
        log.write_text('{"count": 1}\n\n{"count": 2}\n', encoding="utf-8")
        monkeypatch.setattr(vos, "LOG_FILE", log)
        result = load_entries()
        assert len(result) == 2


class TestMainExitCodes:
    def _run_main(self, monkeypatch, log_file: Path) -> int:
        monkeypatch.setattr(vos, "LOG_FILE", log_file)
        import sys as _sys
        from io import StringIO
        old_argv = _sys.argv
        _sys.argv = ["verify_orphan_streak.py"]
        try:
            return vos.main()
        except SystemExit as e:
            return int(e.code)
        finally:
            _sys.argv = old_argv

    def test_fail_when_file_missing(self, tmp_path, monkeypatch):
        code = self._run_main(monkeypatch, tmp_path / "missing.jsonl")
        assert code == 1

    def test_fail_when_too_few_entries(self, tmp_path, monkeypatch):
        entries = [{"date": f"2026-01-0{i+1}", "count": 1} for i in range(REQUIRED_STREAK - 1)]
        log = _make_log(tmp_path, entries)
        code = self._run_main(monkeypatch, log)
        assert code == 1

    def test_pass_when_streak_clean(self, tmp_path, monkeypatch):
        entries = [{"date": f"2026-01-{i+1:02d}", "count": THRESHOLD - 1}
                   for i in range(REQUIRED_STREAK)]
        log = _make_log(tmp_path, entries)
        code = self._run_main(monkeypatch, log)
        assert code == 0

    def test_fail_when_any_violation_in_last_n(self, tmp_path, monkeypatch):
        entries = [{"date": f"2026-01-{i+1:02d}", "count": 1} for i in range(REQUIRED_STREAK)]
        entries[-1]["count"] = THRESHOLD  # last entry violates
        log = _make_log(tmp_path, entries)
        code = self._run_main(monkeypatch, log)
        assert code == 1
