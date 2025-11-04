-- Automagik Telemetry ClickHouse Schema
-- This schema is optimized for OTLP telemetry data storage

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS telemetry;

USE telemetry;

-- Traces table - stores all telemetry events
CREATE TABLE IF NOT EXISTS traces (
    -- Trace identification
    trace_id String,
    span_id String,
    parent_span_id String DEFAULT '',

    -- Timing
    timestamp DateTime DEFAULT now(),
    timestamp_ns UInt64 DEFAULT 0,
    duration_ms UInt32 DEFAULT 0,

    -- Event metadata
    service_name String,
    span_name String,
    span_kind String DEFAULT 'INTERNAL',
    status_code String DEFAULT 'OK',
    status_message String DEFAULT '',

    -- Resource attributes (application info)
    project_name String,
    project_version String,
    environment String DEFAULT 'production',
    hostname String DEFAULT '',

    -- Span attributes (event data)
    attributes Map(String, String) DEFAULT map(),

    -- User/session tracking (privacy-safe)
    user_id String DEFAULT '',
    session_id String DEFAULT '',

    -- System information
    os_type String DEFAULT '',
    os_version String DEFAULT '',
    runtime_name String DEFAULT '',
    runtime_version String DEFAULT '',

    -- Cloud metadata
    cloud_provider String DEFAULT '',
    cloud_region String DEFAULT '',
    cloud_availability_zone String DEFAULT '',

    -- Instrumentation
    instrumentation_library_name String DEFAULT '',
    instrumentation_library_version String DEFAULT '',

    -- Indexing
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_span_name span_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, span_name, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Metrics table - stores OTLP metrics (gauge, counter, histogram)
CREATE TABLE IF NOT EXISTS metrics (
    -- Identification
    metric_id UUID DEFAULT generateUUIDv4(),

    -- Timing
    timestamp DateTime DEFAULT now(),
    timestamp_ns UInt64 DEFAULT 0,

    -- Metric details
    metric_name String,
    metric_type Enum8('GAUGE' = 1, 'SUM' = 2, 'HISTOGRAM' = 3, 'EXPONENTIAL_HISTOGRAM' = 4, 'SUMMARY' = 5),

    -- Values (use appropriate field based on type)
    value_int Int64 DEFAULT 0,
    value_double Float64 DEFAULT 0,

    -- Histogram-specific fields
    histogram_count UInt64 DEFAULT 0,
    histogram_sum Float64 DEFAULT 0,
    histogram_bucket_counts Array(UInt64) DEFAULT [],
    histogram_explicit_bounds Array(Float64) DEFAULT [],

    -- Resource attributes
    project_name String,
    project_version String DEFAULT '',
    service_name String,
    environment String DEFAULT 'production',
    hostname String DEFAULT '',

    -- User/session tracking
    user_id String DEFAULT '',
    session_id String DEFAULT '',

    -- Custom attributes
    attributes Map(String, String) DEFAULT map(),

    -- Cloud information
    cloud_provider String DEFAULT '',
    cloud_region String DEFAULT '',

    -- Indexes for fast queries
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_metric_name metric_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, metric_name, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Logs table - stores structured log entries
CREATE TABLE IF NOT EXISTS logs (
    -- Identification
    log_id UUID DEFAULT generateUUIDv4(),

    -- Trace correlation
    trace_id String DEFAULT '',
    span_id String DEFAULT '',

    -- Timing
    timestamp DateTime DEFAULT now(),
    timestamp_ns UInt64 DEFAULT 0,
    observed_timestamp DateTime DEFAULT now(),

    -- Severity
    severity_text String DEFAULT 'INFO',
    severity_number UInt8 DEFAULT 9,

    -- Log content
    body String,
    body_type Enum8('STRING' = 1, 'JSON' = 2, 'BYTES' = 3) DEFAULT 'STRING',

    -- Resource attributes
    project_name String,
    project_version String DEFAULT '',
    service_name String,
    environment String DEFAULT 'production',
    hostname String DEFAULT '',

    -- User/session tracking
    user_id String DEFAULT '',
    session_id String DEFAULT '',

    -- Custom attributes
    attributes Map(String, String) DEFAULT map(),

    -- Exception details
    exception_type String DEFAULT '',
    exception_message String DEFAULT '',
    exception_stacktrace String DEFAULT '',
    is_exception UInt8 DEFAULT 0,

    -- Source location
    source_file String DEFAULT '',
    source_line UInt32 DEFAULT 0,
    source_function String DEFAULT '',

    -- System information
    os_type String DEFAULT '',
    os_version String DEFAULT '',
    runtime_name String DEFAULT '',
    runtime_version String DEFAULT '',

    -- Indexes for fast queries
    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_severity severity_number TYPE minmax GRANULARITY 1,
    INDEX idx_service_name service_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_project_name project_name TYPE bloom_filter GRANULARITY 1,
    INDEX idx_environment environment TYPE bloom_filter GRANULARITY 1,
    INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 1,
    INDEX idx_body body TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, severity_number, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Metrics hourly aggregation table - aggregated trace metrics (for faster dashboard queries)
CREATE TABLE IF NOT EXISTS metrics_hourly (
    timestamp DateTime,
    project_name String,
    service_name String,
    span_name String,
    environment String,

    -- Counters
    total_count UInt64,
    error_count UInt64,

    -- Latency statistics
    p50_duration_ms Float64,
    p95_duration_ms Float64,
    p99_duration_ms Float64,
    avg_duration_ms Float64,
    max_duration_ms UInt32,
    min_duration_ms UInt32
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_name, service_name, span_name, environment, timestamp)
TTL timestamp + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;

-- Materialized view to automatically populate hourly metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_hourly_mv
TO metrics_hourly
AS SELECT
    toStartOfHour(timestamp) AS timestamp,
    project_name,
    service_name,
    span_name,
    environment,

    count() AS total_count,
    countIf(status_code != 'OK') AS error_count,

    quantile(0.5)(duration_ms) AS p50_duration_ms,
    quantile(0.95)(duration_ms) AS p95_duration_ms,
    quantile(0.99)(duration_ms) AS p99_duration_ms,
    avg(duration_ms) AS avg_duration_ms,
    max(duration_ms) AS max_duration_ms,
    min(duration_ms) AS min_duration_ms
FROM traces
GROUP BY
    timestamp,
    project_name,
    service_name,
    span_name,
    environment;

-- Create user with appropriate permissions
-- Note: This is handled by environment variables in docker-compose
