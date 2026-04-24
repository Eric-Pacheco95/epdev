"""Unit tests for tools/scripts/dream.py pure helpers."""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.dream import (
    _infer_memory_type,
    _slug_from_theme,
    _parse_synthesis_themes,
    PROMOTION_MATURITY,
    PROMOTION_MIN_CONFIDENCE,
    TYPE_SIGNALS,
)


class TestInferMemoryType:
    def test_project_pipeline_keyword(self):
        assert _infer_memory_type("Pipeline architecture", "") == "project"

    def test_user_adhd_keyword(self):
        assert _infer_memory_type("Eric ADHD session pattern", "") == "user"

    def test_reference_tool_keyword(self):
        assert _infer_memory_type("External API SDK", "") == "reference"

    def test_keyword_in_implication(self):
        # keyword appears in implication, not theme name
        assert _infer_memory_type("General theme", "This is about infrastructure pipeline") == "project"

    def test_default_is_feedback(self):
        assert _infer_memory_type("random unmatched theme", "no signals here") == "feedback"

    def test_case_insensitive(self):
        assert _infer_memory_type("PIPELINE ARCHITECTURE", "") == "project"

    def test_all_types_have_signals(self):
        for mem_type in ("project", "user", "reference"):
            assert mem_type in TYPE_SIGNALS
            assert len(TYPE_SIGNALS[mem_type]) > 0


class TestSlugFromTheme:
    def test_basic_slug(self):
        assert _slug_from_theme("Hello World") == "hello-world"

    def test_special_chars_replaced(self):
        result = _slug_from_theme("AI/ML: Infrastructure & Tools")
        assert "/" not in result
        assert ":" not in result
        assert "&" not in result
        assert result.islower() or all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in result)

    def test_leading_trailing_hyphens_stripped(self):
        result = _slug_from_theme("-- Theme --")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_max_length_60(self):
        long_name = "word " * 30  # very long
        assert len(_slug_from_theme(long_name)) <= 60

    def test_numbers_preserved(self):
        assert "2026" in _slug_from_theme("Phase 2026 rollout")

    def test_empty_string(self):
        result = _slug_from_theme("")
        assert isinstance(result, str)


class TestParseSynthesisThemes:
    def _write_tmp(self, content: str) -> Path:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return Path(f.name)

    def test_qualifying_theme_returned(self):
        content = (
            "# Synthesis\n\n"
            "### Theme: Proven pattern emerges\n"
            f"- Maturity: {PROMOTION_MATURITY}\n"
            f"- Confidence: {PROMOTION_MIN_CONFIDENCE}%\n"
            "- Implication: Always validate before shipping\n"
        )
        p = self._write_tmp(content)
        try:
            themes = _parse_synthesis_themes(p)
            assert len(themes) == 1
            assert themes[0]["name"] == "Proven pattern emerges"
            assert themes[0]["confidence"] == PROMOTION_MIN_CONFIDENCE
        finally:
            p.unlink()

    def test_low_confidence_filtered(self):
        content = (
            "### Theme: Low confidence theme\n"
            f"- Maturity: {PROMOTION_MATURITY}\n"
            "- Confidence: 70%\n"
            "- Implication: Not ready yet\n"
        )
        p = self._write_tmp(content)
        try:
            assert _parse_synthesis_themes(p) == []
        finally:
            p.unlink()

    def test_wrong_maturity_filtered(self):
        content = (
            "### Theme: Emerging theme\n"
            "- Maturity: emerging\n"
            "- Confidence: 95%\n"
            "- Implication: Still forming\n"
        )
        p = self._write_tmp(content)
        try:
            assert _parse_synthesis_themes(p) == []
        finally:
            p.unlink()

    def test_multiple_themes_filtered_correctly(self):
        content = (
            "### Theme: Good theme\n"
            f"- Maturity: {PROMOTION_MATURITY}\n"
            f"- Confidence: {PROMOTION_MIN_CONFIDENCE}%\n"
            "- Implication: Keep doing this\n"
            "\n"
            "### Theme: Bad theme\n"
            "- Maturity: emerging\n"
            "- Confidence: 50%\n"
            "- Implication: Not ready\n"
        )
        p = self._write_tmp(content)
        try:
            themes = _parse_synthesis_themes(p)
            assert len(themes) == 1
            assert themes[0]["name"] == "Good theme"
        finally:
            p.unlink()

    def test_nonexistent_file_returns_empty(self):
        result = _parse_synthesis_themes(Path("/nonexistent/synthesis.md"))
        assert result == []

    def test_implication_extracted(self):
        content = (
            "### Theme: Has implication\n"
            f"- Maturity: {PROMOTION_MATURITY}\n"
            f"- Confidence: 92%\n"
            "- Implication: This is the key takeaway\n"
        )
        p = self._write_tmp(content)
        try:
            themes = _parse_synthesis_themes(p)
            assert themes[0]["implication"] == "This is the key takeaway"
        finally:
            p.unlink()
