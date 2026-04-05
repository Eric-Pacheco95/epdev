"""Tests for prediction_calibration.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tools.scripts.prediction_calibration import (
    compute_adjustments,
    compute_domain_stats,
    ADJUSTMENT_BOUNDS,
)


# ---------------------------------------------------------------------------
# compute_domain_stats
# ---------------------------------------------------------------------------

def _make_prediction(domain="market", outcome="correct", confidence=0.7):
    return {
        "domain": domain,
        "outcome_label": outcome,
        "primary_confidence": confidence,
    }


def test_stats_single_correct():
    preds = [_make_prediction("market", "correct", 0.7)]
    stats = compute_domain_stats(preds)
    assert "market" in stats
    assert stats["market"]["accuracy"] == 1.0
    assert stats["market"]["n_resolved"] == 1
    assert stats["market"]["correct"] == 1


def test_stats_single_wrong():
    preds = [_make_prediction("market", "wrong", 0.8)]
    stats = compute_domain_stats(preds)
    assert stats["market"]["accuracy"] == 0.0
    assert stats["market"]["wrong"] == 1


def test_stats_partial_counts_half():
    preds = [
        _make_prediction("market", "correct", 0.7),
        _make_prediction("market", "partial", 0.6),
    ]
    stats = compute_domain_stats(preds)
    # 1 correct + 0.5 partial = 1.5 / 2 = 0.75
    assert stats["market"]["accuracy"] == 0.75


def test_stats_multiple_domains():
    preds = [
        _make_prediction("market", "correct", 0.7),
        _make_prediction("geopolitics", "wrong", 0.8),
        _make_prediction("geopolitics", "correct", 0.6),
    ]
    stats = compute_domain_stats(preds)
    assert "market" in stats
    assert "geopolitics" in stats
    assert stats["market"]["n_resolved"] == 1
    assert stats["geopolitics"]["n_resolved"] == 2


def test_stats_overconfidence_delta():
    # 3 predictions, all correct at 0.9 confidence but accuracy is 1.0
    # overconfidence = mean_conf_correct - accuracy = 0.9 - 1.0 = -0.1
    preds = [
        _make_prediction("market", "correct", 0.9),
        _make_prediction("market", "correct", 0.9),
        _make_prediction("market", "correct", 0.9),
    ]
    stats = compute_domain_stats(preds)
    assert stats["market"]["overconfidence_delta"] == -0.1


def test_stats_no_confidence_data():
    preds = [{"domain": "market", "outcome_label": "correct"}]
    stats = compute_domain_stats(preds)
    assert stats["market"]["mean_confidence_correct"] is None


# ---------------------------------------------------------------------------
# compute_adjustments
# ---------------------------------------------------------------------------

def test_adjustments_basic():
    forward_stats = {
        "market": {
            "n_resolved": 10,
            "accuracy": 0.7,
            "overconfidence_delta": 0.1,  # overconfident by 10%
        }
    }
    merged = compute_adjustments(forward_stats, {})
    assert "market" in merged
    # adjustment should be negative of delta = -0.1
    assert merged["market"]["adjustment"] == -0.1
    assert merged["market"]["clamped"] is False


def test_adjustments_clamped_to_bounds():
    forward_stats = {
        "market": {
            "n_resolved": 10,
            "accuracy": 0.3,
            "overconfidence_delta": 0.5,  # way overconfident
        }
    }
    merged = compute_adjustments(forward_stats, {})
    # Raw would be -0.5, clamped to -0.15
    assert merged["market"]["adjustment"] == ADJUSTMENT_BOUNDS[0]
    assert merged["market"]["clamped"] is True


def test_adjustments_blend_forward_and_backtest():
    forward_stats = {
        "market": {
            "n_resolved": 10,
            "accuracy": 0.7,
            "overconfidence_delta": 0.1,
        }
    }
    backtest_stats = {
        "market": {
            "n_resolved": 10,
            "accuracy": 0.6,
            "overconfidence_delta": 0.2,
        }
    }
    merged = compute_adjustments(forward_stats, backtest_stats)
    # Blended delta: (0.1 * 10 * 1.0 + 0.2 * 10 * 0.5) / (10 * 1.0 + 10 * 0.5)
    # = (1.0 + 1.0) / 15 = 0.133...
    assert abs(merged["market"]["overconfidence_delta"] - 0.133) < 0.01


def test_adjustments_backtest_only_domain():
    backtest_stats = {
        "technology": {
            "n_resolved": 5,
            "accuracy": 0.8,
            "overconfidence_delta": -0.05,
        }
    }
    merged = compute_adjustments({}, backtest_stats)
    assert "technology" in merged
    assert merged["technology"]["n_forward"] == 0
    assert merged["technology"]["n_backtest"] == 5


def test_adjustments_zero_delta_no_adjustment():
    forward_stats = {
        "market": {
            "n_resolved": 10,
            "accuracy": 0.7,
            "overconfidence_delta": 0.0,
        }
    }
    merged = compute_adjustments(forward_stats, {})
    assert merged["market"]["adjustment"] == 0.0
    assert merged["market"]["clamped"] is False
