"""Tests for tools/scripts/verify_sampler_schema.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_sampler_schema as vsm


def _make_entry(**overrides):
    entry = {
        "ts": "2026-01-01T00:00:00Z",
        "commit_bytes_sum": 1000,
        "pagefile_free_gb": 10.0,
        "ram_free_gb": 8.0,
        "top5_procs": [],
    }
    entry.update(overrides)
    return entry


def test_valid_file(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    entries = [_make_entry() for _ in range(3)]
    f.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 0


def test_missing_file(tmp_path):
    f = tmp_path / "nonexistent.jsonl"
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 1


def test_empty_file(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    f.write_text("", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 1


def test_missing_required_key(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    entry = _make_entry()
    del entry["ram_free_gb"]
    f.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 1


def test_null_required_key(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    f.write_text(json.dumps(_make_entry(pagefile_free_gb=None)) + "\n", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 1


def test_invalid_json_line(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    f.write_text("not json\n", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 1


def test_validates_last_10_only(tmp_path):
    f = tmp_path / "timeseries.jsonl"
    bad = _make_entry()
    del bad["ts"]
    good = _make_entry()
    lines = [json.dumps(bad)] * 5 + [json.dumps(good)] * 10
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with patch.object(vsm, "LOG_FILE", f):
        assert vsm.main() == 0
