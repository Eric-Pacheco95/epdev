"""Tests for jarvis_dispatcher.py -- validate_context_files security gate."""

from tools.scripts.jarvis_dispatcher import validate_context_files


def test_no_context_files():
    assert validate_context_files({"id": "T1"}) is True


def test_empty_context_files():
    assert validate_context_files({"id": "T1", "context_files": []}) is True


def test_valid_context_file():
    assert validate_context_files({"context_files": ["orchestration/tasklist.md"]}) is True


def test_blocks_dotenv():
    assert validate_context_files({"context_files": [".env"]}) is False


def test_blocks_env_in_path():
    assert validate_context_files({"context_files": ["config/.env"]}) is False


def test_blocks_pem_key():
    assert validate_context_files({"context_files": ["certs/server.pem"]}) is False


def test_blocks_key_file():
    assert validate_context_files({"context_files": ["secrets/private.key"]}) is False


def test_blocks_credentials_json():
    assert validate_context_files({"context_files": ["credentials.json"]}) is False


def test_blocks_ssh_dir():
    assert validate_context_files({"context_files": [".ssh/id_rsa"]}) is False


def test_blocks_aws_dir():
    assert validate_context_files({"context_files": [".aws/credentials"]}) is False


def test_blocks_path_traversal():
    assert validate_context_files({"context_files": ["../../etc/passwd"]}) is False
