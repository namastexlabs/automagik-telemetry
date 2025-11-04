"""
Integration test for Python SDK with ClickHouse backend.

Tests end-to-end flow of tracking telemetry events and verifying data
reaches ClickHouse database directly without going through OTLP collector.

Prerequisites:
- ClickHouse running on localhost:8123 (use docker-compose from infra/)
- Database 'telemetry' and table 'traces' must exist

Run with: pytest -v python/tests/integration/test_clickhouse_integration.py
Skip if no ClickHouse: pytest -v -m "not integration"
"""

import base64
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from automagik_telemetry import AutomagikTelemetry
from automagik_telemetry.client import TelemetryConfig

# Mark as integration test
pytestmark = [pytest.mark.integration]

# Default credentials from docker-compose (infra/docker-compose.yml)
DEFAULT_CLICKHOUSE_USER = os.getenv("AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME", "telemetry")
DEFAULT_CLICKHOUSE_PASSWORD = os.getenv(
    "AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD", "telemetry_password"
)


def clickhouse_request(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    username: str = DEFAULT_CLICKHOUSE_USER,
    password: str = DEFAULT_CLICKHOUSE_PASSWORD,
    timeout: int = 5,
) -> str:
    """Make HTTP request to ClickHouse with authentication."""
    request = Request(url, data=data, method=method)

    if username:
        auth_string = f"{username}:{password}".encode()
        auth_header = b"Basic " + base64.b64encode(auth_string)
        request.add_header("Authorization", auth_header.decode("utf-8"))

    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def check_clickhouse_available(endpoint: str = "http://localhost:8123") -> bool:
    """Check if ClickHouse is available."""
    try:
        from urllib.parse import quote

        query = quote("SELECT 1")
        clickhouse_request(f"{endpoint}/?query={query}", timeout=2)
        return True
    except (HTTPError, URLError, OSError):
        return False


def query_clickhouse(
    query: str,
    endpoint: str = "http://localhost:8123",
    database: str = "telemetry",
) -> list[dict[str, Any]]:
    """Execute a query against ClickHouse and return results as list of dicts."""
    query_with_format = f"{query} FORMAT JSONEachRow"
    url = f"{endpoint}/?database={database}"

    data = clickhouse_request(url, method="POST", data=query_with_format.encode("utf-8"))

    # Parse newline-delimited JSON
    results = []
    for line in data.strip().split("\n"):
        if line:
            results.append(json.loads(line))
    return results


def cleanup_test_data(
    project_name: str,
    endpoint: str = "http://localhost:8123",
    database: str = "telemetry",
    table: str = "traces",
) -> None:
    """Clean up test data from ClickHouse."""
    from urllib.parse import quote

    query = f"ALTER TABLE {database}.{table} DELETE WHERE project_name = '{project_name}'"
    try:
        clickhouse_request(f"{endpoint}/?query={quote(query)}", method="POST")
    except Exception as e:
        print(f"Warning: Failed to cleanup test data: {e}")


@pytest.fixture(scope="module")
def clickhouse_endpoint() -> str:
    """Get ClickHouse endpoint from environment or use default."""
    return os.getenv("AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT", "http://localhost:8123")


@pytest.fixture(scope="module")
def clickhouse_available(clickhouse_endpoint: str) -> bool:
    """Check if ClickHouse is available, skip tests if not."""
    available = check_clickhouse_available(clickhouse_endpoint)
    if not available:
        pytest.skip(
            f"ClickHouse not available at {clickhouse_endpoint}. "
            "Start with: cd infra && docker compose up -d clickhouse"
        )
    return available


@pytest.fixture
def test_project_name() -> str:
    """Generate unique project name for test isolation."""
    return f"test-clickhouse-{int(time.time() * 1000)}"


@pytest.fixture
async def clickhouse_client(
    monkeypatch: pytest.MonkeyPatch,
    clickhouse_available: bool,
    clickhouse_endpoint: str,
    test_project_name: str,
) -> AutomagikTelemetry:
    """Create telemetry client configured for ClickHouse backend."""
    # Enable telemetry for integration tests
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

    config = TelemetryConfig(
        project_name=test_project_name,
        version="1.0.0-test",
        backend="clickhouse",
        clickhouse_endpoint=clickhouse_endpoint,
        clickhouse_database="telemetry",
        clickhouse_username=DEFAULT_CLICKHOUSE_USER,
        clickhouse_password=DEFAULT_CLICKHOUSE_PASSWORD,
        batch_size=1,  # Immediate send for testing
        timeout=10,
    )
    client = AutomagikTelemetry(config=config)

    # Verify client is enabled
    assert client.is_enabled(), "Client should be enabled for integration tests"
    assert client.backend_type == "clickhouse", "Backend should be clickhouse"

    yield client

    # Cleanup: flush and disable
    client.flush()
    time.sleep(1)  # Give time for final flush
    await client.disable()

    # Clean up test data
    cleanup_test_data(test_project_name, clickhouse_endpoint)


