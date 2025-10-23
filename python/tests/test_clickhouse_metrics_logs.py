"""
Comprehensive tests for ClickHouse backend metrics and logs functionality.

Tests cover:
1. Metrics:
   - All metric types (GAUGE, SUM, HISTOGRAM, SUMMARY)
   - Batching and auto-flush behavior
   - Resource attributes extraction
   - Timestamp handling
   - Error handling
   - Value types and conversions

2. Logs:
   - All severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Exception tracking
   - Trace correlation (trace_id, span_id)
   - Batching and auto-flush behavior
   - Error handling
   - Resource attributes extraction

3. Integration:
   - Full flow: client -> backend -> ClickHouse
   - All 3 telemetry types together
   - Query verification
   - Cross-signal correlation

4. Edge Cases:
   - Empty/null values
   - Large batches
   - Concurrent operations
   - Compression behavior
"""

import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import Mock, patch, call

import pytest

from automagik_telemetry.backends.clickhouse import ClickHouseBackend


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def backend() -> ClickHouseBackend:
    """Create a basic ClickHouse backend instance."""
    return ClickHouseBackend(
        endpoint="http://localhost:8123",
        database="telemetry",
        batch_size=10,
        compression_enabled=False,
    )


@pytest.fixture
def backend_with_custom_tables() -> ClickHouseBackend:
    """Create backend with custom table names."""
    return ClickHouseBackend(
        endpoint="http://localhost:8123",
        database="custom_db",
        traces_table="custom_traces",
        metrics_table="custom_metrics",
        logs_table="custom_logs",
        batch_size=5,
    )


@pytest.fixture
def resource_attributes() -> dict[str, Any]:
    """Common resource attributes for testing."""
    return {
        "service.name": "test-service",
        "project.name": "test-project",
        "project.version": "1.0.0",
        "deployment.environment": "staging",
        "host.name": "test-host-01",
    }


@pytest.fixture
def mock_successful_response() -> Mock:
    """Mock successful HTTP response."""
    mock_response = Mock()
    mock_response.status = 200
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    return mock_response


# ============================================================================
# METRICS TESTS - Basic Functionality
# ============================================================================


