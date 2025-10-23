"""
Comprehensive tests for ClickHouse backend.

Tests cover:
- OTLP to ClickHouse transformation
  - trace_id, span_id mapping
  - timestamp conversion (nanoseconds to DateTime)
  - duration calculation (start/end time difference)
  - attribute flattening (OTLP format to dict)
  - resource attribute extraction (service.name, project.name, etc.)
  - status code mapping
- Batch processing
  - add_to_batch() adds rows correctly
  - auto-flush when batch_size is reached
  - manual flush() sends pending rows
  - empty batch doesn't cause errors
- Error handling
  - invalid OTLP data handling
  - network error handling (mock HTTP errors)
  - retry logic with exponential backoff
"""

import gzip
import json
import time
from typing import Any
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from automagik_telemetry.backends.clickhouse import ClickHouseBackend


class TestClickHouseBackendInitialization:
    """Test ClickHouse backend initialization."""

    def test_should_initialize_with_default_parameters(self) -> None:
        """Test basic initialization with default parameters."""
        backend = ClickHouseBackend()

        assert backend.endpoint == "http://localhost:8123"
        assert backend.database == "telemetry"
        assert backend.table == "traces"
        assert backend.username == "default"
        assert backend.password == ""
        assert backend.timeout == 5
        assert backend.batch_size == 100
        assert backend.compression_enabled is True
        assert backend.max_retries == 3
        assert backend._batch == []

    def test_should_initialize_with_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        backend = ClickHouseBackend(
            endpoint="http://custom-host:9000",
            database="custom_db",
            table="custom_table",
            username="custom_user",
            password="secret123",
            timeout=10,
            batch_size=50,
            compression_enabled=False,
            max_retries=5,
        )

        assert backend.endpoint == "http://custom-host:9000"
        assert backend.database == "custom_db"
        assert backend.table == "custom_table"
        assert backend.username == "custom_user"
        assert backend.password == "secret123"
        assert backend.timeout == 10
        assert backend.batch_size == 50
        assert backend.compression_enabled is False
        assert backend.max_retries == 5

    def test_should_strip_trailing_slash_from_endpoint(self) -> None:
        """Test that trailing slashes are removed from endpoint."""
        backend = ClickHouseBackend(endpoint="http://localhost:8123/")

        assert backend.endpoint == "http://localhost:8123"


