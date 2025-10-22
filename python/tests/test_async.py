"""
Comprehensive tests for async telemetry methods.

Tests cover:
- Async event tracking
- Async error tracking
- Async metric tracking
- Async log tracking
- Async flush operations
- Concurrent async operations
- Non-blocking behavior
- Integration with asyncio.gather
"""

import asyncio
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from automagik_telemetry import (
    LogSeverity,
    MetricType,
    StandardEvents,
    TelemetryClient,
    TelemetryConfig,
)

# Mark all tests in this module as asyncio tests
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_home(tmp_path):
    """Mock home directory for tests."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def enabled_telemetry(mock_home):
    """Create telemetry client with telemetry enabled."""
    os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"
    config = TelemetryConfig(
        project_name="test-async",
        version="1.0.0",
        batch_size=1,  # Immediate send for testing
    )
    client = TelemetryClient(config=config)
    yield client
    # Cleanup
    if "AUTOMAGIK_TELEMETRY_ENABLED" in os.environ:
        del os.environ["AUTOMAGIK_TELEMETRY_ENABLED"]


@pytest.fixture
def disabled_telemetry(mock_home):
    """Create telemetry client with telemetry disabled."""
    config = TelemetryConfig(
        project_name="test-async",
        version="1.0.0",
    )
    client = TelemetryClient(config=config)
    yield client


class TestAsyncEventTracking:
    """Test async event tracking functionality."""

    async def test_track_event_async_basic(self, enabled_telemetry):
        """Test basic async event tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_event_async(
                StandardEvents.FEATURE_USED, {"feature_name": "async_test"}
            )

            # Verify request was made
            assert mock_urlopen.called

    async def test_track_event_async_without_attributes(self, enabled_telemetry):
        """Test async event tracking without attributes."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_event_async("test.event")

            assert mock_urlopen.called

    async def test_track_event_async_disabled(self, disabled_telemetry):
        """Test that async event tracking is a no-op when disabled."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            await disabled_telemetry.track_event_async("test.event", {"key": "value"})

            # Should not make any HTTP requests
            assert not mock_urlopen.called

    async def test_track_event_async_non_blocking(self, enabled_telemetry):
        """Test that async event tracking doesn't block event loop."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate slow network
            def slow_response(*args, **kwargs):
                time.sleep(0.1)  # 100ms delay
                mock_response = MagicMock()
                mock_response.status = 200
                return mock_response

            mock_urlopen.return_value.__enter__.side_effect = slow_response

            # Track multiple events concurrently
            start_time = time.time()
            await asyncio.gather(
                enabled_telemetry.track_event_async("event.1"),
                enabled_telemetry.track_event_async("event.2"),
                enabled_telemetry.track_event_async("event.3"),
            )
            elapsed = time.time() - start_time

            # Should complete in roughly the time of one request
            # (due to thread pool parallelization), not 3x the time
            assert elapsed < 0.5  # Should be ~0.1s, not ~0.3s


class TestAsyncErrorTracking:
    """Test async error tracking functionality."""

    async def test_track_error_async_basic(self, enabled_telemetry):
        """Test basic async error tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            error = ValueError("Test error message")
            await enabled_telemetry.track_error_async(
                error, {"error_code": "TEST-001", "operation": "test_op"}
            )

            assert mock_urlopen.called

    async def test_track_error_async_without_context(self, enabled_telemetry):
        """Test async error tracking without context."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            error = RuntimeError("Runtime error")
            await enabled_telemetry.track_error_async(error)

            assert mock_urlopen.called

    async def test_track_error_async_with_exception_context(self, enabled_telemetry):
        """Test async error tracking within try-except block."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            try:
                raise ValueError("Test exception")
            except Exception as e:
                await enabled_telemetry.track_error_async(e, {"caught_in": "test_context"})

            assert mock_urlopen.called


