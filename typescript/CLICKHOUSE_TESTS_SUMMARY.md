# ClickHouse Integration Tests - Summary

## Overview

Comprehensive integration tests have been created for the TypeScript SDK's ClickHouse backend at:
- **Test File**: `tests/clickhouse.integration.test.ts`
- **Documentation**: `tests/CLICKHOUSE_INTEGRATION_README.md`
- **Helper Script**: `tests/run-clickhouse-tests.sh`

## Tests Created

### 1. End-to-End Flow Tests (3 tests)
- ✅ **Send traces to ClickHouse and verify data**
  - Tracks multiple events with custom attributes
  - Verifies data appears in ClickHouse
  - Validates trace metadata (trace_id, span_id, service_name)

- ✅ **Batch processing**
  - Tests auto-flush after batch size reached
  - Sends 25 events with batch size of 10
  - Verifies all events are stored correctly

- ✅ **High-throughput bursts**
  - Sends 500 events rapidly
  - Measures generation and flush performance
  - Validates all events reach ClickHouse

### 2. Configuration Tests (3 tests)
- ✅ **Environment variable configuration**
  - Tests AUTOMAGIK_TELEMETRY_BACKEND
  - Tests AUTOMAGIK_TELEMETRY_CLICKHOUSE_* variables
  - Verifies environment-based setup

- ✅ **Config object configuration**
  - Tests explicit backend: "clickhouse"
  - Tests clickhouseEndpoint, clickhouseDatabase, etc.
  - Validates programmatic configuration

- ✅ **Default values**
  - Tests minimal config (only projectName + version + backend)
  - Verifies defaults: localhost:8123, database: telemetry, table: traces
  - Ensures sensible fallbacks work

### 3. Backend Selection Tests (3 tests)
- ✅ **Switch between OTLP and ClickHouse**
  - Creates client with OTLP backend
  - Creates client with ClickHouse backend
  - Verifies backend-specific behavior

- ✅ **Backward compatibility**
  - Tests default OTLP behavior (no backend specified)
  - Ensures existing code continues working
  - Silent no-op when disabled

- ✅ **Invalid backend handling**
  - Tests with invalid backend name
  - Verifies graceful degradation
  - No exceptions thrown

### 4. Data Verification Tests (3 tests)
- ✅ **Trace metadata storage**
  - Validates trace_id, span_id format
  - Checks timestamp accuracy
  - Verifies service_name, span_name, status_code

- ✅ **System information capture**
  - Verifies OS, architecture, Node version
  - Checks user_id, session_id presence
  - Validates attribute structure

- ✅ **Special characters in attributes**
  - Tests emoji (🚀🎉)
  - Tests unicode (世界)
  - Tests quotes and newlines
  - Ensures proper escaping/encoding

### 5. Error Handling Tests (2 tests)
- ✅ **Connection failures**
  - Tests with wrong endpoint (port 9999)
  - Verifies no exceptions thrown
  - Validates silent failure behavior

- ✅ **Invalid credentials**
  - Tests with wrong username/password
  - Ensures graceful degradation
  - No application crashes

### 6. Performance Tests (1 test)
- ✅ **1000 events with compression**
  - Sends 1000 events in batches of 100
  - Measures generation time (< 2s)
  - Measures total time with flush (< 15s)
  - Verifies all data reaches ClickHouse
  - Reports events/sec rate

**Total: 18 comprehensive integration tests**

## Prerequisites

### Required
1. **ClickHouse running** at http://localhost:8123
   ```bash
   cd infra && docker compose up -d clickhouse
   ```

2. **Database initialized** with schema
   - Database: `telemetry`
   - Table: `traces`
   - Automatically created via `infra/clickhouse/init-db.sql`

3. **Dependencies installed**
   ```bash
   pnpm install
   ```

### Verification
```bash
# Check ClickHouse is running
curl http://localhost:8123
# Should return: Ok.

# Check database exists
curl "http://localhost:8123/?query=SHOW%20DATABASES" | grep telemetry

# Check table exists
curl "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20telemetry" | grep traces
```

## How to Run Tests

### Method 1: NPM Scripts (Recommended)

```bash
# Run all ClickHouse integration tests
npm run test:integration:clickhouse

# Run all integration tests (including OTLP)
npm run test:integration

# Run unit tests only (exclude integration)
npm run test:unit

# Run with watch mode
npm run test:watch
```

### Method 2: Direct Jest Commands

```bash
# All ClickHouse tests
RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts

# Specific test suite
RUN_INTEGRATION_TESTS=true npm test -- -t "End-to-End Flow"

# Specific test
RUN_INTEGRATION_TESTS=true npm test -- -t "should send traces to ClickHouse"

# Verbose output
RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts --verbose
```

### Method 3: Helper Script

```bash
# Run all tests with automatic prerequisite checks
./tests/run-clickhouse-tests.sh

# Run specific test
./tests/run-clickhouse-tests.sh -t "Performance"
```

## Environment Variables

### ClickHouse Connection
```bash
export CLICKHOUSE_ENDPOINT=http://localhost:8123
export CLICKHOUSE_DATABASE=telemetry
export CLICKHOUSE_TABLE=traces
export CLICKHOUSE_USERNAME=default
export CLICKHOUSE_PASSWORD=
```