class TestOTLPTransformation:
    """Test OTLP to ClickHouse transformation."""

    def test_should_transform_minimal_otlp_span(self) -> None:
        """Test transformation of minimal OTLP span."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "abc123",
            "spanId": "def456",
            "name": "test-span",
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["trace_id"] == "abc123"
        assert result["span_id"] == "def456"
        assert result["span_name"] == "test-span"
        assert result["parent_span_id"] == ""
        assert result["service_name"] == "unknown"
        assert result["project_name"] == ""

    def test_should_map_trace_id_and_span_id(self) -> None:
        """Test mapping of trace_id and span_id from OTLP format."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "a" * 32,  # 32-char hex string
            "spanId": "b" * 16,  # 16-char hex string
            "parentSpanId": "c" * 16,
            "name": "test",
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["trace_id"] == "a" * 32
        assert result["span_id"] == "b" * 16
        assert result["parent_span_id"] == "c" * 16

    def test_should_convert_timestamp_from_nanoseconds(self) -> None:
        """Test timestamp conversion from nanoseconds to datetime."""
        backend = ClickHouseBackend()
        # Use a known timestamp: 2024-01-01 00:00:00 UTC = 1704067200 seconds
        timestamp_ns = 1704067200_000_000_000
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "startTimeUnixNano": timestamp_ns,
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["timestamp"] == "2024-01-01 00:00:00"
        assert result["timestamp_ns"] == timestamp_ns

    def test_should_use_current_time_if_no_start_time(self) -> None:
        """Test that current time is used when startTimeUnixNano is missing."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
        }

        with patch("time.time_ns", return_value=1704067200_000_000_000):
            result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["timestamp"] == "2024-01-01 00:00:00"
        assert result["timestamp_ns"] == 1704067200_000_000_000

    def test_should_calculate_duration_in_milliseconds(self) -> None:
        """Test duration calculation from start and end times."""
        backend = ClickHouseBackend()
        start_ns = 1704067200_000_000_000
        end_ns = 1704067200_500_000_000  # 500ms later
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "startTimeUnixNano": start_ns,
            "endTimeUnixNano": end_ns,
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["duration_ms"] == 500

    def test_should_handle_zero_duration(self) -> None:
        """Test duration calculation when start and end are the same."""
        backend = ClickHouseBackend()
        timestamp_ns = 1704067200_000_000_000
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "startTimeUnixNano": timestamp_ns,
            "endTimeUnixNano": timestamp_ns,
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["duration_ms"] == 0

    def test_should_handle_missing_end_time(self) -> None:
        """Test duration calculation when end time is missing."""
        backend = ClickHouseBackend()
        start_ns = 1704067200_000_000_000
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "startTimeUnixNano": start_ns,
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["duration_ms"] == 0

    def test_should_flatten_string_attributes(self) -> None:
        """Test flattening of OTLP string attributes to flat dict."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "attributes": [
                {"key": "http.method", "value": {"stringValue": "GET"}},
                {"key": "http.url", "value": {"stringValue": "https://example.com"}},
            ],
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["attributes"]["http.method"] == "GET"
        assert result["attributes"]["http.url"] == "https://example.com"

    def test_should_flatten_integer_attributes(self) -> None:
        """Test flattening of OTLP integer attributes."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "attributes": [
                {"key": "http.status_code", "value": {"intValue": 200}},
                {"key": "request_count", "value": {"intValue": 42}},
            ],
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["attributes"]["http.status_code"] == "200"
        assert result["attributes"]["request_count"] == "42"

    def test_should_flatten_double_attributes(self) -> None:
        """Test flattening of OTLP double/float attributes."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "attributes": [
                {"key": "response_time", "value": {"doubleValue": 123.45}},
                {"key": "cpu_usage", "value": {"doubleValue": 0.75}},
            ],
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["attributes"]["response_time"] == "123.45"
        assert result["attributes"]["cpu_usage"] == "0.75"

    def test_should_flatten_boolean_attributes(self) -> None:
        """Test flattening of OTLP boolean attributes."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "attributes": [
                {"key": "is_authenticated", "value": {"boolValue": True}},
                {"key": "is_cached", "value": {"boolValue": False}},
            ],
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["attributes"]["is_authenticated"] == "True"
        assert result["attributes"]["is_cached"] == "False"

    def test_should_extract_service_name_from_resource(self) -> None:
        """Test extraction of service.name from resource attributes."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [{"key": "service.name", "value": {"stringValue": "my-service"}}]
            },
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["service_name"] == "my-service"

    def test_should_extract_project_name_and_version(self) -> None:
        """Test extraction of project.name and project.version."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [
                    {"key": "project.name", "value": {"stringValue": "my-project"}},
                    {"key": "project.version", "value": {"stringValue": "1.2.3"}},
                ]
            },
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["project_name"] == "my-project"
        assert result["project_version"] == "1.2.3"

    def test_should_extract_deployment_environment(self) -> None:
        """Test extraction of deployment.environment with default."""
        backend = ClickHouseBackend()

        # Test with explicit environment
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [
                    {"key": "deployment.environment", "value": {"stringValue": "staging"}}
                ]
            },
        }
        result = backend.transform_otlp_to_clickhouse(otlp_span)
        assert result["environment"] == "staging"

        # Test default value
        otlp_span_no_env: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
        }
        result = backend.transform_otlp_to_clickhouse(otlp_span_no_env)
        assert result["environment"] == "production"

    def test_should_extract_host_information(self) -> None:
        """Test extraction of host.name."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [{"key": "host.name", "value": {"stringValue": "server-01"}}]
            },
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["hostname"] == "server-01"

    def test_should_extract_os_information(self) -> None:
        """Test extraction of OS type and version."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [
                    {"key": "os.type", "value": {"stringValue": "linux"}},
                    {"key": "os.version", "value": {"stringValue": "5.15.0"}},
                ]
            },
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["os_type"] == "linux"
        assert result["os_version"] == "5.15.0"

    def test_should_extract_runtime_information(self) -> None:
        """Test extraction of process runtime name and version."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "resource": {
                "attributes": [
                    {"key": "process.runtime.name", "value": {"stringValue": "python"}},
                    {"key": "process.runtime.version", "value": {"stringValue": "3.12.0"}},
                ]
            },
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["runtime_name"] == "python"
        assert result["runtime_version"] == "3.12.0"

    def test_should_extract_user_and_session_ids(self) -> None:
        """Test extraction of user.id and session.id from attributes."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "attributes": [
                {"key": "user.id", "value": {"stringValue": "user-123"}},
                {"key": "session.id", "value": {"stringValue": "session-456"}},
            ],
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["user_id"] == "user-123"
        assert result["session_id"] == "session-456"

    def test_should_map_status_code_ok(self) -> None:
        """Test status code mapping for OK status."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "status": {"code": 1},  # OK status
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["status_code"] == "OK"
        assert result["status_message"] == ""

    def test_should_map_status_code_error(self) -> None:
        """Test status code mapping for error status."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "status": {"code": 2, "message": "Internal error"},  # ERROR status
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["status_code"] == "Internal error"
        assert result["status_message"] == "Internal error"

    def test_should_handle_missing_status(self) -> None:
        """Test status handling when status is missing."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["status_code"] == "OK"
        assert result["status_message"] == ""

    def test_should_handle_span_kind(self) -> None:
        """Test span kind extraction."""
        backend = ClickHouseBackend()
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
            "kind": "CLIENT",
        }

        result = backend.transform_otlp_to_clickhouse(otlp_span)

        assert result["span_kind"] == "CLIENT"


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_should_add_span_to_batch(self) -> None:
        """Test adding a span to the batch queue."""
        backend = ClickHouseBackend(batch_size=10)
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test-span",
        }

        backend.add_to_batch(otlp_span)

        assert len(backend._batch) == 1
        assert backend._batch[0]["trace_id"] == "123"
        assert backend._batch[0]["span_id"] == "456"

    def test_should_add_multiple_spans_to_batch(self) -> None:
        """Test adding multiple spans to batch."""
        backend = ClickHouseBackend(batch_size=10)

        for i in range(5):
            otlp_span: dict[str, Any] = {
                "traceId": f"trace-{i}",
                "spanId": f"span-{i}",
                "name": f"test-{i}",
            }
            backend.add_to_batch(otlp_span)

        assert len(backend._batch) == 5
        assert backend._batch[0]["trace_id"] == "trace-0"
        assert backend._batch[4]["trace_id"] == "trace-4"

    def test_should_auto_flush_when_batch_size_reached(self) -> None:
        """Test auto-flush when batch size is reached."""
        backend = ClickHouseBackend(batch_size=3)

        with patch.object(backend, "flush") as mock_flush:
            # Add spans up to batch_size
            for i in range(3):
                otlp_span: dict[str, Any] = {
                    "traceId": f"trace-{i}",
                    "spanId": f"span-{i}",
                    "name": f"test-{i}",
                }
                backend.add_to_batch(otlp_span)

            # flush should be called when batch_size is reached
            assert mock_flush.call_count == 1

    def test_should_not_flush_before_batch_size_reached(self) -> None:
        """Test that flush is not called before batch size is reached."""
        backend = ClickHouseBackend(batch_size=5)

        with patch.object(backend, "flush") as mock_flush:
            # Add fewer spans than batch_size
            for i in range(3):
                otlp_span: dict[str, Any] = {
                    "traceId": f"trace-{i}",
                    "spanId": f"span-{i}",
                    "name": f"test-{i}",
                }
                backend.add_to_batch(otlp_span)

            # flush should not be called yet
            assert mock_flush.call_count == 0
            assert len(backend._batch) == 3

    def test_should_clear_batch_after_flush(self) -> None:
        """Test that batch is cleared after flush."""
        backend = ClickHouseBackend(batch_size=10)

        # Add some spans
        for i in range(3):
            otlp_span: dict[str, Any] = {
                "traceId": f"trace-{i}",
                "spanId": f"span-{i}",
                "name": f"test-{i}",
            }
            backend.add_to_batch(otlp_span)

        assert len(backend._batch) == 3

        # Mock successful insert
        with patch.object(backend, "_insert_batch", return_value=True):
            result = backend.flush()

        assert result is True
        assert len(backend._batch) == 0

    def test_should_flush_empty_batch_successfully(self) -> None:
        """Test flushing an empty batch doesn't cause errors."""
        backend = ClickHouseBackend()

        result = backend.flush()

        assert result is True
        assert len(backend._batch) == 0

    def test_should_handle_flush_failure(self) -> None:
        """Test batch clearing even when flush fails."""
        backend = ClickHouseBackend()

        # Add a span
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
        }
        backend.add_to_batch(otlp_span)

        # Mock failed insert
        with patch.object(backend, "_insert_batch", return_value=False):
            result = backend.flush()

        assert result is False
        assert len(backend._batch) == 0  # Batch should still be cleared


