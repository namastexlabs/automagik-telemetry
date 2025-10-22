"""
Comprehensive tests for TelemetryClient.

Tests cover:
- Initialization and configuration
- Event tracking (trackEvent, trackError, trackMetric)
- Enable/disable functionality
- User ID persistence
- OTLP payload format
- Environment variable handling
- CI environment detection
- Silent failure behavior
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from automagik_telemetry.client import TelemetryClient


class TestTelemetryClientInitialization:
    """Test TelemetryClient initialization and configuration."""

    def test_should_initialize_with_required_parameters(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test basic client initialization with required parameters."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.project_name == "test-project"
        assert client.project_version == "1.0.0"
        assert client.organization == "namastex"
        assert client.timeout == 5
        assert client.endpoint == "https://telemetry.namastex.ai/v1/traces"

    def test_should_use_custom_endpoint_when_provided(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that custom endpoint is used when provided."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0",
            endpoint="https://custom.example.com/traces"
        )

        assert client.endpoint == "https://custom.example.com/traces"

    def test_should_use_endpoint_from_env_var(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that endpoint is read from environment variable."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://env.example.com/traces")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.endpoint == "https://env.example.com/traces"

    def test_should_use_custom_organization_when_provided(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that custom organization is used."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0",
            organization="custom-org"
        )

        assert client.organization == "custom-org"

    def test_should_use_custom_timeout_when_provided(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that custom timeout is used."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0",
            timeout=10
        )

        assert client.timeout == 10

    def test_should_generate_session_id_on_init(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that session ID is generated on initialization."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.session_id is not None
        assert len(client.session_id) > 0

    def test_should_be_disabled_by_default(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that telemetry is disabled by default (opt-in only)."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False

    def test_should_parse_verbose_mode_from_env(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that verbose mode is read from environment variable."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.verbose is True


class TestUserIdPersistence:
    """Test user ID generation and persistence."""

    def test_should_create_user_id_file_on_first_init(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that user ID file is created on first initialization."""
        user_id_file = temp_home / ".automagik" / "user_id"
        assert not user_id_file.exists()

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert user_id_file.exists()
        assert len(client.user_id) > 0

    def test_should_reuse_existing_user_id(
        self, temp_home: Path, user_id_file: Path, clean_env: None
    ) -> None:
        """Test that existing user ID is reused."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.user_id == "test-user-id-12345"

    def test_should_handle_user_id_file_read_error(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test graceful handling of user ID file read errors."""
        # Create a directory instead of file to trigger read error
        user_id_path = temp_home / ".automagik" / "user_id"
        user_id_path.parent.mkdir(parents=True, exist_ok=True)
        user_id_path.mkdir()

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        # Should generate new ID when read fails
        assert client.user_id is not None
        assert len(client.user_id) > 0

    def test_should_handle_user_id_file_write_error(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test graceful handling of user ID file write errors."""
        with patch("pathlib.Path.write_text", side_effect=PermissionError):
            client = TelemetryClient(
                project_name="test-project",
                version="1.0.0"
            )

            # Should still have in-memory user ID
            assert client.user_id is not None
            assert len(client.user_id) > 0


class TestTelemetryEnabled:
    """Test telemetry enable/disable logic."""

    def test_should_be_enabled_when_env_var_is_true(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test enabling via environment variable."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is True

    @pytest.mark.parametrize("value", ["1", "yes", "on", "TRUE", "Yes", "ON"])
    def test_should_accept_various_true_values(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        """Test that various truthy values are accepted."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", value)

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is True

    def test_should_be_disabled_when_opt_out_file_exists(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file disables telemetry."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False

    @pytest.mark.parametrize("ci_var", ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI", "CIRCLECI"])
    def test_should_be_disabled_in_ci_environments(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, ci_var: str
    ) -> None:
        """Test that telemetry is disabled in CI environments."""
        monkeypatch.setenv(ci_var, "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False

    @pytest.mark.parametrize("env_value", ["development", "dev", "test", "testing"])
    def test_should_be_disabled_in_dev_environments(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, env_value: str
    ) -> None:
        """Test that telemetry is disabled in development environments."""
        monkeypatch.setenv("ENVIRONMENT", env_value)

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False


class TestEventTracking:
    """Test event tracking functionality."""

    def test_should_not_send_event_when_disabled(
        self, temp_home: Path, clean_env: None, mock_urlopen: Mock
    ) -> None:
        """Test that events are not sent when telemetry is disabled."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        # Should not make HTTP request when disabled
        mock_urlopen.assert_not_called()

    def test_should_send_event_when_enabled(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that events are sent when telemetry is enabled."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        # Should make HTTP request when enabled
        mock_urlopen.assert_called_once()

    def test_should_create_valid_otlp_payload(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that OTLP payload is correctly formatted."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        # Get the request that was made
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Parse the payload
        payload = json.loads(request.data.decode("utf-8"))

        # Verify OTLP structure
        assert "resourceSpans" in payload
        assert len(payload["resourceSpans"]) == 1

        resource_span = payload["resourceSpans"][0]
        assert "resource" in resource_span
        assert "scopeSpans" in resource_span

        # Verify resource attributes
        resource_attrs = {
            attr["key"]: attr["value"]
            for attr in resource_span["resource"]["attributes"]
        }
        assert resource_attrs["service.name"]["stringValue"] == "test-project"
        assert resource_attrs["service.version"]["stringValue"] == "1.0.0"

        # Verify spans
        scope_spans = resource_span["scopeSpans"][0]
        assert "spans" in scope_spans
        assert len(scope_spans["spans"]) == 1

        span = scope_spans["spans"][0]
        assert span["name"] == "test.event"
        assert "traceId" in span
        assert "spanId" in span
        assert len(span["traceId"]) == 32  # 32 hex chars
        assert len(span["spanId"]) == 16  # 16 hex chars

    def test_should_include_system_information(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that system information is included in attributes."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        # Extract span attributes
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}

        # Verify system attributes are present
        assert "system.os" in attributes
        assert "system.python_version" in attributes
        assert "system.architecture" in attributes
        assert "system.project_name" in attributes
        assert attributes["system.project_name"]["stringValue"] == "test-project"

    def test_should_handle_various_attribute_types(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that different attribute types are correctly encoded."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {
            "string_val": "hello",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
        })

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        # Extract attributes
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}

        assert "stringValue" in attributes["string_val"]
        assert attributes["string_val"]["stringValue"] == "hello"

        assert "doubleValue" in attributes["int_val"]
        assert attributes["int_val"]["doubleValue"] == 42.0

        assert "doubleValue" in attributes["float_val"]
        assert attributes["float_val"]["doubleValue"] == 3.14

        assert "boolValue" in attributes["bool_val"]
        assert attributes["bool_val"]["boolValue"] is True

    def test_should_truncate_long_strings(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that long strings are truncated to prevent payload bloat."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        long_string = "x" * 1000
        client.track_event("test.event", {"long_value": long_string})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        # Extract attributes
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}

        # Should be truncated to 500 chars
        assert len(attributes["long_value"]["stringValue"]) == 500


class TestErrorTracking:
    """Test error tracking functionality."""

    def test_should_track_error_with_exception_details(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test tracking an error with exception details."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        try:
            raise ValueError("Test error message")
        except Exception as e:
            client.track_error(e, {"error_code": "TEST-001"})

        # Verify event was sent
        mock_urlopen.assert_called_once()

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        # Verify error details
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["name"] == "automagik.error"

        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}
        assert attributes["error_type"]["stringValue"] == "ValueError"
        assert attributes["error_message"]["stringValue"] == "Test error message"
        assert attributes["error_code"]["stringValue"] == "TEST-001"

    def test_should_truncate_long_error_messages(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that long error messages are truncated."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        long_message = "x" * 1000
        try:
            raise ValueError(long_message)
        except Exception as e:
            client.track_error(e)

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}

        # Should be truncated to 500 chars
        assert len(attributes["error_message"]["stringValue"]) == 500


class TestMetricTracking:
    """Test metric tracking functionality."""

    def test_should_track_metric_with_value(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test tracking a metric with a numeric value."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_metric("operation.latency", 123.45, {
            "operation_type": "api_request"
        })

        # Verify event was sent
        mock_urlopen.assert_called_once()

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["name"] == "operation.latency"

        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}
        assert attributes["value"]["doubleValue"] == 123.45
        assert attributes["operation_type"]["stringValue"] == "api_request"


class TestEnableDisable:
    """Test enable/disable functionality."""

    def test_should_enable_telemetry(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test enabling telemetry."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False

        client.enable()

        assert client.enabled is True

    def test_should_remove_opt_out_file_when_enabled(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file is removed when enabling."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.enable()

        assert not opt_out_file.exists()

    def test_should_disable_telemetry(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test disabling telemetry."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is True

        client.disable()

        assert client.enabled is False

    def test_should_create_opt_out_file_when_disabled(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that opt-out file is created when disabling."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.disable()

        opt_out_file = temp_home / ".automagik-no-telemetry"
        assert opt_out_file.exists()

    def test_should_check_if_enabled(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test is_enabled() method."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.is_enabled() is True

        client.disable()

        assert client.is_enabled() is False


class TestStatusInfo:
    """Test telemetry status information."""

    def test_should_return_complete_status(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test get_status() returns complete information."""
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        status = client.get_status()

        assert "enabled" in status
        assert "user_id" in status
        assert "session_id" in status
        assert "project_name" in status
        assert "project_version" in status
        assert "endpoint" in status
        assert "opt_out_file_exists" in status
        assert "env_var" in status
        assert "verbose" in status

        assert status["project_name"] == "test-project"
        assert status["project_version"] == "1.0.0"


class TestSilentFailure:
    """Test that telemetry failures don't crash the application."""

    def test_should_handle_network_error_silently(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that network errors are handled silently."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("urllib.request.urlopen", side_effect=URLError("Network error")):
            client = TelemetryClient(
                project_name="test-project",
                version="1.0.0"
            )

            # Should not raise exception
            client.track_event("test.event", {"key": "value"})

    def test_should_handle_http_error_silently(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that HTTP errors are handled silently."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("urllib.request.urlopen", side_effect=HTTPError("url", 500, "Server error", {}, None)):
            client = TelemetryClient(
                project_name="test-project",
                version="1.0.0"
            )

            # Should not raise exception
            client.track_event("test.event", {"key": "value"})

    def test_should_handle_timeout_error_silently(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that timeout errors are handled silently."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
            client = TelemetryClient(
                project_name="test-project",
                version="1.0.0"
            )

            # Should not raise exception
            client.track_event("test.event", {"key": "value"})

    def test_should_handle_generic_exception_silently(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generic exceptions are handled silently."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("urllib.request.urlopen", side_effect=Exception("Unexpected error")):
            client = TelemetryClient(
                project_name="test-project",
                version="1.0.0"
            )

            # Should not raise exception
            client.track_event("test.event", {"key": "value"})


class TestVerboseMode:
    """Test verbose mode functionality."""

    def test_should_print_events_in_verbose_mode(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that events are printed to console in verbose mode."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        captured = capsys.readouterr()
        assert "[Telemetry] Sending event: test.event" in captured.out
        assert "Project: test-project" in captured.out

    def test_should_not_print_events_when_not_verbose(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that events are not printed when verbose mode is off."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        captured = capsys.readouterr()
        assert "[Telemetry]" not in captured.out
