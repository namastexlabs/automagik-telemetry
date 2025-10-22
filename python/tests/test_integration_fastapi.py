"""
Integration test for FastAPI with telemetry.

Tests realistic HTTP request/response cycles with telemetry tracking.
Measures overhead and ensures telemetry doesn't block the event loop.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

# Skip if fastapi not installed
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from automagik_telemetry import TelemetryClient, TelemetryConfig

# Mark as integration test
pytestmark = pytest.mark.integration


@pytest.fixture
def telemetry_client(monkeypatch: pytest.MonkeyPatch) -> TelemetryClient:
    """Create telemetry client with test configuration."""
    # Enable telemetry for integration tests
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    config = TelemetryConfig(
        project_name="test-fastapi",
        version="1.0.0",
        endpoint="https://telemetry.namastex.ai",
        batch_size=10,  # Small batch for faster testing
        flush_interval=1.0,  # Quick flush
    )
    client = TelemetryClient(config=config)
    yield client

    # Cleanup: flush and disable
    client.flush()
    client.disable()


@pytest.fixture
def fastapi_app(telemetry_client: TelemetryClient) -> FastAPI:
    """Create FastAPI app with telemetry instrumentation."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        telemetry_client.track_event(
            "api.request",
            {
                "endpoint": "/",
                "method": "GET",
            },
        )
        return {"message": "Hello World"}

    @app.get("/slow")
    async def slow_endpoint() -> dict[str, str]:
        """Simulated slow endpoint."""
        start_time = time.time()

        # Simulate async work
        await asyncio.sleep(0.1)

        latency = (time.time() - start_time) * 1000
        telemetry_client.track_metric(
            "api.latency",
            latency,
            attributes={"endpoint": "/slow"},
        )
        telemetry_client.track_event(
            "api.request",
            {
                "endpoint": "/slow",
                "method": "GET",
            },
        )

        return {"message": "Slow response"}

    @app.post("/data")
    async def post_data(data: dict[str, Any]) -> dict[str, Any]:
        """POST endpoint with data processing."""
        telemetry_client.track_event(
            "api.data_received",
            {
                "endpoint": "/data",
                "method": "POST",
                "data_keys": list(data.keys()),
            },
        )

        # Process data
        result = {"processed": True, "count": len(data)}

        telemetry_client.track_metric(
            "api.data_processed",
            len(data),
            attributes={"endpoint": "/data"},
        )

        return result

    @app.get("/error")
    async def error_endpoint() -> None:
        """Endpoint that raises an error."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            telemetry_client.track_error(
                e,
                {
                    "endpoint": "/error",
                    "method": "GET",
                },
            )
            raise

    return app


def test_fastapi_basic_request(fastapi_app: FastAPI) -> None:
    """Test basic FastAPI request with telemetry."""
    client = TestClient(fastapi_app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_fastapi_async_endpoint(fastapi_app: FastAPI) -> None:
    """Test async endpoint with telemetry and latency tracking."""
    client = TestClient(fastapi_app)

    start = time.time()
    response = client.get("/slow")
    duration = time.time() - start

    assert response.status_code == 200
    assert response.json() == {"message": "Slow response"}

    # Should take at least 0.1 seconds (simulated sleep)
    assert duration >= 0.1

    # Telemetry shouldn't add significant overhead (< 50ms)
    # This is a loose bound to avoid flaky tests
    assert duration < 0.2


def test_fastapi_post_request(fastapi_app: FastAPI) -> None:
    """Test POST request with data and telemetry."""
    client = TestClient(fastapi_app)

    test_data = {
        "name": "test",
        "value": 123,
        "items": ["a", "b", "c"],
    }

    response = client.post("/data", json=test_data)

    assert response.status_code == 200
    result = response.json()
    assert result["processed"] is True
    assert result["count"] == 3


def test_fastapi_error_tracking(fastapi_app: FastAPI) -> None:
    """Test error tracking in FastAPI."""
    client = TestClient(fastapi_app)

    with pytest.raises(ValueError, match="Test error"):
        client.get("/error")


def test_fastapi_concurrent_requests(
    fastapi_app: FastAPI, telemetry_client: TelemetryClient
) -> None:
    """Test concurrent requests to ensure telemetry doesn't block."""
    client = TestClient(fastapi_app)

    # Number of concurrent requests
    num_requests = 100

    def make_request(i: int) -> dict[str, Any]:
        """Make a single request."""
        response = client.get("/")
        return {
            "index": i,
            "status": response.status_code,
            "data": response.json(),
        }

    # Measure time for concurrent requests
    start = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(make_request, range(num_requests)))

    duration = time.time() - start

    # All requests should succeed
    assert len(results) == num_requests
    assert all(r["status"] == 200 for r in results)

    # Concurrent requests should complete reasonably fast
    # With 20 workers, 100 requests should take < 2 seconds
    assert duration < 2.0

    print(f"\nConcurrent requests: {num_requests}")
    print(f"Total time: {duration:.3f}s")
    print(f"Requests/sec: {num_requests / duration:.1f}")

    # Flush telemetry to ensure events are sent
    telemetry_client.flush()


