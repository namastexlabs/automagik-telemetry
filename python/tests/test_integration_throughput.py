"""
Integration test for high-throughput telemetry.

Tests sustained high load scenarios to verify:
- Batch efficiency
- Queue management under load
- Memory usage stability
- Event delivery reliability
"""

import gc
import os
import threading
import time

import pytest

from automagik_telemetry import MetricType, TelemetryClient, TelemetryConfig

# Mark as integration test and add timeout
pytestmark = [pytest.mark.integration, pytest.mark.timeout(120)]


@pytest.fixture
def high_throughput_client(monkeypatch: pytest.MonkeyPatch) -> TelemetryClient:
    """Create telemetry client optimized for high throughput."""
    # Enable telemetry for integration tests
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    config = TelemetryConfig(
        project_name="test-throughput",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=100,  # Large batch for efficiency
        flush_interval=1.0,  # Flush every second
        compression_enabled=True,
        compression_threshold=512,
    )
    client = TelemetryClient(config=config)
    yield client

    # Cleanup: flush and disable
    client.flush()
    client.disable()


def test_burst_events(high_throughput_client: TelemetryClient) -> None:
    """Test handling burst of events."""
    num_events = 1000

    start = time.time()

    for i in range(num_events):
        high_throughput_client.track_event(
            "test.burst",
            {
                "event_number": i,
                "category": f"category_{i % 10}",
            },
        )

    duration = time.time() - start

    print(f"\nBurst test: {num_events} events in {duration:.3f}s")
    print(f"Events/sec: {num_events / duration:.1f}")

    # Should handle 1000 events quickly (< 1 second)
    assert duration < 1.0

    # Flush to ensure all events are sent
    flush_start = time.time()
    high_throughput_client.flush()
    flush_duration = time.time() - flush_start

    print(f"Flush time: {flush_duration:.3f}s")


def test_sustained_throughput(high_throughput_client: TelemetryClient) -> None:
    """Test sustained high throughput over time."""
    duration_seconds = 10
    target_rate = 1000  # events per second
    total_events = duration_seconds * target_rate

    event_times: list[float] = []
    start = time.time()

    for i in range(total_events):
        high_throughput_client.track_event(
            "test.sustained",
            {
                "event_id": i,
                "timestamp": time.time(),
            },
        )
        event_times.append(time.time())

        # Sleep to maintain target rate
        # (in real apps, events come naturally)
        if i % 100 == 0 and i > 0:
            elapsed = time.time() - start
            expected = i / target_rate
            if elapsed < expected:
                time.sleep(expected - elapsed)

    duration = time.time() - start

    print("\nSustained throughput test:")
    print(f"  Total events: {total_events}")
    print(f"  Duration: {duration:.3f}s")
    print(f"  Average rate: {total_events / duration:.1f} events/sec")
    print(f"  Target rate: {target_rate} events/sec")

    # Should achieve close to target rate
    actual_rate = total_events / duration
    assert actual_rate >= target_rate * 0.8  # Allow 20% variance

    # Flush all events
    high_throughput_client.flush()


