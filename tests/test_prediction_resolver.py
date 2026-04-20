"""Tests for prediction_resolver.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from tools.scripts.prediction_resolver import (
    count_resolved,
    parse_verdict,
    write_resolution,
    read_prediction,
    append_analysis,
)


# ---------------------------------------------------------------------------
# parse_verdict
# ---------------------------------------------------------------------------

def test_parse_correct():
    verdict, note = parse_verdict("correct")
    assert verdict == "correct"
    assert note == ""


def test_parse_wrong():
    verdict, note = parse_verdict("wrong")
    assert verdict == "wrong"
    assert note == ""


def test_parse_right_alias():
    verdict, note = parse_verdict("right")
    assert verdict == "correct"


def test_parse_partial_with_note():
    verdict, note = parse_verdict("partial: outcome 1 correct, outcome 3 wrong")
    assert verdict == "partial"
    assert "outcome 1 correct" in note


def test_parse_defer_valid_date():
    verdict, note = parse_verdict("defer: 2026-12-31")
    assert verdict == "defer"
    assert note == "2026-12-31"


def test_parse_defer_invalid_date():
    with pytest.raises(ValueError, match="Invalid defer date"):
        parse_verdict("defer: not-a-date")


def test_parse_reviewed():
    verdict, note = parse_verdict("reviewed: geo-btc-2021")
    assert verdict == "reviewed"
    assert note == "geo-btc-2021"


def test_parse_rejected():
    verdict, note = parse_verdict("rejected: geo-btc-2021")
    assert verdict == "rejected"
    assert note == "geo-btc-2021"


def test_parse_unknown_verdict_raises():
    with pytest.raises(ValueError, match="Unknown verdict"):
        parse_verdict("maybe")


def test_parse_case_insensitive():
    verdict, _ = parse_verdict("CORRECT")
    assert verdict == "correct"


# ---------------------------------------------------------------------------
# read_prediction
# ---------------------------------------------------------------------------

def test_read_prediction_with_frontmatter(tmp_path):
    prediction_file = tmp_path / "test_prediction.md"
    prediction_file.write_text(
        "---\ndate: 2026-04-05\ndomain: market\nstatus: open\n---\n\n# Test\n",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    assert fm["domain"] == "market"
    assert fm["status"] == "open"
    assert "# Test" in body


def test_read_prediction_no_frontmatter(tmp_path):
    prediction_file = tmp_path / "test.md"
    prediction_file.write_text("# No frontmatter\n", encoding="utf-8")
    fm, fm_raw, body = read_prediction(prediction_file)
    assert fm == {}


# ---------------------------------------------------------------------------
# write_resolution
# ---------------------------------------------------------------------------

def test_write_resolution_correct(tmp_path):
    prediction_file = tmp_path / "test.md"
    prediction_file.write_text(
        "---\ndate: 2026-04-01\ndomain: market\nstatus: open\nquestion: Will BTC hit ATH?\n---\n\n# Prediction\n",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    write_resolution(prediction_file, fm, fm_raw, body, "correct", "")
    content = prediction_file.read_text(encoding="utf-8")
    assert "resolved" in content
    assert "correct" in content
    assert "## Resolution" in content


def test_write_resolution_wrong(tmp_path):
    prediction_file = tmp_path / "test.md"
    prediction_file.write_text(
        "---\ndate: 2026-04-01\ndomain: geopolitics\nstatus: open\n---\n\n# Prediction\n",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    write_resolution(prediction_file, fm, fm_raw, body, "wrong", "")
    content = prediction_file.read_text(encoding="utf-8")
    assert "resolved" in content
    assert "wrong" in content


def test_write_resolution_defer(tmp_path):
    prediction_file = tmp_path / "test.md"
    prediction_file.write_text(
        "---\ndate: 2026-04-01\ndomain: market\nstatus: open\n---\n\n# Prediction\n",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    write_resolution(prediction_file, fm, fm_raw, body, "defer", "2027-01-01")
    content = prediction_file.read_text(encoding="utf-8")
    assert "deferred" in content
    assert "## Resolution" in content


def test_write_resolution_partial_with_note(tmp_path):
    prediction_file = tmp_path / "test.md"
    prediction_file.write_text(
        "---\ndate: 2026-04-01\ndomain: market\nstatus: open\n---\n\n# Prediction\n",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    write_resolution(prediction_file, fm, fm_raw, body, "partial", "Outcome 1 correct, 2 wrong")
    content = prediction_file.read_text(encoding="utf-8")
    assert "partial" in content
    assert "Outcome 1 correct" in content


def test_write_resolution_appends_not_overwrites(tmp_path):
    prediction_file = tmp_path / "test.md"
    original_body = "# Original prediction content\n\nImportant analysis here."
    prediction_file.write_text(
        f"---\ndate: 2026-04-01\ndomain: market\nstatus: open\n---\n\n{original_body}",
        encoding="utf-8",
    )
    fm, fm_raw, body = read_prediction(prediction_file)
    write_resolution(prediction_file, fm, fm_raw, body, "correct", "")
    content = prediction_file.read_text(encoding="utf-8")
    # Original content must still be present
    assert "Important analysis here" in content
    assert "## Resolution" in content


# ---------------------------------------------------------------------------
# count_resolved (integration -- uses actual predictions dir)
# ---------------------------------------------------------------------------

def test_count_resolved_returns_int():
    count = count_resolved(forward_only=True)
    assert isinstance(count, int)
    assert count >= 0


def test_count_resolved_total_gte_forward():
    forward = count_resolved(forward_only=True)
    total = count_resolved(forward_only=False)
    assert total >= forward


# ---------------------------------------------------------------------------
# append_analysis
# ---------------------------------------------------------------------------

def test_append_analysis_adds_section(tmp_path):
    f = tmp_path / "pred.md"
    f.write_text("---\ntitle: Test\n---\n\nBody\n", encoding="utf-8")
    append_analysis(f, "## Prediction Analysis\nGreat job.")
    text = f.read_text(encoding="utf-8")
    assert "Prediction Analysis" in text
    assert "Great job." in text


def test_append_analysis_skips_if_already_exists(tmp_path):
    f = tmp_path / "pred.md"
    original = "---\ntitle: T\n---\n\n## Prediction Analysis\nOld.\n"
    f.write_text(original, encoding="utf-8")
    append_analysis(f, "## Prediction Analysis\nNew.")
    text = f.read_text(encoding="utf-8")
    assert text.count("Prediction Analysis") == 1
    assert "Old." in text
    assert "New." not in text
