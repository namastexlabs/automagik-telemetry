"""
Comprehensive tests to achieve 100% coverage for backend error paths and edge cases.

This test file targets specific uncovered lines:
- clickhouse.py: lines 265, 272, 278, 289-292, 295, 306, 373-379, 391-392, 394-395, 534-540
- otlp.py: line 209
- base.py: abstract methods already have # pragma: no cover
"""

import io
import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from automagik_telemetry.backends.clickhouse import ClickHouseBackend
from automagik_telemetry.backends.otlp import OTLPBackend


class TestClickHouseErrorPathsWithVerbose:
    """Test ClickHouse error handling with verbose mode enabled."""

    def test_verbose_success_message_on_200_response(self, capsys: Any) -> None:
        """Test verbose print statement on successful 200 response (line 265)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1)

        # Add a span to batch
        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock the HTTP request to return 200
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend.add_to_batch(span_data)

        # Check that verbose message was printed
        captured = capsys.readouterr()
        assert "Inserted 1 rows to ClickHouse table traces successfully" in captured.out

    def test_verbose_message_on_5xx_server_error(self, capsys: Any) -> None:
        """Test 5xx server error handling creates exception with response body (line 272)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1, max_retries=1)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock 5xx error response
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 500
            mock_response.read.return_value = b"Internal Server Error"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend.add_to_batch(span_data)

        # Verify error handling occurred
        captured = capsys.readouterr()
        assert "Failed to insert to ClickHouse" in captured.out

    def test_verbose_message_on_4xx_client_error(self, capsys: Any) -> None:
        """Test verbose print on 4xx client error (line 278)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock 4xx error response
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.read.return_value = b"Bad Request"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            backend.add_to_batch(span_data)

        captured = capsys.readouterr()
        assert "ClickHouse returned status 400" in captured.out

    def test_verbose_message_on_http_error_4xx(self, capsys: Any) -> None:
        """Test verbose print on HTTPError with 4xx status (lines 289-290)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock HTTPError with 400 status
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            http_error = HTTPError(
                "http://test", 400, "Bad Request", {}, io.BytesIO(b"Bad Request")
            )  # type: ignore
            mock_urlopen.side_effect = http_error

            backend.add_to_batch(span_data)

        captured = capsys.readouterr()
        assert "Failed to insert to ClickHouse" in captured.out

    def test_verbose_message_on_retryable_error(self, capsys: Any) -> None:
        """Test verbose print on retryable error (line 295)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1, max_retries=2)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock URLError (retryable)
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("Network error")

            backend.add_to_batch(span_data)

        captured = capsys.readouterr()
        assert "Error inserting to ClickHouse (attempt" in captured.out

    def test_verbose_message_after_retry_exhaustion(self, capsys: Any) -> None:
        """Test verbose print after all retries exhausted (line 306)."""
        backend = ClickHouseBackend(
            verbose=True, batch_size=1, max_retries=1, retry_backoff_base=0.01
        )

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock persistent error
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timeout")

            backend.add_to_batch(span_data)

        captured = capsys.readouterr()
        assert "Failed to insert to ClickHouse after 1 retries" in captured.out


class TestClickHouseMetricEdgeCases:
    """Test ClickHouse metric sending edge cases."""

    def test_send_metric_with_dict_payload_interface(self) -> None:
        """Test new dict payload interface for metrics (lines 373-379)."""
        backend = ClickHouseBackend(batch_size=100)

        # Use new dict payload interface
        metric_payload = {
            "metric_name": "test_metric",
            "value": 42.5,
            "metric_type": "gauge",
            "unit": "ms",
            "attributes": {"key": "value"},
            "resource_attributes": {"service.name": "test"},
            "timestamp": datetime.now(UTC),
        }

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_metric(payload=metric_payload)

        assert result is True

    def test_send_metric_missing_name_validation(self) -> None:
        """Test metric validation for missing metric_name (line 391)."""
        backend = ClickHouseBackend()

        # Try to send metric without name
        result = backend.send_metric(payload=None, value=10.0)

        assert result is False

    def test_send_metric_missing_value_validation(self) -> None:
        """Test metric validation for missing value (line 394)."""
        backend = ClickHouseBackend()

        # Try to send metric without value (non-dict payload)
        result = backend.send_metric(payload="test_metric", value=None)

        assert result is False


class TestClickHouseLogEdgeCases:
    """Test ClickHouse log sending edge cases."""

    def test_send_log_with_dict_payload_interface(self) -> None:
        """Test new dict payload interface for logs (lines 534-540)."""
        backend = ClickHouseBackend(batch_size=100)

        # Use new dict payload interface
        log_payload = {
            "message": "Test log message",
            "level": "ERROR",
            "attributes": {"key": "value"},
            "resource_attributes": {"service.name": "test"},
            "timestamp": datetime.now(UTC),
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
        }

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_log(payload=log_payload)

        assert result is True


class TestOTLPBackendFlush:
    """Test OTLP backend flush method."""

    def test_flush_returns_true_no_op(self) -> None:
        """Test that OTLP flush() returns True as no-op (line 209)."""
        backend = OTLPBackend(
            endpoint="http://localhost:4318/v1/traces",
            metrics_endpoint="http://localhost:4318/v1/metrics",
            logs_endpoint="http://localhost:4318/v1/logs",
        )

        result = backend.flush()

        assert result is True


class TestClickHouseHTTPErrorHandling:
    """Test specific HTTP error handling paths."""

    def test_http_error_with_5xx_status_triggers_retry(self) -> None:
        """Test HTTPError with 5xx status triggers retry logic (line 272)."""
        backend = ClickHouseBackend(batch_size=1, max_retries=2, retry_backoff_base=0.01)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock 503 server error response that eventually succeeds
        call_count = 0

        def mock_urlopen_side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: 503 error
                mock_response = Mock()
                mock_response.status = 503
                mock_response.read.return_value = b"Service Unavailable"
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                return mock_response
            else:
                # Second call: success
                mock_response = Mock()
                mock_response.status = 200
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                return mock_response

        with patch(
            "automagik_telemetry.backends.clickhouse.urlopen", side_effect=mock_urlopen_side_effect
        ):
            backend.add_to_batch(span_data)

        # Should have retried and succeeded
        assert call_count == 2

    def test_general_exception_during_insert(self, capsys: Any) -> None:
        """Test general Exception handling during insert (line 284)."""
        backend = ClickHouseBackend(verbose=True, batch_size=1, max_retries=1)

        span_data = {
            "trace_id": "12345678901234567890123456789012",
            "span_id": "1234567890123456",
            "name": "test_span",
            "start_time": 1234567890000000000,
            "end_time": 1234567891000000000,
            "attributes": {},
            "resource_attributes": {"service.name": "test"},
        }

        # Mock unexpected exception
        with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Unexpected error")

            backend.add_to_batch(span_data)

        captured = capsys.readouterr()
        assert "Error inserting to ClickHouse" in captured.out


class TestBackwardCompatibilityMetrics:
    """Test backward compatibility for metric sending."""

    def test_send_metric_string_payload_backward_compat(self) -> None:
        """Test backward compatible string payload for metrics (line 382)."""
        backend = ClickHouseBackend(batch_size=100)

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_metric(payload="metric_name", value=10.0)

        assert result is True

    def test_send_metric_kwargs_backward_compat(self) -> None:
        """Test backward compatible kwargs interface (line 386)."""
        backend = ClickHouseBackend(batch_size=100)

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_metric(payload=None, metric_name="test_metric", value=10.0)

        assert result is True


class TestBackwardCompatibilityLogs:
    """Test backward compatibility for log sending."""

    def test_send_log_string_payload_backward_compat(self) -> None:
        """Test backward compatible string payload for logs."""
        backend = ClickHouseBackend(batch_size=100)

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_log(payload="Test log message")

        assert result is True

    def test_send_log_kwargs_backward_compat(self) -> None:
        """Test backward compatible kwargs interface for logs."""
        backend = ClickHouseBackend(batch_size=100)

        with patch("automagik_telemetry.backends.clickhouse.urlopen"):
            result = backend.send_log(payload=None, message="Test log message", level="INFO")

        assert result is True
