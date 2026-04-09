"""Tests for ntfy_notify.py -- push notification helper."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "ntfy_notify.py"


def _load():
    spec = importlib.util.spec_from_file_location("ntfy_notify", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestNtfyNotifyPush:
    def test_returns_false_when_no_topic(self, monkeypatch):
        monkeypatch.delenv("NTFY_TOPIC", raising=False)
        mod = _load()
        result = mod.push("hello")
        assert result is False

    def test_returns_false_when_topic_is_blank(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "   ")
        mod = _load()
        result = mod.push("hello")
        assert result is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")
        mod = _load()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read = lambda: b"ok"

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = mod.push("Test title", "Test body")
        assert result is True

    def test_returns_false_on_network_error(self, monkeypatch):
        import urllib.error
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")
        mod = _load()

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = mod.push("fail test")
        assert result is False

    def test_payload_includes_tags(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "my-topic")
        mod = _load()

        captured_data = {}

        def fake_urlopen(req, timeout=None):
            import json
            captured_data["payload"] = json.loads(req.data)
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            m.read = lambda: b"ok"
            return m

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mod.push("t", "b", priority="high", tags=["brain", "warning"])

        assert captured_data["payload"]["tags"] == ["brain", "warning"]
        assert captured_data["payload"]["priority"] == "high"

    def test_payload_omits_message_when_empty_body(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "my-topic")
        mod = _load()
        captured_data = {}

        def fake_urlopen(req, timeout=None):
            import json
            captured_data["payload"] = json.loads(req.data)
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            m.read = lambda: b"ok"
            return m

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mod.push("title only")

        assert "message" not in captured_data["payload"]

    def test_uses_custom_server(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "t")
        monkeypatch.setenv("NTFY_SERVER", "https://my.custom.server")
        mod = _load()
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            m.read = lambda: b"ok"
            return m

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mod.push("hello")

        assert "my.custom.server" in captured["url"]
