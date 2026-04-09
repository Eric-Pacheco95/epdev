"""Tests for hook_notification.py -- notification routing logic."""
from __future__ import annotations

import importlib.util
import json
import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "hook_notification.py"


def _load():
    spec = importlib.util.spec_from_file_location("hook_notification", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Patch ntfy push before module execution so no real network calls
    with patch.dict("sys.modules", {"tools.scripts.ntfy_notify": MagicMock()}):
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestPromptElapsedSeconds:
    def test_returns_zero_when_file_missing(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "_PROMPT_TS_FILE", tmp_path / "missing.json")
        result = mod._prompt_elapsed_seconds()
        assert result == 0.0

    def test_returns_zero_on_invalid_json(self, tmp_path, monkeypatch):
        bad = tmp_path / "prompt_ts.json"
        bad.write_text("not json")
        mod = _load()
        monkeypatch.setattr(mod, "_PROMPT_TS_FILE", bad)
        result = mod._prompt_elapsed_seconds()
        assert result == 0.0

    def test_returns_elapsed_from_timestamp(self, tmp_path, monkeypatch):
        ts_file = tmp_path / "prompt_ts.json"
        past = time.time() - 600  # 10 minutes ago
        ts_file.write_text(json.dumps({"ts": past}))
        mod = _load()
        monkeypatch.setattr(mod, "_PROMPT_TS_FILE", ts_file)
        elapsed = mod._prompt_elapsed_seconds()
        assert 590 < elapsed < 620

    def test_returns_zero_on_missing_ts_key(self, tmp_path, monkeypatch):
        ts_file = tmp_path / "prompt_ts.json"
        ts_file.write_text(json.dumps({"other": 123}))
        mod = _load()
        monkeypatch.setattr(mod, "_PROMPT_TS_FILE", ts_file)
        result = mod._prompt_elapsed_seconds()
        assert result == 0.0


class TestHookNotificationMain:
    def _run(self, payload: dict, elapsed: float = 400):
        mod = _load()
        push_mock = MagicMock(return_value=True)
        mod.push = push_mock
        monkeypatch_elapsed = lambda: elapsed
        mod._prompt_elapsed_seconds = monkeypatch_elapsed

        stdin_data = StringIO(json.dumps(payload))
        with patch("sys.stdin", stdin_data), patch("sys.exit", side_effect=SystemExit):
            try:
                mod.main()
            except SystemExit:
                pass

        return push_mock

    def test_permission_request_always_pushes(self):
        push_mock = self._run(
            {"notification_type": "permission_request", "tool_name": "Bash", "message": "approve?"},
            elapsed=10,  # very short elapsed, but permission_request ignores it
        )
        push_mock.assert_called_once()
        call_kwargs = push_mock.call_args
        assert call_kwargs[1].get("priority") == "high" or "high" in str(call_kwargs)

    def test_idle_notification_skipped_when_under_threshold(self):
        push_mock = self._run(
            {"notification_type": "idle", "message": "waiting"},
            elapsed=30,  # under 300s threshold
        )
        push_mock.assert_not_called()

    def test_idle_notification_sends_when_over_threshold(self):
        push_mock = self._run(
            {"notification_type": "idle", "message": "waiting"},
            elapsed=400,
        )
        push_mock.assert_called_once()

    def test_permission_request_title_includes_tool_name(self):
        push_mock = self._run(
            {"notification_type": "permission_request", "tool_name": "Edit", "message": "ok?"},
            elapsed=10,
        )
        call_args = push_mock.call_args[0]
        assert "Edit" in call_args[0]  # title

    def test_body_truncated_to_200(self):
        long_msg = "x" * 300
        push_mock = self._run(
            {"notification_type": "permission_request", "tool_name": "Bash", "message": long_msg},
            elapsed=10,
        )
        call_args = push_mock.call_args[0]
        body = call_args[1]
        assert len(body) <= 200
