"""Tests for tools/scripts/lib/skill_launcher_lib.py pure functions."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.lib.skill_launcher_lib import (
    parse_tokens_from_stream_json,
    estimate_cost_usd,
    write_park_gate,
    write_run_log,
    build_prompt,
)

_DEFAULT_MODEL = "claude-sonnet-4-6"


class TestParseTokensFromStreamJson:
    def test_empty_text_returns_zeros(self):
        tokens, model = parse_tokens_from_stream_json("")
        assert tokens == 0
        assert model == _DEFAULT_MODEL

    def test_skips_malformed_lines(self):
        tokens, model = parse_tokens_from_stream_json("not json\n{bad")
        assert tokens == 0

    def test_sums_input_and_output_tokens(self):
        line = json.dumps({"usage": {"input_tokens": 100, "output_tokens": 50}})
        tokens, _ = parse_tokens_from_stream_json(line)
        assert tokens == 150

    def test_accumulates_multiple_lines(self):
        lines = [
            json.dumps({"usage": {"input_tokens": 100, "output_tokens": 50}}),
            json.dumps({"usage": {"input_tokens": 200, "output_tokens": 75}}),
        ]
        tokens, _ = parse_tokens_from_stream_json("\n".join(lines))
        assert tokens == 425

    def test_detects_model_from_message(self):
        line = json.dumps({"message": {"model": "claude-opus-4-7", "usage": {}}})
        _, model = parse_tokens_from_stream_json(line)
        assert model == "claude-opus-4-7"

    def test_detects_model_at_top_level(self):
        line = json.dumps({"model": "claude-haiku-4-5", "usage": {}})
        _, model = parse_tokens_from_stream_json(line)
        assert model == "claude-haiku-4-5"

    def test_ignores_blank_lines(self):
        text = "\n\n" + json.dumps({"usage": {"input_tokens": 10, "output_tokens": 5}}) + "\n\n"
        tokens, _ = parse_tokens_from_stream_json(text)
        assert tokens == 15

    def test_usage_inside_message_dict(self):
        line = json.dumps({"message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 300, "output_tokens": 100}}})
        tokens, model = parse_tokens_from_stream_json(line)
        assert tokens == 400
        assert model == "claude-sonnet-4-6"


class TestEstimateCostUsd:
    def test_returns_float(self):
        result = estimate_cost_usd(1000, _DEFAULT_MODEL)
        assert isinstance(result, float)

    def test_zero_tokens_is_zero_cost(self):
        result = estimate_cost_usd(0, _DEFAULT_MODEL)
        assert result == 0.0

    def test_unknown_model_falls_back_to_zero(self):
        # Unknown model with no pricing file -> should not raise, returns 0.0
        result = estimate_cost_usd(100, "nonexistent-model-xyz")
        assert isinstance(result, float)


class TestWriteParkGate:
    def test_creates_json_file(self, tmp_path):
        path = write_park_gate(
            tmp_path, "abc123", "autoresearch", "topic here",
            "verifier_failed", "python tool.py", "2026-04-26T00:00:00Z", 500, 0.25
        )
        assert path.exists()
        assert path.suffix == ".json"

    def test_file_contains_expected_fields(self, tmp_path):
        path = write_park_gate(
            tmp_path, "def456", "autoresearch", "my topic",
            "timeout", "cmd here", "2026-04-26T01:00:00Z", 1000, 1.5
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["run_id"] == "def456"
        assert data["skill"] == "autoresearch"
        assert data["topic"] == "my topic"
        assert data["exit_reason"] == "timeout"
        assert data["tokens_spent"] == 1000
        assert data["cost_usd"] == 1.5

    def test_creates_parent_directory(self, tmp_path):
        sub = tmp_path / "park" / "gates"
        write_park_gate(sub, "ghi789", "autoresearch", "topic", "success", "cmd", "ts", 0, 0.0)
        assert sub.is_dir()


class TestBuildPrompt:
    def test_contains_skill_command_tag(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        result = build_prompt("autoresearch", "some topic", 1.5)
        assert "<command-name>/autoresearch</command-name>" in result

    def test_contains_cost_cap(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        result = build_prompt("research", "topic", 2.0)
        assert "$2.0 USD" in result

    def test_contains_input_section(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        result = build_prompt("research", "my topic here", 1.0)
        assert "INPUT:" in result
        assert "my topic here" in result

    def test_contains_autonomous_rules(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        result = build_prompt("research", "topic", 1.0)
        assert "AUTONOMOUS EXECUTION RULES" in result
        assert "NEVER ask Eric" in result

    def test_includes_skill_definition_when_file_exists(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        skill_dir = tmp_path / "research"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Research skill content\n", encoding="utf-8")
        result = build_prompt("research", "topic", 1.0)
        assert "Research skill content" in result

    def test_truncated_to_90000_chars(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        skill_dir = tmp_path / "big"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("x" * 100000, encoding="utf-8")
        result = build_prompt("big", "topic", 1.0)
        assert len(result) <= 90000

    def test_no_skill_file_graceful(self, monkeypatch, tmp_path):
        import tools.scripts.lib.skill_launcher_lib as mod
        monkeypatch.setattr(mod, "_SKILLS_DIR", tmp_path)
        result = build_prompt("nonexistent_skill", "topic", 1.0)
        assert "SKILL DEFINITION:" in result


class TestWriteRunLog:
    def test_creates_json_file(self, tmp_path):
        write_run_log(tmp_path, "run001", "claude-sonnet-4-6", "claude-opus-4-7", "s1", "s2")
        assert (tmp_path / "run001.json").exists()

    def test_file_contains_model_fields(self, tmp_path):
        write_run_log(tmp_path, "run002", "claude-sonnet-4-6", "claude-opus-4-7", "sess-gen", "sess-qg")
        data = json.loads((tmp_path / "run002.json").read_text(encoding="utf-8"))
        assert data["generator_model"] == "claude-sonnet-4-6"
        assert data["quality_gate_model"] == "claude-opus-4-7"
        assert data["generator_session"] == "sess-gen"
        assert data["quality_gate_session"] == "sess-qg"
