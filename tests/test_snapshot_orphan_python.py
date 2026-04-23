"""Tests for tools/scripts/snapshot_orphan_python.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.snapshot_orphan_python as sop


def _fake_process(name):
    proc = MagicMock()
    proc.info = {"name": name}
    return proc


def test_count_python_procs_counts_exact(monkeypatch):
    procs = [
        _fake_process("python.exe"),
        _fake_process("python.exe"),
        _fake_process("node.exe"),
        _fake_process("python"),
    ]
    with patch("tools.scripts.snapshot_orphan_python.psutil.process_iter", return_value=procs):
        assert sop.count_python_procs() == 3


def test_count_skips_none_name(monkeypatch):
    procs = [_fake_process(None), _fake_process("python.exe")]
    with patch("tools.scripts.snapshot_orphan_python.psutil.process_iter", return_value=procs):
        assert sop.count_python_procs() == 1


def test_count_handles_access_denied(monkeypatch):
    import psutil
    bad = MagicMock()
    bad.info = MagicMock(side_effect=psutil.AccessDenied(0))
    good = _fake_process("python.exe")

    def fake_iter(attrs):
        yield bad
        yield good

    with patch("tools.scripts.snapshot_orphan_python.psutil.process_iter", side_effect=fake_iter):
        assert sop.count_python_procs() == 1


def test_main_appends_jsonl(tmp_path):
    log = tmp_path / "logs" / "orphan_python_snapshot.jsonl"
    with patch.object(sop, "LOG_FILE", log), \
         patch.object(sop, "count_python_procs", return_value=7):
        ret = sop.main()

    assert ret == 0
    assert log.exists()
    entry = json.loads(log.read_text(encoding="utf-8").strip())
    assert entry["count"] == 7
    assert "date" in entry


def test_main_appends_multiple_entries(tmp_path):
    log = tmp_path / "logs" / "orphan.jsonl"
    log.parent.mkdir(parents=True)
    with patch.object(sop, "LOG_FILE", log), \
         patch.object(sop, "count_python_procs", return_value=3):
        sop.main()
    with patch.object(sop, "LOG_FILE", log), \
         patch.object(sop, "count_python_procs", return_value=5):
        sop.main()

    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
