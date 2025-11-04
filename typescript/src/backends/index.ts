/**
 * Telemetry backends for different storage systems.
 *
 * Available backends:
 * - otlp: Standard OpenTelemetry Protocol (default)
 * - clickhouse: Direct ClickHouse insertion via HTTP API
 */

export { TelemetryBackend } from "./base";
export { ClickHouseBackend, ClickHouseBackendConfig } from "./clickhouse";
export { OTLPBackend, OTLPBackendConfig } from "./otlp";
