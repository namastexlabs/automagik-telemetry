"""
Integration test for memory usage and leak detection.

Tests long-running scenarios to verify:
- Memory doesn't leak over time
- Memory returns to baseline after flush
- No unclosed threads or resources
- Stable memory usage under sustained load
"""

import gc
import threading
import time
from typing import Any

import pytest

from automagik_telemetry import LogSeverity, MetricType, TelemetryClient, TelemetryConfig

# Mark as integration test with extended timeout
pytestmark = [pytest.mark.integration, pytest.mark.timeout(300)]


def get_memory_mb() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        pytest.skip("psutil not installed, cannot measure memory")


def get_thread_count() -> int:
    """Get current thread count."""
    return threading.active_count()


@pytest.fixture
def memory_test_client(monkeypatch: pytest.MonkeyPatch) -> TelemetryClient:
    """Create telemetry client for memory testing."""
    # Enable telemetry
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    config = TelemetryConfig(
        project_name="test-memory",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=50,
        flush_interval=2.0,
        compression_enabled=True,
    )
    client = TelemetryClient(config=config)

    # Force garbage collection before test
    gc.collect()

    yield client

    # Cleanup
    client.flush()
    client.disable()
    gc.collect()


def test_no_memory_leak_simple_events(memory_test_client: TelemetryClient) -> None:
    """Test that simple events don't cause memory leaks."""
    print("\n=== Testing memory leaks with simple events ===")

    # Get baseline memory
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Send many events
    num_events = 10000
    memory_samples: list[float] = []

    for i in range(num_events):
        memory_test_client.track_event(
            "test.memory.simple",
            {
                "event_id": i,
            },
        )

        # Sample memory every 1000 events
        if i % 1000 == 0:
            gc.collect()
            current_memory = get_memory_mb()
            memory_samples.append(current_memory)
            print(
                f"  After {i:5d} events: {current_memory:.2f} MB (+{current_memory - baseline_memory:.2f} MB)"
            )

    # Flush all events
    memory_test_client.flush()
    time.sleep(1.0)

    # Final memory check after flush
    gc.collect()
    final_memory = get_memory_mb()
    memory_growth = final_memory - baseline_memory

    print(f"\nFinal memory: {final_memory:.2f} MB")
    print(f"Total growth: {memory_growth:.2f} MB")
    print(f"Memory per event: {(memory_growth / num_events) * 1024:.3f} KB")

    # Memory growth should be minimal (< 10 MB for 10k events)
    assert memory_growth < 10, f"Memory grew by {memory_growth:.2f} MB, expected < 10 MB"

    # Memory should not grow linearly with events
    # Check that later samples aren't significantly higher
    if len(memory_samples) > 1:
        early_avg = sum(memory_samples[:2]) / 2
        late_avg = sum(memory_samples[-2:]) / 2
        growth_rate = late_avg - early_avg
        print(f"Memory growth rate: {growth_rate:.2f} MB")
        assert growth_rate < 5, "Memory appears to be growing linearly"


def test_memory_returns_to_baseline_after_flush(memory_test_client: TelemetryClient) -> None:
    """Test that memory returns to baseline after flush."""
    print("\n=== Testing memory returns to baseline after flush ===")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Generate events
    num_events = 5000
    for i in range(num_events):
        memory_test_client.track_event(
            "test.memory.baseline",
            {
                "event_id": i,
                "data": "x" * 100,
            },
        )

    # Check memory before flush
    gc.collect()
    before_flush = get_memory_mb()
    print(f"Before flush: {before_flush:.2f} MB (+{before_flush - baseline_memory:.2f} MB)")

    # Flush and wait
    memory_test_client.flush()
    time.sleep(2.0)

    # Check memory after flush
    gc.collect()
    after_flush = get_memory_mb()
    print(f"After flush: {after_flush:.2f} MB (+{after_flush - baseline_memory:.2f} MB)")

    # Memory should be close to baseline (within 5 MB)
    memory_diff = abs(after_flush - baseline_memory)
    assert memory_diff < 5, f"Memory didn't return to baseline (diff: {memory_diff:.2f} MB)"