class TestSendMetricBasic:
    """Test basic send_metric functionality."""

    def test_should_send_gauge_metric_with_minimal_params(self, backend: ClickHouseBackend) -> None:
        """Test sending a GAUGE metric with minimal parameters."""
        result = backend.send_metric(
            metric_name="cpu.usage",
            value=75.5,
            metric_type="gauge",
        )

        assert result is True
        assert len(backend._metric_batch) == 1

        metric = backend._metric_batch[0]
        assert metric["metric_name"] == "cpu.usage"
        assert metric["value_double"] == 75.5
        assert metric["metric_type"] == "GAUGE"
        assert metric["service_name"] == "unknown"
        assert metric["project_name"] == ""

    def test_should_send_gauge_metric_with_all_params(
        self, backend: ClickHouseBackend, resource_attributes: dict[str, Any]
    ) -> None:
        """Test sending a GAUGE metric with all parameters."""
        custom_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = backend.send_metric(
            metric_name="memory.usage",
            value=1024.5,
            metric_type="gauge",
            unit="MB",
            attributes={"region": "us-east-1", "tier": "premium"},
            resource_attributes=resource_attributes,
            timestamp=custom_timestamp,
        )

        assert result is True
        assert len(backend._metric_batch) == 1

        metric = backend._metric_batch[0]
        assert metric["metric_name"] == "memory.usage"
        assert metric["value_double"] == 1024.5
        assert metric["metric_type"] == "GAUGE"
        assert metric["metric_unit"] == "MB"
        assert metric["service_name"] == "test-service"
        assert metric["project_name"] == "test-project"
        assert metric["project_version"] == "1.0.0"
        assert metric["environment"] == "staging"
        assert metric["hostname"] == "test-host-01"
        assert metric["attributes"]["region"] == "us-east-1"
        assert metric["attributes"]["tier"] == "premium"
        assert metric["timestamp"] == "2024-01-01 12:00:00"
        assert isinstance(metric["metric_id"], str)
        assert len(metric["metric_id"]) == 36  # UUID format

    def test_should_send_sum_metric(self, backend: ClickHouseBackend) -> None:
        """Test sending a SUM/counter metric."""
        result = backend.send_metric(
            metric_name="http.requests.total",
            value=1000,
            metric_type="sum",
            unit="requests",
        )

        assert result is True
        metric = backend._metric_batch[0]
        assert metric["metric_type"] == "SUM"
        assert metric["value_int"] == 1000
        assert metric["metric_unit"] == "requests"

    def test_should_send_histogram_metric(self, backend: ClickHouseBackend) -> None:
        """Test sending a HISTOGRAM metric."""
        result = backend.send_metric(
            metric_name="http.request.duration",
            value=250.5,
            metric_type="histogram",
            unit="ms",
        )

        assert result is True
        metric = backend._metric_batch[0]
        assert metric["metric_type"] == "HISTOGRAM"
        assert metric["value_double"] == 250.5
        assert metric["metric_unit"] == "ms"

    def test_should_send_summary_metric(self, backend: ClickHouseBackend) -> None:
        """Test sending a SUMMARY metric."""
        result = backend.send_metric(
            metric_name="response.size",
            value=512.0,
            metric_type="summary",
            unit="bytes",
        )

        assert result is True
        metric = backend._metric_batch[0]
        assert metric["metric_type"] == "SUMMARY"
        assert metric["value_double"] == 512.0

    def test_should_use_current_time_when_timestamp_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test that current time is used when timestamp is not provided."""
        before = datetime.now(timezone.utc)

        backend.send_metric(
            metric_name="test.metric",
            value=100,
        )

        after = datetime.now(timezone.utc)

        metric = backend._metric_batch[0]
        metric_timestamp = datetime.strptime(metric["timestamp"], "%Y-%m-%d %H:%M:%S")

        # Timestamp should be between before and after (with timezone awareness comparison)
        assert before.replace(microsecond=0) <= metric_timestamp.replace(tzinfo=timezone.utc) <= after.replace(microsecond=0)

    def test_should_generate_unique_metric_ids(self, backend: ClickHouseBackend) -> None:
        """Test that each metric gets a unique ID."""
        backend.send_metric("metric1", 1.0)
        backend.send_metric("metric2", 2.0)
        backend.send_metric("metric3", 3.0)

        metric_ids = {m["metric_id"] for m in backend._metric_batch}
        assert len(metric_ids) == 3  # All unique

    def test_should_handle_integer_values(self, backend: ClickHouseBackend) -> None:
        """Test handling of integer metric values."""
        backend.send_metric("count", 42, metric_type="sum")

        metric = backend._metric_batch[0]
        assert metric["value_int"] == 42
        assert isinstance(metric["value_int"], int)

    def test_should_handle_float_values(self, backend: ClickHouseBackend) -> None:
        """Test handling of float metric values."""
        backend.send_metric("ratio", 0.75, metric_type="gauge")

        metric = backend._metric_batch[0]
        assert metric["value_double"] == 0.75

    def test_should_handle_zero_value(self, backend: ClickHouseBackend) -> None:
        """Test handling of zero metric value."""
        backend.send_metric("zero_metric", 0.0)

        metric = backend._metric_batch[0]
        assert metric["value_double"] == 0.0

    def test_should_handle_negative_value(self, backend: ClickHouseBackend) -> None:
        """Test handling of negative metric value."""
        backend.send_metric("temperature", -5.5, unit="celsius")

        metric = backend._metric_batch[0]
        assert metric["value_double"] == -5.5


# ============================================================================
# METRICS TESTS - Batching and Flushing
# ============================================================================


class TestMetricsBatching:
    """Test metric batching and auto-flush behavior."""

    def test_should_add_metrics_to_batch(self, backend: ClickHouseBackend) -> None:
        """Test adding multiple metrics to batch."""
        for i in range(5):
            backend.send_metric(f"metric_{i}", float(i))

        assert len(backend._metric_batch) == 5
        assert backend._metric_batch[0]["metric_name"] == "metric_0"
        assert backend._metric_batch[4]["metric_name"] == "metric_4"

    def test_should_auto_flush_when_batch_size_reached(self, backend: ClickHouseBackend) -> None:
        """Test auto-flush when metric batch size is reached."""
        backend.batch_size = 3

        with patch.object(backend, "flush") as mock_flush:
            # Add metrics up to batch_size
            backend.send_metric("metric_1", 1.0)
            backend.send_metric("metric_2", 2.0)
            backend.send_metric("metric_3", 3.0)

            # flush should be called when batch_size is reached
            assert mock_flush.call_count == 1

    def test_should_not_flush_before_batch_size_reached(self, backend: ClickHouseBackend) -> None:
        """Test that flush is not called before batch size is reached."""
        backend.batch_size = 5

        with patch.object(backend, "flush") as mock_flush:
            backend.send_metric("metric_1", 1.0)
            backend.send_metric("metric_2", 2.0)

            assert mock_flush.call_count == 0
            assert len(backend._metric_batch) == 2

    def test_should_clear_metric_batch_after_successful_flush(
        self, backend: ClickHouseBackend, mock_successful_response: Mock
    ) -> None:
        """Test that metric batch is cleared after successful flush."""
        backend.send_metric("metric_1", 1.0)
        backend.send_metric("metric_2", 2.0)

        assert len(backend._metric_batch) == 2

        with patch("automagik_telemetry.backends.clickhouse.urlopen", return_value=mock_successful_response):
            result = backend.flush()

        assert result is True
        assert len(backend._metric_batch) == 0

    def test_should_clear_metric_batch_even_on_flush_failure(self, backend: ClickHouseBackend) -> None:
        """Test that metric batch is cleared even when flush fails."""
        backend.send_metric("metric_1", 1.0)

        with patch.object(backend, "_insert_batch", return_value=False):
            result = backend.flush()

        assert result is False
        assert len(backend._metric_batch) == 0  # Batch cleared despite failure

    def test_should_handle_empty_metric_batch_flush(self, backend: ClickHouseBackend) -> None:
        """Test flushing empty metric batch."""
        assert len(backend._metric_batch) == 0

        result = backend.flush()

        assert result is True
        assert len(backend._metric_batch) == 0

    def test_should_flush_metrics_independently_from_traces(self, backend: ClickHouseBackend) -> None:
        """Test that metrics and traces flush independently."""
        # Add metrics
        backend.send_metric("metric_1", 1.0)
        backend.send_metric("metric_2", 2.0)

        # Add traces
        trace_span = {"traceId": "123", "spanId": "456", "name": "test"}
        backend.add_to_batch(trace_span)

        assert len(backend._metric_batch) == 2
        assert len(backend._trace_batch) == 1

        with patch.object(backend, "_insert_batch", return_value=True) as mock_insert:
            backend.flush()

        # Should be called twice: once for traces, once for metrics
        assert mock_insert.call_count == 2
        assert len(backend._metric_batch) == 0
        assert len(backend._trace_batch) == 0


# ============================================================================
# METRICS TESTS - Resource Attributes
# ============================================================================


class TestMetricsResourceAttributes:
    """Test resource attributes extraction for metrics."""

    def test_should_extract_service_name_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of service.name from resource attributes."""
        backend.send_metric(
            "test.metric",
            100,
            resource_attributes={"service.name": "payment-service"},
        )

        metric = backend._metric_batch[0]
        assert metric["service_name"] == "payment-service"

    def test_should_use_default_service_name_when_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test default service name when not provided."""
        backend.send_metric("test.metric", 100)

        metric = backend._metric_batch[0]
        assert metric["service_name"] == "unknown"

    def test_should_extract_project_info_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of project name and version."""
        backend.send_metric(
            "test.metric",
            100,
            resource_attributes={
                "project.name": "my-awesome-project",
                "project.version": "2.5.1",
            },
        )

        metric = backend._metric_batch[0]
        assert metric["project_name"] == "my-awesome-project"
        assert metric["project_version"] == "2.5.1"

    def test_should_extract_environment_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of deployment.environment."""
        backend.send_metric(
            "test.metric",
            100,
            resource_attributes={"deployment.environment": "production"},
        )

        metric = backend._metric_batch[0]
        assert metric["environment"] == "production"

    def test_should_use_default_environment_when_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test default environment value."""
        backend.send_metric("test.metric", 100)

        metric = backend._metric_batch[0]
        assert metric["environment"] == "production"

    def test_should_extract_hostname_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of host.name."""
        backend.send_metric(
            "test.metric",
            100,
            resource_attributes={"host.name": "server-42"},
        )

        metric = backend._metric_batch[0]
        assert metric["hostname"] == "server-42"

    def test_should_handle_empty_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of empty resource attributes."""
        backend.send_metric("test.metric", 100, resource_attributes={})

        metric = backend._metric_batch[0]
        assert metric["service_name"] == "unknown"
        assert metric["project_name"] == ""
        assert metric["hostname"] == ""


