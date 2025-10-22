"""
Tests for advanced OTLP features.

Tests cover:
- OTLP metrics export
- OTLP logs export
- Batch processing
- Compression
- Retry logic with exponential backoff
"""

import gzip
import json
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import pytest

from automagik_telemetry.client import (
    LogSeverity,
    MetricType,
    TelemetryClient,
    TelemetryConfig,
)


class TestMetricsExport:
    """Test OTLP metrics export functionality."""

    def test_should_send_gauge_metric(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test sending a gauge metric."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        client.track_metric(
            "cpu.usage", 75.5, metric_type=MetricType.GAUGE, attributes={"host": "server1"}
        )

        # Should make HTTP request when enabled
        mock_urlopen.assert_called_once()

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Verify endpoint
        assert "/v1/metrics" in request.full_url

        # Parse the payload
        payload = json.loads(request.data.decode("utf-8"))

        # Verify OTLP metrics structure
        assert "resourceMetrics" in payload
        resource_metrics = payload["resourceMetrics"][0]
        assert "scopeMetrics" in resource_metrics

        metrics = resource_metrics["scopeMetrics"][0]["metrics"]
        assert len(metrics) == 1

        metric = metrics[0]
        assert metric["name"] == "cpu.usage"
        assert "gauge" in metric
        assert metric["gauge"]["dataPoints"][0]["asDouble"] == 75.5

    def test_should_send_counter_metric(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test sending a counter metric."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        client.track_metric(
            "requests.total",
            1000,
            metric_type=MetricType.COUNTER,
            attributes={"endpoint": "/api/users"},
        )

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        metric = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]
        assert metric["name"] == "requests.total"
        assert "sum" in metric
        assert metric["sum"]["isMonotonic"] is True

    def test_should_send_histogram_metric(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test sending a histogram metric."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        client.track_metric(
            "request.duration",
            145.3,
            metric_type=MetricType.HISTOGRAM,
            attributes={"status_code": "200"},
        )

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        metric = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]
        assert metric["name"] == "request.duration"
        assert "histogram" in metric
        assert metric["histogram"]["dataPoints"][0]["sum"] == 145.3


