"""Tests for vitals_collector.py Phase 4 additions: FR-006/007/008/009."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "vitals_collector.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("vitals_collector", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_ticks(path: Path, ticks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(t) for t in ticks) + "\n",
        encoding="utf-8",
    )


def _tick(ts: datetime, commit_bytes: int, top1_name: str = "python", top1_mb: float = 500.0) -> dict:
    return {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_bytes_sum": commit_bytes,
        "pagefile_free_gb": 50.0,
        "ram_free_gb": 8.0,
        "top5_procs": [
            {"name": top1_name, "pid": 1234, "paged_mb": top1_mb},
            {"name": "claude", "pid": 5678, "paged_mb": 200.0},
        ],
    }


class TestBuildMemorySummary:
    def test_no_data_returns_zero_peak(self):
        mod = _load_mod()
        out = mod.build_memory_summary([], commit_limit_bytes=64 * 1024**3)
        assert out["status"] == "NO_DATA"
        assert out["tick_count"] == 0
        assert out["peak_commit_bytes"] == 0
        assert out["top1_consumer_at_peak"] is None

    def test_peak_picks_highest_commit_and_names_top1(self):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        ticks = [
            _tick(now - timedelta(minutes=30), 10 * 1024**3, top1_name="chrome", top1_mb=300),
            _tick(now - timedelta(minutes=20), 40 * 1024**3, top1_name="claude", top1_mb=2000),
            _tick(now - timedelta(minutes=10), 20 * 1024**3, top1_name="python", top1_mb=500),
        ]
        out = mod.build_memory_summary(ticks, commit_limit_bytes=64 * 1024**3)
        assert out["peak_commit_bytes"] == 40 * 1024**3
        assert out["top1_consumer_at_peak"] == "claude"
        assert out["tick_count"] == 3

    def test_ratio_thresholds_set_status(self):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        limit = 64 * 1024**3
        # Healthy: 50% ratio
        healthy = [_tick(now, int(limit * 0.5))]
        assert mod.build_memory_summary(healthy, limit)["status"] == "HEALTHY"
        # Warn: 75% ratio
        warn = [_tick(now, int(limit * 0.75))]
        assert mod.build_memory_summary(warn, limit)["status"] == "WARN"
        # Critical: 95% ratio
        crit = [_tick(now, int(limit * 0.95))]
        assert mod.build_memory_summary(crit, limit)["status"] == "CRITICAL"

    def test_required_fields_present(self):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        out = mod.build_memory_summary([_tick(now, 10 * 1024**3)], 64 * 1024**3)
        # FR-006: peak, ratio, top-1 consumer, tick completion rate
        for key in (
            "status", "peak_commit_bytes", "peak_commit_gb", "peak_ratio",
            "pagefile_pressure", "top1_consumer_at_peak", "tick_completion_rate",
            "tick_count", "expected_ticks", "commit_limit_bytes",
            "warn_threshold_ratio", "critical_threshold_ratio",
        ):
            assert key in out, f"missing key: {key}"


class TestBuildMemoryDetail:
    def test_hourly_buckets_group_by_hour(self):
        mod = _load_mod()
        base = datetime(2026, 4, 19, 3, 0, 0, tzinfo=timezone.utc)
        ticks = [
            _tick(base + timedelta(minutes=5), 10 * 1024**3),
            _tick(base + timedelta(minutes=45), 20 * 1024**3),
            _tick(base + timedelta(hours=1, minutes=5), 30 * 1024**3),
        ]
        out = mod.build_memory_detail(ticks, commit_limit_bytes=64 * 1024**3)
        hours = [b["hour"] for b in out["hourly_buckets"]]
        assert hours == ["2026-04-19T03:00Z", "2026-04-19T04:00Z"]
        hour3 = out["hourly_buckets"][0]
        assert hour3["tick_count"] == 2
        assert hour3["max_gb"] == 20.0
        assert hour3["avg_gb"] == 15.0

    def test_top5_histogram_ranks_by_occurrence(self):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        ticks = [
            _tick(now - timedelta(minutes=i), 10 * 1024**3, top1_name="claude", top1_mb=1000)
            for i in range(5)
        ]
        ticks.append(_tick(now, 10 * 1024**3, top1_name="node", top1_mb=400))
        out = mod.build_memory_detail(ticks, 64 * 1024**3)
        # claude should outrank node
        names = [h["name"] for h in out["top5_histogram"]]
        assert names[0] == "claude"
        # claude occurrences = 6 ticks (top1 in each) but each tick has 2 procs → claude+other counted
        assert out["top5_histogram"][0]["occurrences"] >= 5

    def test_overcommit_crossings_flagged(self):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        pagefile = 64 * 1024**3
        ticks = [
            _tick(now - timedelta(minutes=10), int(pagefile * 0.5)),  # below
            _tick(now - timedelta(minutes=5), int(pagefile * 1.1)),   # over
        ]
        out = mod.build_memory_detail(ticks, pagefile)
        assert len(out["overcommit_crossings"]) == 1
        assert out["overcommit_crossings"][0]["ratio"] >= 1.0


class TestPeakRatioDenominator:
    def test_21gb_peak_against_44gb_commit_limit_is_not_critical(self):
        """Denominator fix: 21 GB peak / 44 GB commit limit ≈ 0.48, not >1.0."""
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        peak = 21 * 1024**3
        limit = 44 * 1024**3
        out = mod.build_memory_summary([_tick(now, peak)], commit_limit_bytes=limit)
        assert 0.47 < out["peak_ratio"] < 0.49, f"peak_ratio={out['peak_ratio']}"
        assert out["status"] == "HEALTHY"

    def test_pagefile_pressure_computed_from_pagefile_bytes(self):
        """pagefile_pressure uses swap-only denominator, not commit limit."""
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        pf_total_bytes = int(12.5 * 1024**3)
        pf_free_gb = 12.38
        tick = {
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit_bytes_sum": int(21 * 1024**3),
            "pagefile_free_gb": pf_free_gb,
            "ram_free_gb": 6.28,
            "top5_procs": [],
        }
        out = mod.build_memory_summary(
            [tick],
            commit_limit_bytes=int(44.5 * 1024**3),
            pagefile_bytes=pf_total_bytes,
        )
        # 12.5 - 12.38 = 0.12 GB used → pressure ≈ 0.0096
        assert out["pagefile_pressure"] < 0.02, f"pressure={out['pagefile_pressure']}"
        assert out["status"] == "HEALTHY"


class TestContextFileCounts:
    def test_returns_top_n_and_filters_md(self, tmp_path):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        events = []
        # 25 distinct .md paths, each read a variable number of times
        for i in range(25):
            path = f"C:/repo/file_{i:02d}.md"
            repeats = 25 - i  # first path read 25x, last read 1x
            for j in range(repeats):
                events.append({
                    "ts": (now - timedelta(hours=j % 24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "hook": "PostToolUse",
                    "tool": "Read",
                    "file_path": path,
                })
        # Add a non-.md read that must be excluded
        events.append({
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": "PostToolUse",
            "tool": "Read",
            "file_path": "C:/repo/config.yaml",
        })
        # Add a Bash event with command — must be ignored entirely
        events.append({
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": "PostToolUse",
            "tool": "Bash",
            "file_path": "C:/repo/bogus.md",
        })
        (tmp_path / "2026-04-19.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events), encoding="utf-8"
        )
        out = mod.load_context_file_counts(tmp_path, days=7, top_n=20, now=now)
        assert len(out) == 20, f"expected 20 entries, got {len(out)}"
        # Descending order by count
        counts = [row["count"] for row in out]
        assert counts == sorted(counts, reverse=True)
        # No .yaml
        assert all(row["file_path"].endswith(".md") for row in out)

    def test_filters_outside_time_window(self, tmp_path):
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        events = [
            {"ts": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "hook": "PostToolUse", "tool": "Read", "file_path": "C:/repo/old.md"},
            {"ts": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "hook": "PostToolUse", "tool": "Read", "file_path": "C:/repo/recent.md"},
        ]
        (tmp_path / "evt.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events), encoding="utf-8"
        )
        out = mod.load_context_file_counts(tmp_path, days=7, top_n=20, now=now)
        assert len(out) == 1
        assert out[0]["file_path"] == "C:/repo/recent.md"

    def test_missing_dir_returns_empty(self, tmp_path):
        mod = _load_mod()
        missing = tmp_path / "does_not_exist"
        assert mod.load_context_file_counts(missing, days=7, top_n=20) == []


class TestCliStubs:
    @pytest.mark.parametrize("flag", ["--token-costs", "--reaper-log"])
    def test_stub_exact_message_and_exit_zero(self, flag):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), flag],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        assert r.returncode == 0, f"{flag} exit={r.returncode}"
        assert re.match(
            r"^not yet available — blocked on \[dependency\]$",
            r.stdout.strip(),
        ), f"{flag} stdout mismatch: {r.stdout!r}"


class TestCliMemory:
    def test_memory_flag_emits_summary_and_detail(self, tmp_path, monkeypatch):
        """--memory fast path returns hourly_buckets + top5_histogram + overcommit_crossings."""
        mod = _load_mod()
        now = datetime.now(timezone.utc)
        tick_path = tmp_path / "mem.jsonl"
        ticks = [_tick(now - timedelta(minutes=i * 5), (i + 1) * 1024**3) for i in range(6)]
        _write_ticks(tick_path, ticks)
        monkeypatch.setattr(mod, "MEMORY_TIMESERIES", tick_path)
        # Call the pure function path (subprocess would re-import and miss monkeypatch)
        loaded = mod.load_memory_ticks(tick_path, since_hours=24)
        assert len(loaded) == 6
        detail = mod.build_memory_detail(loaded, 64 * 1024**3)
        assert "hourly_buckets" in detail
        assert "top5_histogram" in detail
        assert "overcommit_crossings" in detail
        assert "summary" in detail


class TestDefaultOutputHasMemory:
    def test_default_run_has_top_level_memory_key(self):
        """FR-006 verify: default `--pretty` output contains top-level `memory` with required sub-fields."""
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--pretty"],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=90,
        )
        assert r.returncode == 0, f"collector failed: {r.stderr[-500:]}"
        data = json.loads(r.stdout)
        assert "memory" in data
        mem = data["memory"]
        for key in ("status", "peak_commit_bytes", "peak_ratio", "top1_consumer_at_peak", "tick_completion_rate"):
            assert key in mem, f"missing {key} in memory block"
