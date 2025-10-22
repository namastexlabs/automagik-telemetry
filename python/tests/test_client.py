"""
Comprehensive tests for AutomagikTelemetry.

Tests cover:
- Initialization and configuration
- Event tracking (trackEvent, trackError, trackMetric)
- Enable/disable functionality
- User ID persistence
- OTLP payload format
- Environment variable handling
- CI environment detection
- Silent failure behavior
- Backwards compatibility with TelemetryClient alias
"""

import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from automagik_telemetry.client import AutomagikTelemetry, TelemetryClient, TelemetryConfig


def parse_request_payload(request) -> Dict[str, Any]:
    """
    Helper to parse request payload, handling both compressed and uncompressed data.

    Args:
        request: The HTTP request object with .data attribute

    Returns:
        Parsed JSON payload as dictionary
    """
    try:
        # Try to parse as plain JSON first
        return json.loads(request.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # If that fails, try decompressing first
        try:
            decompressed = gzip.decompress(request.data)
            return json.loads(decompressed.decode("utf-8"))
        except Exception:
            # Re-raise the original error if decompression fails
            return json.loads(request.data.decode("utf-8"))


class TestAutomagikTelemetryInitialization:
    """Test AutomagikTelemetry initialization and configuration."""

    def test_should_initialize_with_required_parameters(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test basic client initialization with required parameters."""
        client = AutomagikTelemetry(
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
        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.endpoint == "https://env.example.com/traces"

    def test_should_use_custom_organization_when_provided(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that custom organization is used."""
        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0",
            organization="custom-org"
        )

        assert client.organization == "custom-org"

    def test_should_use_custom_timeout_when_provided(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that custom timeout is used."""
        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0",
            timeout=10
        )

        assert client.timeout == 10

    def test_should_generate_session_id_on_init(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that session ID is generated on initialization."""
        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.session_id is not None
        assert len(client.session_id) > 0

    def test_should_be_disabled_by_default(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that telemetry is disabled by default (opt-in only)."""
        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is False

    def test_should_parse_verbose_mode_from_env(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that verbose mode is read from environment variable."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.verbose is True


class TestBackwardsCompatibility:
    """Test backwards compatibility with TelemetryClient alias."""

    def test_telemetry_client_alias_works(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that TelemetryClient alias still works."""
        # Should be able to use TelemetryClient
        client = TelemetryClient(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.project_name == "test-project"
        assert client.project_version == "1.0.0"

    def test_telemetry_client_is_same_class(self) -> None:
        """Test that TelemetryClient is actually AutomagikTelemetry."""
        assert TelemetryClient is AutomagikTelemetry


class TestUserIdPersistence:
    """Test user ID generation and persistence."""

    def test_should_create_user_id_file_on_first_init(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that user ID file is created on first initialization."""
        user_id_file = temp_home / ".automagik" / "user_id"
        assert not user_id_file.exists()

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert user_id_file.exists()
        assert len(client.user_id) > 0

    def test_should_reuse_existing_user_id(
        self, temp_home: Path, user_id_file: Path, clean_env: None
    ) -> None:
        """Test that existing user ID is reused."""
        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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
            client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        assert client.enabled is True

    def test_should_be_disabled_when_opt_out_file_exists(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file disables telemetry."""
        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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
        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        # Get the request that was made
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Parse the payload
        payload = parse_request_payload(request)

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
        assert len(span["traceId"]) in (32, 64)  # Hex string (16 or 32 bytes)
        assert len(span["spanId"]) in (16, 32)  # Hex string (8 or 16 bytes)

    def test_should_include_system_information(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that system information is included in attributes."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = parse_request_payload(request)

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

        client = AutomagikTelemetry(
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
        payload = parse_request_payload(request)

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

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        long_string = "x" * 1000
        client.track_event("test.event", {"long_value": long_string})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = parse_request_payload(request)

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

        client = AutomagikTelemetry(
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
        payload = parse_request_payload(request)

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

        client = AutomagikTelemetry(
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
        payload = parse_request_payload(request)

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

        client = AutomagikTelemetry(
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
        payload = parse_request_payload(request)

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
        client = AutomagikTelemetry(
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
        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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
        client = AutomagikTelemetry(
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
            client = AutomagikTelemetry(
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
            client = AutomagikTelemetry(
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
            client = AutomagikTelemetry(
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
            client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
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

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        client.track_event("test.event", {"key": "value"})

        captured = capsys.readouterr()
        assert "[Telemetry]" not in captured.out


class TestEdgeCasesAndErrorPaths:
    """Test edge cases and error handling paths for 100% coverage."""

    def test_should_raise_error_when_no_config_and_missing_params(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that ValueError is raised when neither config nor required params provided."""
        with pytest.raises(ValueError, match="Either 'config' or both 'project_name' and 'version' must be provided"):
            AutomagikTelemetry(project_name=None, version=None)

        with pytest.raises(ValueError, match="Either 'config' or both 'project_name' and 'version' must be provided"):
            AutomagikTelemetry(project_name="test", version=None)

        with pytest.raises(ValueError, match="Either 'config' or both 'project_name' and 'version' must be provided"):
            AutomagikTelemetry(project_name=None, version="1.0.0")

    def test_should_handle_custom_endpoint_without_path(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test endpoint handling when custom endpoint is just a base URL."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0",
            endpoint="https://custom.example.com"
        )

        assert client.endpoint == "https://custom.example.com/v1/traces"
        assert client.metrics_endpoint == "https://custom.example.com/v1/metrics"
        assert client.logs_endpoint == "https://custom.example.com/v1/logs"

    def test_should_schedule_flush_with_batching(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that flush is scheduled when batch_size > 1."""
        import time
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            batch_size=10,
            flush_interval=0.1  # 100ms for fast test
        )
        client = AutomagikTelemetry(config=config)

        # Add an event
        client.track_event("test.event", {})

        # Wait for auto-flush
        time.sleep(0.2)

        # Should have sent the event
        assert mock_urlopen.called

    def test_should_handle_number_attributes_in_system_info(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that number attributes are handled correctly in system info."""
        import gzip
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = AutomagikTelemetry(
            project_name="test-project",
            version="1.0.0"
        )

        # Patch the instance method to return number values
        original_get_system_info = client._get_system_info
        def mock_get_system_info():
            info = original_get_system_info()
            info["cpu_count"] = 8  # Add number attribute
            info["memory_gb"] = 16.5  # Add float attribute
            return info

        client._get_system_info = mock_get_system_info

        client.track_event("test.event", {})

        # Get the request and verify number handling
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = parse_request_payload(request)

        # Find system attributes
        attributes = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
        cpu_attr = next((a for a in attributes if a["key"] == "system.cpu_count"), None)
        mem_attr = next((a for a in attributes if a["key"] == "system.memory_gb"), None)

        assert cpu_attr is not None
        assert "doubleValue" in cpu_attr["value"]
        assert cpu_attr["value"]["doubleValue"] == 8.0

        assert mem_attr is not None
        assert "doubleValue" in mem_attr["value"]
        assert mem_attr["value"]["doubleValue"] == 16.5

    def test_should_not_schedule_flush_when_shutdown(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that flush scheduling respects shutdown flag."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            batch_size=10
        )
        client = AutomagikTelemetry(config=config)

        # Cancel any existing timer
        if client._flush_timer:
            client._flush_timer.cancel()

        # Set shutdown flag
        client._shutdown = True

        # Try to schedule flush (should be no-op)
        client._schedule_flush()

        # Verify no new timer was created after shutdown
        # The timer should be None or not running
        assert client._flush_timer is None or not client._flush_timer.is_alive()

    def test_should_handle_http_4xx_errors_without_retry(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that 4xx errors don't trigger retries."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("automagik_telemetry.client.urlopen") as mock_urlopen:
            # Simulate 400 Bad Request
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 400, "Bad Request", {}, None
            )

            client = AutomagikTelemetry(
                project_name="test-project",
                version="1.0.0"
            )

            # Should not raise, just fail silently
            client.track_event("test.event", {})

            # Should only try once (no retries for 4xx)
            assert mock_urlopen.call_count == 1

    def test_should_retry_on_5xx_errors(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that 5xx errors trigger retries."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("automagik_telemetry.client.urlopen") as mock_urlopen:
            # Simulate 500 Internal Server Error
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 500, "Internal Server Error", {}, None
            )

            config = TelemetryConfig(
                project_name="test-project",
                version="1.0.0",
                max_retries=3
            )
            client = AutomagikTelemetry(config=config)

            # Should not raise, just fail silently after retries
            client.track_event("test.event", {})

            # Should try max_retries + 1 times
            assert mock_urlopen.call_count == 4  # 1 initial + 3 retries

    def test_should_handle_network_errors_with_retry(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that network errors trigger retries."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        with patch("automagik_telemetry.client.urlopen") as mock_urlopen:
            # Simulate network error
            mock_urlopen.side_effect = URLError("Network unreachable")

            config = TelemetryConfig(
                project_name="test-project",
                version="1.0.0",
                max_retries=2
            )
            client = AutomagikTelemetry(config=config)

            # Should not raise, just fail silently after retries
            client.track_event("test.event", {})

            # Should try max_retries + 1 times
            assert mock_urlopen.call_count == 3  # 1 initial + 2 retries

    def test_should_handle_compression_with_large_payloads(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that large payloads are compressed."""
        import gzip
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_threshold=100  # Low threshold to force compression
        )
        client = AutomagikTelemetry(config=config)

        # Send event with large data
        large_data = {"message": "x" * 500}
        client.track_event("test.event", large_data)

        # Verify compression header
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.headers.get("Content-encoding") == "gzip"

        # Verify can decompress
        decompressed = gzip.decompress(request.data)
        payload = json.loads(decompressed.decode("utf-8"))
        assert "resourceSpans" in payload

    def test_should_not_compress_small_payloads(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that small payloads are not compressed."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_threshold=10000  # High threshold to prevent compression
        )
        client = AutomagikTelemetry(config=config)

        # Send small event
        client.track_event("test.event", {"small": "data"})

        # Verify no compression header
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.headers.get("Content-encoding") != "gzip"

        # Verify can parse directly
        payload = parse_request_payload(request)
        assert "resourceSpans" in payload

    def test_should_respect_compression_disabled(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that compression can be disabled."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_enabled=False
        )
        client = AutomagikTelemetry(config=config)

        # Send large event that would normally be compressed
        large_data = {"message": "x" * 2000}
        client.track_event("test.event", large_data)

        # Verify no compression
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.headers.get("Content-encoding") != "gzip"

        # Verify can parse directly
        payload = parse_request_payload(request)
        assert "resourceSpans" in payload
