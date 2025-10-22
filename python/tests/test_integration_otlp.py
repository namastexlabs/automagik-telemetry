"""
Integration test with real OTLP collector.

Tests actual network communication with the telemetry backend at
https://telemetry.namastex.ai. These tests require network access
and are skipped by default in CI.

Run with: pytest -v -m integration
"""

import os
import time

import pytest

from automagik_telemetry import (
    LogSeverity,
    MetricType,
    TelemetryClient,
    TelemetryConfig,
)

# Mark as integration test requiring network
pytestmark = [pytest.mark.integration, pytest.mark.network]


@pytest.fixture
def otlp_endpoint() -> str:
    """Get OTLP endpoint from environment or use default."""
    return os.getenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://telemetry.namastex.ai")


@pytest.fixture
def otlp_client(monkeypatch: pytest.MonkeyPatch, otlp_endpoint: str) -> TelemetryClient:
    """Create telemetry client configured for real OTLP collector."""
    # Enable telemetry for integration tests
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
    # Enable verbose mode to see requests
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

    config = TelemetryConfig(
        project_name="test-otlp-integration",
        version="1.0.0",
        endpoint=otlp_endpoint,
        batch_size=1,  # Immediate send for integration tests
        timeout=10,  # Longer timeout for network requests
        max_retries=2,
    )
    client = TelemetryClient(config=config)

    # Verify client is enabled
    assert client.is_enabled(), "Client should be enabled for integration tests"

    yield client

    # Cleanup: flush and disable
    client.flush()
    client.disable()


def test_send_trace_to_collector(otlp_client: TelemetryClient) -> None:
    """Test sending trace (span) to real OTLP collector."""
    print("\n=== Testing trace to OTLP collector ===")

    # Send a test trace
    otlp_client.track_event(
        "integration.test.trace",
        {
            "test_type": "trace",
            "timestamp": time.time(),
            "environment": "integration_test",
        },
    )

    # Flush to ensure immediate send
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("Trace sent successfully (no exceptions)")


def test_send_metric_to_collector(otlp_client: TelemetryClient) -> None:
    """Test sending metrics to real OTLP collector."""
    print("\n=== Testing metrics to OTLP collector ===")

    # Send different metric types
    # 1. Gauge
    otlp_client.track_metric(
        "integration.test.gauge",
        42.5,
        metric_type=MetricType.GAUGE,
        attributes={"test_type": "gauge"},
    )

    # 2. Counter
    otlp_client.track_metric(
        "integration.test.counter",
        100,
        metric_type=MetricType.COUNTER,
        attributes={"test_type": "counter"},
    )

    # 3. Histogram
    otlp_client.track_metric(
        "integration.test.histogram",
        123.45,
        metric_type=MetricType.HISTOGRAM,
        attributes={"test_type": "histogram"},
    )

    # Flush to ensure immediate send
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("Metrics sent successfully (no exceptions)")


def test_send_log_to_collector(otlp_client: TelemetryClient) -> None:
    """Test sending logs to real OTLP collector."""
    print("\n=== Testing logs to OTLP collector ===")

    # Send different severity levels
    severities = [
        (LogSeverity.TRACE, "This is a trace log"),
        (LogSeverity.DEBUG, "This is a debug log"),
        (LogSeverity.INFO, "This is an info log"),
        (LogSeverity.WARN, "This is a warning log"),
        (LogSeverity.ERROR, "This is an error log"),
    ]

    for severity, message in severities:
        otlp_client.track_log(
            message,
            severity=severity,
            attributes={
                "test_type": "log",
                "severity_name": severity.name,
            },
        )

    # Flush to ensure immediate send
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("Logs sent successfully (no exceptions)")


def test_send_all_signal_types(otlp_client: TelemetryClient) -> None:
    """Test sending all three signal types in sequence."""
    print("\n=== Testing all signal types to OTLP collector ===")

    # 1. Trace
    otlp_client.track_event(
        "integration.test.all_signals",
        {
            "signal_type": "trace",
            "step": 1,
        },
    )

    # 2. Metric
    otlp_client.track_metric(
        "integration.test.all_signals",
        456.78,
        metric_type=MetricType.GAUGE,
        attributes={"signal_type": "metric", "step": 2},
    )

    # 3. Log
    otlp_client.track_log(
        "All signals test completed",
        severity=LogSeverity.INFO,
        attributes={"signal_type": "log", "step": 3},
    )

    # Flush all signals
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("All signal types sent successfully")


def test_error_tracking_to_collector(otlp_client: TelemetryClient) -> None:
    """Test tracking errors to real OTLP collector."""
    print("\n=== Testing error tracking to OTLP collector ===")

    # Create and track a test error
    try:
        raise ValueError("This is a test error for integration testing")
    except Exception as e:
        otlp_client.track_error(
            e,
            {
                "test_context": "integration_test",
                "error_category": "test",
            },
        )

    # Flush to ensure immediate send
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("Error tracking sent successfully")


