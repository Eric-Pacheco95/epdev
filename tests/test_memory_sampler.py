"""Tests for tools/scripts/memory_sampler.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.memory_sampler as ms


def _make_swap(free: int = 4 * 1024 ** 3) -> MagicMock:
    m = MagicMock()
    m.free = free
    return m


def _make_vm(available: int = 8 * 1024 ** 3) -> MagicMock:
    m = MagicMock()
    m.available = available
    return m


def _make_ps_data(sum_val: int = 1_000_000_000, top5=None) -> dict:
    if top5 is None:
        top5 = [
            {"name": "python", "pid": 1234, "paged_mb": 200.5},
            {"name": "chrome", "pid": 5678, "paged_mb": 150.0},
        ]
    return {"sum": sum_val, "top5": top5}


class TestCollectFromPowershell:
    def test_returns_parsed_json(self):
        ps_data = {"sum": 500000000, "top5": []}
        run_result = MagicMock()
        run_result.stdout = json.dumps(ps_data)
        with patch("subprocess.run", return_value=run_result):
            result = ms.collect_from_powershell()
        assert result["sum"] == 500000000

    def test_empty_stdout_raises(self):
        run_result = MagicMock()
        run_result.stdout = "   "
        with patch("subprocess.run", return_value=run_result):
            try:
                ms.collect_from_powershell()
                assert False, "expected RuntimeError"
            except RuntimeError:
                pass


class TestBuildEntry:
    def _run(self, ps_data=None, swap_free=4 * 1024 ** 3, vm_available=8 * 1024 ** 3):
        if ps_data is None:
            ps_data = _make_ps_data()
        with patch.object(ms, "collect_from_powershell", return_value=ps_data), \
             patch("psutil.swap_memory", return_value=_make_swap(swap_free)), \
             patch("psutil.virtual_memory", return_value=_make_vm(vm_available)):
            return ms.build_entry()

    def test_has_ts_field(self):
        entry = self._run()
        assert "ts" in entry
        assert entry["ts"].endswith("Z")

    def test_ts_format(self):
        import re
        entry = self._run()
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", entry["ts"])

    def test_commit_bytes_sum_is_int(self):
        entry = self._run(ps_data=_make_ps_data(sum_val=123456789))
        assert entry["commit_bytes_sum"] == 123456789
        assert isinstance(entry["commit_bytes_sum"], int)

    def test_pagefile_free_gb_rounded(self):
        entry = self._run(swap_free=4 * 1024 ** 3)
        assert entry["pagefile_free_gb"] == round(4, 3)

    def test_ram_free_gb_rounded(self):
        entry = self._run(vm_available=16 * 1024 ** 3)
        assert entry["ram_free_gb"] == round(16, 3)

    def test_top5_procs_structure(self):
        entry = self._run()
        assert isinstance(entry["top5_procs"], list)
        for proc in entry["top5_procs"]:
            assert "name" in proc
            assert "pid" in proc
            assert "paged_mb" in proc

    def test_top5_single_dict_wrapped_in_list(self):
        ps_data = {"sum": 100, "top5": {"name": "only", "pid": 1, "paged_mb": 10.0}}
        entry = self._run(ps_data=ps_data)
        assert isinstance(entry["top5_procs"], list)
        assert len(entry["top5_procs"]) == 1

    def test_top5_empty_list(self):
        entry = self._run(ps_data=_make_ps_data(top5=[]))
        assert entry["top5_procs"] == []

    def test_top5_none_treated_as_empty(self):
        entry = self._run(ps_data={"sum": 1000, "top5": None})
        assert entry["top5_procs"] == []

    def test_proc_fields_typed(self):
        top5 = [{"name": "notepad", "pid": "99", "paged_mb": "55.5"}]
        entry = self._run(ps_data=_make_ps_data(top5=top5))
        proc = entry["top5_procs"][0]
        assert isinstance(proc["name"], str)
        assert isinstance(proc["pid"], int)
        assert isinstance(proc["paged_mb"], float)


class TestMain:
    def test_main_returns_0(self, tmp_path):
        ps_data = _make_ps_data()
        with patch.object(ms, "collect_from_powershell", return_value=ps_data), \
             patch("psutil.swap_memory", return_value=_make_swap()), \
             patch("psutil.virtual_memory", return_value=_make_vm()), \
             patch.object(ms, "LOG_FILE", tmp_path / "memory_timeseries.jsonl"):
            rc = ms.main()
        assert rc == 0

    def test_main_writes_jsonl(self, tmp_path):
        ps_data = _make_ps_data(sum_val=999)
        log_file = tmp_path / "memory_timeseries.jsonl"
        with patch.object(ms, "collect_from_powershell", return_value=ps_data), \
             patch("psutil.swap_memory", return_value=_make_swap()), \
             patch("psutil.virtual_memory", return_value=_make_vm()), \
             patch.object(ms, "LOG_FILE", log_file):
            ms.main()
        assert log_file.exists()
        entry = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert entry["commit_bytes_sum"] == 999

    def test_main_appends_multiple_lines(self, tmp_path):
        ps_data = _make_ps_data()
        log_file = tmp_path / "memory_timeseries.jsonl"
        with patch.object(ms, "collect_from_powershell", return_value=ps_data), \
             patch("psutil.swap_memory", return_value=_make_swap()), \
             patch("psutil.virtual_memory", return_value=_make_vm()), \
             patch.object(ms, "LOG_FILE", log_file):
            ms.main()
            ms.main()
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
