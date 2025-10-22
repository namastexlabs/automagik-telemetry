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
    timestamp DateTime64(3) DEFAULT now64(),
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

-- Metrics table - aggregated metrics (optional, for faster queries)
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