class TestAsyncMetricTracking:
    """Test async metric tracking functionality."""

    async def test_track_metric_async_gauge(self, enabled_telemetry):
        """Test async gauge metric tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_metric_async(
                "cpu.usage", 75.5, MetricType.GAUGE, {"core": "0"}
            )

            assert mock_urlopen.called

    async def test_track_metric_async_counter(self, enabled_telemetry):
        """Test async counter metric tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_metric_async("requests.total", 100, MetricType.COUNTER)

            assert mock_urlopen.called

    async def test_track_metric_async_histogram(self, enabled_telemetry):
        """Test async histogram metric tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_metric_async(
                "api.latency", 123.45, MetricType.HISTOGRAM, {"endpoint": "/v1/users"}
            )

            assert mock_urlopen.called

    async def test_track_metric_async_default_gauge(self, enabled_telemetry):
        """Test async metric tracking with default GAUGE type."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_metric_async("temperature", 22.5)

            assert mock_urlopen.called


class TestAsyncLogTracking:
    """Test async log tracking functionality."""

    async def test_track_log_async_info(self, enabled_telemetry):
        """Test async log tracking with INFO severity."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_log_async(
                "User logged in", LogSeverity.INFO, {"user_id": "anon-123"}
            )

            assert mock_urlopen.called

    async def test_track_log_async_error(self, enabled_telemetry):
        """Test async log tracking with ERROR severity."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_log_async(
                "Database connection failed", LogSeverity.ERROR, {"error_code": "DB-001"}
            )

            assert mock_urlopen.called

    async def test_track_log_async_default_severity(self, enabled_telemetry):
        """Test async log tracking with default INFO severity."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_log_async("Application started")

            assert mock_urlopen.called

    async def test_track_log_async_without_attributes(self, enabled_telemetry):
        """Test async log tracking without attributes."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            await enabled_telemetry.track_log_async("Simple log message", LogSeverity.DEBUG)

            assert mock_urlopen.called


class TestAsyncFlush:
    """Test async flush functionality."""

    async def test_flush_async_basic(self, enabled_telemetry):
        """Test basic async flush operation."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Track event and flush
            await enabled_telemetry.track_event_async("test.event")
            await enabled_telemetry.flush_async()

            # Verify flush was called
            assert mock_urlopen.called

    async def test_flush_async_disabled(self, disabled_telemetry):
        """Test that async flush is a no-op when disabled."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            await disabled_telemetry.flush_async()

            # Should not make any HTTP requests
            assert not mock_urlopen.called


class TestConcurrentAsyncOperations:
    """Test concurrent async operations."""

    async def test_concurrent_event_tracking(self, enabled_telemetry):
        """Test concurrent async event tracking."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Track multiple events concurrently
            tasks = [
                enabled_telemetry.track_event_async(f"event.{i}", {"index": i}) for i in range(10)
            ]
            await asyncio.gather(*tasks)

            # All events should have been sent
            assert mock_urlopen.call_count == 10

    async def test_concurrent_mixed_operations(self, enabled_telemetry):
        """Test concurrent mixed async operations."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Mix different operation types
            tasks = [
                enabled_telemetry.track_event_async("event.1"),
                enabled_telemetry.track_metric_async("metric.1", 42.0),
                enabled_telemetry.track_log_async("Log message 1"),
                enabled_telemetry.track_event_async("event.2"),
                enabled_telemetry.track_metric_async("metric.2", 100.0, MetricType.COUNTER),
            ]
            await asyncio.gather(*tasks)

            # All operations should complete
            assert mock_urlopen.call_count == 5

    async def test_concurrent_with_errors(self, enabled_telemetry):
        """Test concurrent operations with some errors."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # First call succeeds, second fails, third succeeds
            mock_response_ok = MagicMock()
            mock_response_ok.status = 200
            mock_response_err = MagicMock()
            mock_response_err.status = 500

            mock_urlopen.return_value.__enter__.side_effect = [
                mock_response_ok,
                mock_response_err,
                mock_response_ok,
            ]

            # Should not raise exceptions (silent failure)
            tasks = [
                enabled_telemetry.track_event_async("event.1"),
                enabled_telemetry.track_event_async("event.2"),
                enabled_telemetry.track_event_async("event.3"),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            # All requests should have been attempted
            assert mock_urlopen.call_count >= 3


class TestAsyncNonBlockingBehavior:
    """Test that async methods don't block the event loop."""

    async def test_event_tracking_non_blocking(self, enabled_telemetry):
        """Verify event tracking doesn't block event loop."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate slow network (100ms delay)
            def slow_response(*args, **kwargs):
                time.sleep(0.1)
                mock_response = MagicMock()
                mock_response.status = 200
                return mock_response

            mock_urlopen.return_value.__enter__.side_effect = slow_response

            # Other async work
            async def other_work():
                await asyncio.sleep(0.05)  # 50ms
                return "completed"

            # Track event and do other work concurrently
            start = time.time()
            event_task = enabled_telemetry.track_event_async("test.event")
            work_task = other_work()

            results = await asyncio.gather(event_task, work_task)
            elapsed = time.time() - start

            # Should complete in ~100ms (network time), not 150ms (network + work)
            assert elapsed < 0.15
            assert results[1] == "completed"

    async def test_flush_non_blocking(self, enabled_telemetry):
        """Verify flush doesn't block event loop."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate slow network
            def slow_response(*args, **kwargs):
                time.sleep(0.1)
                mock_response = MagicMock()
                mock_response.status = 200
                return mock_response

            mock_urlopen.return_value.__enter__.side_effect = slow_response

            # Other async work
            async def counter():
                count = 0
                for _ in range(10):
                    await asyncio.sleep(0.01)
                    count += 1
                return count

            # Track event, flush, and count concurrently
            await enabled_telemetry.track_event_async("test.event")
            flush_task = enabled_telemetry.flush_async()
            count_task = counter()

            results = await asyncio.gather(flush_task, count_task)

            # Counter should complete successfully
            assert results[1] == 10


