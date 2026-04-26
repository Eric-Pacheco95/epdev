"""Tests for tools/scripts/analyze_recording.load_music_context."""

from pathlib import Path
from tools.scripts.analyze_recording import load_music_context


MUSIC_MD = """# MUSIC.md

## Player Profile
Eric plays electric guitar, jazz-focused, intermediate level.

**Heroes**: John Scofield, Kurt Rosenwinkel, Pat Metheny

## Current Development Areas
| Priority | Area | Finding |
|----------|------|---------|
| 1 | Chord voicings | Needs wider voicing variety |
| 2 | Timing | Rushing on eighth notes |

## Other Section
Not relevant.
"""


class TestLoadMusicContext:
    def test_returns_none_for_missing_file(self, tmp_path):
        result = load_music_context(str(tmp_path / "nonexistent.md"))
        assert result is None

    def test_returns_none_for_none_path(self):
        result = load_music_context(None)
        assert result is None

    def test_returns_none_for_empty_content(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text("", encoding="utf-8")
        result = load_music_context(str(f))
        assert result is None

    def test_extracts_heroes(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text(MUSIC_MD, encoding="utf-8")
        result = load_music_context(str(f))
        assert "Scofield" in result
        assert "musical influences" in result

    def test_extracts_development_areas(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text(MUSIC_MD, encoding="utf-8")
        result = load_music_context(str(f))
        assert "Chord voicings" in result
        assert "Timing" in result

    def test_extracts_player_profile(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text(MUSIC_MD, encoding="utf-8")
        result = load_music_context(str(f))
        assert "Player profile" in result
        assert "electric guitar" in result

    def test_returns_context_header(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text(MUSIC_MD, encoding="utf-8")
        result = load_music_context(str(f))
        assert "CONTEXT ABOUT THIS PLAYER" in result

    def test_file_with_only_irrelevant_content(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text("# Just a heading\nNo relevant sections here.\n", encoding="utf-8")
        result = load_music_context(str(f))
        assert result is None

    def test_heroes_only_file(self, tmp_path):
        f = tmp_path / "MUSIC.md"
        f.write_text("**Heroes**: Bill Evans, McCoy Tyner\n", encoding="utf-8")
        result = load_music_context(str(f))
        assert result is not None
        assert "Bill Evans" in result
