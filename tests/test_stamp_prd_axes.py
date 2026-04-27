"""Unit tests for tools/scripts/stamp_prd_axes.py pure helpers."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.stamp_prd_axes import (
    _has_frontmatter,
    _text_contains_any,
    _score_axis,
    _classify_prd,
    _build_frontmatter,
    _STAKES_HIGH,
    _STAKES_LOW,
    _AMBIGUITY_HIGH,
    _AMBIGUITY_LOW,
    _SOLVABILITY_HIGH,
    _SOLVABILITY_LOW,
    _VERIFIABILITY_HIGH,
    _VERIFIABILITY_LOW,
)


class TestHasFrontmatter:
    def test_detects_frontmatter(self):
        text = "---\nstakes: high\n---\n\n# PRD"
        assert _has_frontmatter(text) is True

    def test_no_frontmatter(self):
        text = "# PRD Title\n\nSome content"
        assert _has_frontmatter(text) is False

    def test_empty_string(self):
        assert _has_frontmatter("") is False

    def test_frontmatter_only(self):
        text = "---\nkey: value\n---\n"
        assert _has_frontmatter(text) is True

    def test_partial_frontmatter_not_matched(self):
        # Only an opening --- without closing should not match
        text = "---\nkey: value\n\n# heading"
        assert _has_frontmatter(text) is False


class TestTextContainsAny:
    def test_match_found(self):
        assert _text_contains_any("production deploy script", {"deploy", "log"}) is True

    def test_no_match(self):
        assert _text_contains_any("rename the file", {"deploy", "secret"}) is False

    def test_case_insensitive(self):
        assert _text_contains_any("PRODUCTION environment", {"production"}) is True

    def test_empty_text(self):
        assert _text_contains_any("", {"deploy"}) is False

    def test_empty_keywords(self):
        assert _text_contains_any("anything", set()) is False


class TestScoreAxis:
    def test_high_tier_when_high_dominates(self):
        tier, n = _score_axis("production deploy credential", _STAKES_HIGH, _STAKES_LOW)
        assert tier == "high"
        assert n > 0

    def test_low_tier_when_low_dominates(self):
        tier, n = _score_axis("rename script doc comment", _STAKES_HIGH, _STAKES_LOW)
        assert tier == "low"
        assert n > 0

    def test_medium_tier_on_tie(self):
        tier, _ = _score_axis("nothing relevant here", _STAKES_HIGH, _STAKES_LOW)
        assert tier == "medium"

    def test_high_verifiability(self):
        tier, _ = _score_axis("pytest assert validate exit code test", _VERIFIABILITY_HIGH, _VERIFIABILITY_LOW)
        assert tier == "high"

    def test_low_solvability_research(self):
        tier, _ = _score_axis("explore strategy novel research design", _SOLVABILITY_HIGH, _SOLVABILITY_LOW)
        assert tier == "low"


class TestClassifyPrd:
    def test_returns_required_keys(self):
        content = "## OVERVIEW\nA simple rename script.\n## ACCEPTANCE CRITERIA\nFile renamed."
        result = _classify_prd(content, Path("PRD_rename.md"))
        for key in ("stakes", "ambiguity", "solvability", "verifiability", "confidence", "rationale"):
            assert key in result

    def test_tier_values_valid(self):
        content = "## OVERVIEW\nDeploy to production with credential rotation.\n"
        result = _classify_prd(content, Path("PRD_deploy.md"))
        for key in ("stakes", "ambiguity", "solvability", "verifiability"):
            assert result[key] in ("high", "medium", "low")

    def test_confidence_levels_valid(self):
        content = "## OVERVIEW\nMinimal PRD.\n"
        result = _classify_prd(content, Path("PRD_test.md"))
        assert result["confidence"] in ("high", "medium", "low")

    def test_high_signal_yields_high_confidence(self):
        # Dense content touching many keyword sets
        content = (
            "## OVERVIEW\nDeploy and fix production credential rotation script "
            "with pytest assert validate exit code test rename add.\n"
            "## ACCEPTANCE CRITERIA\nAll tests pass, exit code 0.\n"
        )
        result = _classify_prd(content, Path("PRD_dense.md"))
        assert result["confidence"] == "high"

    def test_rationale_contains_all_axes(self):
        content = "## OVERVIEW\nAdd a test fixture.\n"
        result = _classify_prd(content, Path("PRD_simple.md"))
        assert "stakes:" in result["rationale"]
        assert "ambiguity:" in result["rationale"]
        assert "solvability:" in result["rationale"]
        assert "verifiability:" in result["rationale"]

    def test_low_confidence_on_sparse_content(self):
        # No keyword hits → low confidence
        content = "## OVERVIEW\nA thing.\n"
        result = _classify_prd(content, Path("PRD_sparse.md"))
        assert result["confidence"] == "low"


class TestBuildFrontmatter:
    def test_valid_all_high(self):
        out = _build_frontmatter("high", "high", "high", "high")
        assert "stakes:        high" in out
        assert "ambiguity:     high" in out

    def test_valid_mixed_values(self):
        out = _build_frontmatter("low", "medium", "high", "low")
        assert "stakes:        low" in out
        assert "ambiguity:     medium" in out
        assert "solvability:   high" in out
        assert "verifiability: low" in out

    def test_output_starts_with_yaml_delimiters(self):
        out = _build_frontmatter("medium", "medium", "medium", "medium")
        assert out.startswith("---\n")
        assert "---\n\n" in out

    def test_invalid_stakes_raises(self):
        import pytest
        with pytest.raises(ValueError, match="stakes"):
            _build_frontmatter("extreme", "low", "low", "low")

    def test_invalid_verifiability_raises(self):
        import pytest
        with pytest.raises(ValueError, match="verifiability"):
            _build_frontmatter("low", "low", "low", "unknown")

    def test_empty_value_raises(self):
        import pytest
        with pytest.raises(ValueError):
            _build_frontmatter("", "low", "low", "low")
