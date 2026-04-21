"""Autonomous Read must not access data/financial/ (Phase 4→5 bridge)."""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def autonomous_env(monkeypatch):
    monkeypatch.setenv("JARVIS_SESSION_TYPE", "autonomous")
    yield
    monkeypatch.delenv("JARVIS_SESSION_TYPE", raising=False)


def test_blocks_read_financial_snapshot(autonomous_env, monkeypatch):
    from security.validators import validate_tool_use

    monkeypatch.delenv("JARVIS_WORKTREE_ROOT", raising=False)
    hit = validate_tool_use._check_autonomous_read_secrets(
        "Read",
        {"file_path": r"C:\Users\x\epdev\data\financial\snapshot.jsonl"},
    )
    assert hit is not None
    assert hit["decision"] == "block"
    assert "financial" in hit["reason"].lower()


def test_allows_read_financial_interactive(monkeypatch):
    from security.validators import validate_tool_use

    monkeypatch.delenv("JARVIS_SESSION_TYPE", raising=False)
    hit = validate_tool_use._check_autonomous_read_secrets(
        "Read",
        {"file_path": "data/financial/snapshot.jsonl"},
    )
    assert hit is None
