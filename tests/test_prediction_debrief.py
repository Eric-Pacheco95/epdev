"""Tests for prediction_debrief.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import tools.scripts.prediction_debrief as pd_mod
from tools.scripts.prediction_debrief import (
    generate_draft,
    parse_frontmatter,
    load_state,
    save_state,
    DEBRIEF_EVERY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_resolved(question="Will X happen?", domain="market", outcome="correct",
                   pred_date="2026-03-01", resolved_date="2026-04-01", note=""):
    return {
        "question": question,
        "domain": domain,
        "outcome_label": outcome,
        "date": pred_date,
        "resolved_date": resolved_date,
        "resolution_note": note,
        "_path": Path(f"data/predictions/{pred_date}-test.md"),
        "_body": "",
    }


# ---------------------------------------------------------------------------
# generate_draft
# ---------------------------------------------------------------------------

def test_draft_contains_title():
    preds = [_make_resolved()]
    draft = generate_draft(preds, 1)
    assert "Prediction Debrief #1" in draft


def test_draft_contains_scorecard():
    preds = [
        _make_resolved(outcome="correct"),
        _make_resolved(outcome="wrong"),
        _make_resolved(outcome="partial"),
    ]
    draft = generate_draft(preds, 1)
    assert "Scorecard" in draft
    assert "| Correct | 1 |" in draft
    assert "| Wrong | 1 |" in draft
    assert "| Partial | 1 |" in draft


def test_draft_accuracy_calculation():
    preds = [
        _make_resolved(outcome="correct"),
        _make_resolved(outcome="correct"),
        _make_resolved(outcome="wrong"),
        _make_resolved(outcome="partial"),
    ]
    draft = generate_draft(preds, 1)
    # 2 correct + 0.5 partial = 2.5 / 4 = 62.5% -> rounds to 62%
    assert "62%" in draft or "63%" in draft


def test_draft_contains_domain_breakdown():
    preds = [
        _make_resolved(domain="market", outcome="correct"),
        _make_resolved(domain="geopolitics", outcome="wrong"),
    ]
    draft = generate_draft(preds, 1)
    assert "Market" in draft
    assert "Geopolitics" in draft


def test_draft_contains_individual_predictions():
    preds = [_make_resolved(question="Will BTC hit 100K?")]
    draft = generate_draft(preds, 1)
    assert "Will BTC hit 100K?" in draft
    assert "CORRECT" in draft


def test_draft_has_frontmatter():
    preds = [_make_resolved()]
    draft = generate_draft(preds, 1)
    assert draft.startswith("---")
    assert "status: draft" in draft
    assert "type: prediction-debrief" in draft


def test_draft_includes_resolution_note():
    preds = [_make_resolved(outcome="partial", note="Got direction right but timing wrong")]
    draft = generate_draft(preds, 1)
    assert "Got direction right" in draft


def test_debrief_every_constant():
    assert DEBRIEF_EVERY == 5


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter_parsed(self, tmp_path):
        p = tmp_path / "pred.md"
        p.write_text("---\nquestion: Will X?\nstatus: resolved\n---\nbody text\n", encoding="utf-8")
        result = parse_frontmatter(p)
        assert result is not None
        assert result["question"] == "Will X?"
        assert result["_body"] == "body text"

    def test_missing_file_returns_none(self, tmp_path):
        assert parse_frontmatter(tmp_path / "missing.md") is None

    def test_no_frontmatter_delimiter_returns_none(self, tmp_path):
        p = tmp_path / "pred.md"
        p.write_text("# Just a heading\nsome content\n", encoding="utf-8")
        assert parse_frontmatter(p) is None

    def test_incomplete_frontmatter_returns_none(self, tmp_path):
        p = tmp_path / "pred.md"
        p.write_text("---\nquestion: Will X?\n", encoding="utf-8")
        assert parse_frontmatter(p) is None

    def test_path_field_injected(self, tmp_path):
        p = tmp_path / "pred.md"
        p.write_text("---\nk: v\n---\nbody\n", encoding="utf-8")
        result = parse_frontmatter(p)
        assert result["_path"] == p


# ---------------------------------------------------------------------------
# load_state / save_state
# ---------------------------------------------------------------------------

class TestLoadSaveState:
    def test_load_state_missing_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pd_mod, "STATE_FILE", tmp_path / "missing.json")
        state = load_state()
        assert state["last_debrief_at_count"] == 0
        assert state["debriefs_written"] == 0

    def test_load_state_corrupt_returns_defaults(self, tmp_path, monkeypatch):
        f = tmp_path / "state.json"
        f.write_text("not json", encoding="utf-8")
        monkeypatch.setattr(pd_mod, "STATE_FILE", f)
        state = load_state()
        assert state["last_debrief_at_count"] == 0

    def test_save_load_roundtrip(self, tmp_path, monkeypatch):
        f = tmp_path / "state.json"
        monkeypatch.setattr(pd_mod, "STATE_FILE", f)
        save_state({"last_debrief_at_count": 15, "debriefs_written": 3})
        result = load_state()
        assert result["last_debrief_at_count"] == 15
        assert result["debriefs_written"] == 3
