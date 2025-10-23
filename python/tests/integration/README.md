# Integration Tests

This directory contains integration tests for the Automagik Telemetry SDK that require external services.

## Prerequisites

### ClickHouse Backend Tests

The ClickHouse integration tests require a running ClickHouse instance with the telemetry database and schema.

**Start ClickHouse:**
```bash
cd ../../infra
docker compose up -d clickhouse
```

**Verify ClickHouse is running:**
```bash
curl http://localhost:8123/?query=SELECT%201
```

Expected output: `1`

**Check schema:**
```bash
curl "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20telemetry"
```

Expected output should include `traces` table.

### OTLP Collector Tests

OTLP integration tests use the existing `test_integration_otlp.py` file and require network access to the telemetry collector.

**Start local collector (optional):**
```bash
cd ../../infra
docker compose up -d collector
```

## Running Tests

### Run all integration tests
```bash
# From repository root
pytest -v python/tests/integration/

# Or from python directory
cd python
pytest -v tests/integration/
```

### Run only ClickHouse integration tests
```bash
pytest -v python/tests/integration/test_clickhouse_integration.py
```

### Run with verbose output (see print statements)
```bash
pytest -v -s python/tests/integration/test_clickhouse_integration.py
```

### Run specific test
```bash
pytest -v python/tests/integration/test_clickhouse_integration.py::test_track_single_event_to_clickhouse
```

### Skip integration tests (when running all tests)
```bash
pytest -v python/tests/ -m "not integration"
```

### Run only integration tests
```bash
pytest -v python/tests/ -m integration
```

## Test Coverage

### ClickHouse Integration Tests (`test_clickhouse_integration.py`)

The test suite covers:

1. **Backend Initialization**
   - `test_clickhouse_backend_initialization` - Verify ClickHouse backend is properly set up

2. **End-to-End Flow**
   - `test_track_single_event_to_clickhouse` - Track one event and verify in database
   - `test_track_multiple_events_to_clickhouse` - Track batch of 10 events
   - `test_track_event_with_error_status` - Track error and verify error status

3. **Data Structure**
   - `test_verify_data_structure_in_clickhouse` - Verify schema matches ClickHouse table
   - `test_query_count_by_project` - Query event counts by project
   - `test_query_events_by_timerange` - Query events by time range

4. **Configuration**
   - `test_backend_configuration_from_env` - Configure via environment variables
   - `test_backend_configuration_from_config` - Configure via TelemetryConfig object
   - `test_backend_default_to_otlp` - Verify default backend is OTLP
   - `test_backend_switching` - Switch between OTLP and ClickHouse backends

5. **Data Verification**
   - `test_user_and_session_tracking` - Verify user_id and session_id are tracked
   - `test_system_information_tracking` - Verify OS and runtime info is tracked

## Configuration

### Environment Variables

The tests support the following environment variables:

- `AUTOMAGIK_TELEMETRY_ENABLED` - Enable telemetry (set to `true` in tests)
- `AUTOMAGIK_TELEMETRY_BACKEND` - Backend type (`clickhouse` or `otlp`)
- `AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT` - ClickHouse HTTP endpoint (default: `http://localhost:8123`)
- `AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE` - Database name (default: `telemetry`)
- `AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE` - Table name (default: `traces`)
- `AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME` - Username (default: `default`)
- `AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD` - Password (default: empty)

### Test Fixtures

Key fixtures:
- `clickhouse_endpoint` - ClickHouse HTTP endpoint URL
- `clickhouse_available` - Checks ClickHouse availability, skips tests if not available
- `test_project_name` - Generates unique project name for test isolation
- `clickhouse_client` - Pre-configured AutomagikTelemetry client with ClickHouse backend

## Cleanup

The tests automatically clean up test data after each test run using the `cleanup_test_data()` function. Test data is isolated by using unique project names for each test run.

## Troubleshooting

### Tests are skipped
If you see:
```
SKIPPED [1] test_clickhouse_integration.py:XX: ClickHouse not available at http://localhost:8123
```

**Solution:** Start ClickHouse:
```bash
cd ../../infra
docker compose up -d clickhouse
```

### Connection refused
If tests fail with connection errors:

**Check ClickHouse is running:**
```bash
docker ps | grep clickhouse
```

**Check ClickHouse logs:**
```bash
docker logs automagik-clickhouse
```

**Restart ClickHouse:**
```bash
cd ../../infra
docker compose restart clickhouse
```

### Schema errors
If tests fail with schema-related errors (missing table, columns, etc.):

**Re-initialize database:**
```bash
cd ../../infra
docker compose down -v
docker compose up -d clickhouse
```

This will recreate the database with the correct schema from `infra/clickhouse/init-db.sql`.

### Query timeouts
If tests timeout when querying ClickHouse:

1. Check ClickHouse is not overloaded
2. Increase timeout in test configuration
3. Check network connectivity

## Manual Testing

You can run individual tests manually:

```python
# Run a single test interactively
python python/tests/integration/test_clickhouse_integration.py
```

Or use pytest with specific test names:
```bash
pytest -v -s python/tests/integration/test_clickhouse_integration.py::test_track_single_event_to_clickhouse
```

## CI/CD Integration

To run integration tests in CI/CD:

1. Ensure ClickHouse service is started in CI pipeline
2. Set environment variables as needed
3. Run tests with integration marker:
   ```bash
   pytest -v python/tests/ -m integration
   ```

Example GitHub Actions:
```yaml
- name: Start ClickHouse
  run: |
    cd infra
    docker compose up -d clickhouse

- name: Wait for ClickHouse
  run: |
    timeout 30 bash -c 'until curl -s http://localhost:8123/?query=SELECT%201 > /dev/null; do sleep 1; done'

- name: Run integration tests
  run: |
    cd python
    pytest -v tests/integration/
```
