"""Tests for tools/scripts/ceremony_tier.py."""

import pytest

from tools.scripts.ceremony_tier import (
    InvalidAxisValueError,
    MissingFrontmatterError,
    band_for_tier,
    compute_tier,
    parse_axes_arg,
)


class TestComputeTier:
    def test_all_favorable_is_tier_0(self):
        axes = {"stakes": "low", "ambiguity": "low", "solvability": "high", "verifiability": "high"}
        tier, defaults = compute_tier(axes)
        assert tier == 0
        assert defaults == []

    def test_all_unfavorable_is_tier_4(self):
        axes = {"stakes": "high", "ambiguity": "high", "solvability": "low", "verifiability": "low"}
        tier, defaults = compute_tier(axes)
        assert tier == 4
        assert defaults == []

    def test_single_unfavorable_stakes(self):
        axes = {"stakes": "high", "ambiguity": "low", "solvability": "high", "verifiability": "high"}
        tier, _ = compute_tier(axes)
        assert tier == 1

    def test_missing_axis_defaults_to_medium_favorable(self):
        # ambiguity missing -> defaults to "medium" (favorable)
        axes = {"stakes": "high"}
        tier, defaults = compute_tier(axes)
        assert "ambiguity" in defaults
        assert "solvability" in defaults
        assert "verifiability" in defaults
        assert tier == 1  # only stakes=high counts

    def test_empty_string_axis_defaults_to_medium(self):
        axes = {"stakes": "high", "ambiguity": "", "solvability": "", "verifiability": ""}
        tier, defaults = compute_tier(axes)
        assert tier == 1
        assert len(defaults) == 3

    def test_invalid_axis_value_raises(self):
        with pytest.raises(InvalidAxisValueError, match="critical"):
            compute_tier({"stakes": "critical"})

    def test_axes_not_dict_raises(self):
        with pytest.raises(InvalidAxisValueError):
            compute_tier("stakes=high")

    def test_all_medium_is_tier_0(self):
        axes = {"stakes": "medium", "ambiguity": "medium", "solvability": "medium", "verifiability": "medium"}
        tier, _ = compute_tier(axes)
        assert tier == 0

    def test_two_unfavorable(self):
        axes = {"stakes": "high", "ambiguity": "high", "solvability": "high", "verifiability": "high"}
        tier, _ = compute_tier(axes)
        assert tier == 2  # only stakes=high and ambiguity=high are unfavorable


class TestBandForTier:
    def test_tier_0_is_T0(self):
        assert band_for_tier(0) == "T0"

    def test_tier_1_is_T12(self):
        assert band_for_tier(1) == "T1-2"

    def test_tier_2_is_T12(self):
        assert band_for_tier(2) == "T1-2"

    def test_tier_3_is_T34(self):
        assert band_for_tier(3) == "T3-4"

    def test_tier_4_is_T34(self):
        assert band_for_tier(4) == "T3-4"

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            band_for_tier(5)


class TestParseAxesArg:
    def test_all_four_axes(self):
        result = parse_axes_arg("stakes=high,ambiguity=low,solvability=high,verifiability=high")
        assert result == {
            "stakes": "high",
            "ambiguity": "low",
            "solvability": "high",
            "verifiability": "high",
        }

    def test_single_axis(self):
        assert parse_axes_arg("stakes=high") == {"stakes": "high"}

    def test_extra_whitespace_stripped(self):
        result = parse_axes_arg(" stakes = high , ambiguity = low ")
        assert result["stakes"] == "high"
        assert result["ambiguity"] == "low"

    def test_missing_equals_raises(self):
        with pytest.raises(InvalidAxisValueError, match="missing '='"):
            parse_axes_arg("stakeshigh")

    def test_empty_string_returns_empty_dict(self):
        assert parse_axes_arg("") == {}

    def test_trailing_comma_ignored(self):
        result = parse_axes_arg("stakes=high,")
        assert result == {"stakes": "high"}
