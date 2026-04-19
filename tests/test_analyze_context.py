"""Tests for analyze_context pure functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.analyze_context import est_tokens


class TestEstTokens:
    def test_empty_string(self):
        assert est_tokens("") == 0

    def test_four_chars_is_one_token(self):
        assert est_tokens("abcd") == 1

    def test_eight_chars_is_two_tokens(self):
        assert est_tokens("abcdefgh") == 2

    def test_non_string_converted(self):
        result = est_tokens({"key": "val"})
        assert isinstance(result, int)
        assert result > 0

    def test_integer_input(self):
        result = est_tokens(12345)
        assert result == len("12345") // 4

    def test_floor_division(self):
        assert est_tokens("abc") == 0
        assert est_tokens("abcde") == 1
