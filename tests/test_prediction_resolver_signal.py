"""Tests for prediction_resolver.py -- write_resolution_signal."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.prediction_resolver as pr


def _make_fm(domain="geopolitics", question="Will X happen?", backtested=False):
    return {"domain": domain, "question": question, "backtested": backtested}


class TestWriteResolutionSignal:
    def test_creates_signal_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "2026-04-01_test-pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "note")
        assert result.exists()

    def test_returns_path_object(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "prediction.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        assert isinstance(result, Path)

    def test_correct_verdict_rating_7(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        content = result.read_text(encoding="utf-8")
        assert "rating: 7" in content

    def test_incorrect_verdict_rating_5(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "incorrect", "")
        content = result.read_text(encoding="utf-8")
        assert "rating: 5" in content

    def test_partial_verdict_rating_6(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "partial", "")
        content = result.read_text(encoding="utf-8")
        assert "rating: 6" in content

    def test_backtested_flag_lowers_rating(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm(backtested=True)
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        content = result.read_text(encoding="utf-8")
        assert "rating: 6" in content
        assert "backtested: true" in content

    def test_backtested_weight_is_half(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm(backtested=True)
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        content = result.read_text(encoding="utf-8")
        assert "weight: 0.5" in content

    def test_forward_weight_is_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm(backtested=False)
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        content = result.read_text(encoding="utf-8")
        assert "weight: 1.0" in content

    def test_domain_in_signal_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm(domain="crypto")
        pred_path = tmp_path / "pred.md"
        result = pr.write_resolution_signal(fm, pred_path, "correct", "")
        content = result.read_text(encoding="utf-8")
        assert "domain: crypto" in content

    def test_dedup_on_collision(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "SIGNALS_DIR", tmp_path)
        fm = _make_fm()
        pred_path = tmp_path / "pred.md"
        r1 = pr.write_resolution_signal(fm, pred_path, "correct", "")
        r2 = pr.write_resolution_signal(fm, pred_path, "correct", "")
        assert r1 != r2
        assert r1.exists()
        assert r2.exists()