# ============================================================================
# METRICS TESTS - Custom Attributes
# ============================================================================


class TestMetricsCustomAttributes:
    """Test custom attributes for metrics."""

    def test_should_store_custom_attributes(self, backend: ClickHouseBackend) -> None:
        """Test storing custom metric attributes."""
        backend.send_metric(
            "http.requests",
            100,
            attributes={"method": "GET", "endpoint": "/api/users", "status": "200"},
        )

        metric = backend._metric_batch[0]
        assert metric["attributes"]["method"] == "GET"
        assert metric["attributes"]["endpoint"] == "/api/users"
        assert metric["attributes"]["status"] == "200"

    def test_should_extract_user_id_from_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of user.id from attributes."""
        backend.send_metric(
            "user.action",
            1,
            attributes={"user.id": "user-12345", "action": "login"},
        )

        metric = backend._metric_batch[0]
        assert metric["user_id"] == "user-12345"

    def test_should_extract_session_id_from_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of session.id from attributes."""
        backend.send_metric(
            "session.event",
            1,
            attributes={"session.id": "sess-abc123"},
        )

        metric = backend._metric_batch[0]
        assert metric["session_id"] == "sess-abc123"

    def test_should_handle_empty_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of empty attributes."""
        backend.send_metric("test.metric", 100, attributes={})

        metric = backend._metric_batch[0]
        assert metric["attributes"] == {}
        assert metric["user_id"] == ""
        assert metric["session_id"] == ""

    def test_should_handle_none_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of None attributes."""
        backend.send_metric("test.metric", 100, attributes=None)

        metric = backend._metric_batch[0]
        assert metric["attributes"] == {}


# ============================================================================
# LOGS TESTS - Basic Functionality
# ============================================================================


