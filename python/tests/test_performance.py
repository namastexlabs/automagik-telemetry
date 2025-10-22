"""
Performance benchmarks for TelemetryClient.

Tests verify that telemetry operations meet the <1ms overhead requirement.
These tests can be skipped in CI with pytest -m "not performance".
"""

import os
import statistics
import time
from unittest.mock import MagicMock, patch

import pytest

from automagik_telemetry import TelemetryClient


@pytest.fixture
def performance_client():
    """Create a telemetry client with mocked HTTP for performance testing."""
    with patch("automagik_telemetry.client.urlopen") as mock_urlopen:
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Force enable telemetry
        with patch.dict(os.environ, {"AUTOMAGIK_TELEMETRY_ENABLED": "true"}):
            client = TelemetryClient(
                project_name="benchmark-test",
                version="1.0.0",
                timeout=5,
            )
            yield client


@pytest.fixture
def disabled_client():
    """Create a disabled telemetry client for overhead testing."""
    with patch.dict(os.environ, {"AUTOMAGIK_TELEMETRY_ENABLED": "false"}):
        client = TelemetryClient(
            project_name="benchmark-test",
            version="1.0.0",
        )
        yield client


def calculate_stats(timings: list[float]) -> dict:
    """Calculate timing statistics."""
    sorted_timings = sorted(timings)
    n = len(sorted_timings)

    return {
        "count": n,
        "mean": statistics.mean(timings),
        "median": statistics.median(timings),
        "min": min(timings),
        "max": max(timings),
        "p95": sorted_timings[int(n * 0.95)] if n > 0 else 0,
        "p99": sorted_timings[int(n * 0.99)] if n > 0 else 0,
        "stdev": statistics.stdev(timings) if n > 1 else 0,
    }


