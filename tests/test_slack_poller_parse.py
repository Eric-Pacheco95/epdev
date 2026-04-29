"""Tests for slack_poller.py -- _parse_message pure function."""

from tools.scripts.slack_poller import _parse_message


def test_parse_valid_url_with_depth():
    url, depth, error = _parse_message("https://example.com/article --normal")
    assert url == "https://example.com/article"
    assert depth == "normal"
    assert error is None


def test_parse_quick_depth():
    url, depth, error = _parse_message("https://example.com --quick")
    assert depth == "quick"
    assert error is None


def test_parse_deep_depth():
    url, depth, error = _parse_message("https://example.com --deep")
    assert depth == "deep"
    assert error is None


def test_parse_no_url_no_flag():
    url, depth, error = _parse_message("just some random text")
    assert url is None
    assert depth is None
    assert error is not None
    assert "#jarvis-inbox" in error


def test_parse_depth_flag_no_url():
    url, depth, error = _parse_message("--normal")
    assert url is None
    assert error is not None
    assert "No URL found" in error


def test_parse_url_no_depth_flag():
    url, depth, error = _parse_message("https://example.com")
    assert url is None
    assert error is not None
    assert "--quick" in error
    assert "--normal" in error
    assert "--deep" in error


def test_parse_case_insensitive_flag_matching():
    """Depth flags are matched case-insensitively."""
    url, depth, error = _parse_message("https://example.com --NORMAL")
    assert error is None
    assert depth is not None  # flag matched regardless of case


def test_parse_first_depth_flag_wins():
    url, depth, error = _parse_message("https://example.com --quick --deep")
    assert error is None
    assert depth == "quick"


def test_parse_url_with_trailing_path():
    url, depth, error = _parse_message("https://example.com/path/to/article --normal")
    assert url == "https://example.com/path/to/article"
    assert depth == "normal"


def test_parse_url_returned_without_dashes():
    url, depth, error = _parse_message("https://example.com --deep")
    assert depth == "deep"
    assert not depth.startswith("-")


def test_parse_extra_text_around_url():
    url, depth, error = _parse_message("Check this out https://example.com/post --normal please")
    assert url is not None
    assert depth == "normal"
    assert error is None


def test_parse_empty_string():
    url, depth, error = _parse_message("")
    assert url is None
    assert depth is None
    assert error is not None