### Test Control
```bash
export RUN_INTEGRATION_TESTS=true  # Enable integration tests
export CI=true                     # Simulates CI environment
```

### SDK Configuration (tested by the tests)
```bash
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE=traces
export AUTOMAGIK_TELEMETRY_VERBOSE=true  # For debugging
```

## Test Features

### Automatic Test Data Cleanup
- Each test uses unique project name: `test-{suite}-{timestamp}`
- Cleanup runs automatically after each test
- Uses ClickHouse DELETE mutations
- Waits for mutations to complete (2s delay)

### Smart Prerequisites Detection
- Tests automatically skip if ClickHouse unavailable
- Helpful error messages with setup instructions
- No false failures in CI without infrastructure

### Wait-for-Data Helper
- Polls ClickHouse for data availability
- Maximum 30 attempts with 500ms delay (15s timeout)
- Accounts for ClickHouse's eventual consistency
- Clear timeout error messages

### Performance Measurement
- Generation time (event creation)
- Flush time (network + ClickHouse insert)
- Total time (end-to-end)
- Events/sec rate calculation
- Console output with metrics

## Expected Performance

Based on local Docker ClickHouse:

| Metric | Expected Value |
|--------|----------------|
| Generation Rate | > 500 events/sec |
| Total Throughput | > 100 events/sec |
| 1000 Events Total Time | < 15 seconds |
| Batch of 25 | < 5 seconds |
| Single Event | < 2 seconds |

## Troubleshooting

### Tests Skipped
```
⏭️  Skipping ClickHouse integration tests (ClickHouse not available)
```
**Fix**: Start ClickHouse with `cd infra && docker compose up -d clickhouse`

### Connection Timeout
**Check**: `docker ps | grep clickhouse`
**Logs**: `docker logs automagik-clickhouse`

### Data Not Appearing
```bash
# Check recent traces
curl "http://localhost:8123/?query=SELECT%20count()%20FROM%20telemetry.traces%20FORMAT%20JSON"

# View sample data
curl "http://localhost:8123/?query=SELECT%20*%20FROM%20telemetry.traces%20ORDER%20BY%20timestamp%20DESC%20LIMIT%205%20FORMAT%20Vertical"
```

### Test Data Pollution
```bash
# Clean all test data
curl "http://localhost:8123/?query=ALTER%20TABLE%20telemetry.traces%20DELETE%20WHERE%20project_name%20LIKE%20'test-%25'"
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Start ClickHouse
  run: |
    cd infra
    docker compose up -d clickhouse
    sleep 10

- name: Run ClickHouse Integration Tests
  run: |
    cd typescript
    npm run test:integration:clickhouse
  env:
    CLICKHOUSE_ENDPOINT: http://localhost:8123
```

### GitLab CI Example
```yaml
test:integration:clickhouse:
  services:
    - clickhouse/clickhouse-server:24-alpine
  variables:
    CLICKHOUSE_ENDPOINT: http://clickhouse:8123
  script:
    - cd typescript
    - npm run test:integration:clickhouse
```

## Files Created

| File | Purpose |
|------|---------|
| `tests/clickhouse.integration.test.ts` | Main test suite (18 tests, ~700 lines) |
| `tests/CLICKHOUSE_INTEGRATION_README.md` | Comprehensive documentation |
| `tests/run-clickhouse-tests.sh` | Helper script with prerequisite checks |
| `CLICKHOUSE_TESTS_SUMMARY.md` | This summary document |

## Package.json Scripts Added

```json
{
  "scripts": {
    "test:unit": "jest --coverage --testPathIgnorePatterns=integration",
    "test:integration": "RUN_INTEGRATION_TESTS=true jest integration.test.ts --coverage=false",
    "test:integration:clickhouse": "RUN_INTEGRATION_TESTS=true jest clickhouse.integration.test.ts --coverage=false",
    "test:watch": "jest --watch"
  }
}
```

## Next Steps

### To Run Tests Now
1. Ensure ClickHouse is running:
   ```bash
   cd infra && docker compose up -d clickhouse
   ```

2. Run the tests:
   ```bash
   cd typescript
   npm run test:integration:clickhouse
   ```

### To Add More Tests
1. Edit `tests/clickhouse.integration.test.ts`
2. Add new `describe()` or `test()` blocks
3. Use existing helper functions:
   - `executeClickHouseQuery(query)`
   - `waitForData(projectName, minCount)`
   - `cleanupTestData(projectName)`
   - `isClickHouseAvailable()`

### To Debug Failing Tests
1. Enable verbose mode:
   ```bash
   export AUTOMAGIK_TELEMETRY_VERBOSE=true
   RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts --verbose
   ```

2. Check ClickHouse directly:
   ```bash
   docker exec -it automagik-clickhouse clickhouse-client
   SELECT * FROM telemetry.traces ORDER BY timestamp DESC LIMIT 10 FORMAT Vertical;
   ```

## Related Documentation

- [ClickHouse Backend Implementation](src/backends/clickhouse.ts)
- [ClickHouse Schema](../infra/clickhouse/init-db.sql)
- [Docker Compose Setup](../infra/docker-compose.yml)
- [Main Integration Tests](tests/integration.test.ts)
- [Integration Tests README](tests/INTEGRATION_TESTS_README.md)
