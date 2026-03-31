"""Output sanitizer for script->LLM boundary.

Strips prompt injection patterns and redacts secret-matching values
from structured JSON output before the LLM processes it.

Reuses patterns from security/validators/validate_tool_use.py.

Usage:
    from tools.scripts.lib.output_sanitizer import sanitize
    clean_json = sanitize(raw_json_string)
"""

from __future__ import annotations

import json
import re

# Prompt injection patterns (from validate_tool_use.py)
INJECTION_SUBSTRINGS = (
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "disregard all previous",
    "you are now",
    "new instructions:",
    "system prompt",
    "developer message",
    "sudo ignore",
    "dan mode",
    "jailbreak",
)

# Secret patterns — match common key/token formats
SECRET_PATTERNS = [
    re.compile(r"(?:sk|pk|api|token|key|secret|password|passwd|auth)[-_]?[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"xox[bpsa]-[a-zA-Z0-9-]+"),  # Slack tokens
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PATs
    re.compile(r"glpat-[a-zA-Z0-9\-_]{20,}"),  # GitLab PATs
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access keys
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"ntfy://[a-zA-Z0-9]+"),  # ntfy topics with secrets
]


def _sanitize_value(value: str) -> str:
    """Sanitize a single string value."""
    lowered = value.lower()

    # Check for injection patterns
    for pattern in INJECTION_SUBSTRINGS:
        if pattern in lowered:
            value = value.replace(
                next(v for v in [value[i:i+len(pattern)]
                      for i in range(len(value) - len(pattern) + 1)]
                     if v.lower() == pattern),
                "[REDACTED:injection]"
            )

    # Check for secret patterns
    for pat in SECRET_PATTERNS:
        value = pat.sub("[REDACTED:secret]", value)

    return value


def _sanitize_obj(obj):
    """Recursively sanitize all string values in a JSON-like structure."""
    if isinstance(obj, str):
        return _sanitize_value(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_obj(item) for item in obj]
    return obj


def sanitize(json_string: str) -> str:
    """Sanitize a JSON string by redacting injection patterns and secrets.

    Args:
        json_string: Raw JSON string from a script's stdout.

    Returns:
        Sanitized JSON string safe for LLM consumption.
    """
    try:
        data = json.loads(json_string)
        sanitized = _sanitize_obj(data)
        return json.dumps(sanitized, ensure_ascii=True)
    except json.JSONDecodeError:
        # If not valid JSON, sanitize as plain text
        result = json_string
        for pattern in INJECTION_SUBSTRINGS:
            result = re.sub(re.escape(pattern), "[REDACTED:injection]", result, flags=re.IGNORECASE)
        for pat in SECRET_PATTERNS:
            result = pat.sub("[REDACTED:secret]", result)
        return result