def test_batch_send_to_collector(otlp_client: TelemetryClient) -> None:
    """Test sending batch of events to collector."""
    print("\n=== Testing batch send to OTLP collector ===")

    # Send multiple events
    num_events = 50

    for i in range(num_events):
        otlp_client.track_event(
            "integration.test.batch",
            {
                "event_number": i,
                "batch_test": True,
            },
        )

    # Flush all events
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(1.0)

    print(f"Batch of {num_events} events sent successfully")


def test_large_payload_to_collector(otlp_client: TelemetryClient) -> None:
    """Test sending large payload with compression."""
    print("\n=== Testing large payload to OTLP collector ===")

    # Create a large payload that will trigger compression
    large_data = {
        "large_field_1": "x" * 1000,
        "large_field_2": "y" * 1000,
        "large_field_3": "z" * 1000,
        "test_type": "large_payload",
    }

    otlp_client.track_event("integration.test.large_payload", large_data)

    # Flush to ensure immediate send
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(0.5)

    print("Large payload sent successfully (likely compressed)")


def test_concurrent_sends_to_collector(otlp_client: TelemetryClient) -> None:
    """Test concurrent sends to collector."""
    import threading

    print("\n=== Testing concurrent sends to OTLP collector ===")

    def send_events(thread_id: int) -> None:
        """Send events from a thread."""
        for i in range(10):
            otlp_client.track_event(
                "integration.test.concurrent",
                {
                    "thread_id": thread_id,
                    "event_id": i,
                },
            )

    # Create and start threads
    threads = []
    num_threads = 5

    for tid in range(num_threads):
        thread = threading.Thread(target=send_events, args=(tid,))
        thread.start()
        threads.append(thread)

    # Wait for all threads
    for thread in threads:
        thread.join()

    # Flush all events
    otlp_client.flush()

    # Give some time for async processing
    time.sleep(1.0)

    print(f"Concurrent sends from {num_threads} threads completed successfully")


def test_retry_on_temporary_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test retry logic with temporary failures."""
    print("\n=== Testing retry logic ===")

    # Enable telemetry
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

    # Create client with aggressive retry settings
    config = TelemetryConfig(
        project_name="test-retry",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=1,
        timeout=5,
        max_retries=3,
        retry_backoff_base=0.5,  # Fast retry for testing
    )
    client = TelemetryClient(config=config)

    # Send an event (should succeed with retries if needed)
    client.track_event(
        "integration.test.retry",
        {
            "test_type": "retry",
        },
    )

    client.flush()
    time.sleep(0.5)

    print("Retry logic test completed")

    # Cleanup
    client.disable()


def test_custom_endpoint_configuration() -> None:
    """Test custom endpoint configuration."""
    print("\n=== Testing custom endpoint configuration ===")

    custom_endpoint = "https://telemetry.namastex.ai"

    config = TelemetryConfig(
        project_name="test-custom-endpoint",
        version="1.0.0",
        endpoint=custom_endpoint,
        batch_size=1,
    )
    client = TelemetryClient(config=config)
    client.enable()

    # Verify endpoints are set correctly
    assert client.endpoint == f"{custom_endpoint}/v1/traces"
    assert client.metrics_endpoint == f"{custom_endpoint}/v1/metrics"
    assert client.logs_endpoint == f"{custom_endpoint}/v1/logs"

    print(f"Traces endpoint: {client.endpoint}")
    print(f"Metrics endpoint: {client.metrics_endpoint}")
    print(f"Logs endpoint: {client.logs_endpoint}")

    # Send test event
    client.track_event(
        "integration.test.custom_endpoint",
        {
            "endpoint_test": True,
        },
    )

    client.flush()
    time.sleep(0.5)

    # Cleanup
    client.disable()

    print("Custom endpoint configuration test completed")


def test_telemetry_status_with_real_collector(otlp_client: TelemetryClient) -> None:
    """Test telemetry status with real collector configuration."""
    print("\n=== Testing telemetry status ===")

    status = otlp_client.get_status()

    print("\nTelemetry Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Verify status
    assert status["enabled"] is True
    assert status["project_name"] == "test-otlp-integration"
    assert status["project_version"] == "1.0.0"
    assert "telemetry.namastex.ai" in status["endpoint"]
    assert "user_id" in status
    assert "session_id" in status


def test_compression_with_real_collector(otlp_client: TelemetryClient) -> None:
    """Test that compression works with real collector."""
    print("\n=== Testing compression with real collector ===")

    # Send events with large payloads that should be compressed
    for i in range(10):
        large_payload = {
            "event_id": i,
            "large_data": "a" * 2000,  # 2KB of data
            "more_data": "b" * 2000,
        }
        otlp_client.track_event("integration.test.compression", large_payload)

    # Flush (should trigger compression due to size)
    otlp_client.flush()
    time.sleep(1.0)

    print("Compression test with real collector completed")


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    # Run with: python test_integration_otlp.py
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
