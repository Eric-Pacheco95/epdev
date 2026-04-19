"""Unit tests for verify_sampler_coverage.py (FR-004 / Phase 2 ISC #1 and #3).

ISC #1: unit test feeds synthetic JSONL with a 25-min night gap;
        verifier exits 1 and names the gap window.
ISC #3: pressure_gaps[] key is populated from the sampling window;
        empty list on a healthy system is valid.

Night window (EDT = UTC-4): local 22:00-08:00 = UTC 02:00-12:00.
Test uses UTC 06:00-07:00 (local 02:00-03:00 EDT) — unambiguously night.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.scripts.verify_sampler_coverage import (
    classify_pressure_gaps,
    expected_cadence,
    expected_ticks_in_range,
    find_gaps,
    is_night_local,
    load_ticks,
    main,
    NIGHT_CADENCE,
    DAY_CADENCE,
    parse_window,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NIGHT_UTC_HOUR = 6  # UTC 06:00 = EDT 02:00 (unambiguously night)
DAY_UTC_HOUR = 14   # UTC 14:00 = EDT 10:00 (unambiguously day)

PAGEFILE_64GB = 64 * (1024 ** 3)


def _ts(utc_hour: int, utc_minute: int = 0, date: str = "2026-04-19") -> str:
    return f"{date}T{utc_hour:02d}:{utc_minute:02d}:00Z"


def _tick(ts: str, commit_bytes: int = 10_000_000_000) -> dict:
    return {
        "ts": ts,
        "commit_bytes_sum": commit_bytes,
        "pagefile_free_gb": 50.0,
        "ram_free_gb": 15.0,
        "top5_procs": [],
    }


def _write_jsonl(path: Path, ticks: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for t in ticks:
            f.write(json.dumps(t) + "\n")


def _attach_ts(ticks: list[dict]) -> list[dict]:
    """Add _ts field (datetime) as load_ticks() does."""
    for t in ticks:
        t["_ts"] = datetime.fromisoformat(t["ts"].replace("Z", "+00:00"))
    return ticks


# ---------------------------------------------------------------------------
# parse_window
# ---------------------------------------------------------------------------

def test_parse_window_hours():
    assert parse_window("24h") == timedelta(hours=24)
    assert parse_window("48h") == timedelta(hours=48)


def test_parse_window_days():
    assert parse_window("7d") == timedelta(days=7)


def test_parse_window_invalid():
    with pytest.raises(ValueError):
        parse_window("30m")


# ---------------------------------------------------------------------------
# is_night_local / expected_cadence
# ---------------------------------------------------------------------------

def test_is_night_local_midnight():
    # UTC 06:00 = EDT 02:00 — night
    dt = datetime(2026, 4, 19, NIGHT_UTC_HOUR, 0, tzinfo=timezone.utc).astimezone()
    assert is_night_local(dt) is True


def test_is_night_local_midday():
    # UTC 14:00 = EDT 10:00 — day
    dt = datetime(2026, 4, 19, DAY_UTC_HOUR, 0, tzinfo=timezone.utc).astimezone()
    assert is_night_local(dt) is False


def test_expected_cadence_night():
    dt = datetime(2026, 4, 19, NIGHT_UTC_HOUR, 0, tzinfo=timezone.utc).astimezone()
    assert expected_cadence(dt) == NIGHT_CADENCE  # 2 min


def test_expected_cadence_day():
    dt = datetime(2026, 4, 19, DAY_UTC_HOUR, 0, tzinfo=timezone.utc).astimezone()
    assert expected_cadence(dt) == DAY_CADENCE  # 10 min


# ---------------------------------------------------------------------------
# find_gaps — ISC #1 core test
# ---------------------------------------------------------------------------

def test_find_gaps_no_gaps_night():
    """Normal night: 2-min ticks → no gaps."""
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0)),
        _tick(_ts(NIGHT_UTC_HOUR, 2)),
        _tick(_ts(NIGHT_UTC_HOUR, 4)),
    ])
    assert find_gaps(ticks) == []


def test_find_gaps_25min_night_gap_exits_fail():
    """ISC #1: 25-min gap during night hours → 1 gap detected.

    Night max allowed = 2 × 2 min = 4 min. A 25-min gap is clearly a fail.
    UTC 06:00 → 06:25 = 25 min (local 02:00 EDT, unambiguously night).
    """
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0)),
        _tick(_ts(NIGHT_UTC_HOUR, 25)),  # 25-min gap — exceeds 4-min threshold
        _tick(_ts(NIGHT_UTC_HOUR, 27)),
    ])
    gaps = find_gaps(ticks)
    assert len(gaps) == 1
    g = gaps[0]
    assert g.start_ts == _ts(NIGHT_UTC_HOUR, 0)
    assert g.end_ts == _ts(NIGHT_UTC_HOUR, 25)
    assert g.gap_minutes == 25.0
    assert g.max_allowed_minutes == 4.0  # 2 × 2 min = 4 min


def test_find_gaps_names_gap_window():
    """ISC #1: verifier names the gap window (start_ts and end_ts present)."""
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0)),
        _tick(_ts(NIGHT_UTC_HOUR, 25)),
    ])
    gaps = find_gaps(ticks)
    assert len(gaps) == 1
    assert "start_ts" in gaps[0]._asdict()
    assert "end_ts" in gaps[0]._asdict()
    assert gaps[0].start_ts != ""
    assert gaps[0].end_ts != ""