def test_fastapi_telemetry_overhead(fastapi_app: FastAPI) -> None:
    """Measure telemetry overhead in request/response cycle."""
    client = TestClient(fastapi_app)

    # Warmup
    for _ in range(10):
        client.get("/")

    # Measure with telemetry
    iterations = 100
    timings: list[float] = []

    for _ in range(iterations):
        start = time.time()
        response = client.get("/")
        duration = time.time() - start

        assert response.status_code == 200
        timings.append(duration)

    avg_time = sum(timings) / len(timings)
    max_time = max(timings)
    min_time = min(timings)

    print(f"\nTelemetry overhead measurement ({iterations} requests):")
    print(f"  Average: {avg_time * 1000:.3f}ms")
    print(f"  Min: {min_time * 1000:.3f}ms")
    print(f"  Max: {max_time * 1000:.3f}ms")

    # Average request should be fast (< 10ms with telemetry)
    assert avg_time < 0.01


def test_fastapi_no_event_loop_blocking(fastapi_app: FastAPI) -> None:
    """Ensure telemetry doesn't block the async event loop."""
    client = TestClient(fastapi_app)

    # Make requests to multiple endpoints concurrently
    def stress_test() -> None:
        endpoints = ["/", "/slow", "/"]
        for endpoint in endpoints:
            client.get(endpoint)

    # Run multiple stress tests in parallel
    start = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(stress_test) for _ in range(10)]
        for future in futures:
            future.result()

    duration = time.time() - start

    print(f"\nEvent loop stress test: {duration:.3f}s")

    # Should complete without hanging
    assert duration < 5.0


@pytest.mark.asyncio
async def test_fastapi_async_telemetry(telemetry_client: TelemetryClient) -> None:
    """Test telemetry with async/await patterns."""

    async def async_operation() -> None:
        """Simulate async operation with telemetry."""
        telemetry_client.track_event(
            "async.operation.start",
            {
                "operation": "test",
            },
        )

        await asyncio.sleep(0.01)

        telemetry_client.track_event(
            "async.operation.end",
            {
                "operation": "test",
            },
        )

    # Run multiple async operations concurrently
    tasks = [async_operation() for _ in range(50)]
    await asyncio.gather(*tasks)

    # Flush telemetry
    telemetry_client.flush()


def test_fastapi_telemetry_status(telemetry_client: TelemetryClient) -> None:
    """Test telemetry status reporting."""
    status = telemetry_client.get_status()

    assert status["enabled"] is True
    assert status["project_name"] == "test-fastapi"
    assert status["project_version"] == "1.0.0"
    assert "user_id" in status
    assert "session_id" in status


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
