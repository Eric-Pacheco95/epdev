"""Tests for tools/scripts/local_model.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.local_model import (
    LocalModelUnavailable,
    LocalModelTimeout,
    check_ollama_health,
    call_local,
    _log_fallback,
)
import tools.scripts.local_model as lm

_BASE_CONFIG = {
    "base_url": "http://127.0.0.1:11434",
    "model": "test-model",
    "max_response_wait_s": 10,
    "fallback_on_error": True,
}


# --- Exception hierarchy ---

def test_timeout_is_unavailable():
    assert issubclass(LocalModelTimeout, LocalModelUnavailable)


def test_exception_message():
    exc = LocalModelUnavailable("cannot reach")
    assert "cannot reach" in str(exc)


# --- check_ollama_health ---

def test_health_true_on_200(tmp_path):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    with patch.object(lm, "_load_config", return_value=_BASE_CONFIG), \
         patch.object(lm, "_find_repo_root", return_value=tmp_path), \
         patch("tools.scripts.local_model.urllib.request.urlopen", return_value=mock_resp):
        assert check_ollama_health() is True


def test_health_false_on_exception(tmp_path):
    with patch.object(lm, "_load_config", return_value=_BASE_CONFIG), \
         patch.object(lm, "_find_repo_root", return_value=tmp_path), \
         patch("tools.scripts.local_model.urllib.request.urlopen", side_effect=OSError("conn refused")):
        assert check_ollama_health() is False


def test_health_false_on_config_error():
    with patch.object(lm, "_load_config", side_effect=FileNotFoundError("no config")):
        assert check_ollama_health() is False


# --- call_local ---

def test_call_local_rejects_non_localhost(tmp_path):
    import pytest
    cfg = {**_BASE_CONFIG, "base_url": "http://external.api.com"}
    with patch.object(lm, "_load_config", return_value=cfg), \
         patch.object(lm, "_find_repo_root", return_value=tmp_path):
        with pytest.raises(LocalModelUnavailable, match="localhost"):
            call_local("prompt", "task_type")


def test_call_local_returns_ascii_text(tmp_path):
    response_body = json.dumps({"response": "hello world"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = response_body

    with patch.object(lm, "_load_config", return_value=_BASE_CONFIG), \
         patch.object(lm, "_find_repo_root", return_value=tmp_path), \
         patch("tools.scripts.local_model.urllib.request.urlopen", return_value=mock_resp):
        result = call_local("my prompt", "summarization")

    assert result == "hello world"


def test_call_local_timeout_raises(tmp_path):
    import socket, pytest
    with patch.object(lm, "_load_config", return_value=_BASE_CONFIG), \
         patch.object(lm, "_find_repo_root", return_value=tmp_path), \
         patch("tools.scripts.local_model.urllib.request.urlopen", side_effect=socket.timeout("timed out")), \
         patch.object(lm, "_log_fallback"):
        with pytest.raises(LocalModelTimeout):
            call_local("prompt", "task")


# --- _log_fallback ---

def test_log_fallback_creates_file(tmp_path):
    with patch.object(lm, "_find_repo_root", return_value=tmp_path):
        _log_fallback("test_task", "connection refused")

    log_path = tmp_path / "data" / "local_routing.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="ascii")
    assert "FALLBACK" in content
    assert "test_task" in content
