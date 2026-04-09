"""Tests for voice_inbox_sync.py -- sync logic."""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "voice_inbox_sync.py"


def _load():
    spec = importlib.util.spec_from_file_location("voice_inbox_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestResolveWatchDir:
    def test_returns_none_when_no_sources_exist(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", tmp_path / "no_icloud")
        monkeypatch.setattr(mod, "ONEDRIVE_WATCH", tmp_path / "no_onedrive")
        watch, transport = mod._resolve_watch_dir()
        assert watch is None
        assert transport == "none"

    def test_prefers_icloud_over_onedrive(self, tmp_path, monkeypatch):
        icloud = tmp_path / "icloud"
        icloud.mkdir()
        onedrive = tmp_path / "onedrive"
        onedrive.mkdir()
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", icloud)
        monkeypatch.setattr(mod, "ONEDRIVE_WATCH", onedrive)
        watch, transport = mod._resolve_watch_dir()
        assert watch == icloud
        assert "iCloud" in transport

    def test_falls_back_to_onedrive(self, tmp_path, monkeypatch):
        onedrive = tmp_path / "onedrive"
        onedrive.mkdir()
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", tmp_path / "no_icloud")
        monkeypatch.setattr(mod, "ONEDRIVE_WATCH", onedrive)
        watch, transport = mod._resolve_watch_dir()
        assert watch == onedrive
        assert "OneDrive" in transport


class TestSync:
    def test_returns_0_when_no_watch_source(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", tmp_path / "no_icloud")
        monkeypatch.setattr(mod, "ONEDRIVE_WATCH", tmp_path / "no_onedrive")
        monkeypatch.setattr(mod, "INBOX_DIR", tmp_path / "inbox")
        monkeypatch.setattr(mod, "PROCESSED_MARKER", tmp_path / "inbox" / "processed")
        result = mod.sync()
        assert result == 0

    def test_copies_md_files_to_inbox(self, tmp_path, monkeypatch):
        watch = tmp_path / "watch"
        watch.mkdir()
        inbox = tmp_path / "inbox"
        processed = inbox / "processed"
        # Create a voice transcript
        (watch / "note.md").write_text("voice content")
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", watch)
        monkeypatch.setattr(mod, "INBOX_DIR", inbox)
        monkeypatch.setattr(mod, "PROCESSED_MARKER", processed)
        monkeypatch.setattr(mod, "ICLOUD_FILE", watch / "pai-voice-recording")
        result = mod.sync()
        assert result == 1
        assert (inbox / "note.md").exists()

    def test_copies_txt_files_to_inbox(self, tmp_path, monkeypatch):
        watch = tmp_path / "watch"
        watch.mkdir()
        inbox = tmp_path / "inbox"
        processed = inbox / "processed"
        (watch / "note.txt").write_text("text content")
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", watch)
        monkeypatch.setattr(mod, "INBOX_DIR", inbox)
        monkeypatch.setattr(mod, "PROCESSED_MARKER", processed)
        monkeypatch.setattr(mod, "ICLOUD_FILE", watch / "pai-voice-recording")
        result = mod.sync()
        assert result == 1

    def test_skips_already_synced_file(self, tmp_path, monkeypatch):
        watch = tmp_path / "watch"
        watch.mkdir()
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        processed = inbox / "processed"
        src = watch / "note.md"
        src.write_text("content")
        dest = inbox / "note.md"
        dest.write_text("same content")
        # Make dest newer than src
        future = time.time() + 10
        import os
        os.utime(dest, (future, future))
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", watch)
        monkeypatch.setattr(mod, "INBOX_DIR", inbox)
        monkeypatch.setattr(mod, "PROCESSED_MARKER", processed)
        monkeypatch.setattr(mod, "ICLOUD_FILE", watch / "pai-voice-recording")
        result = mod.sync()
        assert result == 0

    def test_overrides_stale_file_in_inbox(self, tmp_path, monkeypatch):
        watch = tmp_path / "watch"
        watch.mkdir()
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        processed = inbox / "processed"
        dest = inbox / "note.md"
        dest.write_text("old content")
        import os, time as _time
        past = _time.time() - 100
        os.utime(dest, (past, past))
        src = watch / "note.md"
        src.write_text("new content")
        mod = _load()
        monkeypatch.setattr(mod, "ICLOUD_SHORTCUTS", watch)
        monkeypatch.setattr(mod, "INBOX_DIR", inbox)
        monkeypatch.setattr(mod, "PROCESSED_MARKER", processed)
        monkeypatch.setattr(mod, "ICLOUD_FILE", watch / "pai-voice-recording")
        result = mod.sync()
        assert result == 1
        assert (inbox / "note.md").read_text() == "new content"
