"""Tests for tools/scripts/task_proposal.py main()."""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.task_proposal as tp


def _run_main(stdin_text, proposal_return=None, proposal_raises=None):
    fake_stdin = io.StringIO(stdin_text)
    mock_append = MagicMock()
    if proposal_raises:
        mock_append.side_effect = proposal_raises
    else:
        mock_append.return_value = proposal_return

    with patch.object(sys, "stdin", fake_stdin), \
         patch("tools.scripts.task_proposal.proposal_append", mock_append, create=True):
        # Inject into the module's import namespace
        import tools.scripts.lib.task_proposals as tpl_mod
        with patch.object(tpl_mod, "proposal_append", mock_append):
            return tp.main()


def test_empty_stdin_returns_1():
    fake_stdin = io.StringIO("")
    with patch.object(sys, "stdin", fake_stdin):
        assert tp.main() == 1


def test_invalid_json_returns_1():
    fake_stdin = io.StringIO("not json")
    with patch.object(sys, "stdin", fake_stdin):
        assert tp.main() == 1


def test_valid_json_success():
    record = {"title": "Fix bug", "rationale": "signal S", "source": "manual"}
    result = {"id": "1", **record}
    fake_stdin = io.StringIO(json.dumps(record))
    with patch.object(sys, "stdin", fake_stdin), \
         patch("tools.scripts.lib.task_proposals.proposal_append", return_value=result):
        ret = tp.main()
    assert ret == 0


def test_none_return_from_append_returns_2():
    record = {"title": "X"}
    fake_stdin = io.StringIO(json.dumps(record))
    with patch.object(sys, "stdin", fake_stdin), \
         patch("tools.scripts.lib.task_proposals.proposal_append", return_value=None):
        ret = tp.main()
    assert ret == 2


def test_valueerror_from_append_returns_1():
    record = {"title": "X"}
    fake_stdin = io.StringIO(json.dumps(record))
    with patch.object(sys, "stdin", fake_stdin), \
         patch("tools.scripts.lib.task_proposals.proposal_append", side_effect=ValueError("bad")):
        ret = tp.main()
    assert ret == 1