def test_find_gaps_day_normal_10min():
    """Normal day: 10-min ticks → no gaps."""
    ticks = _attach_ts([
        _tick(_ts(DAY_UTC_HOUR, 0)),
        _tick(_ts(DAY_UTC_HOUR, 10)),
        _tick(_ts(DAY_UTC_HOUR, 20)),
    ])
    assert find_gaps(ticks) == []


def test_find_gaps_day_21min_gap():
    """21-min gap during day hours → 1 gap (threshold = 20 min)."""
    ticks = _attach_ts([
        _tick(_ts(DAY_UTC_HOUR, 0)),
        _tick(_ts(DAY_UTC_HOUR, 21)),  # 21-min gap > 20-min threshold
    ])
    gaps = find_gaps(ticks)
    assert len(gaps) == 1
    assert gaps[0].max_allowed_minutes == 20.0  # 2 × 10 min = 20 min


def test_find_gaps_day_exactly_20min_no_gap():
    """Exactly 20-min day gap is NOT a gap (not strictly greater than threshold)."""
    ticks = _attach_ts([
        _tick(_ts(DAY_UTC_HOUR, 0)),
        _tick(_ts(DAY_UTC_HOUR, 20)),  # 20-min gap = threshold → no gap
    ])
    assert find_gaps(ticks) == []


def test_find_gaps_single_tick():
    """Single tick → no pairs → no gaps."""
    ticks = _attach_ts([_tick(_ts(NIGHT_UTC_HOUR, 0))])
    assert find_gaps(ticks) == []


# ---------------------------------------------------------------------------
# classify_pressure_gaps — ISC #3
# ---------------------------------------------------------------------------

def test_pressure_gaps_empty_when_no_gaps():
    """ISC #3: no gaps → pressure_gaps[] is empty (valid, healthy system)."""
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0), commit_bytes=10_000_000_000),
        _tick(_ts(NIGHT_UTC_HOUR, 2), commit_bytes=10_000_000_000),
    ])
    gaps = find_gaps(ticks)
    result = classify_pressure_gaps(gaps, ticks, PAGEFILE_64GB)
    assert result == []


def test_pressure_gaps_detected_when_commit_high():
    """Gap adjacent to high-commit tick (>70% of pagefile) appears in pressure_gaps."""
    threshold_bytes = int(PAGEFILE_64GB * 0.70)
    high_commit = threshold_bytes + 1  # just over 70%
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0), commit_bytes=high_commit),
        _tick(_ts(NIGHT_UTC_HOUR, 25), commit_bytes=10_000_000_000),
    ])
    gaps = find_gaps(ticks)
    assert len(gaps) == 1
    result = classify_pressure_gaps(gaps, ticks, PAGEFILE_64GB)
    assert len(result) == 1
    assert result[0]["start"] == _ts(NIGHT_UTC_HOUR, 0)
    assert "threshold_bytes" in result[0]


