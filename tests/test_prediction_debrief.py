"""Tests for prediction_debrief.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tools.scripts.prediction_debrief import (
    generate_draft,
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
