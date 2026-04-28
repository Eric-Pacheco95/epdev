"""Tests for prediction_calibration.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import tools.scripts.prediction_calibration as pc_mod
from tools.scripts.prediction_calibration import (
    compute_adjustments,
    compute_domain_stats,
    parse_frontmatter,
    write_calibration_json,
    write_narrative,
    _extract_confidence,
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


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

def test_parse_frontmatter_valid():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\ntitle: Test\ndomain: market\n---\nBody text\n")
        path = Path(f.name)
    result = parse_frontmatter(path)
    assert result is not None
    assert result["title"] == "Test"
    assert result["domain"] == "market"
    path.unlink()


def test_parse_frontmatter_no_delimiter():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("No frontmatter here\n")
        path = Path(f.name)
    result = parse_frontmatter(path)
    assert result is None
    path.unlink()


def test_parse_frontmatter_missing_file():
    result = parse_frontmatter(Path("/no/such/file.md"))
    assert result is None


def test_parse_frontmatter_sets_path_key():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("---\nkey: val\n---\n")
        path = Path(f.name)
    result = parse_frontmatter(path)
    assert result["_path"] == path
    path.unlink()


# ---------------------------------------------------------------------------
# _extract_confidence
# ---------------------------------------------------------------------------

def test_extract_confidence_float():
    assert _extract_confidence({"primary_confidence": 0.75}) == 0.75


def test_extract_confidence_string_float():
    assert _extract_confidence({"primary_confidence": "0.8"}) == 0.8


def test_extract_confidence_missing_returns_none():
    assert _extract_confidence({}) is None


def test_extract_confidence_invalid_string_returns_none():
    assert _extract_confidence({"primary_confidence": "high"}) is None


# ---------------------------------------------------------------------------
# write_calibration_json
# ---------------------------------------------------------------------------

def _merged_sample():
    return {
        "market": {
            "adjustment": -0.05, "n_resolved": 15, "n_forward": 10, "n_backtest": 5,
            "accuracy_forward": 0.6, "accuracy_backtest": 0.7,
            "overconfidence_delta": 0.05, "clamped": False,
        }
    }


def test_write_calibration_json_creates_file(tmp_path, monkeypatch):
    f = tmp_path / "calibration.json"
    monkeypatch.setattr(pc_mod, "CALIBRATION_FILE", f)
    write_calibration_json(_merged_sample(), version=3)
    assert f.exists()


def test_write_calibration_json_has_version(tmp_path, monkeypatch):
    f = tmp_path / "calibration.json"
    monkeypatch.setattr(pc_mod, "CALIBRATION_FILE", f)
    write_calibration_json(_merged_sample(), version=7)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["version"] == 7


def test_write_calibration_json_domain_keys(tmp_path, monkeypatch):
    f = tmp_path / "calibration.json"
    monkeypatch.setattr(pc_mod, "CALIBRATION_FILE", f)
    write_calibration_json(_merged_sample(), version=1)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert "market" in data["domains"]
    assert "adjustment" in data["domains"]["market"]


# ---------------------------------------------------------------------------
# write_narrative
# ---------------------------------------------------------------------------

def test_write_narrative_creates_file(tmp_path, monkeypatch):
    f = tmp_path / "narrative.md"
    monkeypatch.setattr(pc_mod, "NARRATIVE_FILE", f)
    write_narrative(_merged_sample(), version=2)
    assert f.exists()


def test_write_narrative_contains_version_header(tmp_path, monkeypatch):
    f = tmp_path / "narrative.md"
    monkeypatch.setattr(pc_mod, "NARRATIVE_FILE", f)
    write_narrative(_merged_sample(), version=4)
    content = f.read_text(encoding="utf-8")
    assert "v4" in content


def test_write_narrative_contains_domain_section(tmp_path, monkeypatch):
    f = tmp_path / "narrative.md"
    monkeypatch.setattr(pc_mod, "NARRATIVE_FILE", f)
    write_narrative(_merged_sample(), version=1)
    content = f.read_text(encoding="utf-8")
    assert "Market" in content