def test_clickhouse_backend_initialization(clickhouse_client: AutomagikTelemetry) -> None:
    """Test that ClickHouse backend is properly initialized."""
    print("\n=== Testing ClickHouse backend initialization ===")

    assert clickhouse_client.backend_type == "clickhouse"
    assert clickhouse_client._clickhouse_backend is not None
    assert clickhouse_client._clickhouse_backend.endpoint == "http://localhost:8123"
    assert clickhouse_client._clickhouse_backend.database == "telemetry"

    print("ClickHouse backend initialized successfully")


def test_track_single_event_to_clickhouse(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test tracking a single event and verifying it in ClickHouse."""
    print("\n=== Testing single event to ClickHouse ===")

    # Track an event
    event_name = "test.single_event"
    clickhouse_client.track_event(
        event_name,
        {
            "test_type": "single_event",
            "timestamp": str(time.time()),
            "data": "test_value",
        },
    )

    # Flush to ensure immediate send
    clickhouse_client.flush()

    # Wait for ClickHouse to process
    time.sleep(2)

    # Query ClickHouse to verify data
    results = query_clickhouse(
        f"SELECT * FROM traces WHERE project_name = '{test_project_name}' AND span_name = '{event_name}'",
        endpoint=clickhouse_endpoint,
    )

    print(f"Found {len(results)} events in ClickHouse")

    # Verify we got the event
    assert len(results) >= 1, "Event should be stored in ClickHouse"

    event = results[0]
    print(f"Event data: {json.dumps(event, indent=2)}")

    # Verify event structure
    assert event["project_name"] == test_project_name
    assert event["span_name"] == event_name
    assert event["service_name"] == test_project_name
    assert "trace_id" in event
    assert "span_id" in event
    assert "timestamp" in event
    assert "attributes" in event

    # Verify attributes (stored as Map in ClickHouse)
    attributes = event["attributes"]
    assert "test_type" in attributes
    assert attributes["test_type"] == "single_event"

    print("Single event verified successfully in ClickHouse")


def test_track_multiple_events_to_clickhouse(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test tracking multiple events and verifying batch insertion."""
    print("\n=== Testing multiple events to ClickHouse ===")

    num_events = 10
    event_name = "test.multiple_events"

    # Track multiple events
    for i in range(num_events):
        clickhouse_client.track_event(
            event_name,
            {
                "test_type": "multiple_events",
                "event_number": str(i),
                "batch_test": "true",
            },
        )

    # Flush all events
    clickhouse_client.flush()

    # Wait for ClickHouse to process
    time.sleep(2)

    # Query ClickHouse to verify data
    results = query_clickhouse(
        f"SELECT * FROM traces WHERE project_name = '{test_project_name}' AND span_name = '{event_name}' ORDER BY timestamp",
        endpoint=clickhouse_endpoint,
    )

    print(f"Found {len(results)} events in ClickHouse")

    # Verify we got all events
    assert len(results) >= num_events, f"Should have at least {num_events} events in ClickHouse"

    # Verify event sequence
    for i, event in enumerate(results[:num_events]):
        assert event["project_name"] == test_project_name
        assert event["span_name"] == event_name
        attributes = event["attributes"]
        assert "event_number" in attributes

    print(f"All {num_events} events verified successfully in ClickHouse")


def test_track_event_with_error_status(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test tracking an error and verifying error status in ClickHouse."""
    print("\n=== Testing error tracking to ClickHouse ===")

    # Track an error
    try:
        raise ValueError("Test error for ClickHouse integration")
    except Exception as e:
        clickhouse_client.track_error(
            e,
            {
                "test_type": "error_tracking",
                "error_category": "test",
            },
        )

    # Flush to ensure immediate send
    clickhouse_client.flush()

    # Wait for ClickHouse to process
    time.sleep(2)

    # Query ClickHouse to verify error data
    results = query_clickhouse(
        f"SELECT * FROM traces WHERE project_name = '{test_project_name}' AND status_code != 'OK'",
        endpoint=clickhouse_endpoint,
    )

    print(f"Found {len(results)} error events in ClickHouse")

    # Verify we got the error
    assert len(results) >= 1, "Error should be stored in ClickHouse"

    error_event = results[0]
    print(f"Error event: {json.dumps(error_event, indent=2)}")

    # Verify error fields
    assert error_event["project_name"] == test_project_name
    assert error_event["status_code"] != "OK"
    assert "attributes" in error_event

    print("Error tracking verified successfully in ClickHouse")


def test_verify_data_structure_in_clickhouse(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test that data structure matches ClickHouse schema."""
    print("\n=== Testing data structure in ClickHouse ===")

    # Track a comprehensive event with all fields
    clickhouse_client.track_event(
        "test.data_structure",
        {
            "string_field": "test_value",
            "numeric_field": "42",
            "boolean_field": "true",
            "nested_data": "nested_value",
        },
    )

    # Flush to ensure immediate send
    clickhouse_client.flush()

    # Wait for ClickHouse to process
    time.sleep(2)

    # Query ClickHouse schema
    results = query_clickhouse(
        f"SELECT * FROM traces WHERE project_name = '{test_project_name}' AND span_name = 'test.data_structure' LIMIT 1",
        endpoint=clickhouse_endpoint,
    )

    assert len(results) == 1, "Event should be stored in ClickHouse"

    event = results[0]
    print(f"Event structure: {json.dumps(list(event.keys()), indent=2)}")

    # Verify all expected fields are present
    expected_fields = [
        "trace_id",
        "span_id",
        "parent_span_id",
        "timestamp",
        "timestamp_ns",
        "duration_ms",
        "service_name",
        "span_name",
        "span_kind",
        "status_code",
        "status_message",
        "project_name",
        "project_version",
        "environment",
        "hostname",
        "attributes",
        "user_id",
        "session_id",
        "os_type",
        "os_version",
        "runtime_name",
        "runtime_version",
    ]

    for field in expected_fields:
        assert field in event, f"Field '{field}' should be present in ClickHouse row"

    # Verify data types
    assert isinstance(event["trace_id"], str)
    assert isinstance(event["span_id"], str)
    assert isinstance(event["timestamp"], str)  # DateTime as string in JSON
    assert isinstance(event["duration_ms"], int)
    assert isinstance(event["attributes"], dict)  # Map as dict in JSON

    print("Data structure verified successfully")


def test_backend_configuration_from_env(
    monkeypatch: pytest.MonkeyPatch,
    clickhouse_available: bool,
    clickhouse_endpoint: str,
) -> None:
    """Test configuring ClickHouse backend via environment variables."""
    print("\n=== Testing environment variable configuration ===")

    # Set environment variables
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_BACKEND", "clickhouse")
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT", clickhouse_endpoint)
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE", "telemetry")
    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE", "traces")

    # Create client with minimal config (should use env vars)
    config = TelemetryConfig(
        project_name="test-env-config",
        version="1.0.0",
    )
    client = AutomagikTelemetry(config=config)

    # Verify backend configuration from env
    assert client.backend_type == "clickhouse"
    assert client._clickhouse_backend is not None
    assert client._clickhouse_backend.endpoint == clickhouse_endpoint
    assert client._clickhouse_backend.database == "telemetry"
    assert client._clickhouse_backend.traces_table == "traces"

    print("Environment variable configuration verified successfully")

    # Cleanup
    client.disable()


def test_backend_configuration_from_config(
    monkeypatch: pytest.MonkeyPatch,
    clickhouse_available: bool,
    clickhouse_endpoint: str,
) -> None:
    """Test configuring ClickHouse backend via TelemetryConfig object."""
    print("\n=== Testing config object configuration ===")

    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    # Create config with explicit ClickHouse settings
    config = TelemetryConfig(
        project_name="test-config-object",
        version="1.0.0",
        backend="clickhouse",
        clickhouse_endpoint=clickhouse_endpoint,
        clickhouse_database="telemetry",
        clickhouse_table="traces",
        clickhouse_username=DEFAULT_CLICKHOUSE_USER,
        clickhouse_password=DEFAULT_CLICKHOUSE_PASSWORD,
        batch_size=10,
        timeout=5,
    )
    client = AutomagikTelemetry(config=config)

    # Verify backend configuration
    assert client.backend_type == "clickhouse"
    assert client._clickhouse_backend is not None
    assert client._clickhouse_backend.endpoint == clickhouse_endpoint
    assert client._clickhouse_backend.database == "telemetry"
    assert client._clickhouse_backend.traces_table == "traces"
    assert client._clickhouse_backend.batch_size == 10
    assert client._clickhouse_backend.timeout == 5

    print("Config object configuration verified successfully")

    # Cleanup
    client.disable()


async def test_backend_default_to_otlp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that backend defaults to OTLP for backward compatibility."""
    print("\n=== Testing backward compatibility (default to OTLP) ===")

    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    # Create client without specifying backend
    config = TelemetryConfig(
        project_name="test-default-backend",
        version="1.0.0",
    )
    client = AutomagikTelemetry(config=config)

    # Verify defaults to OTLP
    assert client.backend_type == "otlp"
    assert client._clickhouse_backend is None

    print("Default backend (OTLP) verified successfully")

    # Cleanup
    client.disable()


async def test_backend_switching(
    monkeypatch: pytest.MonkeyPatch,
    clickhouse_available: bool,
    clickhouse_endpoint: str,
) -> None:
    """Test switching between OTLP and ClickHouse backends."""
    print("\n=== Testing backend switching ===")

    monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

    # Create OTLP client
    otlp_config = TelemetryConfig(
        project_name="test-backend-switch",
        version="1.0.0",
        backend="otlp",
    )
    otlp_client = AutomagikTelemetry(config=otlp_config)

    assert otlp_client.backend_type == "otlp"
    assert otlp_client._clickhouse_backend is None

    otlp_client.disable()

    # Create ClickHouse client
    clickhouse_config = TelemetryConfig(
        project_name="test-backend-switch",
        version="1.0.0",
        backend="clickhouse",
        clickhouse_endpoint=clickhouse_endpoint,
        clickhouse_username=DEFAULT_CLICKHOUSE_USER,
        clickhouse_password=DEFAULT_CLICKHOUSE_PASSWORD,
    )
    clickhouse_client = AutomagikTelemetry(config=clickhouse_config)

    assert clickhouse_client.backend_type == "clickhouse"
    assert clickhouse_client._clickhouse_backend is not None

    print("Backend switching verified successfully")

    # Cleanup
    await clickhouse_client.disable()


def test_query_count_by_project(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test querying event count by project name."""
    print("\n=== Testing query count by project ===")

    # Track several events
    for i in range(5):
        clickhouse_client.track_event(
            f"test.count.event_{i}",
            {"test_type": "count_test", "index": str(i)},
        )

    clickhouse_client.flush()
    time.sleep(2)

    # Query count
    results = query_clickhouse(
        f"SELECT count() as count FROM traces WHERE project_name = '{test_project_name}'",
        endpoint=clickhouse_endpoint,
    )

    assert len(results) >= 1
    count = results[0]["count"]

    print(f"Total events for project '{test_project_name}': {count}")
    assert count >= 5, "Should have at least 5 events"


def test_query_events_by_timerange(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test querying events within a time range."""
    print("\n=== Testing query by time range ===")

    # Track event with timestamp
    clickhouse_client.track_event(
        "test.timerange",
        {"test_type": "timerange_test"},
    )
    clickhouse_client.flush()
    time.sleep(2)

    # Query events from last minute
    results = query_clickhouse(
        f"SELECT * FROM traces WHERE project_name = '{test_project_name}' "
        f"AND timestamp >= now() - INTERVAL 1 MINUTE",
        endpoint=clickhouse_endpoint,
    )

    print(f"Found {len(results)} events in last minute")
    assert len(results) >= 1, "Should find recent events"


def test_user_and_session_tracking(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test that user_id and session_id are tracked in ClickHouse."""
    print("\n=== Testing user and session tracking ===")

    # Track event
    clickhouse_client.track_event(
        "test.user_session",
        {"test_type": "user_session_test"},
    )
    clickhouse_client.flush()
    time.sleep(2)

    # Query event
    results = query_clickhouse(
        f"SELECT user_id, session_id FROM traces WHERE project_name = '{test_project_name}' "
        f"AND span_name = 'test.user_session' LIMIT 1",
        endpoint=clickhouse_endpoint,
    )

    assert len(results) == 1
    event = results[0]

    # Verify user_id and session_id are present
    assert "user_id" in event
    assert "session_id" in event
    assert event["user_id"] != ""
    assert event["session_id"] != ""

    print(f"User ID: {event['user_id']}")
    print(f"Session ID: {event['session_id']}")
    print("User and session tracking verified successfully")


def test_system_information_tracking(
    clickhouse_client: AutomagikTelemetry,
    test_project_name: str,
    clickhouse_endpoint: str,
) -> None:
    """Test that system information (OS, runtime) is tracked."""
    print("\n=== Testing system information tracking ===")

    # Track event
    clickhouse_client.track_event(
        "test.system_info",
        {"test_type": "system_info_test"},
    )
    clickhouse_client.flush()
    time.sleep(2)

    # Query event
    results = query_clickhouse(
        f"SELECT os_type, os_version, runtime_name, runtime_version, hostname "
        f"FROM traces WHERE project_name = '{test_project_name}' "
        f"AND span_name = 'test.system_info' LIMIT 1",
        endpoint=clickhouse_endpoint,
    )

    assert len(results) == 1
    event = results[0]

    # Verify system information fields
    print(f"OS Type: {event['os_type']}")
    print(f"OS Version: {event['os_version']}")
    print(f"Runtime Name: {event['runtime_name']}")
    print(f"Runtime Version: {event['runtime_version']}")
    print(f"Hostname: {event['hostname']}")

    # At least some fields should be populated
    assert event["os_type"] != "" or event["runtime_name"] != ""

    print("System information tracking verified successfully")


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    # Run with: python test_clickhouse_integration.py
    pytest.main([__file__, "-v", "-s"])
