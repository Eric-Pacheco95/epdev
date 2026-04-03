"""
local_model.py -- Jarvis Local Model Integration Layer

Provides call_local() for routing inference to a local Ollama instance.
Uses only stdlib (urllib, json, socket). Never calls external processes or third-party HTTP libs.
"""

import json
import socket
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LocalModelUnavailable(Exception):
    """Raised when Ollama is unreachable or returns an error."""


class LocalModelTimeout(LocalModelUnavailable):
    """Raised when the Ollama request times out (subclass of LocalModelUnavailable)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path:
    """Walk up from this file's location until local_model_config.json is found."""
    current = Path(__file__).resolve().parent
    while True:
        candidate = current / "local_model_config.json"
        if candidate.exists():
            return current
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(
                "local_model_config.json not found in any parent directory of "
                + str(Path(__file__))
            )
        current = parent


def _load_config() -> dict:
    """Read local_model_config.json fresh on every call -- no module-level caching."""
    repo_root = _find_repo_root()
    config_path = repo_root / "local_model_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _log_fallback(task_type: str, reason: str) -> None:
    """Append a single fallback line to data/local_routing.log atomically."""
    repo_root = _find_repo_root()
    log_path = repo_root / "data" / "local_routing.log"
    # Ensure data/ directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)
    iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Sanitize to ASCII before writing
    line = (
        f"{iso_ts} FALLBACK task_type={task_type} reason={reason}\n"
        .encode("ascii", errors="replace")
        .decode("ascii")
    )
    with open(log_path, "a", encoding="ascii") as fh:
        fh.write(line)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_ollama_health() -> bool:
    """
    GET {base_url}/api/tags with a 2s timeout.
    Returns False on any error; True if the endpoint responds 200.
    """
    try:
        cfg = _load_config()
        url = f"{cfg['base_url']}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def call_local(prompt: str, task_type: str, timeout_s: int = None) -> str:
    """
    POST prompt to local Ollama instance and return the response text.

    Parameters
    ----------
    prompt    : The full prompt string to send.
    task_type : Label used for logging/routing (e.g. 'isc_format_validation').
    timeout_s : Override the config max_response_wait_s if provided.

    Returns
    -------
    ASCII-safe response string from the model.

    Raises
    ------
    LocalModelTimeout       -- if the request exceeds the timeout.
    LocalModelUnavailable   -- on any other HTTP/network error.
    """
    cfg = _load_config()
    base_url = cfg["base_url"]
    if not base_url.startswith(("http://localhost", "http://127.0.0.1")):
        raise LocalModelUnavailable(f"base_url must be localhost, got: {base_url}")
    timeout = timeout_s if timeout_s is not None else cfg.get("max_response_wait_s", 120)

    payload = json.dumps({
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{cfg['base_url']}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body.get("response", "")
            # Guarantee ASCII-safe output (Windows cp1252 safety)
            return text.encode("ascii", errors="replace").decode("ascii")

    except socket.timeout as e:
        _log_fallback(task_type, f"timeout after {timeout}s")
        raise LocalModelTimeout(f"Ollama timed out after {timeout}s") from e

    except Exception as e:
        _log_fallback(task_type, str(e))
        raise LocalModelUnavailable(str(e)) from e
