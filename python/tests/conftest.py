"""
Pytest configuration and shared fixtures for telemetry tests.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_home(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """
    Create a temporary home directory for testing.
    Automatically patches Path.home() to return the temp directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Patch Path.home() to return our temp directory
        monkeypatch.setattr(Path, "home", lambda: temp_path)

        yield temp_path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Clean environment variables related to telemetry.
    Ensures tests start with a clean slate.
    """
    env_vars_to_remove = [
        "AUTOMAGIK_TELEMETRY_ENABLED",
        "AUTOMAGIK_TELEMETRY_ENDPOINT",
        "AUTOMAGIK_TELEMETRY_VERBOSE",
        "AUTOMAGIK_TELEMETRY_TIMEOUT",
        "CI",
        "GITHUB_ACTIONS",
        "TRAVIS",
        "JENKINS",
        "GITLAB_CI",
        "CIRCLECI",
        "ENVIRONMENT",
    ]

    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_http_response() -> Mock:
    """
    Create a mock HTTP response object.
    Returns a successful response by default.
    """
    mock_response = Mock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"success": true}'
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    return mock_response


@pytest.fixture
def mock_urlopen(mock_http_response: Mock) -> Generator[Mock, None, None]:
    """
    Mock urllib.request.urlopen to prevent actual HTTP requests.
    Patches where urlopen is used (in client module) rather than where it's defined.
    """
    with patch("automagik_telemetry.client.urlopen", return_value=mock_http_response) as mock:
        yield mock


@pytest.fixture
def mock_stdin() -> Generator[Mock, None, None]:
    """
    Mock sys.stdin for testing interactive input.
    """
    with patch("sys.stdin") as mock:
        mock.isatty.return_value = True
        yield mock


@pytest.fixture
def mock_stdout() -> Generator[Mock, None, None]:
    """
    Mock sys.stdout for testing output.
    """
    with patch("sys.stdout") as mock:
        mock.isatty.return_value = True
        yield mock


@pytest.fixture
def sample_telemetry_config() -> dict[str, Any]:
    """
    Sample telemetry configuration for testing.
    """
    return {
        "project_name": "test-project",
        "version": "1.0.0",
        "endpoint": "https://test.example.com/v1/traces",
        "organization": "test-org",
        "timeout": 5,
    }


@pytest.fixture
def sample_event_data() -> dict[str, Any]:
    """
    Sample event data for testing.
    """
    return {
        "feature_name": "test_feature",
        "feature_category": "testing",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_sensitive_data() -> dict[str, Any]:
    """
    Sample data containing PII for privacy testing.
    """
    return {
        "user_email": "user@example.com",
        "phone_number": "+1-555-555-5555",
        "api_key": "sk_test_FAKE_KEY_NOT_REAL_12345678r",
        "credit_card": "4532-1234-5678-9010",
        "ip_address": "192.168.1.100",
        "user_path": "/home/johndoe/project/file.py",
        "password": "secret123",
        "normal_text": "This is normal text",
    }


@pytest.fixture
def mock_uuid() -> Generator[Mock, None, None]:
    """
    Mock uuid.uuid4() to return predictable values.
    """
    with patch("uuid.uuid4") as mock:
        # Return predictable UUID values
        mock.side_effect = [
            Mock(hex="a" * 32, __str__=lambda _: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            Mock(hex="b" * 32, __str__=lambda _: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            Mock(hex="c" * 32, __str__=lambda _: "cccccccc-cccc-cccc-cccc-cccccccccccc"),
        ]
        yield mock


@pytest.fixture
def mock_time() -> Generator[Mock, None, None]:
    """
    Mock time.time() to return a predictable timestamp.
    """
    with patch("time.time", return_value=1704067200.0) as mock:  # 2024-01-01 00:00:00 UTC
        yield mock


@pytest.fixture
def ci_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set up environment variables to simulate CI environment.
    """
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


@pytest.fixture
def non_interactive_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock terminal to be non-interactive.
    """
    with patch("sys.stdin.isatty", return_value=False):
        with patch("sys.stdout.isatty", return_value=False):
            yield


@pytest.fixture
def interactive_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock terminal to be interactive.
    """
    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout.isatty", return_value=True):
            yield


@pytest.fixture
def automagik_dir(temp_home: Path) -> Path:
    """
    Create .automagik directory in temp home.
    """
    automagik_dir = temp_home / ".automagik"
    automagik_dir.mkdir(parents=True, exist_ok=True)
    return automagik_dir


@pytest.fixture
def user_id_file(automagik_dir: Path) -> Path:
    """
    Create user_id file with a test UUID.
    """
    user_id_file = automagik_dir / "user_id"
    user_id_file.write_text("test-user-id-12345")
    return user_id_file


@pytest.fixture
def telemetry_preference_file(automagik_dir: Path) -> Path:
    """
    Create telemetry_preference file.
    """
    pref_file = automagik_dir / "telemetry_preference"
    pref_file.write_text("enabled")
    return pref_file


@pytest.fixture
def opt_out_file(temp_home: Path) -> Path:
    """
    Create opt-out file.
    """
    opt_out = temp_home / ".automagik-no-telemetry"
    opt_out.touch()
    return opt_out