class TestHTTPInsertion:
    """Test HTTP insertion to ClickHouse."""

    def test_should_insert_batch_with_correct_format(self) -> None:
        """Test that batch is inserted with correct JSONEachRow format."""
        backend = ClickHouseBackend(compression_enabled=False)
        rows = [
            {"trace_id": "123", "span_id": "456", "span_name": "test1"},
            {"trace_id": "789", "span_id": "012", "span_name": "test2"},
        ]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = backend._insert_batch(rows, backend.traces_table)

        assert result is True
        assert mock_urlopen.called

        # Check request data format
        request = mock_urlopen.call_args[0][0]
        data = request.data.decode("utf-8")
        lines = data.split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["trace_id"] == "123"
        assert json.loads(lines[1])["trace_id"] == "789"

    def test_should_use_correct_endpoint_url(self) -> None:
        """Test that correct ClickHouse endpoint URL is used."""
        backend = ClickHouseBackend(
            endpoint="http://localhost:8123", database="test_db", table="test_table"
        )
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert "INSERT%20INTO%20test_db.test_table%20FORMAT%20JSONEachRow" in request.full_url or "test_db.test_table" in request.full_url

    def test_should_compress_data_when_enabled(self) -> None:
        """Test gzip compression when enabled and data is large enough."""
        backend = ClickHouseBackend(compression_enabled=True)
        # Create rows with enough data to trigger compression (>1024 bytes)
        rows = [{"trace_id": "x" * 200, "data": "y" * 200} for _ in range(5)]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert request.headers.get("Content-encoding") == "gzip"

        # Verify data is compressed
        decompressed = gzip.decompress(request.data)
        assert len(decompressed) > len(request.data)

    def test_should_not_compress_small_data(self) -> None:
        """Test that small data is not compressed."""
        backend = ClickHouseBackend(compression_enabled=True)
        rows = [{"trace_id": "123"}]  # Small data

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert request.headers.get("Content-encoding") is None

    def test_should_not_compress_when_disabled(self) -> None:
        """Test that compression is skipped when disabled."""
        backend = ClickHouseBackend(compression_enabled=False)
        rows = [{"trace_id": "x" * 500} for _ in range(10)]  # Large data

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert request.headers.get("Content-encoding") is None

    def test_should_include_auth_header_when_provided(self) -> None:
        """Test that authentication header is included when credentials provided."""
        backend = ClickHouseBackend(username="admin", password="secret123")
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Basic ")

    def test_should_not_include_auth_header_when_no_username(self) -> None:
        """Test that auth header is omitted when no username provided."""
        backend = ClickHouseBackend(username="", password="")
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert "Authorization" not in request.headers

    def test_should_return_false_on_empty_batch(self) -> None:
        """Test that inserting empty batch returns True."""
        backend = ClickHouseBackend()

        result = backend._insert_batch([], backend.traces_table)

        assert result is True

    def test_should_use_correct_content_type(self) -> None:
        """Test that correct Content-Type header is used."""
        backend = ClickHouseBackend()
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend._insert_batch(rows, backend.traces_table)

        request = mock_urlopen.call_args[0][0]
        assert request.headers.get("Content-type") == "application/x-ndjson"


