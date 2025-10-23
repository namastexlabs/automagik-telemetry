# ClickHouse Data Verification Guide

This guide helps you verify that telemetry data is correctly flowing into ClickHouse and understand how to query and visualize it in Grafana.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Automated Verification](#automated-verification)
3. [Manual Verification](#manual-verification)
4. [Grafana Dashboard Verification](#grafana-dashboard-verification)
5. [Expected Data Structure](#expected-data-structure)
6. [Common Queries](#common-queries)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Run Automated Verification

The fastest way to verify your ClickHouse setup:

```bash
cd infra
./scripts/verify_clickhouse_data.sh
```

This script will:
- Check if services are running (starts them if needed)
- Test Python SDK with ClickHouse backend
- Test TypeScript SDK with ClickHouse backend
- Verify data integrity and schema
- Display sample data and statistics

---

## Automated Verification

### What the Script Tests

The verification script (`infra/scripts/verify_clickhouse_data.sh`) performs the following checks:

1. **Service Health**
   - ClickHouse HTTP API (port 8123)
   - OTLP Collector (port 4318)
   - Grafana (port 3000)

2. **SDK Integration**
   - Python SDK sending data directly to ClickHouse
   - TypeScript SDK sending data directly to ClickHouse

3. **Data Integrity**
   - Row counts before and after test
   - Schema validation
   - Sample data inspection

4. **Expected Output**
   ```
   ========================================
   ClickHouse Data Verification Script
   ========================================

   [1/6] Checking services...
   ✓ ClickHouse is running
   ✓ OTLP Collector is running
   ✓ Grafana is running

   [2/6] Getting baseline row counts...
     Traces: 1234
     Metrics: 56

   [3/6] Testing Python SDK with ClickHouse backend...
   ✓ Sent event 1/5
   ...
   ✓ Python SDK test passed

   [4/6] Testing TypeScript SDK with ClickHouse backend...
   ✓ Sent event 1/5
   ...
   ✓ TypeScript SDK test passed

   [5/6] Verifying data in ClickHouse...
     Total traces: 1244 (+10 new)
     Total metrics: 56

   ✓ Schema validation passed

   [6/6] Verification Summary
   ========================================
   ✓ Python SDK with ClickHouse backend
   ✓ TypeScript SDK with ClickHouse backend
   ✓ Data successfully written to ClickHouse

   Results: 3/3 checks passed
   ```

---

## Manual Verification

### 1. Check ClickHouse Service

```bash
# Check if ClickHouse is responding
curl http://localhost:8123/ping

# Expected output: Ok.
```

### 2. Connect to ClickHouse CLI

```bash
cd infra
make query
```

Or directly:

```bash
docker compose exec clickhouse clickhouse-client --database=telemetry
```

### 3. Basic Queries

Once in the ClickHouse CLI:

```sql
-- Count total traces
SELECT count() FROM traces;

-- View recent traces
SELECT
    timestamp,
    project_name,
    span_name,
    status_code
FROM traces
ORDER BY timestamp DESC
LIMIT 10;

-- Check data by project
SELECT
    project_name,
    count() as total_events,
    countIf(status_code != 'OK') as errors,
    avg(duration_ms) as avg_duration_ms
FROM traces
GROUP BY project_name
ORDER BY total_events DESC;

-- View trace details with attributes
SELECT
    timestamp,
    trace_id,
    span_name,
    project_name,
    attributes
FROM traces
ORDER BY timestamp DESC
LIMIT 5
FORMAT Vertical;
```

### 4. Verify Schema

```sql
-- Show table structure
DESCRIBE traces;

-- Expected columns:
-- trace_id            String
-- span_id             String
-- parent_span_id      String
-- timestamp           DateTime
-- timestamp_ns        UInt64
-- duration_ms         UInt32
-- service_name        String
-- span_name           String
-- span_kind           String
-- status_code         String
-- status_message      String
-- project_name        String
-- project_version     String
-- environment         String
-- hostname            String
-- attributes          Map(String, String)
-- user_id             String
-- session_id          String
-- os_type             String
-- os_version          String
-- runtime_name        String
-- runtime_version     String
```

---

## Grafana Dashboard Verification

### Access Grafana

1. **Open Grafana**
   ```bash
   # Open in browser
   cd infra
   make dashboard

   # Or visit manually
   # http://localhost:3000
   ```

2. **Login Credentials**
   - Username: `admin`
   - Password: `admin`

### Configure ClickHouse Data Source

If not already configured:

1. Go to **Configuration** (gear icon) → **Data Sources**
2. Click **Add data source**
3. Select **ClickHouse**
4. Configure:
   ```
   URL: http://clickhouse:8123
   Database: telemetry
   Username: telemetry
   Password: telemetry_password
   ```
5. Click **Save & Test**

### Create a Dashboard

#### Query 1: Traces Over Time

```sql
SELECT
    toStartOfInterval(timestamp, INTERVAL 1 minute) AS time,
    count() AS value
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

**Expected Result:**
- Line chart showing trace volume over time
- Should see spikes corresponding to your test data

#### Query 2: Events by Project

```sql
SELECT
    project_name,
    count() AS events
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY project_name
ORDER BY events DESC
LIMIT 10
```

**Expected Result:**
- Bar chart or table showing top projects by event count
- Should see your test projects: `test-python-clickhouse`, `test-typescript-clickhouse`

#### Query 3: Error Rate

```sql
SELECT
    toStartOfInterval(timestamp, INTERVAL 5 minute) AS time,
    countIf(status_code != 'OK') * 100.0 / count() AS error_rate
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

**Expected Result:**
- Line chart showing error percentage over time
- Should be low (near 0%) for test data

#### Query 4: P95 Latency by Event

```sql
SELECT
    span_name,
    quantile(0.95)(duration_ms) AS p95_latency_ms
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
    AND duration_ms > 0
GROUP BY span_name
ORDER BY p95_latency_ms DESC
LIMIT 10
```

**Expected Result:**
- Table showing slowest operations
- Useful for performance analysis

### What to Look For

✅ **Healthy Dashboard Indicators:**
- Data appears in all panels
- Timestamps are recent
- No gaps in time-series data
- Test projects appear in project breakdown
- Attributes are properly parsed (not all empty)

❌ **Problems to Watch For:**
- All zero values
- "No data" messages
- Old timestamps only
- Missing attributes
- Error messages in panels

---

## Expected Data Structure

### Traces Table

Each event creates a row with this structure:

```json
{
  "trace_id": "a1b2c3d4e5f6...",
  "span_id": "1a2b3c4d...",
  "timestamp": "2025-10-22 18:30:45",
  "timestamp_ns": 1729620645000000000,
  "duration_ms": 123,
  "service_name": "my-service",
  "span_name": "user.login",
  "project_name": "my-project",
  "project_version": "1.0.0",
  "environment": "production",
  "status_code": "OK",
  "attributes": {
    "user.id": "u_12345",
    "event.type": "authentication",
    "custom.field": "value"
  }
}
```

### Key Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | String | Unique identifier for the trace |
| `span_id` | String | Unique identifier for this span |
| `timestamp` | DateTime | Event timestamp |
| `duration_ms` | UInt32 | Duration in milliseconds |
| `service_name` | String | Service/SDK name |
| `span_name` | String | Event name |
| `project_name` | String | Your project name |
| `status_code` | String | "OK" or error status |
| `attributes` | Map | Custom event properties |

---

## Common Queries

### 1. Recent Activity

```sql
SELECT
    timestamp,
    project_name,
    span_name,
    formatReadableTimeDelta(now() - timestamp) AS ago
FROM traces
ORDER BY timestamp DESC
LIMIT 20;
```

### 2. Top Events by Volume

```sql
SELECT
    span_name,
    count() AS total,
    uniq(trace_id) AS unique_traces
FROM traces
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY span_name
ORDER BY total DESC
LIMIT 10;
```

### 3. Error Analysis

```sql
SELECT
    project_name,
    span_name,
    status_code,
    count() AS occurrences,
    max(timestamp) AS last_seen
FROM traces
WHERE status_code != 'OK'
    AND timestamp >= now() - INTERVAL 1 DAY
GROUP BY project_name, span_name, status_code
ORDER BY occurrences DESC;
```

### 4. Performance by Project

```sql
SELECT
    project_name,
    count() AS total_events,
    quantile(0.50)(duration_ms) AS p50_ms,
    quantile(0.95)(duration_ms) AS p95_ms,
    quantile(0.99)(duration_ms) AS p99_ms,
    max(duration_ms) AS max_ms
FROM traces
WHERE duration_ms > 0
    AND timestamp >= now() - INTERVAL 1 HOUR
GROUP BY project_name
ORDER BY total_events DESC;
```

### 5. Attribute Analysis

```sql
-- See which attributes are being used
SELECT
    arrayJoin(mapKeys(attributes)) AS attribute_key,
    count() AS usage_count
FROM traces
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY attribute_key
ORDER BY usage_count DESC
LIMIT 20;
```

### 6. Time-Series Data (hourly aggregates)

```sql
SELECT
    toStartOfHour(timestamp) AS hour,
    project_name,
    count() AS events,
    countIf(status_code != 'OK') AS errors,
    round(avg(duration_ms), 2) AS avg_duration_ms
FROM traces
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY hour, project_name
ORDER BY hour DESC, events DESC;
```

---

## Troubleshooting

### No Data Appearing

**Check 1: Is ClickHouse running?**
```bash
curl http://localhost:8123/ping
```

**Check 2: Are tables created?**
```bash
cd infra
make query
# Then run: SHOW TABLES;
```

**Check 3: Check ClickHouse logs**
```bash
cd infra
make logs-clickhouse
```

**Check 4: Test direct insertion**
```bash
# Simple test insert
curl -X POST 'http://localhost:8123/' \
  --user 'telemetry:telemetry_password' \
  --data-binary "INSERT INTO telemetry.traces (trace_id, span_id, timestamp, service_name, span_name, project_name) VALUES ('test123', 'span123', now(), 'test', 'test.event', 'manual-test')"

# Verify it was inserted
curl 'http://localhost:8123/' \
  --user 'telemetry:telemetry_password' \
  --data-urlencode "query=SELECT * FROM telemetry.traces WHERE trace_id='test123'"
```

### Schema Errors

**Problem:** "Column not found" or schema mismatch

**Solution:**
```bash
# Reset the database
cd infra
make stop
docker volume rm infra_clickhouse-data
make start

# This will recreate tables with the correct schema
```

### Authentication Errors

**Problem:** "Authentication failed" or "Access denied"

**Solution:**
Check credentials in `docker-compose.yml`:
```yaml
environment:
  CLICKHOUSE_USER: telemetry
  CLICKHOUSE_PASSWORD: telemetry_password
```

### Grafana Can't Connect

**Problem:** Grafana shows "Connection failed"

**Solution:**
1. Use internal Docker network hostname: `http://clickhouse:8123`
2. Don't use `localhost` from Grafana container
3. Ensure Grafana and ClickHouse are on same Docker network

### Old Data Only

**Problem:** Only seeing old test data

**Solution:**
```bash
# Clear old data
cd infra
make reset

# Or view what's there
make query-traces
```

### Performance Issues

**Problem:** Queries are slow

**Solution:**
```sql
-- Check table size
SELECT
    formatReadableSize(sum(bytes)) AS size,
    count() AS rows
FROM system.parts
WHERE database = 'telemetry' AND table = 'traces';

-- Optimize table (merges parts)
OPTIMIZE TABLE traces FINAL;
```

---

## Additional Resources

### Makefile Commands

```bash
cd infra

# View all available commands
make help

# Query commands
make query              # Interactive ClickHouse CLI
make query-traces       # Show recent traces
make query-stats        # Show statistics by project

# Service commands
make start              # Start all services
make stop               # Stop all services
make restart            # Restart all services
make health             # Check service health
make logs               # View all logs
make logs-clickhouse    # View ClickHouse logs only

# Data commands
make reset              # Clear all data
make backup             # Backup data to CSV
```

### SDK Configuration Examples

**Python:**
```python
from automagik_telemetry import TelemetryClient

config = {
    "project_name": "my-project",
    "version": "1.0.0",
    "backend": "clickhouse",
    "clickhouse_endpoint": "http://localhost:8123",
    "clickhouse_database": "telemetry",
    "clickhouse_username": "telemetry",
    "clickhouse_password": "telemetry_password",
}

client = TelemetryClient(config)
client.track_event("user.action", {"key": "value"})
client.flush()
```

**TypeScript:**
```typescript
import { TelemetryClient } from '@automagik/telemetry';
import { ClickHouseBackend } from '@automagik/telemetry/backends/clickhouse';

const backend = new ClickHouseBackend({
  endpoint: 'http://localhost:8123',
  database: 'telemetry',
  username: 'telemetry',
  password: 'telemetry_password',
});

const client = new TelemetryClient({
  projectName: 'my-project',
  version: '1.0.0',
});

client.trackEvent('user.action', { key: 'value' });
await client.flush();
```

### Documentation

- [ClickHouse Backend Design](./CLICKHOUSE_BACKEND_DESIGN.md)
- [Infrastructure README](../README.md)
- [Main Repository README](../../README.md)

---

## Summary Checklist

Use this checklist to verify your ClickHouse setup:

- [ ] ClickHouse service is running (`make health`)
- [ ] Tables are created (`make query` → `SHOW TABLES`)
- [ ] Test data can be inserted (`./scripts/verify_clickhouse_data.sh`)
- [ ] Data is queryable in ClickHouse CLI (`make query-traces`)
- [ ] Grafana can connect to ClickHouse
- [ ] Dashboards show recent data
- [ ] Python SDK successfully sends data
- [ ] TypeScript SDK successfully sends data
- [ ] Schema matches expected structure
- [ ] Attributes are properly stored as Map
- [ ] Timestamps are recent and correct

If all items are checked, your ClickHouse telemetry system is fully operational! 🎉

---

**Last Updated:** 2025-10-22
**Version:** 1.0.0
