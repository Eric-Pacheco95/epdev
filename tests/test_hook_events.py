"""Tests for hook_events.py -- event record structure and routing logic."""
from __future__ import annotations

import importlib.util
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "hook_events.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("hook_events", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _run_main(payload: dict, tmp_events_dir: Path):
    """Execute hook_events.main() with a faked stdin payload, writing to tmp dir."""
    mod = _load_mod()
    mod.EVENTS_DIR = tmp_events_dir

    stdin_data = StringIO(json.dumps(payload))
    with patch("sys.stdin", stdin_data), patch("sys.exit"):
        mod.main()

    # Return the written JSONL content
    files = list(tmp_events_dir.glob("*.jsonl"))
    assert files, "No event file written"
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


class TestHookEventsRecord:
    def test_post_tool_use_success_record(self, tmp_path):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "session_id": "sess-abc",
            "tool_input": {"command": "ls"},
            "tool_response": {"is_error": False},
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert r["hook"] == "PostToolUse"
        assert r["tool"] == "Bash"
        assert r["success"] is True
        assert r["error"] is None
        assert r["session_id"] == "sess-abc"

    def test_post_tool_use_error_record(self, tmp_path):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "session_id": "sess-err",
            "tool_input": {"command": "bad"},
            "tool_response": {"is_error": True, "content": "command not found"},
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert r["success"] is False
        assert "command not found" in (r["error"] or "")

    def test_pre_tool_use_success_is_null(self, tmp_path):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "session_id": "sess-pre",
            "tool_input": {"file_path": "/some/file.py", "old_string": "a", "new_string": "b"},
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert r["hook"] == "PreToolUse"
        assert r["success"] is None  # intent, no outcome
        assert r["tool"] == "Edit"

    def test_stop_hook_sets_session_tool(self, tmp_path):
        payload = {
            "hook_event_name": "Stop",
            "session_id": "sess-stop",
            "stop_reason": "end_turn",
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert r["tool"] == "_session"
        assert r["hook"] == "Stop"
        assert r["stop_reason"] == "end_turn"
        assert r["success"] is True

    def test_invalid_json_writes_default_record(self, tmp_path):
        mod = _load_mod()
        mod.EVENTS_DIR = tmp_path
        tmp_path.mkdir(parents=True, exist_ok=True)

        bad_stdin = StringIO("not valid json {{{")
        with patch("sys.stdin", bad_stdin), patch("sys.exit"):
            mod.main()

        files = list(tmp_path.glob("*.jsonl"))
        assert files
        records = [json.loads(l) for l in files[0].read_text().splitlines()]
        # Should still write a record with defaults
        assert records[-1]["hook"] == "PostToolUse"

    def test_input_len_computed(self, tmp_path):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "session_id": "s",
            "tool_input": {"command": "echo hello"},
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        expected_len = len(json.dumps({"command": "echo hello"}))
        assert r["input_len"] == expected_len

    def test_error_message_truncated_to_120(self, tmp_path):
        long_error = "x" * 200
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "session_id": "s",
            "tool_input": {},
            "tool_response": {"is_error": True, "content": long_error},
        }
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert len(r["error"]) <= 120

    def test_record_has_ts_field(self, tmp_path):
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Read", "session_id": "s",
                   "tool_input": {}, "tool_response": {"is_error": False}}
        records = _run_main(payload, tmp_path)
        r = records[-1]
        assert "ts" in r
        assert "T" in r["ts"]  # ISO-8601 shape
