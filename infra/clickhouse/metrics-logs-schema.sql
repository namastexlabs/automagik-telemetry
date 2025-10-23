-- Automagik Telemetry - Metrics and Logs Schema
-- Production-ready ClickHouse tables for OTLP metrics and logs
-- Designed to complement the existing traces table

USE telemetry;

-- ============================================================================
-- METRICS TABLE - Store OTLP Metrics (Gauge, Counter, Histogram, Summary)
-- ============================================================================

CREATE TABLE IF NOT EXISTS metrics (
    -- Metric identification
    metric_id String,                           -- Unique identifier for this metric point
    metric_name String,                         -- Name of the metric (e.g., http.request.duration)
    metric_type Enum8(                          -- OTLP metric types
        'GAUGE' = 1,
        'SUM' = 2,
        'HISTOGRAM' = 3,
        'EXPONENTIAL_HISTOGRAM' = 4,
        'SUMMARY' = 5
    ),
    metric_unit String DEFAULT '',              -- Unit of measurement (ms, bytes, requests, etc.)
    metric_description String DEFAULT '',       -- Human-readable description

    -- Timing
    timestamp DateTime DEFAULT now(),           -- When the metric was recorded
    timestamp_ns UInt64 DEFAULT 0,              -- Nanosecond precision timestamp
    time_window_start DateTime DEFAULT now(),   -- Start of aggregation window (for deltas)
    time_window_end DateTime DEFAULT now(),     -- End of aggregation window

    -- Metric values (based on type)
    -- For GAUGE and SUM
    value_int Int64 DEFAULT 0,                  -- Integer value
    value_double Float64 DEFAULT 0.0,           -- Float value
    is_monotonic UInt8 DEFAULT 0,               -- For SUM: is it monotonic/cumulative?
    aggregation_temporality Enum8(              -- For SUM: delta or cumulative
        'UNSPECIFIED' = 0,
        'DELTA' = 1,
        'CUMULATIVE' = 2
    ) DEFAULT 'UNSPECIFIED',

    -- For HISTOGRAM
    histogram_count UInt64 DEFAULT 0,           -- Total count of observations
    histogram_sum Float64 DEFAULT 0.0,          -- Sum of all observations
    histogram_min Float64 DEFAULT 0.0,          -- Minimum value (if available)
    histogram_max Float64 DEFAULT 0.0,          -- Maximum value (if available)
    histogram_bucket_counts Array(UInt64) DEFAULT [], -- Count for each bucket
    histogram_explicit_bounds Array(Float64) DEFAULT [], -- Upper bounds for buckets

    -- For SUMMARY (percentiles)
    summary_count UInt64 DEFAULT 0,
    summary_sum Float64 DEFAULT 0.0,
    quantile_values Map(Float64, Float64) DEFAULT map(), -- percentile -> value mapping

    -- Resource attributes (application/service info)
    project_name String,
    project_version String DEFAULT '',
    service_name String,
    service_namespace String DEFAULT '',        -- Service namespace/team
    service_instance_id String DEFAULT '',      -- Specific instance
    environment String DEFAULT 'production',
    hostname String DEFAULT '',

    -- Metric attributes (labels/dimensions)
    attributes Map(String, String) DEFAULT map(), -- Key-value pairs for filtering/grouping

    -- User/session tracking (privacy-safe)
    user_id String DEFAULT '',
    session_id String DEFAULT '',

    -- System information
    os_type String DEFAULT '',
    os_version String DEFAULT '',
    runtime_name String DEFAULT '',
    runtime_version String DEFAULT '',
    cloud_provider String DEFAULT '',           -- AWS, GCP, Azure, etc.
    cloud_region String DEFAULT '',             -- us-east-1, europe-west1, etc.
    cloud_availability_zone String DEFAULT '',

    -- Additional metadata
    instrumentation_library_name String DEFAULT '',
    instrumentation_library_version String DEFAULT '',
    schema_url String DEFAULT '',               -- OTLP schema URL

    -- Indexing for fast queries
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_metric_name metric_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1,
    INDEX idx_metric_type metric_type TYPE set GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, metric_name, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- ============================================================================
-- LOGS TABLE - Store OTLP Logs with Severity Levels
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs (
    -- Log identification
    log_id String,                              -- Unique identifier for this log entry
    trace_id String DEFAULT '',                 -- Optional: link to trace
    span_id String DEFAULT '',                  -- Optional: link to span

    -- Timing
    timestamp DateTime DEFAULT now(),           -- When the log was created
    timestamp_ns UInt64 DEFAULT 0,              -- Nanosecond precision timestamp
    observed_timestamp DateTime DEFAULT now(),  -- When the log was observed/collected
    observed_timestamp_ns UInt64 DEFAULT 0,

    -- Log content
    severity_text String DEFAULT '',            -- Human-readable severity (ERROR, WARN, INFO, etc.)
    severity_number UInt8 DEFAULT 0,            -- Numeric severity (1-24, OTLP standard)
                                                -- 1-4: TRACE, 5-8: DEBUG, 9-12: INFO
                                                -- 13-16: WARN, 17-20: ERROR, 21-24: FATAL

    body String,                                -- The actual log message
    body_type Enum8(                            -- Type of body content
        'EMPTY' = 0,
        'STRING' = 1,
        'JSON' = 2,
        'BYTES' = 3
    ) DEFAULT 'STRING',

    -- Resource attributes (application/service info)
    project_name String,
    project_version String DEFAULT '',
    service_name String,
    service_namespace String DEFAULT '',
    service_instance_id String DEFAULT '',
    environment String DEFAULT 'production',
    hostname String DEFAULT '',

    -- Log attributes (structured context)
    attributes Map(String, String) DEFAULT map(), -- Key-value pairs for context

    -- User/session tracking (privacy-safe)
    user_id String DEFAULT '',
    session_id String DEFAULT '',

    -- System information
    os_type String DEFAULT '',
    os_version String DEFAULT '',
    runtime_name String DEFAULT '',
    runtime_version String DEFAULT '',
    cloud_provider String DEFAULT '',
    cloud_region String DEFAULT '',
    cloud_availability_zone String DEFAULT '',

    -- Additional metadata
    instrumentation_library_name String DEFAULT '',
    instrumentation_library_version String DEFAULT '',
    schema_url String DEFAULT '',

    -- Error/exception tracking
    exception_type String DEFAULT '',           -- e.g., ValueError, NullPointerException
    exception_message String DEFAULT '',        -- Exception message
    exception_stacktrace String DEFAULT '',     -- Full stack trace
    is_exception UInt8 DEFAULT 0,               -- Flag: is this an exception log?

    -- Source location (code context)
    source_file String DEFAULT '',              -- Source file path
    source_line UInt32 DEFAULT 0,               -- Line number
    source_function String DEFAULT '',          -- Function/method name

    -- Flags
    flags UInt32 DEFAULT 0,                     -- OTLP flags (bit field)

    -- Indexing for fast queries
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_severity severity_number TYPE minmax GRANULARITY 1,
    INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1,
    INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 1,
    INDEX idx_is_exception is_exception TYPE set GRANULARITY 1,
    INDEX idx_body body TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 1  -- Full-text search
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, severity_number, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- ============================================================================
-- MATERIALIZED VIEWS - Precomputed Aggregations
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Metrics Aggregation - 5-minute rollup for fast dashboards
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS metrics_5min (
    timestamp DateTime,                         -- Rounded to 5-minute window
    project_name String,
    service_name String,
    metric_name String,
    metric_type String,
    environment String,

    -- Aggregated stats
    count UInt64,                               -- Number of metric points
    sum_value Float64,                          -- Sum of all values
    avg_value Float64,                          -- Average value
    min_value Float64,                          -- Minimum value
    max_value Float64,                          -- Maximum value
    p50_value Float64,                          -- 50th percentile
    p95_value Float64,                          -- 95th percentile
    p99_value Float64                           -- 99th percentile
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_name, service_name, metric_name, environment, timestamp)
TTL timestamp + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;

-- Materialized view to populate metrics_5min
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_5min_mv
TO metrics_5min
AS SELECT
    toStartOfFiveMinute(timestamp) AS timestamp,
    project_name,
    service_name,
    metric_name,
    toString(metric_type) AS metric_type,
    environment,

    count() AS count,
    sum(value_double) AS sum_value,
    avg(value_double) AS avg_value,
    min(value_double) AS min_value,
    max(value_double) AS max_value,
    quantile(0.5)(value_double) AS p50_value,
    quantile(0.95)(value_double) AS p95_value,
    quantile(0.99)(value_double) AS p99_value
FROM metrics
WHERE metric_type IN ('GAUGE', 'SUM')
GROUP BY
    timestamp,
    project_name,
    service_name,
    metric_name,
    metric_type,
    environment;

-- ----------------------------------------------------------------------------
-- Logs Error Summary - Hourly error counts by severity
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS logs_error_summary (
    timestamp DateTime,                         -- Rounded to hour
    project_name String,
    service_name String,
    environment String,
    severity_text String,
    severity_number UInt8,

    -- Counts
    total_logs UInt64,                          -- Total log entries
    error_logs UInt64,                          -- Logs with severity >= ERROR (17+)
    warn_logs UInt64,                           -- Logs with severity WARN (13-16)
    exception_logs UInt64,                      -- Logs flagged as exceptions

    -- Sample of errors (for quick debugging)
    sample_messages Array(String)               -- Up to 10 sample error messages
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_name, service_name, environment, severity_number, timestamp)
TTL timestamp + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;

-- Materialized view to populate logs_error_summary
CREATE MATERIALIZED VIEW IF NOT EXISTS logs_error_summary_mv
TO logs_error_summary
AS SELECT
    toStartOfHour(timestamp) AS timestamp,
    project_name,
    service_name,
    environment,
    severity_text,
    severity_number,

    count() AS total_logs,
    countIf(severity_number >= 17) AS error_logs,
    countIf(severity_number >= 13 AND severity_number < 17) AS warn_logs,
    countIf(is_exception = 1) AS exception_logs,

    -- Sample up to 10 error messages for quick inspection
    groupArray(10)(body) AS sample_messages
FROM logs
GROUP BY
    timestamp,
    project_name,
    service_name,
    environment,
    severity_text,
    severity_number;

-- ----------------------------------------------------------------------------
-- Cross-Signal Correlation View - Join traces with logs by trace_id
-- ----------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS trace_logs_correlation AS
SELECT
    t.trace_id,
    t.span_id,
    t.service_name,
    t.span_name,
    t.timestamp AS trace_timestamp,
    t.status_code,
    t.project_name,
    t.environment,

    l.log_id,
    l.timestamp AS log_timestamp,
    l.severity_text,
    l.severity_number,
    l.body AS log_message,
    l.is_exception,
    l.exception_type,
    l.exception_message

FROM traces AS t
INNER JOIN logs AS l ON t.trace_id = l.trace_id
WHERE l.trace_id != ''
ORDER BY t.timestamp DESC;

-- ============================================================================
-- UTILITY QUERIES - Common patterns for observability
-- ============================================================================

-- Example: Recent error logs with full context
-- SELECT * FROM logs
-- WHERE severity_number >= 17
--   AND timestamp >= now() - INTERVAL 1 HOUR
--   AND project_name = 'my-project'
-- ORDER BY timestamp DESC
-- LIMIT 100;

-- Example: Metric percentiles over time
-- SELECT
--     toStartOfInterval(timestamp, INTERVAL 1 MINUTE) as time_bucket,
--     metric_name,
--     quantile(0.50)(value_double) as p50,
--     quantile(0.95)(value_double) as p95,
--     quantile(0.99)(value_double) as p99
-- FROM metrics
-- WHERE metric_name = 'http.request.duration'
--   AND timestamp >= now() - INTERVAL 1 HOUR
-- GROUP BY time_bucket, metric_name
-- ORDER BY time_bucket;

-- Example: Find traces with associated error logs
-- SELECT * FROM trace_logs_correlation
-- WHERE severity_number >= 17
--   AND environment = 'production'
--   AND trace_timestamp >= now() - INTERVAL 6 HOUR
-- ORDER BY trace_timestamp DESC
-- LIMIT 50;

-- Example: Histogram analysis
-- SELECT
--     metric_name,
--     histogram_count,
--     histogram_sum,
--     histogram_min,
--     histogram_max,
--     arrayZip(histogram_explicit_bounds, histogram_bucket_counts) as buckets
-- FROM metrics
-- WHERE metric_type = 'HISTOGRAM'
--   AND metric_name = 'http.request.size'
--   AND timestamp >= now() - INTERVAL 5 MINUTE
-- ORDER BY timestamp DESC;
