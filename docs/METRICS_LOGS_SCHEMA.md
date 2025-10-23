# Metrics and Logs Schema Design

Complete ClickHouse schema design for OTLP metrics and logs, complementing the existing traces table in the Automagik Telemetry system.

## Table of Contents

- [Overview](#overview)
- [Metrics Table](#metrics-table)
- [Logs Table](#logs-table)
- [Materialized Views](#materialized-views)
- [Design Decisions](#design-decisions)
- [Performance Optimizations](#performance-optimizations)
- [Query Examples](#query-examples)
- [Integration Guide](#integration-guide)

## Overview

This schema follows OTLP (OpenTelemetry Protocol) standards and ClickHouse best practices to provide:

- **High cardinality support** - Handle millions of unique metric/log combinations
- **Fast time-series queries** - Optimized for temporal analysis
- **Rich context** - Full resource and span attributes
- **Cross-signal correlation** - Link traces, metrics, and logs
- **Automatic aggregations** - Materialized views for dashboard queries
- **Data retention** - 90-day TTL with optional longer retention for aggregates

## Metrics Table

### Schema Design

The `metrics` table stores all OTLP metric types:

**Metric Types Supported:**
- `GAUGE` - Point-in-time measurements (CPU usage, memory, queue depth)
- `SUM` - Cumulative or delta counters (request count, bytes sent)
- `HISTOGRAM` - Distribution of values (request duration, response sizes)
- `EXPONENTIAL_HISTOGRAM` - Exponential bucket histograms
- `SUMMARY` - Pre-calculated percentiles

### Key Features

**Flexible Value Storage:**
```sql
value_int Int64           -- Integer metrics
value_double Float64      -- Float metrics
histogram_*               -- Histogram data (buckets, bounds, stats)
quantile_values Map       -- Summary percentiles
```

**Temporal Precision:**
```sql
timestamp DateTime                 -- Second precision
timestamp_ns UInt64               -- Nanosecond precision
time_window_start/end DateTime    -- Aggregation windows for delta metrics
```

**Rich Context:**
```sql
attributes Map(String, String)    -- Metric labels/dimensions
project_name String               -- Project identifier
service_name String               -- Service identifier
environment String                -- production/staging/dev
cloud_provider String             -- AWS/GCP/Azure
cloud_region String              -- Geographic region
```

### Indexes

Optimized for common query patterns:

```sql
INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1
INDEX idx_metric_name metric_name TYPE bloom_filter GRANULARITY 1
INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1
INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1
INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1
INDEX idx_metric_type metric_type TYPE set GRANULARITY 1
```

**Index Types Explained:**
- `minmax` - Fast range filtering on timestamps
- `bloom_filter` - Fast string equality checks (metric names, services)
- `set` - Fast enum filtering (metric types, environments)

### Partitioning & TTL

```sql
PARTITION BY toYYYYMM(timestamp)   -- Monthly partitions
ORDER BY (service_name, metric_name, timestamp)
TTL timestamp + INTERVAL 90 DAY    -- Auto-delete after 90 days
```

**Benefits:**
- Fast queries on recent data
- Efficient partition pruning for time ranges
- Automatic data cleanup
- Easy backup/restore of specific months

## Logs Table

### Schema Design

The `logs` table stores structured log entries with OTLP standard fields:

**Severity Levels (OTLP Standard):**
- `1-4`: TRACE (verbose debugging)
- `5-8`: DEBUG (debugging information)
- `9-12`: INFO (informational messages)
- `13-16`: WARN (warning messages)
- `17-20`: ERROR (error messages)
- `21-24`: FATAL (fatal errors)

### Key Features

**Log Content:**
```sql
body String                  -- The log message
body_type Enum8             -- STRING, JSON, BYTES
severity_number UInt8       -- Numeric severity (1-24)
severity_text String        -- Human-readable (ERROR, WARN, INFO)
```

**Trace Correlation:**
```sql
trace_id String             -- Link to distributed trace
span_id String              -- Link to specific span
```

**Exception Tracking:**
```sql
exception_type String       -- Exception class name
exception_message String    -- Exception message
exception_stacktrace String -- Full stack trace
is_exception UInt8          -- Flag for fast exception queries
```

**Source Location:**
```sql
source_file String          -- File path
source_line UInt32          -- Line number
source_function String      -- Function/method name
```

### Indexes

```sql
INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1
INDEX idx_severity severity_number TYPE minmax GRANULARITY 1
INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1
INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1
INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1
INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 1
INDEX idx_is_exception is_exception TYPE set GRANULARITY 1
INDEX idx_body body TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 1
```

**Special Index:**
- `tokenbf_v1` - Full-text search on log messages using token bloom filter

### Partitioning & TTL

```sql
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, severity_number, timestamp)
TTL timestamp + INTERVAL 90 DAY
```

**Ordering by severity** enables fast error log queries without scanning all logs.

## Materialized Views

### Metrics 5-Minute Rollup

Pre-aggregated metrics for fast dashboard queries:

```sql
CREATE TABLE metrics_5min (
    timestamp DateTime,
    project_name String,
    service_name String,
    metric_name String,
    metric_type String,
    environment String,

    count UInt64,
    sum_value Float64,
    avg_value Float64,
    min_value Float64,
    max_value Float64,
    p50_value Float64,
    p95_value Float64,
    p99_value Float64
)
ENGINE = SummingMergeTree()
```

**Benefits:**
- 5-minute time buckets
- Pre-calculated percentiles (p50, p95, p99)
- 180-day retention (2x longer than raw data)
- 12x data reduction (assuming 10-second collection interval)

**Use Case:** Real-time dashboards showing metric trends without scanning raw data.

### Logs Error Summary

Hourly error counts for alerting and monitoring:

```sql
CREATE TABLE logs_error_summary (
    timestamp DateTime,
    project_name String,
    service_name String,
    environment String,
    severity_text String,
    severity_number UInt8,

    total_logs UInt64,
    error_logs UInt64,
    warn_logs UInt64,
    exception_logs UInt64,
    sample_messages Array(String)
)
ENGINE = SummingMergeTree()
```

**Benefits:**
- Hourly rollup of error counts
- Severity breakdown
- Sample error messages for debugging
- 180-day retention
- 3600x data reduction for error monitoring

**Use Case:** Error rate monitoring, SLO tracking, anomaly detection.

### Trace-Logs Correlation View

Join traces and logs for root cause analysis:

```sql
CREATE VIEW trace_logs_correlation AS
SELECT
    t.trace_id,
    t.span_id,
    t.service_name,
    t.span_name,
    t.timestamp AS trace_timestamp,
    t.status_code,

    l.log_id,
    l.timestamp AS log_timestamp,
    l.severity_text,
    l.body AS log_message,
    l.is_exception,
    l.exception_type
FROM traces AS t
INNER JOIN logs AS l ON t.trace_id = l.trace_id
WHERE l.trace_id != ''
```

**Use Case:** Find all logs associated with a failed trace, or traces associated with error logs.

## Design Decisions

### Why Map(String, String) for Attributes?

**Pros:**
- Support arbitrary key-value pairs
- No schema changes needed for new attributes
- ClickHouse Map type is well-optimized
- Matches OTLP flexible attribute model

**Cons:**
- No type safety (all values are strings)
- Slightly slower than native columns

**Decision:** Flexibility wins for observability data where attribute schema is unpredictable.

### Why Separate value_int and value_double?

**Reason:** ClickHouse doesn't have a universal numeric type. Separating int/float:
- Preserves precision for integers
- Avoids unnecessary type conversions
- Better compression for integer metrics

### Why tokenbf_v1 Index on Log Body?

**Reason:** Enable fast full-text search on log messages:
```sql
SELECT * FROM logs
WHERE body LIKE '%OutOfMemoryError%'
AND timestamp >= now() - INTERVAL 1 HOUR
```

The token bloom filter makes this query fast even on billions of logs.

### Why Monthly Partitions?

**Benefits:**
- Balance between partition count and size
- Align with business reporting cycles
- Easy to drop old data: `ALTER TABLE logs DROP PARTITION '202410'`
- Efficient for queries spanning days/weeks

**Alternative:** Daily partitions create too many partitions for large systems.

### Why 90-Day TTL?

**Reasoning:**
- **Compliance:** Most systems need 60-90 days for incident investigation
- **Cost:** Storage cost after 90 days rarely justifies the retention
- **Performance:** Smaller dataset = faster queries
- **Aggregates:** Keep 180-day rollups for long-term trends

**Customization:** Adjust based on your compliance requirements.

## Performance Optimizations

### 1. Column Ordering

Primary columns (left to right) should be:
1. **Highest cardinality filters** - service_name, metric_name
2. **Medium cardinality** - environment, severity
3. **Timestamp** - Range filtering

This ordering enables:
- Fast filtering by service/metric
- Efficient partition pruning by time
- Good compression (similar values grouped)

### 2. Data Types

**Optimized types:**
- `DateTime` instead of `String` for timestamps
- `UInt8` instead of `String` for boolean flags
- `Enum8` instead of `String` for fixed sets
- `Array` and `Map` instead of JSON strings

**Storage savings:** ~50% compared to naive string-based schema.

### 3. Compression

ClickHouse automatically compresses data. Our schema is compression-friendly:
- Enum types compress to 1 byte
- Repeated strings (service_name) compress well with LZ4
- Timestamp ordering groups similar values

**Expected compression ratio:** 10:1 to 20:1

### 4. Materialized Views

Pre-aggregate common queries:
- **metrics_5min_mv** - Dashboard queries
- **logs_error_summary_mv** - Error rate monitoring

**Query speedup:** 100x-1000x for aggregation queries.

### 5. Indexes

Strategic index placement:
- **minmax** on timestamp - Fast date range filters
- **bloom_filter** on strings - Fast equality checks
- **tokenbf_v1** on log body - Fast substring search
- **set** on enums - Fast set membership

**Query speedup:** 10x-100x for filtered queries.

## Query Examples

### Metrics Queries

**Get metric values over time:**
```sql
SELECT
    toStartOfInterval(timestamp, INTERVAL 1 MINUTE) as time_bucket,
    metric_name,
    avg(value_double) as avg_value,
    quantile(0.95)(value_double) as p95_value
FROM metrics
WHERE metric_name = 'http.request.duration'
  AND service_name = 'api-gateway'
  AND timestamp >= now() - INTERVAL 1 HOUR
GROUP BY time_bucket, metric_name
ORDER BY time_bucket;
```

**Analyze histogram distribution:**
```sql
SELECT
    metric_name,
    timestamp,
    histogram_count,
    histogram_sum,
    histogram_sum / histogram_count as mean,
    arrayZip(histogram_explicit_bounds, histogram_bucket_counts) as distribution
FROM metrics
WHERE metric_type = 'HISTOGRAM'
  AND metric_name = 'http.request.size'
  AND timestamp >= now() - INTERVAL 5 MINUTE
ORDER BY timestamp DESC
LIMIT 10;
```

**Compare metrics across environments:**
```sql
SELECT
    environment,
    metric_name,
    count() as sample_count,
    avg(value_double) as avg_value,
    quantile(0.50)(value_double) as p50,
    quantile(0.95)(value_double) as p95,
    quantile(0.99)(value_double) as p99
FROM metrics
WHERE metric_name = 'api.latency'
  AND timestamp >= now() - INTERVAL 1 DAY
GROUP BY environment, metric_name
ORDER BY environment;
```

**Fast dashboard query using materialized view:**
```sql
SELECT
    timestamp,
    service_name,
    metric_name,
    avg_value,
    p95_value,
    p99_value
FROM metrics_5min
WHERE project_name = 'my-project'
  AND timestamp >= now() - INTERVAL 24 HOUR
ORDER BY timestamp DESC;
```

### Logs Queries

**Recent error logs:**
```sql
SELECT
    timestamp,
    service_name,
    severity_text,
    body,
    exception_type,
    source_file,
    source_line
FROM logs
WHERE severity_number >= 17  -- ERROR or FATAL
  AND project_name = 'my-project'
  AND timestamp >= now() - INTERVAL 1 HOUR
ORDER BY timestamp DESC
LIMIT 100;
```

**Full-text search in logs:**
```sql
SELECT
    timestamp,
    service_name,
    severity_text,
    body,
    attributes
FROM logs
WHERE body LIKE '%OutOfMemoryError%'
  AND timestamp >= now() - INTERVAL 6 HOUR
ORDER BY timestamp DESC
LIMIT 50;
```

**Exception analysis:**
```sql
SELECT
    exception_type,
    count() as occurrence_count,
    groupArray(5)(exception_message) as sample_messages,
    groupArray(5)(service_name) as affected_services
FROM logs
WHERE is_exception = 1
  AND timestamp >= now() - INTERVAL 1 DAY
GROUP BY exception_type
ORDER BY occurrence_count DESC
LIMIT 20;
```

**Error rate over time:**
```sql
SELECT
    toStartOfHour(timestamp) as hour,
    service_name,
    countIf(severity_number >= 17) as error_count,
    count() as total_logs,
    (error_count / total_logs) * 100 as error_rate_pct
FROM logs
WHERE timestamp >= now() - INTERVAL 7 DAY
  AND project_name = 'my-project'
GROUP BY hour, service_name
HAVING error_count > 0
ORDER BY hour DESC, error_rate_pct DESC;
```

**Using error summary materialized view:**
```sql
SELECT
    timestamp,
    service_name,
    environment,
    sum(error_logs) as total_errors,
    sum(warn_logs) as total_warnings,
    sum(exception_logs) as total_exceptions,
    arrayFlatten(groupArray(sample_messages)) as all_samples
FROM logs_error_summary
WHERE timestamp >= now() - INTERVAL 24 HOUR
  AND project_name = 'my-project'
GROUP BY timestamp, service_name, environment
HAVING total_errors > 10
ORDER BY timestamp DESC;
```

### Cross-Signal Queries

**Find all logs for a specific trace:**
```sql
SELECT
    trace_id,
    span_id,
    service_name,
    span_name,
    trace_timestamp,
    status_code,
    log_timestamp,
    severity_text,
    log_message,
    exception_type
FROM trace_logs_correlation
WHERE trace_id = 'abc123xyz'
ORDER BY log_timestamp;
```

**Find traces with error logs:**
```sql
SELECT
    trace_id,
    service_name,
    span_name,
    trace_timestamp,
    count() as error_log_count,
    groupArray(3)(log_message) as sample_errors
FROM trace_logs_correlation
WHERE severity_number >= 17
  AND trace_timestamp >= now() - INTERVAL 6 HOUR
GROUP BY trace_id, service_name, span_name, trace_timestamp
HAVING error_log_count >= 3
ORDER BY trace_timestamp DESC
LIMIT 50;
```

**Correlate metrics with errors:**
```sql
WITH metric_data AS (
    SELECT
        toStartOfMinute(timestamp) as time_bucket,
        service_name,
        avg(value_double) as avg_latency
    FROM metrics
    WHERE metric_name = 'http.request.duration'
      AND timestamp >= now() - INTERVAL 1 HOUR
    GROUP BY time_bucket, service_name
),
error_data AS (
    SELECT
        toStartOfMinute(timestamp) as time_bucket,
        service_name,
        count() as error_count
    FROM logs
    WHERE severity_number >= 17
      AND timestamp >= now() - INTERVAL 1 HOUR
    GROUP BY time_bucket, service_name
)
SELECT
    m.time_bucket,
    m.service_name,
    m.avg_latency,
    COALESCE(e.error_count, 0) as error_count
FROM metric_data m
LEFT JOIN error_data e ON m.time_bucket = e.time_bucket AND m.service_name = e.service_name
ORDER BY m.time_bucket DESC;
```

## Integration Guide

### 1. Update ClickHouse Schema

Apply the schema to your ClickHouse instance:

```bash
# Connect to ClickHouse
clickhouse-client --host localhost --port 9000

# Or via docker
docker exec -it clickhouse-server clickhouse-client

# Apply schema
cat /path/to/metrics-logs-schema.sql | clickhouse-client
```

### 2. Update Backend Code

Add metrics and logs support to the existing `ClickHouseBackend`:

**TypeScript example structure:**
```typescript
interface ClickHouseMetricRow {
  metric_id: string;
  metric_name: string;
  metric_type: string;
  timestamp: string;
  value_double: number;
  service_name: string;
  project_name: string;
  attributes: Record<string, string>;
  // ... other fields
}

interface ClickHouseLogRow {
  log_id: string;
  timestamp: string;
  severity_number: number;
  severity_text: string;
  body: string;
  service_name: string;
  project_name: string;
  trace_id: string;
  attributes: Record<string, string>;
  // ... other fields
}

class ClickHouseBackend {
  // Existing trace methods...

  sendMetric(otlpMetric: any): boolean {
    const row = this.transformOTLPMetricToClickHouse(otlpMetric);
    return this.insertRow('metrics', row);
  }

  sendLog(otlpLog: any): boolean {
    const row = this.transformOTLPLogToClickHouse(otlpLog);
    return this.insertRow('logs', row);
  }
}
```

### 3. OTLP Transformation

Transform OTLP format to ClickHouse schema:

**Metric transformation:**
```typescript
private transformOTLPMetricToClickHouse(otlpMetric: any): ClickHouseMetricRow {
  const metricPoint = otlpMetric.gauge?.dataPoints?.[0] ||
                      otlpMetric.sum?.dataPoints?.[0] ||
                      otlpMetric.histogram?.dataPoints?.[0];

  return {
    metric_id: generateUUID(),
    metric_name: otlpMetric.name,
    metric_type: determineMetricType(otlpMetric),
    timestamp: new Date(Number(metricPoint.timeUnixNano) / 1_000_000)
                .toISOString().replace('T', ' ').substring(0, 19),
    value_double: metricPoint.asDouble || 0,
    service_name: extractResourceAttribute(otlpMetric, 'service.name'),
    project_name: extractResourceAttribute(otlpMetric, 'project.name'),
    attributes: transformAttributes(metricPoint.attributes),
    // ... other fields
  };
}
```

**Log transformation:**
```typescript
private transformOTLPLogToClickHouse(otlpLog: any): ClickHouseLogRow {
  const severityMap = {
    'TRACE': 1, 'DEBUG': 5, 'INFO': 9,
    'WARN': 13, 'ERROR': 17, 'FATAL': 21
  };

  return {
    log_id: generateUUID(),
    timestamp: new Date(Number(otlpLog.timeUnixNano) / 1_000_000)
                .toISOString().replace('T', ' ').substring(0, 19),
    severity_number: otlpLog.severityNumber ||
                     severityMap[otlpLog.severityText] || 0,
    severity_text: otlpLog.severityText || '',
    body: otlpLog.body?.stringValue || '',
    service_name: extractResourceAttribute(otlpLog, 'service.name'),
    project_name: extractResourceAttribute(otlpLog, 'project.name'),
    trace_id: otlpLog.traceId || '',
    attributes: transformAttributes(otlpLog.attributes),
    // ... other fields
  };
}
```

### 4. Testing

Validate the schema and data flow:

```sql
-- Insert test metric
INSERT INTO telemetry.metrics FORMAT JSONEachRow
{"metric_id":"test-1","metric_name":"test.metric","metric_type":"GAUGE","timestamp":"2025-01-15 10:00:00","value_double":42.5,"service_name":"test-service","project_name":"test-project"}

-- Insert test log
INSERT INTO telemetry.logs FORMAT JSONEachRow
{"log_id":"log-1","timestamp":"2025-01-15 10:00:00","severity_number":17,"severity_text":"ERROR","body":"Test error message","service_name":"test-service","project_name":"test-project"}

-- Verify
SELECT * FROM telemetry.metrics LIMIT 1;
SELECT * FROM telemetry.logs LIMIT 1;
```

### 5. Monitoring

Monitor the new tables:

```sql
-- Table sizes
SELECT
    table,
    formatReadableSize(sum(bytes)) as size,
    sum(rows) as row_count,
    max(modification_time) as last_modified
FROM system.parts
WHERE database = 'telemetry'
  AND table IN ('metrics', 'logs', 'metrics_5min', 'logs_error_summary')
  AND active = 1
GROUP BY table;

-- Partition info
SELECT
    table,
    partition,
    sum(rows) as rows,
    formatReadableSize(sum(bytes)) as size
FROM system.parts
WHERE database = 'telemetry'
  AND table IN ('metrics', 'logs')
  AND active = 1
GROUP BY table, partition
ORDER BY table, partition DESC;

-- Materialized view status
SELECT
    database,
    name,
    create_table_query
FROM system.tables
WHERE database = 'telemetry'
  AND name LIKE '%_mv'
  AND engine = 'MaterializedView';
```

## Best Practices

### 1. Use Batch Inserts

Insert data in batches (100-1000 rows) for best performance:

```typescript
const batch: ClickHouseMetricRow[] = [];
for (const metric of metrics) {
  batch.push(transformMetric(metric));

  if (batch.length >= 100) {
    await insertBatch('metrics', batch);
    batch.length = 0;
  }
}
```

### 2. Set Appropriate Cardinality

**High cardinality is OK for:**
- metric_name (thousands of metrics)
- service_name (hundreds of services)
- attributes keys (hundreds of attribute types)

**Avoid high cardinality for:**
- attribute values (don't use UUIDs as attribute values)
- user_id in attributes (use dedicated user_id column)

### 3. Use Compression

Enable gzip for batch inserts over 1KB:

```typescript
const compressed = gzipSync(Buffer.from(jsonData));
// Send compressed data with Content-Encoding: gzip header
```

### 4. Query Optimization

- **Use PREWHERE** for large scans with selective filters
- **Use materialized views** for dashboard queries
- **Avoid SELECT *** - Select only needed columns
- **Use LIMIT** - Always limit results for safety

Example:
```sql
SELECT timestamp, body, severity_text
FROM logs
PREWHERE severity_number >= 17
WHERE project_name = 'my-project'
  AND timestamp >= now() - INTERVAL 1 HOUR
ORDER BY timestamp DESC
LIMIT 1000;
```

### 5. Monitoring & Alerting

Set up alerts on:
- Error rate (from logs_error_summary)
- Metric anomalies (p99 latency spikes)
- Exception counts
- Table sizes (approaching storage limits)

## Conclusion

This schema provides a production-ready foundation for metrics and logs in your OTLP telemetry system. Key benefits:

- **OTLP compliant** - Standards-based design
- **High performance** - Optimized indexes and partitioning
- **Rich context** - Full resource and span attributes
- **Cross-signal correlation** - Link traces, metrics, and logs
- **Cost effective** - Automatic TTL and compression
- **Query flexibility** - Materialized views for common patterns

For questions or improvements, consult the [ClickHouse documentation](https://clickhouse.com/docs/) and [OTLP specification](https://opentelemetry.io/docs/specs/otlp/).
