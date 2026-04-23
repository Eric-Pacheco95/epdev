"""Tests for tools/scripts/hook_tavily_usage.py."""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.hook_tavily_usage as htu


def _run(stdin_data, log_path=None):
    """Run main() with given stdin data; return SystemExit code."""
    fake_stdin = io.StringIO(json.dumps(stdin_data))
    patches = [patch.object(sys, "stdin", fake_stdin)]
    if log_path is not None:
        patches.append(patch.object(htu, "USAGE_LOG", log_path))

    with patches[0]:
        if log_path is not None:
            with patches[1]:
                with pytest.raises(SystemExit) as exc:
                    htu.main()
        else:
            with pytest.raises(SystemExit) as exc:
                htu.main()
    return exc.value.code


def test_invalid_json_exits_0():
    fake_stdin = io.StringIO("not json")
    with patch.object(sys, "stdin", fake_stdin):
        with pytest.raises(SystemExit) as exc:
            htu.main()
    assert exc.value.code == 0


def test_non_tavily_tool_exits_0_without_write(tmp_path):
    log = tmp_path / "tavily_usage.jsonl"
    data = {"tool_name": "mcp__brave__search", "session_id": "abc"}
    code = _run(data, log)
    assert code == 0
    assert not log.exists()


def test_tavily_tool_writes_record(tmp_path):
    log = tmp_path / "tavily_usage.jsonl"
    data = {"tool_name": "mcp__tavily__tavily_search", "session_id": "sess1", "duration_ms": 500}
    code = _run(data, log)
    assert code == 0
    assert log.exists()
    record = json.loads(log.read_text(encoding="utf-8").strip())
    assert record["tool"] == "mcp__tavily__tavily_search"
    assert record["session_id"] == "sess1"
    assert record["duration_ms"] == 500


def test_duration_from_fallback_key(tmp_path):
    log = tmp_path / "tavily_usage.jsonl"
    data = {"tool_name": "mcp__tavily__tavily_search", "duration": 300}
    _run(data, log)
    record = json.loads(log.read_text(encoding="utf-8").strip())
    assert record["duration_ms"] == 300


def test_missing_duration_records_none(tmp_path):
    log = tmp_path / "tavily_usage.jsonl"
    data = {"tool_name": "mcp__tavily__tavily_search"}
    _run(data, log)
    record = json.loads(log.read_text(encoding="utf-8").strip())
    assert record["duration_ms"] is None