def print_stats(operation: str, stats: dict):
    """Print timing statistics in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"Performance: {operation}")
    print(f"{'=' * 60}")
    print(f"  Count:      {stats['count']:,} operations")
    print(f"  Mean:       {stats['mean']:.3f} ms")
    print(f"  Median:     {stats['median']:.3f} ms")
    print(f"  Min:        {stats['min']:.3f} ms")
    print(f"  Max:        {stats['max']:.3f} ms")
    print(f"  P95:        {stats['p95']:.3f} ms")
    print(f"  P99:        {stats['p99']:.3f} ms")
    print(f"  StdDev:     {stats['stdev']:.3f} ms")
    print(f"{'=' * 60}\n")


@pytest.mark.performance
def test_track_event_performance(performance_client):
    """Test track_event() performance with realistic payloads."""
    iterations = 1000
    timings = []

    # Realistic event payload
    event_data = {
        "feature_name": "api_endpoint",
        "feature_category": "messaging",
        "user_action": "send_message",
        "message_type": "text",
        "success": True,
    }

    # Warmup
    for _ in range(10):
        performance_client.track_event("benchmark.test", event_data)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client.track_event("benchmark.feature_used", event_data)
        end = time.perf_counter()
        timings.append((end - start) * 1000)  # Convert to milliseconds

    stats = calculate_stats(timings)
    print_stats("track_event() with realistic payload", stats)

    # Assertions
    assert stats["mean"] < 1.0, f"Average {stats['mean']:.3f}ms exceeds 1ms requirement"
    assert stats["p99"] < 5.0, f"P99 {stats['p99']:.3f}ms exceeds 5ms threshold"


@pytest.mark.performance
def test_track_error_performance(performance_client):
    """Test track_error() performance with realistic error data."""
    iterations = 1000
    timings = []

    # Create realistic error
    try:
        raise ValueError("Connection timeout after 30 seconds")
    except ValueError as e:
        test_error = e

    context = {
        "error_code": "OMNI-1001",
        "operation": "send_message",
        "retry_count": 3,
        "endpoint": "/api/v1/messages",
    }

    # Warmup
    for _ in range(10):
        performance_client.track_error(test_error, context)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client.track_error(test_error, context)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("track_error() with context", stats)

    # Assertions
    assert stats["mean"] < 1.0, f"Average {stats['mean']:.3f}ms exceeds 1ms requirement"
    assert stats["p99"] < 5.0, f"P99 {stats['p99']:.3f}ms exceeds 5ms threshold"


@pytest.mark.performance
def test_track_metric_performance(performance_client):
    """Test track_metric() performance with realistic metrics."""
    iterations = 1000
    timings = []

    attributes = {
        "operation_type": "api_request",
        "endpoint": "/v1/contacts",
        "status_code": 200,
        "cache_hit": True,
    }

    # Warmup
    for _ in range(10):
        performance_client.track_metric("benchmark.latency", 123.45, attributes)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client.track_metric("operation.latency", 123.45, attributes)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("track_metric() with attributes", stats)

    # Assertions
    assert stats["mean"] < 1.0, f"Average {stats['mean']:.3f}ms exceeds 1ms requirement"
    assert stats["p99"] < 5.0, f"P99 {stats['p99']:.3f}ms exceeds 5ms threshold"


@pytest.mark.performance
def test_disabled_client_overhead(disabled_client):
    """Test that disabled client has near-zero overhead."""
    iterations = 10000
    timings = []

    event_data = {
        "feature_name": "test_feature",
        "action": "click",
    }

    # Warmup
    for _ in range(100):
        disabled_client.track_event("test.event", event_data)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        disabled_client.track_event("test.event", event_data)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("Disabled client overhead", stats)

    # Disabled client should be extremely fast (just a boolean check)
    assert stats["mean"] < 0.01, f"Disabled client overhead {stats['mean']:.3f}ms too high"
    assert stats["p99"] < 0.1, f"Disabled client P99 {stats['p99']:.3f}ms too high"


@pytest.mark.performance
def test_attribute_serialization_performance(performance_client):
    """Test performance with large attribute sets."""
    iterations = 1000
    timings = []

    # Large but realistic attribute set
    large_attributes = {f"attribute_{i}": f"value_{i}" for i in range(50)}
    large_attributes.update(
        {
            "feature_name": "complex_operation",
            "user_id": "anon-12345",
            "session_duration": 3600,
            "items_processed": 1000,
            "success_rate": 0.95,
            "error_count": 5,
            "warning_count": 12,
        }
    )

    # Warmup
    for _ in range(10):
        performance_client.track_event("benchmark.large_attrs", large_attributes)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client.track_event("benchmark.large_attrs", large_attributes)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("Large attribute set (50+ attributes)", stats)

    # Should still be fast even with many attributes
    assert stats["mean"] < 2.0, f"Large attribute overhead {stats['mean']:.3f}ms too high"
    assert stats["p99"] < 10.0, f"Large attribute P99 {stats['p99']:.3f}ms too high"


@pytest.mark.performance
def test_concurrent_tracking_simulation(performance_client):
    """Simulate concurrent tracking operations (synchronous)."""
    iterations = 500
    timings = []

    events = [
        ("feature.used", {"feature": "export", "format": "csv"}),
        ("error.occurred", {"code": "E001", "severity": "low"}),
        ("metric.recorded", {"latency": 45.2, "endpoint": "/api/data"}),
    ]

    # Warmup
    for _ in range(10):
        for event_name, data in events:
            performance_client.track_event(event_name, data)

    # Actual benchmark - track multiple events in quick succession
    for _ in range(iterations):
        start = time.perf_counter()
        for event_name, data in events:
            performance_client.track_event(event_name, data)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("3 concurrent events per iteration", stats)

    # Total time for 3 events should be reasonable
    avg_per_event = stats["mean"] / 3
    print(f"  Avg per event: {avg_per_event:.3f} ms")

    assert avg_per_event < 1.5, f"Average per event {avg_per_event:.3f}ms too high"


@pytest.mark.performance
def test_payload_size_impact():
    """Test impact of different payload sizes on serialization time."""
    iterations = 1000

    with patch("automagik_telemetry.client.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch.dict(os.environ, {"AUTOMAGIK_TELEMETRY_ENABLED": "true"}):
            client = TelemetryClient(project_name="test", version="1.0.0")

            # Test different payload sizes
            payload_sizes = [1, 10, 50, 100]
            results = {}

            for size in payload_sizes:
                timings = []
                data = {f"key_{i}": f"value_{i}" for i in range(size)}

                # Warmup
                for _ in range(10):
                    client.track_event("size.test", data)

                # Benchmark
                for _ in range(iterations):
                    start = time.perf_counter()
                    client.track_event("size.test", data)
                    end = time.perf_counter()
                    timings.append((end - start) * 1000)

                results[size] = calculate_stats(timings)

            # Print comparison
            print(f"\n{'=' * 60}")
            print("Payload Size Impact")
            print(f"{'=' * 60}")
            print(f"{'Size':<10} {'Mean':<10} {'P95':<10} {'P99':<10}")
            print(f"{'-' * 60}")
            for size, stats in results.items():
                print(
                    f"{size:<10} {stats['mean']:<10.3f} {stats['p95']:<10.3f} {stats['p99']:<10.3f}"
                )
            print(f"{'=' * 60}\n")

            # Even large payloads should be reasonable
            assert results[100]["mean"] < 5.0, "Large payload (100 attrs) too slow"


@pytest.mark.performance
def test_memory_usage_no_leaks(disabled_client):
    """Test that tracking events doesn't cause memory leaks (disabled client for accurate test)."""
    import gc

    # Use disabled client to avoid mock overhead
    # Force garbage collection
    gc.collect()

    # Track initial memory
    import tracemalloc

    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Track many events
    event_count = 10000
    for i in range(event_count):
        disabled_client.track_event(
            "memory.test",
            {
                "iteration": i,
                "data": f"test_data_{i}",
                "value": i * 1.5,
            },
        )

    # Force garbage collection
    gc.collect()

    # Check final memory
    snapshot2 = tracemalloc.take_snapshot()
    top_stats = snapshot2.compare_to(snapshot1, "lineno")

    total_diff = sum(stat.size_diff for stat in top_stats)
    bytes_per_event = total_diff / event_count

    print(f"\n{'=' * 60}")
    print("Memory Usage Test (Disabled Client)")
    print(f"{'=' * 60}")
    print(f"  Events tracked:    {event_count:,}")
    print(f"  Total memory diff: {total_diff:,} bytes ({total_diff / 1024:.2f} KB)")
    print(f"  Per event:         {bytes_per_event:.2f} bytes")
    print(f"{'=' * 60}\n")

    tracemalloc.stop()

    # Disabled client should have minimal memory impact (just function call overhead)
    # Allow up to 100 bytes per event for Python overhead
    assert bytes_per_event < 100, f"Memory usage too high: {bytes_per_event:.2f} bytes/event"


