"""Tests for tools/scripts/lib/task_proposals.py — validate, append, count_by_status."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.lib.task_proposals import count_by_status, proposal_append, validate_proposal


# ---------------------------------------------------------------------------
# validate_proposal
# ---------------------------------------------------------------------------

def test_validate_accepts_minimal_valid():
    errs = validate_proposal({"title": "Fix bug", "rationale": "signal S", "source": "auto"})
    assert errs == []


def test_validate_requires_title():
    errs = validate_proposal({"rationale": "R", "source": "auto"})
    assert any("title" in e for e in errs)


def test_validate_rejects_empty_title():
    errs = validate_proposal({"title": "  ", "rationale": "R"})
    assert any("title" in e for e in errs)


def test_validate_requires_rationale():
    errs = validate_proposal({"title": "Fix bug", "source": "auto"})
    assert any("rationale" in e for e in errs)


def test_validate_rejects_empty_rationale():
    errs = validate_proposal({"title": "X", "rationale": ""})
    assert any("rationale" in e for e in errs)


def test_validate_source_must_be_string():
    errs = validate_proposal({"title": "X", "rationale": "R", "source": 42})
    assert any("source" in e for e in errs)


def test_validate_suggested_task_must_be_dict_or_omitted():
    errs = validate_proposal({"title": "X", "rationale": "R", "suggested_task": "not-dict"})
    assert any("suggested_task" in e for e in errs)


def test_validate_accepts_suggested_task_as_dict():
    errs = validate_proposal({"title": "X", "rationale": "R", "suggested_task": {"key": "val"}})
    assert errs == []


def test_validate_accepts_no_source_field():
    # source defaults to "unknown" in append; validate just checks it's a str if present
    errs = validate_proposal({"title": "X", "rationale": "R"})
    assert errs == []


# ---------------------------------------------------------------------------
# proposal_append (env-gated)
# ---------------------------------------------------------------------------

def test_proposal_append_skips_when_flag_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_TASK_PROPOSALS_ENABLED", raising=False)
    p = tmp_path / "proposals.jsonl"
    result = proposal_append({"title": "X", "rationale": "R"}, path=p)
    assert result is None
    assert not p.exists()


def test_proposal_append_writes_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_TASK_PROPOSALS_ENABLED", "true")
    p = tmp_path / "proposals.jsonl"
    rec = proposal_append({"title": "X", "rationale": "R", "source": "test"}, path=p)
    assert rec is not None
    assert p.exists()
    row = json.loads(p.read_text(encoding="utf-8").strip())
    assert row["title"] == "X"
    assert row["status"] == "pending"
    assert "id" in row
    assert "created" in row


def test_proposal_append_raises_on_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_TASK_PROPOSALS_ENABLED", "1")
    p = tmp_path / "proposals.jsonl"
    import pytest
    with pytest.raises(ValueError):
        proposal_append({"title": ""}, path=p)


def test_proposal_append_accepts_true_and_yes(tmp_path, monkeypatch):
    for flag in ("1", "yes", "true"):
        monkeypatch.setenv("JARVIS_TASK_PROPOSALS_ENABLED", flag)
        p = tmp_path / f"proposals_{flag}.jsonl"
        rec = proposal_append({"title": "X", "rationale": "R"}, path=p)
        assert rec is not None


# ---------------------------------------------------------------------------
# count_by_status
# ---------------------------------------------------------------------------

def test_count_by_status_missing_file(tmp_path):
    p = tmp_path / "nope.jsonl"
    assert count_by_status(path=p) == {}


def test_count_by_status_aggregates(tmp_path):
    p = tmp_path / "proposals.jsonl"
    rows = [
        {"status": "pending"},
        {"status": "pending"},
        {"status": "approved"},
        {"status": "rejected"},
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    counts = count_by_status(path=p)
    assert counts["pending"] == 2
    assert counts["approved"] == 1
    assert counts["rejected"] == 1


def test_count_by_status_skips_bad_json(tmp_path):
    p = tmp_path / "proposals.jsonl"
    p.write_text(
        "not json\n" + json.dumps({"status": "pending"}) + "\n",
        encoding="utf-8",
    )
    counts = count_by_status(path=p)
    assert counts.get("pending") == 1


def test_count_by_status_missing_status_uses_unknown(tmp_path):
    p = tmp_path / "proposals.jsonl"
    p.write_text(json.dumps({"title": "no status field"}) + "\n", encoding="utf-8")
    counts = count_by_status(path=p)
    assert counts.get("unknown") == 1
