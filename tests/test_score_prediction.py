"""Tests for run_prediction_pipeline score_prediction pure function."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.run_prediction_pipeline_2026_04_08 import score_prediction


class TestScorePrediction:
    def test_low_confidence_not_suspect(self):
        result = score_prediction("evt-01", {"primary_confidence": 0.5})
        assert result["suspect_leakage"] is False
        assert result["leakage_flag"] == ""

    def test_high_confidence_marks_suspect(self):
        result = score_prediction("evt-02", {"primary_confidence": 0.90})
        assert result["suspect_leakage"] is True
        assert "SUSPECT LEAKAGE" in result["leakage_flag"]

    def test_explicit_suspect_leakage_flag_overrides(self):
        result = score_prediction("evt-03", {"primary_confidence": 0.5, "suspect_leakage": True})
        assert result["suspect_leakage"] is True

    def test_threshold_boundary_exact(self):
        result = score_prediction("evt-04", {"primary_confidence": 0.85})
        # 0.85 is NOT > 0.85, so should not be suspect
        assert result["suspect_leakage"] is False

    def test_threshold_just_above(self):
        result = score_prediction("evt-05", {"primary_confidence": 0.851})
        assert result["suspect_leakage"] is True

    def test_returns_required_keys(self):
        result = score_prediction("evt-06", {"primary_confidence": 0.7})
        for key in ("primary_confidence", "alignment_score", "suspect_leakage",
                    "leakage_flag", "score_method", "note"):
            assert key in result

    def test_primary_confidence_preserved(self):
        result = score_prediction("evt-07", {"primary_confidence": 0.73})
        assert result["primary_confidence"] == 0.73

    def test_alignment_score_is_numeric(self):
        result = score_prediction("evt-08", {"primary_confidence": 0.5})
        assert isinstance(result["alignment_score"], (int, float))

    def test_score_method_is_string(self):
        result = score_prediction("evt-09", {"primary_confidence": 0.5})
        assert isinstance(result["score_method"], str)
        assert result["score_method"]

    def test_leakage_flag_empty_when_not_suspect(self):
        result = score_prediction("evt-10", {"primary_confidence": 0.3})
        assert result["leakage_flag"] == ""

    def test_leakage_flag_nonempty_when_suspect(self):
        result = score_prediction("evt-11", {"primary_confidence": 0.9})
        assert result["leakage_flag"] != ""

    def test_suspect_leakage_false_by_default(self):
        result = score_prediction("evt-12", {"primary_confidence": 0.4})
        assert result["suspect_leakage"] is False

    def test_explicit_false_leakage_flag_does_not_override_confidence(self):
        result = score_prediction("evt-13", {"primary_confidence": 0.9, "suspect_leakage": False})
        # confidence > 0.85 -> suspect regardless of explicit False
        assert result["suspect_leakage"] is True