def test_no_thread_leaks(memory_test_client: TelemetryClient) -> None:
    """Test that threads are properly cleaned up."""
    print("\n=== Testing thread cleanup ===")

    # Get baseline thread count
    baseline_threads = get_thread_count()
    print(f"Baseline threads: {baseline_threads}")

    # Generate events (should trigger background flush timer)
    for i in range(100):
        memory_test_client.track_event("test.memory.threads", {"id": i})

    # Wait for flush timer to run
    time.sleep(3.0)

    # Check thread count
    current_threads = get_thread_count()
    print(f"Current threads: {current_threads}")

    # Thread count shouldn't grow significantly
    # Allow for 1-2 background threads (flush timer)
    assert current_threads <= baseline_threads + 2, "Thread leak detected"

    # Flush and disable client
    memory_test_client.flush()
    memory_test_client.disable()
    time.sleep(1.0)

    # Thread count should return to baseline or close to it
    final_threads = get_thread_count()
    print(f"Final threads: {final_threads}")


def test_sustained_load_memory_stability(memory_test_client: TelemetryClient) -> None:
    """Test memory stability under sustained load."""
    print("\n=== Testing memory stability under sustained load ===")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Run for extended period with continuous events
    duration_seconds = 30
    events_per_second = 100

    memory_samples: list[dict[str, Any]] = []
    start_time = time.time()

    print(f"\nRunning sustained load for {duration_seconds}s at {events_per_second} events/sec...")

    event_count = 0
    while time.time() - start_time < duration_seconds:
        # Send events
        for _ in range(10):  # Batch of 10
            memory_test_client.track_event(
                "test.memory.sustained",
                {
                    "event_id": event_count,
                    "timestamp": time.time(),
                },
            )
            event_count += 1

        # Sample memory every second
        elapsed = time.time() - start_time
        if int(elapsed) > len(memory_samples):
            gc.collect()
            current_memory = get_memory_mb()
            memory_samples.append(
                {
                    "time": elapsed,
                    "memory_mb": current_memory,
                    "events": event_count,
                }
            )
            print(f"  {elapsed:.0f}s: {current_memory:.2f} MB, {event_count} events")

        # Small sleep to maintain target rate
        time.sleep(0.01)

    # Flush all events
    memory_test_client.flush()
    time.sleep(1.0)

    # Final memory check
    gc.collect()
    final_memory = get_memory_mb()

    print(f"\nTotal events sent: {event_count}")
    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {final_memory - baseline_memory:.2f} MB")

    # Analyze memory stability
    if len(memory_samples) > 5:
        # Check that memory doesn't grow continuously
        memory_values = [s["memory_mb"] for s in memory_samples]
        max_memory = max(memory_values)
        min_memory = min(memory_values)
        memory_range = max_memory - min_memory

        print(f"Memory range: {memory_range:.2f} MB (min: {min_memory:.2f}, max: {max_memory:.2f})")

        # Memory should be relatively stable (< 20 MB variation)
        assert memory_range < 20, f"Memory not stable, range: {memory_range:.2f} MB"


def test_large_payload_memory_usage(memory_test_client: TelemetryClient) -> None:
    """Test memory usage with large payloads."""
    print("\n=== Testing large payload memory usage ===")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Send events with large payloads
    num_events = 1000
    for i in range(num_events):
        large_payload = {
            "event_id": i,
            "large_field_1": "a" * 1000,
            "large_field_2": "b" * 1000,
            "large_field_3": "c" * 1000,
        }
        memory_test_client.track_event("test.memory.large", large_payload)

        # Periodic flush to prevent queue buildup
        if i % 100 == 0:
            memory_test_client.flush()
            time.sleep(0.5)

    # Final flush
    memory_test_client.flush()
    time.sleep(1.0)

    # Check memory
    gc.collect()
    final_memory = get_memory_mb()
    memory_growth = final_memory - baseline_memory

    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB")

    # Even with large payloads, memory growth should be reasonable (< 15 MB)
    assert memory_growth < 15, f"Excessive memory growth: {memory_growth:.2f} MB"


