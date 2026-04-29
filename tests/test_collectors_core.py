"""Tests for collectors.core -- _resolve_path, _result, and pure collector logic."""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tools" / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

from collectors.core import _resolve_path, _result


FAKE_ROOT = Path(__file__).resolve().parents[1]


def test_resolve_path_relative():
    result = _resolve_path("tools/scripts/foo.py", FAKE_ROOT)
    assert result == (FAKE_ROOT / "tools" / "scripts" / "foo.py").resolve()


def test_resolve_path_traversal_blocked():
    with pytest.raises(ValueError, match="traversal blocked"):
        _resolve_path("../../etc/passwd", FAKE_ROOT)


def test_result_basic():
    r = _result("my_metric", 42, "count")
    assert r == {"name": "my_metric", "value": 42, "unit": "count", "detail": None}


def test_result_with_detail():
    r = _result("m", 3.14, "ratio", "some detail")
    assert r["detail"] == "some detail"
    assert r["value"] == 3.14
