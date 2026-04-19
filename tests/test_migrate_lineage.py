"""Tests for migrate_lineage pure functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.migrate_lineage import (
    strip_signal_prefix,
    is_old_schema,
    is_new_schema,
    migrate,
)


class TestStripSignalPrefix:
    def test_strips_processed_prefix(self):
        assert strip_signal_prefix("memory/learning/signals/processed/foo.md") == "foo.md"

    def test_strips_signals_prefix(self):
        assert strip_signal_prefix("memory/learning/signals/bar.md") == "bar.md"

    def test_bare_filename_unchanged(self):
        assert strip_signal_prefix("baz.md") == "baz.md"

    def test_backslash_path_normalized(self):
        raw = "memory" + chr(92) + "learning" + chr(92) + "signals" + chr(92) + "processed" + chr(92) + "x.md"
        assert strip_signal_prefix(raw) == "x.md"


class TestSchemaDetection:
    def test_old_schema_detected(self):
        assert is_old_schema({"signal_filename": "a.md", "synthesis_filename": "s.md"}) is True

    def test_new_schema_detected(self):
        assert is_new_schema({"synthesis_id": "2026-04-09", "signals": []}) is True

    def test_old_schema_not_new(self):
        assert is_new_schema({"signal_filename": "a.md"}) is False

    def test_new_schema_not_old(self):
        assert is_old_schema({"synthesis_id": "x", "signals": []}) is False


class TestMigrate:
    def test_old_schema_grouped_by_synthesis(self):
        old1 = json.dumps({"signal_filename": "memory/learning/signals/a.md", "synthesis_filename": "s1.md", "date": "2026-01-01"})
        old2 = json.dumps({"signal_filename": "memory/learning/signals/b.md", "synthesis_filename": "s1.md", "date": "2026-01-01"})
        result = migrate([old1, old2])
        assert len(result) == 1
        assert set(result[0]["signals"]) == {"a.md", "b.md"}

    def test_new_schema_passes_through(self):
        rec = json.dumps({"synthesis_id": "2026-04-09", "signals": ["x.md"], "signal_count": 1})
        result = migrate([rec])
        assert len(result) == 1
        assert result[0]["synthesis_id"] == "2026-04-09"

    def test_blank_lines_skipped(self):
        rec = json.dumps({"synthesis_id": "2026-04-09", "signals": [], "signal_count": 0})
        result = migrate(["", rec, ""])
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        assert migrate([]) == []