class TestErrorHandling:
    """Test error handling and retry logic."""

    def test_should_retry_on_http_error(self) -> None:
        """Test retry logic on HTTP errors."""
        backend = ClickHouseBackend(max_retries=3)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://localhost:8123", 500, "Internal Server Error", {}, None
            )

            result = backend._insert_batch(rows, backend.traces_table)

        assert result is False
        # Should retry max_retries times
        assert mock_urlopen.call_count == 3

    def test_should_retry_on_url_error(self) -> None:
        """Test retry logic on URL/network errors."""
        backend = ClickHouseBackend(max_retries=2)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("Network unreachable")

            result = backend._insert_batch(rows, backend.traces_table)

        assert result is False
        assert mock_urlopen.call_count == 2

    def test_should_use_exponential_backoff(self) -> None:
        """Test exponential backoff between retries."""
        backend = ClickHouseBackend(max_retries=3)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://localhost:8123", 500, "Internal Server Error", {}, None
            )

            with patch("automagik_telemetry.backends.clickhouse.time.sleep") as mock_sleep:
                backend._insert_batch(rows, backend.traces_table)

                # Should sleep with exponential backoff: 2^0, 2^1
                assert mock_sleep.call_count == 2
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls[0] == 1  # 2^0
                assert sleep_calls[1] == 2  # 2^1

    def test_should_not_retry_on_generic_exception(self) -> None:
        """Test that generic exceptions don't trigger retries."""
        backend = ClickHouseBackend(max_retries=3)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Unexpected error")

            result = backend._insert_batch(rows, backend.traces_table)

        assert result is False
        # Should only try once (no retries for generic exceptions)
        assert mock_urlopen.call_count == 1

    def test_should_handle_non_200_status_code(self) -> None:
        """Test handling of non-200 HTTP status codes."""
        backend = ClickHouseBackend(max_retries=2)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.read.return_value = b"Bad request"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = backend._insert_batch(rows, backend.traces_table)

        assert result is False

    def test_should_succeed_after_retry(self) -> None:
        """Test successful insertion after initial failure."""
        backend = ClickHouseBackend(max_retries=3)
        rows = [{"trace_id": "123"}]

        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            # First two calls fail, third succeeds
            mock_response_success = Mock()
            mock_response_success.status = 200
            mock_response_success.__enter__ = Mock(return_value=mock_response_success)
            mock_response_success.__exit__ = Mock(return_value=False)

            mock_urlopen.side_effect = [
                HTTPError("http://localhost:8123", 500, "Error", {}, None),
                HTTPError("http://localhost:8123", 500, "Error", {}, None),
                mock_response_success,
            ]

            with patch("automagik_telemetry.backends.clickhouse.time.sleep"):
                result = backend._insert_batch(rows, backend.traces_table)

        assert result is True
        assert mock_urlopen.call_count == 3

    def test_should_handle_invalid_otlp_data_gracefully(self) -> None:
        """Test handling of invalid OTLP data."""
        backend = ClickHouseBackend()

        # Test with None
        result = backend.transform_otlp_to_clickhouse({})
        assert result["trace_id"] == ""
        assert result["span_id"] == ""

        # Test with missing required fields
        otlp_span: dict[str, Any] = {"some_field": "value"}
        result = backend.transform_otlp_to_clickhouse(otlp_span)
        assert result["trace_id"] == ""
        assert result["span_name"] == "unknown"


class TestSendTrace:
    """Test send_trace convenience method."""

    def test_should_send_single_trace(self) -> None:
        """Test sending a single trace."""
        backend = ClickHouseBackend(batch_size=10)
        otlp_span: dict[str, Any] = {
            "traceId": "123",
            "spanId": "456",
            "name": "test",
        }

        result = backend.send_trace(otlp_span)

        assert result is True
        assert len(backend._batch) == 1

    def test_should_handle_send_trace_error(self) -> None:
        """Test error handling in send_trace."""
        backend = ClickHouseBackend()

        with patch.object(backend, "add_to_batch", side_effect=Exception("Test error")):
            result = backend.send_trace({"traceId": "123"})

        assert result is False
