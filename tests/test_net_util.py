"""Tests for lib/net_util.format_top_holders() -- pure formatting function."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.net_util import format_top_holders, Holder


class TestFormatTopHolders:
    def test_empty_returns_no_data_message(self):
        assert format_top_holders([]) == "no per-process data"

    def test_single_holder_without_cmd(self):
        h = Holder(name="python", count=5, cmd_hint="")
        result = format_top_holders([h])
        assert result == "python=5"

    def test_single_holder_with_cmd(self):
        h = Holder(name="python", count=3, cmd_hint="my_script.py")
        result = format_top_holders([h])
        assert "python(my_script.py)=3" in result

    def test_cmd_truncated_to_max_chars(self):
        long_cmd = "a" * 100
        h = Holder(name="node", count=2, cmd_hint=long_cmd)
        result = format_top_holders([h], max_cmd_chars=10)
        assert "node(aaaaaaaaaa)=2" in result

    def test_multiple_holders_joined_by_comma(self):
        holders = [
            Holder(name="python", count=5, cmd_hint=""),
            Holder(name="node", count=3, cmd_hint=""),
        ]
        result = format_top_holders(holders)
        assert "python=5" in result
        assert "node=3" in result
        assert ", " in result

    def test_python_exe_prefix_stripped(self):
        h = Holder(name="python", count=1, cmd_hint="python.exe my_script.py")
        result = format_top_holders([h])
        assert "my_script.py" in result
        assert "python.exe" not in result

    def test_whitespace_only_cmd_treated_as_no_cmd(self):
        h = Holder(name="python", count=7, cmd_hint="   ")
        result = format_top_holders([h])
        assert result == "python=7"

    def test_quoted_python_exe_prefix_stripped(self):
        h = Holder(name="python", count=1, cmd_hint='python.exe" my_script.py')
        result = format_top_holders([h])
        assert "my_script.py" in result
        assert "python.exe" not in result

    def test_cmd_exactly_at_max_chars(self):
        cmd = "a" * 10
        h = Holder(name="node", count=1, cmd_hint=cmd)
        result = format_top_holders([h], max_cmd_chars=10)
        assert "aaaaaaaaaa" in result

    def test_large_count_formatted(self):
        h = Holder(name="chrome", count=1000, cmd_hint="")
        result = format_top_holders([h])
        assert "chrome=1000" in result

    def test_holder_namedtuple_fields(self):
        h = Holder(name="python", count=5, cmd_hint="script.py")
        assert h.name == "python"
        assert h.count == 5
        assert h.cmd_hint == "script.py"

    def test_three_holders_all_appear(self):
        holders = [
            Holder(name="python", count=5, cmd_hint=""),
            Holder(name="node", count=3, cmd_hint=""),
            Holder(name="chrome", count=1, cmd_hint=""),
        ]
        result = format_top_holders(holders)
        assert "python=5" in result
        assert "node=3" in result
        assert "chrome=1" in result