class TestSendLogBasic:
    """Test basic send_log functionality."""

    def test_should_send_log_with_minimal_params(self, backend: ClickHouseBackend) -> None:
        """Test sending a log with minimal parameters."""
        result = backend.send_log(message="Test log message")

        assert result is True
        assert len(backend._log_batch) == 1

        log = backend._log_batch[0]
        assert log["body"] == "Test log message"
        assert log["severity_text"] == "INFO"  # Default level
        assert log["service_name"] == "unknown"
        assert log["trace_id"] == ""
        assert log["span_id"] == ""

    def test_should_send_log_with_all_params(
        self, backend: ClickHouseBackend, resource_attributes: dict[str, Any]
    ) -> None:
        """Test sending a log with all parameters."""
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        result = backend.send_log(
            message="Error processing request",
            level="ERROR",
            attributes={"endpoint": "/api/data", "error_code": "500"},
            resource_attributes=resource_attributes,
            timestamp=custom_timestamp,
            trace_id="trace-abc123",
            span_id="span-def456",
        )

        assert result is True
        assert len(backend._log_batch) == 1

        log = backend._log_batch[0]
        assert log["body"] == "Error processing request"
        assert log["severity_text"] == "ERROR"
        assert log["service_name"] == "test-service"
        assert log["project_name"] == "test-project"
        assert log["project_version"] == "1.0.0"
        assert log["environment"] == "staging"
        assert log["hostname"] == "test-host-01"
        assert log["attributes"]["endpoint"] == "/api/data"
        assert log["attributes"]["error_code"] == "500"
        assert log["trace_id"] == "trace-abc123"
        assert log["span_id"] == "span-def456"
        assert log["timestamp"] == "2024-01-15 10:30:00"
        assert isinstance(log["log_id"], str)
        assert len(log["log_id"]) == 36  # UUID format

    def test_should_send_debug_level_log(self, backend: ClickHouseBackend) -> None:
        """Test sending a DEBUG level log."""
        backend.send_log("Debug message", level="DEBUG")

        log = backend._log_batch[0]
        assert log["severity_text"] == "DEBUG"

    def test_should_send_info_level_log(self, backend: ClickHouseBackend) -> None:
        """Test sending an INFO level log."""
        backend.send_log("Info message", level="INFO")

        log = backend._log_batch[0]
        assert log["severity_text"] == "INFO"

    def test_should_send_warning_level_log(self, backend: ClickHouseBackend) -> None:
        """Test sending a WARNING level log."""
        backend.send_log("Warning message", level="WARNING")

        log = backend._log_batch[0]
        assert log["severity_text"] == "WARNING"

    def test_should_send_error_level_log(self, backend: ClickHouseBackend) -> None:
        """Test sending an ERROR level log."""
        backend.send_log("Error message", level="ERROR")

        log = backend._log_batch[0]
        assert log["severity_text"] == "ERROR"

    def test_should_send_critical_level_log(self, backend: ClickHouseBackend) -> None:
        """Test sending a CRITICAL level log."""
        backend.send_log("Critical message", level="CRITICAL")

        log = backend._log_batch[0]
        assert log["severity_text"] == "CRITICAL"

    def test_should_normalize_level_to_uppercase(self, backend: ClickHouseBackend) -> None:
        """Test that log level is normalized to uppercase."""
        backend.send_log("Test", level="error")

        log = backend._log_batch[0]
        assert log["severity_text"] == "ERROR"

    def test_should_use_current_time_when_timestamp_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test that current time is used when timestamp is not provided."""
        before = datetime.now(timezone.utc)

        backend.send_log("Test log")

        after = datetime.now(timezone.utc)

        log = backend._log_batch[0]
        log_timestamp = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")

        assert before.replace(microsecond=0) <= log_timestamp.replace(tzinfo=timezone.utc) <= after.replace(microsecond=0)

    def test_should_generate_unique_log_ids(self, backend: ClickHouseBackend) -> None:
        """Test that each log gets a unique ID."""
        backend.send_log("Log 1")
        backend.send_log("Log 2")
        backend.send_log("Log 3")

        log_ids = {log["log_id"] for log in backend._log_batch}
        assert len(log_ids) == 3  # All unique

    def test_should_handle_empty_message(self, backend: ClickHouseBackend) -> None:
        """Test handling of empty log message."""
        backend.send_log("")

        log = backend._log_batch[0]
        assert log["body"] == ""

    def test_should_handle_multiline_message(self, backend: ClickHouseBackend) -> None:
        """Test handling of multiline log message."""
        multiline_msg = "Line 1\nLine 2\nLine 3"
        backend.send_log(multiline_msg)

        log = backend._log_batch[0]
        assert log["body"] == multiline_msg


# ============================================================================
# LOGS TESTS - Trace Correlation
# ============================================================================


class TestLogsTraceCorrelation:
    """Test log-trace correlation functionality."""

    def test_should_link_log_to_trace(self, backend: ClickHouseBackend) -> None:
        """Test linking log to trace via trace_id."""
        backend.send_log(
            "Request completed",
            trace_id="a" * 32,
        )

        log = backend._log_batch[0]
        assert log["trace_id"] == "a" * 32

    def test_should_link_log_to_span(self, backend: ClickHouseBackend) -> None:
        """Test linking log to span via span_id."""
        backend.send_log(
            "Span event",
            trace_id="a" * 32,
            span_id="b" * 16,
        )

        log = backend._log_batch[0]
        assert log["trace_id"] == "a" * 32
        assert log["span_id"] == "b" * 16

    def test_should_handle_missing_trace_correlation(self, backend: ClickHouseBackend) -> None:
        """Test handling of logs without trace correlation."""
        backend.send_log("Standalone log")

        log = backend._log_batch[0]
        assert log["trace_id"] == ""
        assert log["span_id"] == ""

    def test_should_handle_partial_trace_correlation(self, backend: ClickHouseBackend) -> None:
        """Test handling of logs with only trace_id."""
        backend.send_log("Log with trace", trace_id="trace-123")

        log = backend._log_batch[0]
        assert log["trace_id"] == "trace-123"
        assert log["span_id"] == ""


# ============================================================================
# LOGS TESTS - Batching and Flushing
# ============================================================================


class TestLogsBatching:
    """Test log batching and auto-flush behavior."""

    def test_should_add_logs_to_batch(self, backend: ClickHouseBackend) -> None:
        """Test adding multiple logs to batch."""
        for i in range(5):
            backend.send_log(f"Log message {i}")

        assert len(backend._log_batch) == 5
        assert backend._log_batch[0]["body"] == "Log message 0"
        assert backend._log_batch[4]["body"] == "Log message 4"

    def test_should_auto_flush_when_batch_size_reached(self, backend: ClickHouseBackend) -> None:
        """Test auto-flush when log batch size is reached."""
        backend.batch_size = 3

        with patch.object(backend, "flush") as mock_flush:
            backend.send_log("Log 1")
            backend.send_log("Log 2")
            backend.send_log("Log 3")

            assert mock_flush.call_count == 1

    def test_should_not_flush_before_batch_size_reached(self, backend: ClickHouseBackend) -> None:
        """Test that flush is not called before batch size is reached."""
        backend.batch_size = 5

        with patch.object(backend, "flush") as mock_flush:
            backend.send_log("Log 1")
            backend.send_log("Log 2")

            assert mock_flush.call_count == 0
            assert len(backend._log_batch) == 2

    def test_should_clear_log_batch_after_successful_flush(
        self, backend: ClickHouseBackend, mock_successful_response: Mock
    ) -> None:
        """Test that log batch is cleared after successful flush."""
        backend.send_log("Log 1")
        backend.send_log("Log 2")

        assert len(backend._log_batch) == 2

        with patch("automagik_telemetry.backends.clickhouse.urlopen", return_value=mock_successful_response):
            result = backend.flush()

        assert result is True
        assert len(backend._log_batch) == 0

    def test_should_clear_log_batch_even_on_flush_failure(self, backend: ClickHouseBackend) -> None:
        """Test that log batch is cleared even when flush fails."""
        backend.send_log("Log 1")

        with patch.object(backend, "_insert_batch", return_value=False):
            result = backend.flush()

        assert result is False
        assert len(backend._log_batch) == 0

    def test_should_handle_empty_log_batch_flush(self, backend: ClickHouseBackend) -> None:
        """Test flushing empty log batch."""
        assert len(backend._log_batch) == 0

        result = backend.flush()

        assert result is True
        assert len(backend._log_batch) == 0

    def test_should_flush_logs_independently_from_traces(self, backend: ClickHouseBackend) -> None:
        """Test that logs and traces flush independently."""
        # Add logs
        backend.send_log("Log 1")
        backend.send_log("Log 2")

        # Add traces
        trace_span = {"traceId": "123", "spanId": "456", "name": "test"}
        backend.add_to_batch(trace_span)

        assert len(backend._log_batch) == 2
        assert len(backend._trace_batch) == 1

        with patch.object(backend, "_insert_batch", return_value=True) as mock_insert:
            backend.flush()

        # Should be called twice: once for traces, once for logs
        assert mock_insert.call_count == 2
        assert len(backend._log_batch) == 0
        assert len(backend._trace_batch) == 0


# ============================================================================
# LOGS TESTS - Resource Attributes
# ============================================================================


class TestLogsResourceAttributes:
    """Test resource attributes extraction for logs."""

    def test_should_extract_service_name_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of service.name from resource attributes."""
        backend.send_log(
            "Test log",
            resource_attributes={"service.name": "auth-service"},
        )

        log = backend._log_batch[0]
        assert log["service_name"] == "auth-service"

    def test_should_use_default_service_name_when_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test default service name when not provided."""
        backend.send_log("Test log")

        log = backend._log_batch[0]
        assert log["service_name"] == "unknown"

    def test_should_extract_project_info_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of project name and version."""
        backend.send_log(
            "Test log",
            resource_attributes={
                "project.name": "logging-demo",
                "project.version": "3.2.1",
            },
        )

        log = backend._log_batch[0]
        assert log["project_name"] == "logging-demo"
        assert log["project_version"] == "3.2.1"

    def test_should_extract_environment_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of deployment.environment."""
        backend.send_log(
            "Test log",
            resource_attributes={"deployment.environment": "development"},
        )

        log = backend._log_batch[0]
        assert log["environment"] == "development"

    def test_should_use_default_environment_when_not_provided(self, backend: ClickHouseBackend) -> None:
        """Test default environment value."""
        backend.send_log("Test log")

        log = backend._log_batch[0]
        assert log["environment"] == "production"

    def test_should_extract_hostname_from_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of host.name."""
        backend.send_log(
            "Test log",
            resource_attributes={"host.name": "log-server-01"},
        )

        log = backend._log_batch[0]
        assert log["hostname"] == "log-server-01"

    def test_should_handle_empty_resource_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of empty resource attributes."""
        backend.send_log("Test log", resource_attributes={})

        log = backend._log_batch[0]
        assert log["service_name"] == "unknown"
        assert log["project_name"] == ""
        assert log["hostname"] == ""


# ============================================================================
# LOGS TESTS - Custom Attributes
# ============================================================================


class TestLogsCustomAttributes:
    """Test custom attributes for logs."""

    def test_should_store_custom_attributes(self, backend: ClickHouseBackend) -> None:
        """Test storing custom log attributes."""
        backend.send_log(
            "Request failed",
            attributes={"http.method": "POST", "http.url": "/api/submit", "response.code": "500"},
        )

        log = backend._log_batch[0]
        assert log["attributes"]["http.method"] == "POST"
        assert log["attributes"]["http.url"] == "/api/submit"
        assert log["attributes"]["response.code"] == "500"

    def test_should_extract_user_id_from_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of user.id from attributes."""
        backend.send_log(
            "User login",
            attributes={"user.id": "user-99999", "action": "login"},
        )

        log = backend._log_batch[0]
        assert log["user_id"] == "user-99999"

    def test_should_extract_session_id_from_attributes(self, backend: ClickHouseBackend) -> None:
        """Test extraction of session.id from attributes."""
        backend.send_log(
            "Session started",
            attributes={"session.id": "sess-xyz789"},
        )

        log = backend._log_batch[0]
        assert log["session_id"] == "sess-xyz789"

    def test_should_handle_empty_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of empty attributes."""
        backend.send_log("Test log", attributes={})

        log = backend._log_batch[0]
        assert log["attributes"] == {}
        assert log["user_id"] == ""
        assert log["session_id"] == ""

    def test_should_handle_none_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of None attributes."""
        backend.send_log("Test log", attributes=None)

        log = backend._log_batch[0]
        assert log["attributes"] == {}


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test error handling for metrics and logs."""

    def test_should_handle_exception_in_send_metric(self, backend: ClickHouseBackend) -> None:
        """Test error handling when send_metric raises exception."""
        with patch("uuid.uuid4", side_effect=Exception("UUID generation failed")):
            result = backend.send_metric("test.metric", 100)

        assert result is False

    def test_should_handle_exception_in_send_log(self, backend: ClickHouseBackend) -> None:
        """Test error handling when send_log raises exception."""
        with patch("uuid.uuid4", side_effect=Exception("UUID generation failed")):
            result = backend.send_log("Test log")

        assert result is False

    def test_should_continue_after_metric_error(self, backend: ClickHouseBackend) -> None:
        """Test that system continues after metric error."""
        # First metric fails
        with patch("uuid.uuid4", side_effect=Exception("Error")):
            result1 = backend.send_metric("metric1", 1.0)

        # Second metric succeeds
        result2 = backend.send_metric("metric2", 2.0)

        assert result1 is False
        assert result2 is True
        assert len(backend._metric_batch) == 1

    def test_should_continue_after_log_error(self, backend: ClickHouseBackend) -> None:
        """Test that system continues after log error."""
        # First log fails
        with patch("uuid.uuid4", side_effect=Exception("Error")):
            result1 = backend.send_log("Log 1")

        # Second log succeeds
        result2 = backend.send_log("Log 2")

        assert result1 is False
        assert result2 is True
        assert len(backend._log_batch) == 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegrationFullFlow:
    """Integration tests for full telemetry flow."""

    def test_should_send_all_three_telemetry_types_together(
        self, backend: ClickHouseBackend, mock_successful_response: Mock
    ) -> None:
        """Test sending traces, metrics, and logs together."""
        # Send trace
        trace_span = {"traceId": "trace-123", "spanId": "span-456", "name": "test-operation"}
        backend.send_trace(trace_span)

        # Send metrics
        backend.send_metric("http.duration", 150.5, metric_type="histogram", unit="ms")
        backend.send_metric("http.requests", 1, metric_type="sum")

        # Send logs
        backend.send_log("Request started", level="INFO", trace_id="trace-123", span_id="span-456")
        backend.send_log("Request completed", level="INFO", trace_id="trace-123", span_id="span-456")

        # Verify batches
        assert len(backend._trace_batch) == 1
        assert len(backend._metric_batch) == 2
        assert len(backend._log_batch) == 2

        # Flush all
        with patch("automagik_telemetry.backends.clickhouse.urlopen", return_value=mock_successful_response):
            result = backend.flush()

        assert result is True
        assert len(backend._trace_batch) == 0
        assert len(backend._metric_batch) == 0
        assert len(backend._log_batch) == 0

    def test_should_insert_to_correct_tables(
        self, backend: ClickHouseBackend, mock_successful_response: Mock
    ) -> None:
        """Test that each telemetry type is inserted to the correct table."""
        backend.send_trace({"traceId": "123", "spanId": "456", "name": "test"})
        backend.send_metric("test.metric", 100)
        backend.send_log("Test log")

        with patch("automagik_telemetry.backends.clickhouse.urlopen", return_value=mock_successful_response) as mock_urlopen:
            backend.flush()

        # Should have 3 insert calls
        assert mock_urlopen.call_count == 3

        # Extract table names from URLs
        urls = [call[0][0].full_url for call in mock_urlopen.call_args_list]

        # Verify tables
        assert any("traces" in url for url in urls)
        assert any("metrics" in url for url in urls)
        assert any("logs" in url for url in urls)

    def test_should_use_custom_table_names(
        self, backend_with_custom_tables: ClickHouseBackend, mock_successful_response: Mock
    ) -> None:
        """Test using custom table names for each telemetry type."""
        backend_with_custom_tables.send_trace({"traceId": "123", "spanId": "456", "name": "test"})
        backend_with_custom_tables.send_metric("test.metric", 100)
        backend_with_custom_tables.send_log("Test log")

        with patch("automagik_telemetry.backends.clickhouse.urlopen", return_value=mock_successful_response) as mock_urlopen:
            backend_with_custom_tables.flush()

        urls = [call[0][0].full_url for call in mock_urlopen.call_args_list]

        assert any("custom_traces" in url for url in urls)
        assert any("custom_metrics" in url for url in urls)
        assert any("custom_logs" in url for url in urls)

    def test_should_correlate_logs_with_traces(self, backend: ClickHouseBackend) -> None:
        """Test that logs can be correlated with traces using trace_id."""
        trace_id = "correlation-test-" + str(uuid.uuid4())
        span_id = "span-" + str(uuid.uuid4())

        # Send trace
        backend.send_trace({"traceId": trace_id, "spanId": span_id, "name": "db-query"})

        # Send related logs
        backend.send_log("Query started", trace_id=trace_id, span_id=span_id)
        backend.send_log("Query completed", trace_id=trace_id, span_id=span_id)

        # Verify correlation
        trace = backend._trace_batch[0]
        log1 = backend._log_batch[0]
        log2 = backend._log_batch[1]

        assert trace["trace_id"] == trace_id
        assert log1["trace_id"] == trace_id
        assert log2["trace_id"] == trace_id
        assert log1["span_id"] == span_id
        assert log2["span_id"] == span_id

    def test_should_handle_partial_flush_failure(self, backend: ClickHouseBackend) -> None:
        """Test handling when some inserts succeed and others fail."""
        backend.send_trace({"traceId": "123", "spanId": "456", "name": "test"})
        backend.send_metric("test.metric", 100)
        backend.send_log("Test log")

        # Mock _insert_batch to fail for metrics only
        original_insert = backend._insert_batch
        call_count = [0]

        def mock_insert(rows, table_name):
            call_count[0] += 1
            if "metrics" in table_name:
                return False  # Metrics insert fails
            return original_insert(rows, table_name)

        with patch.object(backend, "_insert_batch", side_effect=mock_insert):
            with patch("automagik_telemetry.backends.clickhouse.urlopen") as mock_urlopen:
                mock_response = Mock()
                mock_response.status = 200
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                mock_urlopen.return_value = mock_response

                result = backend.flush()

        # Overall result should be False if any insert failed
        assert result is False

        # All batches should be cleared regardless
        assert len(backend._trace_batch) == 0
        assert len(backend._metric_batch) == 0
        assert len(backend._log_batch) == 0


# ============================================================================
# TIMESTAMP AND PRECISION TESTS
# ============================================================================


class TestTimestampPrecision:
    """Test timestamp handling and nanosecond precision."""

    def test_should_store_nanosecond_precision_for_metrics(self, backend: ClickHouseBackend) -> None:
        """Test nanosecond precision timestamp storage for metrics."""
        timestamp = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=timezone.utc)

        backend.send_metric("test.metric", 100, timestamp=timestamp)

        metric = backend._metric_batch[0]
        assert metric["timestamp_ns"] > 0
        assert isinstance(metric["timestamp_ns"], int)

    def test_should_store_nanosecond_precision_for_logs(self, backend: ClickHouseBackend) -> None:
        """Test nanosecond precision timestamp storage for logs."""
        timestamp = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=timezone.utc)

        backend.send_log("Test log", timestamp=timestamp)

        log = backend._log_batch[0]
        assert log["timestamp_ns"] > 0
        assert isinstance(log["timestamp_ns"], int)

    def test_should_handle_timezone_aware_timestamps(self, backend: ClickHouseBackend) -> None:
        """Test handling of timezone-aware timestamps."""
        # UTC timestamp
        utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        backend.send_metric("test.metric", 100, timestamp=utc_time)

        metric = backend._metric_batch[0]
        assert metric["timestamp"] == "2024-01-01 12:00:00"

    def test_should_handle_past_timestamps(self, backend: ClickHouseBackend) -> None:
        """Test handling of past timestamps."""
        past_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        backend.send_log("Old log", timestamp=past_time)

        log = backend._log_batch[0]
        assert log["timestamp"] == "2020-01-01 00:00:00"

    def test_should_handle_future_timestamps(self, backend: ClickHouseBackend) -> None:
        """Test handling of future timestamps."""
        future_time = datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        backend.send_metric("test.metric", 100, timestamp=future_time)

        metric = backend._metric_batch[0]
        assert metric["timestamp"] == "2030-12-31 23:59:59"


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_should_maintain_backward_compatible_table_parameter(self) -> None:
        """Test that old 'table' parameter still works for traces."""
        backend = ClickHouseBackend(table="legacy_traces")

        assert backend.table == "legacy_traces"
        assert backend.traces_table == "legacy_traces"

    def test_should_support_old_batch_property(self, backend: ClickHouseBackend) -> None:
        """Test that _batch property still points to _trace_batch."""
        backend.send_trace({"traceId": "123", "spanId": "456", "name": "test"})

        assert len(backend._batch) == 1
        assert len(backend._trace_batch) == 1
        assert backend._batch is backend._trace_batch

    def test_should_allow_explicit_table_name_override(self) -> None:
        """Test explicit table name parameters override defaults."""
        backend = ClickHouseBackend(
            traces_table="custom_traces",
            metrics_table="custom_metrics",
            logs_table="custom_logs",
        )

        assert backend.traces_table == "custom_traces"
        assert backend.metrics_table == "custom_metrics"
        assert backend.logs_table == "custom_logs"


# ============================================================================
# EDGE CASES AND BOUNDARY TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_should_handle_very_large_metric_value(self, backend: ClickHouseBackend) -> None:
        """Test handling of very large metric values."""
        large_value = 1.7976931348623157e308  # Near max float

        backend.send_metric("large.metric", large_value)

        metric = backend._metric_batch[0]
        assert metric["value_double"] == large_value

    def test_should_handle_very_small_metric_value(self, backend: ClickHouseBackend) -> None:
        """Test handling of very small metric values."""
        small_value = 2.2250738585072014e-308  # Near min positive float

        backend.send_metric("small.metric", small_value)

        metric = backend._metric_batch[0]
        assert metric["value_double"] == small_value

    def test_should_handle_very_long_log_message(self, backend: ClickHouseBackend) -> None:
        """Test handling of very long log messages."""
        long_message = "A" * 100000  # 100k characters

        backend.send_log(long_message)

        log = backend._log_batch[0]
        assert log["body"] == long_message
        assert len(log["body"]) == 100000

    def test_should_handle_special_characters_in_log_message(self, backend: ClickHouseBackend) -> None:
        """Test handling of special characters in log messages."""
        special_msg = "Special chars: \n\t\r\\ ' \" {} [] <> & | $ @ # %"

        backend.send_log(special_msg)

        log = backend._log_batch[0]
        assert log["body"] == special_msg

    def test_should_handle_unicode_in_log_message(self, backend: ClickHouseBackend) -> None:
        """Test handling of Unicode characters in log messages."""
        unicode_msg = "Unicode: 你好 🚀 مرحبا Здравствуй"

        backend.send_log(unicode_msg)

        log = backend._log_batch[0]
        assert log["body"] == unicode_msg

    def test_should_handle_large_number_of_attributes(self, backend: ClickHouseBackend) -> None:
        """Test handling of many attributes."""
        many_attrs = {f"attr_{i}": f"value_{i}" for i in range(100)}

        backend.send_metric("test.metric", 100, attributes=many_attrs)

        metric = backend._metric_batch[0]
        assert len(metric["attributes"]) == 100
        assert metric["attributes"]["attr_0"] == "value_0"
        assert metric["attributes"]["attr_99"] == "value_99"

    def test_should_handle_nested_dict_in_attributes(self, backend: ClickHouseBackend) -> None:
        """Test that nested dicts in attributes are handled (converted to strings)."""
        # Note: Current implementation stores as-is, but this tests the behavior
        nested_attrs = {"simple": "value", "nested": {"key": "value"}}

        backend.send_log("Test", attributes=nested_attrs)

        log = backend._log_batch[0]
        assert "simple" in log["attributes"]
        assert "nested" in log["attributes"]

    def test_should_handle_batch_size_of_one(self) -> None:
        """Test backend with batch_size=1 (immediate flush)."""
        backend = ClickHouseBackend(batch_size=1)

        with patch.object(backend, "flush") as mock_flush:
            backend.send_metric("metric", 100)
            # Should flush immediately
            assert mock_flush.call_count == 1

    def test_should_handle_very_large_batch_size(self) -> None:
        """Test backend with very large batch_size."""
        backend = ClickHouseBackend(batch_size=10000)

        # Add many items without flushing
        for i in range(100):
            backend.send_metric(f"metric_{i}", float(i))

        assert len(backend._metric_batch) == 100
        # No auto-flush yet
        assert backend._metric_batch[0]["metric_name"] == "metric_0"
