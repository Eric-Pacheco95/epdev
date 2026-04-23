"""Tests for tools/scripts/context_status.py analyze() function."""
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

# context_status.py replaces sys.stdout at module level; isolate to protect pytest capture
_orig_stdout = sys.stdout
_fake_buf = io.BytesIO()
sys.stdout = io.TextIOWrapper(_fake_buf)

_spec = importlib.util.spec_from_file_location(
    "_context_status_isolated",
    str(Path(__file__).resolve().parents[1] / "tools" / "scripts" / "context_status.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
sys.stdout = _orig_stdout

analyze = _mod.analyze
TOKENS_PER_TYPE = _mod.TOKENS_PER_TYPE


def _write_jsonl(tmp_dir, entries):
    path = os.path.join(str(tmp_dir), "session.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


def test_analyze_empty_file(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    tokens, compacts, turns = analyze(str(path))
    assert tokens == 0
    assert compacts == 0
    assert turns == 0


def test_analyze_nonexistent_file():
    tokens, compacts, turns = analyze("/nonexistent/path/session.jsonl")
    assert tokens == 0
    assert compacts == 0
    assert turns == 0


def test_analyze_counts_user_turns(tmp_path):
    entries = [
        {"type": "user", "timestamp": "2026-01-01T00:00:00"},
        {"type": "user", "timestamp": "2026-01-01T00:01:00"},
        {"type": "assistant", "timestamp": "2026-01-01T00:02:00"},
    ]
    path = _write_jsonl(tmp_path, entries)
    tokens, compacts, turns = analyze(path)
    assert turns == 2
    assert compacts == 0


def test_analyze_counts_compact_events(tmp_path):
    entries = [
        {"isMeta": True, "timestamp": "2026-01-01T00:00:00"},
        {"isMeta": True, "timestamp": "2026-01-01T00:05:00"},
        {"type": "user", "timestamp": "2026-01-01T00:06:00"},
    ]
    path = _write_jsonl(tmp_path, entries)
    tokens, compacts, turns = analyze(path)
    assert compacts == 2


def test_analyze_only_live_entries_after_compact(tmp_path):
    entries = [
        {"type": "user", "timestamp": "2026-01-01T00:00:00"},
        {"type": "user", "timestamp": "2026-01-01T00:01:00"},
        {"isMeta": True, "timestamp": "2026-01-01T00:02:00"},
        {"type": "user", "timestamp": "2026-01-01T00:03:00"},
    ]
    path = _write_jsonl(tmp_path, entries)
    tokens, compacts, turns = analyze(path)
    assert turns == 1
    assert compacts == 1


def test_analyze_token_weights(tmp_path):
    entries = [
        {"type": "user", "timestamp": "2026-01-01T00:00:00"},
        {"type": "assistant", "timestamp": "2026-01-01T00:01:00"},
        {"type": "system", "timestamp": "2026-01-01T00:02:00"},
    ]
    path = _write_jsonl(tmp_path, entries)
    tokens, _, _ = analyze(path)
    expected = (
        TOKENS_PER_TYPE["user"]
        + TOKENS_PER_TYPE["assistant"]
        + TOKENS_PER_TYPE["system"]
    )
    assert tokens == expected


def test_analyze_skips_malformed_lines(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"type": "user", "timestamp": "2026-01-01T00:00:00"}\n'
        "not valid json\n"
        '{"type": "assistant", "timestamp": "2026-01-01T00:01:00"}\n',
        encoding="utf-8",
    )
    tokens, compacts, turns = analyze(str(path))
    assert turns == 1
    assert compacts == 0


def test_analyze_unknown_type_uses_default(tmp_path):
    entries = [{"type": "unknown_type", "timestamp": "2026-01-01T00:00:00"}]
    path = _write_jsonl(tmp_path, entries)
    tokens, _, _ = analyze(path)
    assert tokens == TOKENS_PER_TYPE["default"]
