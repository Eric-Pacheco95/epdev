"""Unit tests for tools/scripts/calibration_rollup.py pure helpers."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.calibration_rollup import (
    _filter_four_axis,
    _metric_label_match_rate,
    _metric_danger_cell_catch_rate,
    _metric_vhigh_false_positive,
    _metric_vlow_under_review,
    _status,
    _fmt_value,
    _fmt_threshold,
    MIN_SAMPLE,
)

FOUR_AXIS_KEYS = {"stakes", "ambiguity", "solvability", "verifiability"}


def _make_entry(**kwargs):
    base = {"stakes": "high", "ambiguity": "low", "solvability": "high", "verifiability": "high"}
    base.update(kwargs)
    return base


class TestFilterFourAxis:
    def test_keeps_complete_entries(self):
        entries = [_make_entry(), _make_entry()]
        assert len(_filter_four_axis(entries)) == 2

    def test_drops_incomplete_entries(self):
        entries = [{"stakes": "high"}, _make_entry()]
        assert len(_filter_four_axis(entries)) == 1

    def test_empty_input(self):
        assert _filter_four_axis([]) == []

    def test_all_incomplete(self):
        entries = [{"foo": "bar"}, {"stakes": "low"}]
        assert _filter_four_axis(entries) == []


class TestMetricLabelMatchRate:
    def _make_entries(self, n_kept, n_overridden):
        entries = [_make_entry(label_override=False) for _ in range(n_kept)]
        entries += [_make_entry(label_override=True) for _ in range(n_overridden)]
        return entries

    def test_returns_none_below_min_sample(self):
        entries = self._make_entries(3, 2)  # total 5 < MIN_SAMPLE
        val, n = _metric_label_match_rate(entries)
        assert val is None
        assert n < MIN_SAMPLE

    def test_correct_rate_above_min_sample(self):
        entries = self._make_entries(8, 2)  # 10 total, 8 kept
        val, n = _metric_label_match_rate(entries)
        assert val is not None
        assert abs(val - 0.8) < 1e-9
        assert n == 10

    def test_all_kept(self):
        entries = self._make_entries(MIN_SAMPLE, 0)
        val, _ = _metric_label_match_rate(entries)
        assert val == 1.0

    def test_entries_without_label_override_field_excluded(self):
        # entries lacking the field should not count
        entries = [_make_entry() for _ in range(15)]  # no label_override key
        val, n = _metric_label_match_rate(entries)
        assert val is None
        assert n == 0


class TestMetricDangerCellCatchRate:
    def _make_danger(self, n_caught, n_missed):
        entries = []
        for _ in range(n_caught):
            entries.append(_make_entry(solvability="low", verifiability="low", evaluator="hitl"))
        for _ in range(n_missed):
            entries.append(_make_entry(solvability="low", verifiability="low", evaluator="sonnet"))
        return entries

    def test_returns_none_below_min_sample(self):
        val, n = _metric_danger_cell_catch_rate(self._make_danger(3, 2))
        assert val is None

    def test_correct_catch_rate(self):
        entries = self._make_danger(8, 2)
        val, n = _metric_danger_cell_catch_rate(entries)
        assert val is not None
        assert abs(val - 0.8) < 1e-9

    def test_non_danger_cells_excluded(self):
        # high-solvability entries should not count toward danger-cell metric
        entries = self._make_danger(0, 0)
        entries += [_make_entry(evaluator="hitl") for _ in range(20)]
        val, n = _metric_danger_cell_catch_rate(entries)
        assert val is None  # no danger-cell entries → insufficient data

    def test_rate_limited_excluded(self):
        entries = self._make_danger(5, 5)
        entries += [_make_entry(solvability="low", verifiability="low", evaluator="hitl", rate_limited=True)
                    for _ in range(100)]
        val, n = _metric_danger_cell_catch_rate(entries)
        assert n == 10  # rate_limited ones excluded


class TestMetricVhighFalsePositive:
    def _make_vhigh(self, n_oracle, n_other):
        entries = []
        for _ in range(n_oracle):
            entries.append(_make_entry(verifiability="high", evaluator="script-oracle"))
        for _ in range(n_other):
            entries.append(_make_entry(verifiability="high", evaluator="sonnet"))
        return entries

    def test_returns_none_below_min_sample(self):
        val, _ = _metric_vhigh_false_positive(self._make_vhigh(3, 2))
        assert val is None

    def test_correct_false_positive_rate(self):
        entries = self._make_vhigh(8, 2)
        val, n = _metric_vhigh_false_positive(entries)
        assert val is not None
        assert abs(val - 0.2) < 1e-9

    def test_zero_false_positives(self):
        entries = self._make_vhigh(MIN_SAMPLE, 0)
        val, _ = _metric_vhigh_false_positive(entries)
        assert val == 0.0


class TestMetricVlowUnderReview:
    def _make_vlow(self, n_reviewed, n_missed):
        entries = []
        for _ in range(n_reviewed):
            entries.append(_make_entry(verifiability="low", evaluator="hitl"))
        for _ in range(n_missed):
            entries.append(_make_entry(verifiability="low", evaluator="sonnet"))
        return entries

    def test_returns_none_below_min_sample(self):
        val, _ = _metric_vlow_under_review(self._make_vlow(3, 2))
        assert val is None

    def test_correct_under_review_rate(self):
        entries = self._make_vlow(2, 8)
        val, n = _metric_vlow_under_review(entries)
        assert val is not None
        assert abs(val - 0.8) < 1e-9


class TestStatus:
    def test_green_ge_threshold_met(self):
        assert _status("label_match_rate", 0.70) == "GREEN"

    def test_red_ge_threshold_missed(self):
        assert _status("label_match_rate", 0.50) == "RED"

    def test_green_le_threshold_met(self):
        assert _status("vhigh_false_positive", 0.05) == "GREEN"

    def test_red_le_threshold_exceeded(self):
        assert _status("vhigh_false_positive", 0.20) == "RED"

    def test_insufficient_data(self):
        assert _status("label_match_rate", None) == "INSUFFICIENT_DATA"


class TestFmtValue:
    def test_none_shows_insufficient_data(self):
        result = _fmt_value(None, 5)
        assert "insufficient data" in result
        assert "5" in result

    def test_float_formatted_as_percent(self):
        result = _fmt_value(0.8, 10)
        assert "80.0%" in result
        assert "10" in result


class TestFmtThreshold:
    def test_label_match_rate_threshold(self):
        result = _fmt_threshold("label_match_rate")
        assert ">=" in result
        assert "60" in result

    def test_vhigh_false_positive_threshold(self):
        result = _fmt_threshold("vhigh_false_positive")
        assert "<=" in result
        assert "10" in result
