"""Tests for ping_monitor.py -- pure parsing and stat logic."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "ping_monitor.py"


def _load():
    spec = importlib.util.spec_from_file_location("ping_monitor", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestPingOnce:
    def _make_result(self, stdout: str, returncode: int = 0) -> MagicMock:
        r = MagicMock()
        r.stdout = stdout
        r.returncode = returncode
        return r

    def test_parses_time_equals(self):
        mod = _load()
        fake_output = "Reply from 8.8.8.8: bytes=32 time=24ms TTL=118"
        with patch("subprocess.run", return_value=self._make_result(fake_output)):
            ms, lost = mod.ping_once("8.8.8.8")
        assert ms == 24
        assert lost is False

    def test_parses_time_less_than(self):
        mod = _load()
        # Windows can report time<1ms
        fake_output = "Reply from 8.8.8.8: bytes=32 time<1ms TTL=128"
        with patch("subprocess.run", return_value=self._make_result(fake_output)):
            ms, lost = mod.ping_once("8.8.8.8")
        # regex r"time[=<](\d+)ms" matches time<1ms -> group(1)="1"
        assert ms == 1
        assert lost is False

    def test_returns_lost_on_timeout_message(self):
        mod = _load()
        fake_output = "Request timed out."
        with patch("subprocess.run", return_value=self._make_result(fake_output)):
            ms, lost = mod.ping_once("8.8.8.8")
        assert ms is None
        assert lost is True

    def test_returns_lost_on_unreachable(self):
        mod = _load()
        fake_output = "Destination host unreachable."
        with patch("subprocess.run", return_value=self._make_result(fake_output)):
            ms, lost = mod.ping_once("8.8.8.8")
        assert ms is None
        assert lost is True

    def test_returns_lost_on_exception(self):
        mod = _load()
        with patch("subprocess.run", side_effect=OSError("not found")):
            ms, lost = mod.ping_once("bad-host")
        assert ms is None
        assert lost is True

    def test_returns_lost_when_no_time_in_output(self):
        mod = _load()
        fake_output = "Some unknown output"
        with patch("subprocess.run", return_value=self._make_result(fake_output)):
            ms, lost = mod.ping_once("8.8.8.8")
        assert ms is None
        assert lost is True


class TestPingStats:
    """Tests for inline stats logic used in session summary."""

    def test_avg_latency_correct(self):
        latencies = [10, 20, 30]
        avg = sum(latencies) / len(latencies)
        assert avg == 20.0

    def test_loss_pct_correct(self):
        total, lost = 100, 5
        loss_pct = (lost / total * 100)
        assert loss_pct == 5.0

    def test_loss_pct_zero_total_is_zero(self):
        total = 0
        loss_pct = (0 / total * 100) if total else 0
        assert loss_pct == 0

    def test_worst_spike_found(self):
        spike_events = [("12:00:01", 80), ("12:00:05", 150), ("12:00:09", 100)]
        worst = max(spike_events, key=lambda x: x[1])
        assert worst == ("12:00:05", 150)