def test_concurrent_producers(high_throughput_client: TelemetryClient) -> None:
    """Test multiple threads producing events concurrently."""
    num_threads = 10
    events_per_thread = 500
    total_events = num_threads * events_per_thread

    def producer_thread(thread_id: int) -> None:
        """Producer thread that generates events."""
        for i in range(events_per_thread):
            high_throughput_client.track_event(
                "test.concurrent",
                {
                    "thread_id": thread_id,
                    "event_id": i,
                },
            )

    # Start all threads
    threads = []
    start = time.time()

    for tid in range(num_threads):
        thread = threading.Thread(target=producer_thread, args=(tid,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    duration = time.time() - start

    print("\nConcurrent producers test:")
    print(f"  Threads: {num_threads}")
    print(f"  Events per thread: {events_per_thread}")
    print(f"  Total events: {total_events}")
    print(f"  Duration: {duration:.3f}s")
    print(f"  Rate: {total_events / duration:.1f} events/sec")

    # Should handle concurrent producers without issues
    assert duration < 5.0

    # Flush all events
    high_throughput_client.flush()


def test_mixed_signal_types(high_throughput_client: TelemetryClient) -> None:
    """Test high throughput with mixed signal types (traces, metrics, logs)."""
    num_iterations = 500

    start = time.time()

    for i in range(num_iterations):
        # Send trace (event)
        high_throughput_client.track_event(
            "test.mixed.event",
            {
                "iteration": i,
            },
        )

        # Send metric
        high_throughput_client.track_metric(
            "test.mixed.counter",
            i,
            metric_type=MetricType.COUNTER,
            attributes={"iteration": i},
        )

        # Send log
        from automagik_telemetry import LogSeverity

        high_throughput_client.track_log(
            f"Mixed signal iteration {i}",
            severity=LogSeverity.INFO,
            attributes={"iteration": i},
        )

    duration = time.time() - start
    total_signals = num_iterations * 3  # 3 signal types per iteration

    print("\nMixed signal types test:")
    print(f"  Iterations: {num_iterations}")
    print(f"  Total signals: {total_signals}")
    print(f"  Duration: {duration:.3f}s")
    print(f"  Rate: {total_signals / duration:.1f} signals/sec")

    # Flush all signals
    high_throughput_client.flush()


def test_queue_management(high_throughput_client: TelemetryClient) -> None:
    """Test that queue doesn't grow unbounded under load."""
    # Get initial queue sizes
    initial_status = high_throughput_client.get_status()
    print(f"\nInitial queue sizes: {initial_status['queue_sizes']}")

    # Generate many events quickly
    for i in range(2000):
        high_throughput_client.track_event("test.queue", {"id": i})

    # Check queue size after generation
    mid_status = high_throughput_client.get_status()
    print(f"Queue sizes after generation: {mid_status['queue_sizes']}")

    # Queue should not grow unbounded (batch_size = 100)
    # Some events might be queued, but not all 2000
    total_queued = sum(mid_status["queue_sizes"].values())
    assert total_queued < 500  # Much less than 2000

    # Flush and verify queue is empty
    high_throughput_client.flush()

    final_status = high_throughput_client.get_status()
    print(f"Queue sizes after flush: {final_status['queue_sizes']}")

    # Queue should be empty after flush
    total_queued_final = sum(final_status["queue_sizes"].values())
    assert total_queued_final == 0


def test_memory_usage_under_load() -> None:
    """Test memory usage remains stable under sustained load."""
    # Skip if psutil not available
    pytest.importorskip("psutil")
    import psutil

    process = psutil.Process()

    # Create client
    os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"
    config = TelemetryConfig(
        project_name="test-memory",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=100,
        flush_interval=0.5,
    )
    client = TelemetryClient(config=config)

    # Force garbage collection and get baseline memory
    gc.collect()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"\nBaseline memory: {baseline_memory:.2f} MB")

    # Generate sustained load
    num_events = 10000
    memory_samples: list[float] = []

    for i in range(num_events):
        client.track_event(
            "test.memory",
            {
                "event_id": i,
                "data": "x" * 100,  # Some payload
            },
        )

        # Sample memory every 1000 events
        if i % 1000 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            print(f"  After {i} events: {current_memory:.2f} MB")

    # Final flush
    client.flush()
    gc.collect()

    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"Final memory: {final_memory:.2f} MB")

    # Memory growth should be reasonable (< 50 MB for 10k events)
    memory_growth = final_memory - baseline_memory
    print(f"Memory growth: {memory_growth:.2f} MB")

    assert memory_growth < 50

    # Cleanup
    client.disable()


def test_batch_efficiency(high_throughput_client: TelemetryClient) -> None:
    """Test that batching provides efficiency gains."""
    # Test 1: Small batches (batch_size=1, immediate send)
    small_batch_config = TelemetryConfig(
        project_name="test-batch-small",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=1,  # Immediate send
    )
    small_batch_client = TelemetryClient(config=small_batch_config)
    small_batch_client.enable()

    num_events = 100
    start = time.time()

    for i in range(num_events):
        small_batch_client.track_event("test.batch.small", {"id": i})

    small_batch_client.flush()
    small_batch_time = time.time() - start

    # Test 2: Large batches (batch_size=100)
    start = time.time()

    for i in range(num_events):
        high_throughput_client.track_event("test.batch.large", {"id": i})

    high_throughput_client.flush()
    large_batch_time = time.time() - start

    print("\nBatch efficiency:")
    print(f"  Small batch (size=1): {small_batch_time:.3f}s")
    print(f"  Large batch (size=100): {large_batch_time:.3f}s")
    print(f"  Speedup: {small_batch_time / large_batch_time:.2f}x")

    # Large batches should be faster (or at least comparable)
    # Due to network overhead, batching should provide benefit
    assert large_batch_time <= small_batch_time * 1.2

    # Cleanup
    small_batch_client.disable()


def test_compression_efficiency(high_throughput_client: TelemetryClient) -> None:
    """Test that compression reduces payload size for large batches."""
    # Create client with compression disabled
    no_compression_config = TelemetryConfig(
        project_name="test-compression",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=100,
        compression_enabled=False,
    )
    no_compression_client = TelemetryClient(config=no_compression_config)
    no_compression_client.enable()

    # Generate events with repetitive data (compresses well)
    num_events = 200
    for i in range(num_events):
        payload = {
            "event_id": i,
            "large_field": "a" * 100,  # Repetitive data
            "another_field": "b" * 100,
        }
        no_compression_client.track_event("test.no_compression", payload)
        high_throughput_client.track_event("test.compression", payload)

    # Flush both clients
    start = time.time()
    high_throughput_client.flush()
    compressed_time = time.time() - start

    start = time.time()
    no_compression_client.flush()
    uncompressed_time = time.time() - start

    print("\nCompression efficiency:")
    print(f"  With compression: {compressed_time:.3f}s")
    print(f"  Without compression: {uncompressed_time:.3f}s")

    # Cleanup
    no_compression_client.disable()


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
