"""Tests for tools/scripts/verify_financial_snapshot.py."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_financial_snapshot as vfs


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_missing_file(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 1


def test_snapshot_with_todays_row(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    row = {"ts": _today() + "T10:00:00Z", "total_usd": 5000.0}
    f.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 0


def test_snapshot_no_todays_row(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    row = {"ts": "2020-01-01T10:00:00Z", "total_usd": 1000.0}
    f.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 1


def test_snapshot_skips_invalid_json(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    f.write_text(
        "not json\n"
        + json.dumps({"ts": _today() + "T12:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 0


def test_snapshot_empty_file(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    f.write_text("", encoding="utf-8")
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 1


def test_snapshot_multiple_rows_today_wins(tmp_path):
    f = tmp_path / "snapshot.jsonl"
    rows = [
        {"ts": "2020-06-01T00:00:00Z"},
        {"ts": _today() + "T08:00:00Z"},
        {"ts": "2019-01-01T00:00:00Z"},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    with patch.object(vfs, "SNAP", f):
        assert vfs.main() == 0