def test_pressure_gaps_not_detected_when_commit_low():
    """Gap with both adjacent ticks below 70% threshold → not a pressure gap."""
    ticks = _attach_ts([
        _tick(_ts(NIGHT_UTC_HOUR, 0), commit_bytes=10_000_000_000),  # ~9% of 64GB
        _tick(_ts(NIGHT_UTC_HOUR, 25), commit_bytes=10_000_000_000),
    ])
    gaps = find_gaps(ticks)
    assert len(gaps) == 1
    result = classify_pressure_gaps(gaps, ticks, PAGEFILE_64GB)
    assert result == []


# ---------------------------------------------------------------------------
# load_ticks
# ---------------------------------------------------------------------------

def test_load_ticks_returns_entries_in_window(tmp_path):
    log = tmp_path / "memory_timeseries.jsonl"
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent_ts = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_jsonl(log, [_tick(old_ts), _tick(recent_ts)])

    ticks = load_ticks(log, timedelta(hours=24))
    assert len(ticks) == 1
    assert ticks[0]["ts"] == recent_ts


def test_load_ticks_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ticks(tmp_path / "nonexistent.jsonl", timedelta(hours=24))


def test_load_ticks_skips_malformed_lines(tmp_path):
    log = tmp_path / "memory_timeseries.jsonl"
    now = datetime.now(timezone.utc)
    recent_ts = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.write_text('not json\n' + json.dumps(_tick(recent_ts)) + '\n', encoding="utf-8")
    ticks = load_ticks(log, timedelta(hours=24))
    assert len(ticks) == 1


# ---------------------------------------------------------------------------
# main() integration — ISC #1 exit code
# ---------------------------------------------------------------------------

def test_main_exits_1_on_25min_night_gap(tmp_path):
    """ISC #1: main() exits 1 when synthetic JSONL has a 25-min night gap."""
    log = tmp_path / "memory_timeseries.jsonl"
    now = datetime.now(timezone.utc)
    # Place ticks in the recent past so they fall within any window
    base = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    # Force to a night-hour offset: find how many hours to shift to UTC+6 range
    # Using actual recent ticks at 2-min intervals with a 25-min hole
    t0 = base
    t1 = base + timedelta(minutes=25)  # 25-min gap regardless of local time regime,
    t2 = base + timedelta(minutes=27)  # but use night window for determinism

    # Override to known-night UTC timestamps
    t0_ts = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    t1_ts = (now - timedelta(hours=1, minutes=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
    t2_ts = (now - timedelta(hours=1, minutes=33)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _write_jsonl(log, [_tick(t0_ts), _tick(t1_ts), _tick(t2_ts)])
    result = main(["--window", "6h", "--log-file", str(log)])
    assert result == 1


def test_main_exits_0_on_clean_night_ticks(tmp_path):
    """main() exits 0 when all gaps are within cadence."""
    log = tmp_path / "memory_timeseries.jsonl"
    now = datetime.now(timezone.utc)
    # 3 ticks at 2-min intervals — all well within night and day max gaps
    ticks = [
        _tick((now - timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ")),
        _tick((now - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")),
        _tick(now.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ]
    _write_jsonl(log, ticks)
    result = main(["--window", "1h", "--log-file", str(log), "--min-rate", "0.0"])
    assert result == 0


def test_main_exits_1_on_insufficient_data(tmp_path):
    log = tmp_path / "memory_timeseries.jsonl"
    now = datetime.now(timezone.utc)
    _write_jsonl(log, [_tick(now.strftime("%Y-%m-%dT%H:%M:%SZ"))])
    result = main(["--window", "1h", "--log-file", str(log)])
    assert result == 1