class TestLogsExport:
    """Test OTLP logs export functionality."""

    def test_should_send_info_log(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test sending an INFO level log."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        client.track_log(
            "User logged in successfully",
            severity=LogSeverity.INFO,
            attributes={"user_type": "admin"},
        )

        # Should make HTTP request
        mock_urlopen.assert_called_once()

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Verify endpoint
        assert "/v1/logs" in request.full_url

        # Parse payload
        payload = json.loads(request.data.decode("utf-8"))

        # Verify OTLP logs structure
        assert "resourceLogs" in payload
        resource_logs = payload["resourceLogs"][0]
        assert "scopeLogs" in resource_logs

        log_records = resource_logs["scopeLogs"][0]["logRecords"]
        assert len(log_records) == 1

        log_record = log_records[0]
        assert log_record["body"]["stringValue"] == "User logged in successfully"
        assert log_record["severityNumber"] == LogSeverity.INFO.value
        assert log_record["severityText"] == "INFO"

    def test_should_send_error_log(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test sending an ERROR level log."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        client.track_log(
            "Database connection failed",
            severity=LogSeverity.ERROR,
            attributes={"error_code": "DB_001"},
        )

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        log_record = payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        assert log_record["severityNumber"] == LogSeverity.ERROR.value
        assert log_record["severityText"] == "ERROR"

    def test_should_truncate_long_log_messages(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that long log messages are truncated."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        client = TelemetryClient(project_name="test-project", version="1.0.0")

        long_message = "x" * 2000
        client.track_log(long_message)

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        decompressed_data = gzip.decompress(request.data)
        payload = json.loads(decompressed_data.decode("utf-8"))

        log_record = payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        # Should be truncated to 1000 chars
        assert len(log_record["body"]["stringValue"]) == 1000


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_should_batch_traces(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test batching multiple traces."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(project_name="test-project", version="1.0.0", batch_size=3)
        client = TelemetryClient(config=config)

        # Send 2 events - should not trigger send yet
        client.track_event("event1")
        client.track_event("event2")
        mock_urlopen.assert_not_called()

        # Send 3rd event - should trigger batch send
        client.track_event("event3")
        mock_urlopen.assert_called_once()

        # Verify all 3 events in one payload
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 3

    def test_should_flush_manually(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test manual flush of queued events."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            batch_size=10,  # Won't auto-flush with just 2 events
        )
        client = TelemetryClient(config=config)

        client.track_event("event1")
        client.track_event("event2")
        mock_urlopen.assert_not_called()

        # Manual flush
        client.flush()
        mock_urlopen.assert_called_once()

        # Verify both events were sent
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 2


class TestCompression:
    """Test gzip compression functionality."""

    def test_should_compress_large_payload(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that large payloads are compressed."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_enabled=True,
            compression_threshold=100,  # Low threshold for testing
        )
        client = TelemetryClient(config=config)

        # Send event with large data to trigger compression
        large_data = {"key": "x" * 200}
        client.track_event("large.event", large_data)

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Verify compression header
        assert request.headers.get("Content-encoding") == "gzip"

        # Verify payload is compressed
        compressed_data = request.data
        decompressed_data = gzip.decompress(compressed_data)
        payload = json.loads(decompressed_data.decode("utf-8"))

        # Verify payload structure is intact
        assert "resourceSpans" in payload

    def test_should_not_compress_small_payload(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that small payloads are not compressed."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_enabled=True,
            compression_threshold=5000,  # High threshold
        )
        client = TelemetryClient(config=config)

        client.track_event("small.event", {"key": "value"})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Verify no compression header
        assert request.headers.get("Content-encoding") != "gzip"

        # Payload should be uncompressed JSON
        payload = json.loads(request.data.decode("utf-8"))
        assert "resourceSpans" in payload

    def test_should_respect_compression_disabled(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that compression can be disabled."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            compression_enabled=False,
            compression_threshold=1,  # Even with low threshold, should not compress
        )
        client = TelemetryClient(config=config)

        client.track_event("event", {"data": "x" * 200})

        # Get the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        # Should not be compressed
        assert request.headers.get("Content-encoding") != "gzip"


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_should_retry_on_server_error(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test retrying on 500 server errors."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            max_retries=2,
            retry_backoff_base=0.01,  # Fast retries for testing
        )
        client = TelemetryClient(config=config)

        # Mock server returning 500 error
        mock_response = Mock()
        mock_response.status = 500
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            client.track_event("test.event")

            # Should retry 3 times total (initial + 2 retries)
            assert mock_urlopen.call_count == 3

    def test_should_not_retry_on_client_error(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test not retrying on 4xx client errors."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(project_name="test-project", version="1.0.0", max_retries=3)
        client = TelemetryClient(config=config)

        # Mock HTTPError with 400 status
        with patch(
            "urllib.request.urlopen", side_effect=HTTPError("url", 400, "Bad Request", {}, None)
        ) as mock_urlopen:
            client.track_event("test.event")

            # Should not retry on client error
            assert mock_urlopen.call_count == 1

    def test_should_use_exponential_backoff(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test exponential backoff timing."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", max_retries=3, retry_backoff_base=0.1
        )
        client = TelemetryClient(config=config)

        # Mock server error
        mock_response = Mock()
        mock_response.status = 503
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        sleep_times = []

        def mock_sleep(duration):
            sleep_times.append(duration)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with patch("time.sleep", side_effect=mock_sleep):
                client.track_event("test.event")

        # Should have 3 sleep calls with exponential backoff
        assert len(sleep_times) == 3
        assert sleep_times[0] == 0.1  # 0.1 * 2^0
        assert sleep_times[1] == 0.2  # 0.1 * 2^1
        assert sleep_times[2] == 0.4  # 0.1 * 2^2


class TestCleanup:
    """Test cleanup on client destruction."""

    def test_should_flush_on_del(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, mock_urlopen: Mock
    ) -> None:
        """Test that queued events are flushed when client is destroyed."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            batch_size=10,  # Won't auto-flush
        )
        client = TelemetryClient(config=config)

        client.track_event("event1")
        mock_urlopen.assert_not_called()

        # Destroy client - should trigger flush
        del client

        # Should have flushed
        mock_urlopen.assert_called_once()
