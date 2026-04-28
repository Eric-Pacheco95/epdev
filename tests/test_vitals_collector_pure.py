"""Tests for vitals_collector.py pure helper functions."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
from datetime import datetime, timezone, timedelta

from tools.scripts.vitals_collector import (
    compute_trend_averages,
    _task_scheduler_result_label,
    _summarize_overnight_log,
    _local_hour_from_utc_iso,
    _parse_ts,
    load_memory_ticks,
    build_memory_summary,
)


class TestComputeTrendAverages:
    def _entry(self, **metrics):
        return {"metrics": {k: {"value": v} for k, v in metrics.items()}}

    def test_empty_returns_empty(self):
        assert compute_trend_averages([]) == {}

    def test_single_entry_avg_equals_value(self):
        data = [self._entry(isc_ratio=0.8)]
        result = compute_trend_averages(data)
        assert "isc_ratio" in result
        assert result["isc_ratio"]["avg"] == 0.8
        assert result["isc_ratio"]["min"] == 0.8
        assert result["isc_ratio"]["max"] == 0.8
        assert result["isc_ratio"]["samples"] == 1

    def test_multiple_entries_avg(self):
        data = [self._entry(isc_ratio=0.5), self._entry(isc_ratio=1.0)]
        result = compute_trend_averages(data)
        assert result["isc_ratio"]["avg"] == 0.75
        assert result["isc_ratio"]["min"] == 0.5
        assert result["isc_ratio"]["max"] == 1.0
        assert result["isc_ratio"]["samples"] == 2

    def test_missing_metric_not_included(self):
        data = [self._entry(signal_velocity=5)]
        result = compute_trend_averages(data)
        assert "isc_ratio" not in result
        assert "signal_velocity" in result

    def test_none_value_skipped(self):
        data = [
            {"metrics": {"isc_ratio": {"value": None}}},
            self._entry(isc_ratio=0.6),
        ]
        result = compute_trend_averages(data)
        assert result["isc_ratio"]["samples"] == 1

    def test_non_dict_metric_skipped(self):
        data = [{"metrics": {"isc_ratio": "not-a-dict"}}]
        result = compute_trend_averages(data)
        assert "isc_ratio" not in result


class TestTaskSchedulerResultLabel:
    def test_zero_is_success(self):
        assert _task_scheduler_result_label(0) == "SUCCESS"

    def test_task_ready(self):
        assert _task_scheduler_result_label(0x00041300) == "SCHED_S_TASK_READY"

    def test_task_running(self):
        assert _task_scheduler_result_label(0x00041301) == "SCHED_S_TASK_RUNNING"

    def test_task_disabled(self):
        assert _task_scheduler_result_label(0x00041302) == "SCHED_S_TASK_DISABLED"

    def test_task_has_not_run(self):
        assert _task_scheduler_result_label(0x00041303) == "SCHED_S_TASK_HAS_NOT_RUN"

    def test_unknown_nonzero_returns_hresult(self):
        result = _task_scheduler_result_label(0xDEADBEEF)
        assert result.startswith("HRESULT_0x")
        assert "DEADBEEF" in result.upper()

    def test_negative_one_wraps_to_hresult(self):
        result = _task_scheduler_result_label(-1)
        assert "HRESULT_0x" in result or result == "SUCCESS"


class TestSummarizeOvernightLog:
    def test_empty_content_returns_skipped(self):
        status, code, hint = _summarize_overnight_log("")
        assert status == "skipped"
        assert code is None
        assert hint == ""

    def test_whitespace_only_returns_skipped(self):
        status, code, hint = _summarize_overnight_log("   \n   ")
        assert status == "skipped"

    def test_exit_code_zero_returns_ran(self):
        content = "Script complete (exit code: 0)"
        status, code, hint = _summarize_overnight_log(content)
        assert status == "ran"
        assert code == 0

    def test_exit_code_nonzero_returns_failed(self):
        content = "Script complete (exit code: 1)"
        status, code, hint = _summarize_overnight_log(content)
        assert status == "failed"
        assert code == 1

    def test_traceback_in_content_returns_failed(self):
        content = "doing work\nTraceback (most recent call last):\nsome error"
        status, code, hint = _summarize_overnight_log(content)
        assert status == "failed"

    def test_error_prefix_detected(self):
        content = "running tasks\nError: something went wrong\ndone"
        status, code, hint = _summarize_overnight_log(content)
        assert status == "failed"

    def test_normal_log_without_errors_returns_ran(self):
        content = "starting up\nprocessing items\ncompleted successfully"
        status, code, hint = _summarize_overnight_log(content)
        assert status == "ran"

    def test_hint_is_ascii_safe(self):
        content = "Error: unicode fault — em dash"
        _, _, hint = _summarize_overnight_log(content)
        hint.encode("ascii")


class TestLocalHourFromUtcIso:
    def test_none_returns_none(self):
        assert _local_hour_from_utc_iso(None) is None

    def test_empty_string_returns_none(self):
        assert _local_hour_from_utc_iso("") is None

    def test_non_string_returns_none(self):
        assert _local_hour_from_utc_iso(42) is None

    def test_valid_iso_returns_int(self):
        result = _local_hour_from_utc_iso("2026-04-28T12:00:00Z")
        assert isinstance(result, int)
        assert 0 <= result <= 23

    def test_invalid_iso_returns_none(self):
        assert _local_hour_from_utc_iso("not-a-date") is None


class TestParseTs:
    def test_valid_z_timestamp(self):
        result = _parse_ts("2026-04-28T12:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.hour == 12

    def test_valid_offset_timestamp(self):
        result = _parse_ts("2026-04-28T12:00:00+00:00")
        assert result is not None

    def test_invalid_returns_none(self):
        assert _parse_ts("not-a-date") is None

    def test_empty_returns_none(self):
        assert _parse_ts("") is None


class TestLoadMemoryTicks:
    def _now(self):
        return datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_memory_ticks(tmp_path / "missing.jsonl", 24, self._now())
        assert result == []

    def test_within_window_included(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        tick_ts = (self._now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write_text(json.dumps({"ts": tick_ts, "commit_bytes_sum": 1000}) + "\n", encoding="utf-8")
        result = load_memory_ticks(f, 24, self._now())
        assert len(result) == 1

    def test_outside_window_excluded(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        tick_ts = (self._now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write_text(json.dumps({"ts": tick_ts, "commit_bytes_sum": 1000}) + "\n", encoding="utf-8")
        result = load_memory_ticks(f, 24, self._now())
        assert result == []

    def test_bad_json_lines_skipped(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        tick_ts = (self._now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write_text(
            "not json\n" + json.dumps({"ts": tick_ts, "commit_bytes_sum": 500}) + "\n",
            encoding="utf-8",
        )
        result = load_memory_ticks(f, 24, self._now())
        assert len(result) == 1


class TestBuildMemorySummary:
    def _tick(self, commit_bytes, top5=None):
        return {
            "ts": "2026-04-28T10:00:00Z",
            "commit_bytes_sum": commit_bytes,
            "top5_procs": top5 or [],
        }

    def test_empty_ticks_returns_no_data(self):
        result = build_memory_summary([], 32 * (1024 ** 3))
        assert result["status"] == "NO_DATA"
        assert result["peak_commit_bytes"] == 0

    def test_healthy_status_at_low_ratio(self):
        pagefile = 32 * (1024 ** 3)
        ticks = [self._tick(1 * (1024 ** 3))]  # 1/32 = ~3% ratio
        result = build_memory_summary(ticks, pagefile)
        assert result["status"] == "HEALTHY"

    def test_peak_bytes_captured(self):
        pagefile = 32 * (1024 ** 3)
        ticks = [self._tick(2 * (1024 ** 3)), self._tick(5 * (1024 ** 3))]
        result = build_memory_summary(ticks, pagefile)
        assert result["peak_commit_bytes"] == 5 * (1024 ** 3)

    def test_top1_consumer_extracted(self):
        pagefile = 32 * (1024 ** 3)
        ticks = [self._tick(1 * (1024 ** 3), top5=[{"name": "claude.exe", "paged_mb": 500}])]
        result = build_memory_summary(ticks, pagefile)
        assert result["top1_consumer_at_peak"] == "claude.exe"

    def test_tick_count_reported(self):
        pagefile = 32 * (1024 ** 3)
        ticks = [self._tick(1 * (1024 ** 3))] * 5
        result = build_memory_summary(ticks, pagefile)
        assert result["tick_count"] == 5
