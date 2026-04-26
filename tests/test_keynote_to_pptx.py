"""Tests for tools/scripts/keynote_to_pptx.parse_keynote_md."""

from tools.scripts.keynote_to_pptx import parse_keynote_md


MINIMAL_KEYNOTE = """# PRESENTATION 1: Test Talk

## FLOW
- Introduction
- Main Content
- Conclusion

## DESIRED TAKEAWAY
Learn something useful today.

### Slide 1: Opening
**Bullets**:
- First point
- Second point

**Image**: A photo of something

**Speaker notes**:
- Tell the story here

### Slide 2: Deep Dive
**Bullets**:
- Detail A
- Detail B

**Image**: Diagram of process

**Speaker notes**:
- Explain in detail
"""


class TestParseKeynoteMd:
    def test_extracts_title(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert result["title"] == "Test Talk"

    def test_extracts_flow_items(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert "Introduction" in result["flow"]
        assert "Main Content" in result["flow"]
        assert "Conclusion" in result["flow"]

    def test_extracts_takeaway(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert "Learn something useful" in result["takeaway"]

    def test_extracts_slide_count(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert len(result["slides"]) == 2

    def test_extracts_slide_titles(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert result["slides"][0]["title"] == "Opening"
        assert result["slides"][1]["title"] == "Deep Dive"

    def test_extracts_slide_bullets(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        bullets = result["slides"][0]["bullets"]
        assert "First point" in bullets
        assert "Second point" in bullets

    def test_extracts_slide_image(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert "photo" in result["slides"][0]["image"]

    def test_extracts_speaker_notes(self):
        result = parse_keynote_md(MINIMAL_KEYNOTE)
        assert "Tell the story here" in result["slides"][0]["notes"]

    def test_empty_string_returns_default_structure(self):
        result = parse_keynote_md("")
        assert result["title"] == ""
        assert result["flow"] == []
        assert result["takeaway"] == ""
        assert result["slides"] == []

    def test_h2_title_extraction(self):
        text = "## My Talk\n\n## FLOW\n- Step 1\n\n## DESIRED TAKEAWAY\nDone.\n"
        result = parse_keynote_md(text)
        assert result["title"] == "My Talk"

    def test_numbered_flow_items_stripped(self):
        text = "# Title\n\n## FLOW\n1. First\n2. Second\n\n## DESIRED TAKEAWAY\nOK.\n"
        result = parse_keynote_md(text)
        assert "First" in result["flow"]
        assert "Second" in result["flow"]
        assert not any(item.startswith("1.") for item in result["flow"])

    def test_slide_without_bullets_has_empty_list(self):
        text = (
            "# Title\n\n## FLOW\n- A\n\n## DESIRED TAKEAWAY\nX.\n\n"
            "### Slide 1: Empty Slide\nNo bullets here.\n"
        )
        result = parse_keynote_md(text)
        assert result["slides"][0]["bullets"] == []
