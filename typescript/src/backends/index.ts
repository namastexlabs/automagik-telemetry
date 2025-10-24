/**
 * Telemetry backends for different storage systems.
 *
 * Available backends:
 * - otlp: Standard OpenTelemetry Protocol (default)
 * - clickhouse: Direct ClickHouse insertion via HTTP API
 */

export { ClickHouseBackend, ClickHouseBackendConfig } from "./clickhouse";