class TestAsyncErrorHandling:
    """Test error handling in async methods."""

    async def test_network_error_silent_failure(self, enabled_telemetry):
        """Test that network errors don't raise exceptions."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate network error
            mock_urlopen.side_effect = Exception("Network error")

            # Should not raise exception
            await enabled_telemetry.track_event_async("test.event")

    async def test_timeout_silent_failure(self, enabled_telemetry):
        """Test that timeouts don't raise exceptions."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate timeout
            from urllib.error import URLError

            mock_urlopen.side_effect = URLError("Timeout")

            # Should not raise exception
            await enabled_telemetry.track_metric_async("test.metric", 42.0)


class TestAsyncWithAsyncioLoop:
    """Test async methods work correctly with asyncio event loops."""

    async def test_in_async_context_manager(self, enabled_telemetry):
        """Test async methods work in async context manager."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Simulate using telemetry in async context
            async def async_operation():
                await enabled_telemetry.track_event_async("operation.start")
                await asyncio.sleep(0.01)
                await enabled_telemetry.track_event_async("operation.end")

            await async_operation()

            assert mock_urlopen.call_count == 2

    async def test_with_asyncio_tasks(self, enabled_telemetry):
        """Test async methods work with asyncio.create_task."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Create tasks
            task1 = asyncio.create_task(enabled_telemetry.track_event_async("task.1"))
            task2 = asyncio.create_task(enabled_telemetry.track_event_async("task.2"))

            # Wait for tasks
            await task1
            await task2

            assert mock_urlopen.call_count == 2


class TestAsyncPerformance:
    """Test performance characteristics of async methods."""

    async def test_concurrent_better_than_sequential(self, enabled_telemetry):
        """Test that concurrent execution is faster than sequential."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate 50ms network delay
            def slow_response(*args, **kwargs):
                time.sleep(0.05)
                mock_response = MagicMock()
                mock_response.status = 200
                return mock_response

            mock_urlopen.return_value.__enter__.side_effect = slow_response

            # Sequential execution
            start_seq = time.time()
            for i in range(5):
                await enabled_telemetry.track_event_async(f"seq.{i}")
            seq_time = time.time() - start_seq

            # Concurrent execution
            mock_urlopen.return_value.__enter__.side_effect = slow_response
            start_con = time.time()
            await asyncio.gather(
                *[enabled_telemetry.track_event_async(f"con.{i}") for i in range(5)]
            )
            con_time = time.time() - start_con

            # Concurrent should be significantly faster
            # Sequential: ~250ms (5 * 50ms)
            # Concurrent: ~50ms (all in parallel)
            assert con_time < seq_time / 2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
