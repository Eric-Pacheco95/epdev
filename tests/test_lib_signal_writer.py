"""Tests for tools/scripts/lib/signal_writer.py append_signal()."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.lib.signal_writer import append_signal, REPO_ROOT


def test_creates_parent_dirs(tmp_path):
    target = tmp_path / "deep" / "nested" / "signals.jsonl"
    append_signal(target, {"ts": "2026-01-01T00:00:00Z", "key": "value"})
    assert target.exists()


def test_appends_valid_json(tmp_path):
    target = tmp_path / "signals.jsonl"
    record = {"ts": "2026-01-01T00:00:00Z", "query": "hello world", "score": 0.9}
    append_signal(target, record)
    line = target.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["query"] == "hello world"
    assert abs(parsed["score"] - 0.9) < 1e-6


def test_multiple_appends_produce_multiple_lines(tmp_path):
    target = tmp_path / "signals.jsonl"
    for i in range(3):
        append_signal(target, {"i": i})
    lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    for i, ln in enumerate(lines):
        assert json.loads(ln)["i"] == i


def test_output_is_ascii_only(tmp_path):
    target = tmp_path / "signals.jsonl"
    record = {"key": "ascii safe"}
    append_signal(target, record)
    content = target.read_bytes()
    content.decode("ascii")  # raises if non-ASCII


def test_absolute_path_used_directly(tmp_path):
    target = tmp_path / "abs.jsonl"
    append_signal(str(target), {"x": 1})
    assert target.exists()
    parsed = json.loads(target.read_text().strip())
    assert parsed["x"] == 1
