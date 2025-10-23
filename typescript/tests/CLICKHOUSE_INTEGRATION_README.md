# ClickHouse Backend Integration Tests

This document explains how to run the ClickHouse backend integration tests for the TypeScript SDK.

## Overview

The ClickHouse integration tests verify that the TypeScript SDK can successfully:
- Send telemetry data directly to ClickHouse
- Use both environment variable and config object configuration
- Handle batch processing and high throughput
- Switch between OTLP and ClickHouse backends
- Store and retrieve data correctly from ClickHouse

## Prerequisites

### 1. ClickHouse Running

The tests require a running ClickHouse instance with the telemetry database and schema initialized.

**Start ClickHouse using Docker Compose:**

```bash
cd ../infra
docker compose up -d clickhouse
```

**Verify ClickHouse is running:**

```bash
curl http://localhost:8123
```

You should see: `Ok.`

**Check the database is initialized:**

```bash
curl "http://localhost:8123/?query=SHOW%20DATABASES" | grep telemetry
```

### 2. Install Dependencies

Make sure all npm dependencies are installed:

```bash
cd ../typescript
pnpm install
```

## Running the Tests

### Run All ClickHouse Integration Tests

```bash
RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts
```

### Run Specific Test Suite

```bash
# Run only end-to-end tests
RUN_INTEGRATION_TESTS=true npm test -- -t "End-to-End Flow"

# Run only configuration tests
RUN_INTEGRATION_TESTS=true npm test -- -t "Configuration Tests"

# Run only performance tests
RUN_INTEGRATION_TESTS=true npm test -- -t "Performance"
```

### Run Specific Test

```bash
RUN_INTEGRATION_TESTS=true npm test -- -t "should send traces to ClickHouse"
```

### Run with Verbose Output

```bash
RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts --verbose
```

## Test Coverage

The integration test suite includes:

### 1. End-to-End Flow Tests
- ✅ Send traces to ClickHouse and verify data
- ✅ Batch processing with auto-flush
- ✅ High-throughput bursts (500 events)

### 2. Configuration Tests
- ✅ Environment variable configuration
- ✅ Config object configuration
- ✅ Default values fallback

### 3. Backend Selection Tests
- ✅ Switch between OTLP and ClickHouse backends
- ✅ Backward compatibility with OTLP
- ✅ Invalid backend handling

### 4. Data Verification Tests
- ✅ Trace metadata storage (trace_id, span_id, timestamps)
- ✅ System information capture
- ✅ Special characters in attributes (emoji, unicode, quotes)

### 5. Error Handling Tests
- ✅ Connection failures (wrong endpoint)
- ✅ Invalid credentials
- ✅ Graceful degradation

### 6. Performance Tests
- ✅ 1000 events with compression
- ✅ Rate measurement (events/sec)

## Environment Variables

You can customize the ClickHouse connection using these environment variables:

```bash
# ClickHouse connection
export CLICKHOUSE_ENDPOINT=http://localhost:8123
export CLICKHOUSE_DATABASE=telemetry
export CLICKHOUSE_TABLE=traces
export CLICKHOUSE_USERNAME=default
export CLICKHOUSE_PASSWORD=

# Enable tests in CI
export RUN_INTEGRATION_TESTS=true
```

## Example: Custom ClickHouse Instance

If you're using a custom ClickHouse instance:

```bash
CLICKHOUSE_ENDPOINT=http://my-clickhouse:8123 \
CLICKHOUSE_USERNAME=myuser \
CLICKHOUSE_PASSWORD=mypassword \
RUN_INTEGRATION_TESTS=true \
npm test -- clickhouse.integration.test.ts
```

## Troubleshooting

### Tests are Skipped

If you see:
```
⏭️  Skipping ClickHouse integration tests (ClickHouse not available)
```

**Solution:** Start ClickHouse:
```bash
cd ../infra && docker compose up -d clickhouse
```

### Connection Timeout

If tests fail with timeout errors:

1. Check ClickHouse is running:
   ```bash
   docker ps | grep clickhouse
   ```

2. Check ClickHouse logs:
   ```bash
   docker logs automagik-clickhouse
   ```

3. Verify connectivity:
   ```bash
   curl http://localhost:8123
   ```

### Data Not Appearing

If tests fail waiting for data:

1. Check table exists:
   ```bash
   curl "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20telemetry"
   ```

2. Manually query the table:
   ```bash
   curl "http://localhost:8123/?query=SELECT%20count()%20FROM%20telemetry.traces%20FORMAT%20JSON"
   ```

3. Check for recent data:
   ```bash
   curl "http://localhost:8123/?query=SELECT%20*%20FROM%20telemetry.traces%20ORDER%20BY%20timestamp%20DESC%20LIMIT%2010%20FORMAT%20JSON"
   ```

### Authentication Errors

If you see authentication errors, check the credentials:

```bash
# Check default user works
curl -u default: http://localhost:8123

# Or with custom credentials
curl -u myuser:mypassword http://localhost:8123
```

## Test Data Cleanup

The tests automatically clean up their test data after each test using:

```sql
ALTER TABLE telemetry.traces DELETE WHERE project_name = 'test-xxx'
```

However, mutations in ClickHouse are asynchronous. If you want to manually clean up:

```bash
curl "http://localhost:8123/?query=ALTER%20TABLE%20telemetry.traces%20DELETE%20WHERE%20project_name%20LIKE%20'test-%25'"
```

## Performance Expectations

Based on local testing with Docker ClickHouse:

- **Generation rate**: > 500 events/sec
- **Total throughput**: > 100 events/sec (including flush to ClickHouse)
- **1000 events**: Should complete in < 15 seconds

Your results may vary based on:
- Docker resource allocation
- Network latency
- Disk I/O performance
- ClickHouse configuration

## Integration with CI/CD

To run in CI environments:

```yaml
# Example GitHub Actions workflow
- name: Start ClickHouse
  run: |
    cd infra
    docker compose up -d clickhouse
    sleep 10  # Wait for initialization

- name: Run Integration Tests
  run: |
    cd typescript
    RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts
  env:
    CLICKHOUSE_ENDPOINT: http://localhost:8123
```

## Development Workflow

When developing ClickHouse backend features:

1. **Start infrastructure:**
   ```bash
   cd infra && docker compose up -d clickhouse
   ```

2. **Run tests in watch mode:**
   ```bash
   cd typescript
   RUN_INTEGRATION_TESTS=true npm test -- --watch clickhouse.integration.test.ts
   ```

3. **View ClickHouse data:**
   ```bash
   # Open ClickHouse client
   docker exec -it automagik-clickhouse clickhouse-client

   # Query recent traces
   SELECT * FROM telemetry.traces ORDER BY timestamp DESC LIMIT 10 FORMAT Vertical
   ```

4. **Stop infrastructure:**
   ```bash
   cd infra && docker compose down
   ```

## Additional Resources

- [ClickHouse Schema](../../infra/clickhouse/init-db.sql)
- [ClickHouse Backend Implementation](../src/backends/clickhouse.ts)
- [Docker Compose Setup](../../infra/docker-compose.yml)
- [General Integration Tests](./INTEGRATION_TESTS_README.md)