@pytest.mark.performance
def test_string_truncation_performance(performance_client):
    """Test performance impact of string truncation."""
    iterations = 1000
    timings = []

    # Create very long strings that need truncation
    long_data = {
        "description": "x" * 10000,  # Will be truncated to 500
        "error_message": "y" * 5000,
        "stack_trace": "z" * 8000,
        "normal_field": "regular value",
    }

    # Warmup
    for _ in range(10):
        performance_client.track_event("truncation.test", long_data)

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client.track_event("truncation.test", long_data)
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("String truncation (3 long strings)", stats)

    # Truncation should not add significant overhead
    assert stats["mean"] < 2.0, f"Truncation overhead {stats['mean']:.3f}ms too high"
    assert stats["p99"] < 5.0, f"Truncation P99 {stats['p99']:.3f}ms too high"


@pytest.mark.performance
def test_system_info_collection_overhead(performance_client):
    """Test overhead of system info collection."""
    iterations = 1000
    timings = []

    # Each event collects system info
    for _ in range(iterations):
        start = time.perf_counter()
        performance_client._get_system_info()
        end = time.perf_counter()
        timings.append((end - start) * 1000)

    stats = calculate_stats(timings)
    print_stats("System info collection", stats)

    # System info collection should be very fast
    assert stats["mean"] < 0.1, f"System info overhead {stats['mean']:.3f}ms too high"


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