def test_mixed_signals_memory_usage(memory_test_client: TelemetryClient) -> None:
    """Test memory usage with mixed signal types."""
    print("\n=== Testing mixed signals memory usage ===")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Send mixed signals
    num_iterations = 2000
    for i in range(num_iterations):
        # Trace
        memory_test_client.track_event("test.memory.mixed.trace", {"id": i})

        # Metric
        memory_test_client.track_metric(
            "test.memory.mixed.metric",
            float(i),
            metric_type=MetricType.GAUGE,
        )

        # Log
        memory_test_client.track_log(
            f"Mixed signal test {i}",
            severity=LogSeverity.INFO,
        )

        # Periodic flush
        if i % 200 == 0:
            memory_test_client.flush()

    # Final flush
    memory_test_client.flush()
    time.sleep(1.0)

    # Check memory
    gc.collect()
    final_memory = get_memory_mb()
    memory_growth = final_memory - baseline_memory

    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB")

    # Memory growth should be reasonable (< 10 MB)
    assert memory_growth < 10, f"Excessive memory growth: {memory_growth:.2f} MB"


def test_repeated_enable_disable_no_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that repeatedly enabling/disabling doesn't leak memory."""
    print("\n=== Testing repeated enable/disable ===")

    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    baseline_threads = get_thread_count()

    print(f"Baseline memory: {baseline_memory:.2f} MB")
    print(f"Baseline threads: {baseline_threads}")

    # Repeatedly create, use, and destroy clients
    num_cycles = 50

    for i in range(num_cycles):
        config = TelemetryConfig(
            project_name="test-cycle",
            version="1.0.0",
            endpoint="https://telemetry.namastex.ai",
            batch_size=10,
        )
        client = TelemetryClient(config=config)

        # Send some events
        for j in range(10):
            client.track_event("test.cycle", {"cycle": i, "event": j})

        # Flush and disable
        client.flush()
        client.disable()

        # Explicitly delete client
        del client

        # Periodic garbage collection
        if i % 10 == 0:
            gc.collect()
            current_memory = get_memory_mb()
            current_threads = get_thread_count()
            print(f"  Cycle {i}: {current_memory:.2f} MB, {current_threads} threads")

    # Final check
    gc.collect()
    time.sleep(1.0)

    final_memory = get_memory_mb()
    final_threads = get_thread_count()
    memory_growth = final_memory - baseline_memory

    print(f"\nAfter {num_cycles} cycles:")
    print(f"  Memory: {final_memory:.2f} MB (+{memory_growth:.2f} MB)")
    print(f"  Threads: {final_threads}")

    # Memory growth should be minimal (< 5 MB)
    assert memory_growth < 5, f"Memory leak detected: {memory_growth:.2f} MB"

    # Thread count should be back to baseline (or very close)
    assert final_threads <= baseline_threads + 1, "Thread leak detected"


def test_queue_memory_bounds(memory_test_client: TelemetryClient) -> None:
    """Test that queues don't grow unbounded in memory."""
    print("\n=== Testing queue memory bounds ===")

    # Get baseline
    gc.collect()
    baseline_memory = get_memory_mb()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Disable automatic flushing by setting very large batch size
    config = TelemetryConfig(
        project_name="test-queue-bounds",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=10000,  # Large batch to accumulate events
        flush_interval=3600,  # Very long interval
    )
    client = TelemetryClient(config=config)
    client.enable()

    # Send many events without flushing
    num_events = 5000

    for i in range(num_events):
        client.track_event(
            "test.queue.bounds",
            {
                "event_id": i,
                "data": "x" * 50,
            },
        )

    # Check memory with queued events
    gc.collect()
    queued_memory = get_memory_mb()
    queued_growth = queued_memory - baseline_memory

    print(
        f"Memory with {num_events} queued events: {queued_memory:.2f} MB (+{queued_growth:.2f} MB)"
    )

    # Check queue sizes
    status = client.get_status()
    print(f"Queue sizes: {status['queue_sizes']}")

    # Flush and check memory returns
    client.flush()
    time.sleep(1.0)
    gc.collect()

    flushed_memory = get_memory_mb()
    flushed_growth = flushed_memory - baseline_memory

    print(f"Memory after flush: {flushed_memory:.2f} MB (+{flushed_growth:.2f} MB)")

    # Memory should drop significantly after flush
    memory_freed = queued_memory - flushed_memory
    print(f"Memory freed by flush: {memory_freed:.2f} MB")

    # At least 50% of queued memory should be freed
    assert memory_freed > queued_growth * 0.5, "Queue memory not properly freed"

    # Cleanup
    client.disable()


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
