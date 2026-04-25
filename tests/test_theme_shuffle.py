"""Tests for tools/scripts/theme_shuffle.py pure helper functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# theme_shuffle.py wraps sys.stdout at import time; detach before restoring to
# avoid closing the underlying buffer and breaking pytest's stdout capture.
_saved_stdout = sys.stdout
import tools.scripts.theme_shuffle as ts  # noqa: E402
if sys.stdout is not _saved_stdout:
    sys.stdout.detach()
sys.stdout = _saved_stdout


class TestLuminance:
    def test_black_is_zero(self):
        assert ts._luminance("#000000") == 0.0

    def test_white_is_one(self):
        result = ts._luminance("#FFFFFF")
        assert abs(result - 1.0) < 0.001

    def test_red_channel(self):
        result = ts._luminance("#FF0000")
        assert abs(result - 0.299) < 0.001

    def test_green_channel(self):
        result = ts._luminance("#00FF00")
        assert abs(result - 0.587) < 0.001

    def test_blue_channel(self):
        result = ts._luminance("#0000FF")
        assert abs(result - 0.114) < 0.001

    def test_returns_float(self):
        assert isinstance(ts._luminance("#AABBCC"), float)

    def test_range_zero_to_one(self):
        for hex_val in ["#000000", "#808080", "#FFFFFF", "#FF0000", "#00FF00"]:
            lum = ts._luminance(hex_val)
            assert 0.0 <= lum <= 1.0


class TestFgFor:
    def test_black_bg_returns_white(self):
        assert ts._fg_for("#000000") == "#FFFFFF"

    def test_white_bg_returns_black(self):
        assert ts._fg_for("#FFFFFF") == "#000000"

    def test_returns_one_of_two_colors(self):
        result = ts._fg_for("#808080")
        assert result in ("#000000", "#FFFFFF")

    def test_dark_purple_returns_white(self):
        assert ts._fg_for("#0D0221") == "#FFFFFF"


class TestKeyForName:
    def test_exact_key_match(self):
        assert ts._key_for_name("cyberpunk") == "cyberpunk"

    def test_display_name_match(self):
        assert ts._key_for_name("Cyberpunk") == "cyberpunk"

    def test_case_insensitive(self):
        assert ts._key_for_name("CYBERPUNK") == "cyberpunk"

    def test_synthwave_by_name(self):
        assert ts._key_for_name("Synthwave") == "synthwave"

    def test_tron_by_name(self):
        assert ts._key_for_name("Tron") == "tron"

    def test_unknown_returns_none(self):
        assert ts._key_for_name("does-not-exist") is None

    def test_empty_string_returns_none(self):
        assert ts._key_for_name("") is None


class TestLoadState:
    def test_missing_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ts, "STATE_PATH", tmp_path / "nonexistent.json")
        state = ts._load_state()
        assert state["current"] == "cyberpunk"
        assert state["previous"] is None

    def test_reads_existing_state(self, tmp_path, monkeypatch):
        state_file = tmp_path / "theme_state.json"
        state_file.write_text(json.dumps({"current": "tron", "previous": "synthwave"}))
        monkeypatch.setattr(ts, "STATE_PATH", state_file)
        state = ts._load_state()
        assert state["current"] == "tron"
        assert state["previous"] == "synthwave"

    def test_corrupted_json_returns_defaults(self, tmp_path, monkeypatch):
        state_file = tmp_path / "theme_state.json"
        state_file.write_text("not valid json {{{")
        monkeypatch.setattr(ts, "STATE_PATH", state_file)
        state = ts._load_state()
        assert state["current"] == "cyberpunk"


class TestSaveState:
    def test_writes_json(self, tmp_path, monkeypatch):
        state_file = tmp_path / "theme_state.json"
        monkeypatch.setattr(ts, "STATE_PATH", state_file)
        ts._save_state({"current": "outrun", "previous": "tron"})
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["current"] == "outrun"
        assert data["previous"] == "tron"

    def test_creates_parent_dir(self, tmp_path, monkeypatch):
        state_file = tmp_path / "subdir" / "theme_state.json"
        monkeypatch.setattr(ts, "STATE_PATH", state_file)
        ts._save_state({"current": "blade-runner", "previous": None})
        assert state_file.exists()


class TestBuildOmpTheme:
    def test_returns_dict_with_schema(self):
        theme = ts._build_omp_theme("cyberpunk")
        assert "$schema" in theme

    def test_has_version(self):
        theme = ts._build_omp_theme("synthwave")
        assert theme["version"] == 2

    def test_has_blocks(self):
        theme = ts._build_omp_theme("tron")
        assert "blocks" in theme
        assert len(theme["blocks"]) >= 2

    def test_title_contains_theme_name(self):
        theme = ts._build_omp_theme("outrun")
        assert "Outrun" in theme["console_title_template"]

    def test_all_themes_build_without_error(self):
        for key in ts.THEMES:
            result = ts._build_omp_theme(key)
            assert isinstance(result, dict)


class TestThemesData:
    def test_all_themes_have_required_keys(self):
        required = {"name", "background", "foreground", "cursorColor"}
        for key, theme in ts.THEMES.items():
            missing = required - set(theme.keys())
            assert not missing, f"Theme {key!r} missing: {missing}"

    def test_palette_notes_covers_all_themes(self):
        for key in ts.THEMES:
            assert key in ts.PALETTE_NOTES

    def test_omp_colors_covers_all_themes(self):
        for key in ts.THEMES:
            assert key in ts.OMP_COLORS
