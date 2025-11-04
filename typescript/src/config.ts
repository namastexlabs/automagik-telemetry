/**
 * Configuration management for Automagik Telemetry SDK.
 *
 * Provides centralized configuration with environment variable support,
 * sensible defaults, and validation.
 */

/**
 * Complete telemetry configuration interface.
 */
export interface TelemetryConfig {
  /** Name of the Automagik project (omni, hive, forge, etc.) */
  projectName: string;
  /** Version of the project */
  version: string;
  /** Backend to use ("otlp" or "clickhouse", default: "otlp") */
  backend?: string;
  /** Custom telemetry endpoint (defaults to telemetry.namastex.ai) */
  endpoint?: string;
  /** Organization name (default: namastex) */
  organization?: string;
  /** HTTP timeout in seconds for requests (both SDKs accept seconds; internally converted to milliseconds) (default: 5 seconds) */
  timeout?: number;
  /** Whether telemetry is enabled (opt-in only) */
  enabled?: boolean;
  /** Enable verbose logging to console */
  verbose?: boolean;
  /** Batch size for event queue (default: 100) */
  batchSize?: number;
  /** Flush interval in milliseconds - TypeScript uses milliseconds (Python uses seconds) (default: 5000ms = 5 seconds) */
  flushInterval?: number;
  /** Enable payload compression (default: true) */
  compressionEnabled?: boolean;
  /** Compression threshold in bytes (default: 1024) */
  compressionThreshold?: number;
  /** Maximum retry attempts (default: 3) */
  maxRetries?: number;
  /** Retry backoff base in milliseconds - TypeScript uses milliseconds (Python uses seconds) (default: 1000ms = 1 second) */
  retryBackoffBase?: number;
  /** Custom metrics endpoint (defaults to /v1/metrics) */
  metricsEndpoint?: string;
  /** Custom logs endpoint (defaults to /v1/logs) */
  logsEndpoint?: string;
  /** ClickHouse HTTP endpoint (default: http://localhost:8123) */
  clickhouseEndpoint?: string;
  /** ClickHouse database name (default: telemetry) */
  clickhouseDatabase?: string;
  /** ClickHouse traces table name (default: traces) */
  clickhouseTable?: string;
  /** ClickHouse metrics table name (default: metrics) */
  clickhouseMetricsTable?: string;
  /** ClickHouse logs table name (default: logs) */
  clickhouseLogsTable?: string;
  /** ClickHouse username (default: default) */
  clickhouseUsername?: string;
  /** ClickHouse password (default: "") */
  clickhousePassword?: string;
}

/**
 * Internal validated configuration with all defaults applied.
 */
export interface ValidatedConfig {
  projectName: string;
  version: string;
  endpoint: string;
  organization: string;
  timeout: number;
  enabled: boolean;
  verbose: boolean;
}

/**
 * Default configuration values.
 */
export const DEFAULT_CONFIG = {
  endpoint: "https://telemetry.namastex.ai/v1/traces",
  organization: "namastex",
  timeout: 5, // seconds (converted to milliseconds internally)
  enabled: false, // Disabled by default - opt-in only
  verbose: false,
} as const;

/**
 * Environment variables used for configuration.
 */
export const ENV_VARS = {
  ENABLED: "AUTOMAGIK_TELEMETRY_ENABLED",
  ENDPOINT: "AUTOMAGIK_TELEMETRY_ENDPOINT",
  VERBOSE: "AUTOMAGIK_TELEMETRY_VERBOSE",
  TIMEOUT: "AUTOMAGIK_TELEMETRY_TIMEOUT",
} as const;

/**
 * Load configuration from environment variables.
 *
 * Supported environment variables:
 * - AUTOMAGIK_TELEMETRY_ENABLED: Enable/disable telemetry (true/false/1/0/yes/no/on/off)
 * - AUTOMAGIK_TELEMETRY_ENDPOINT: Custom telemetry endpoint URL
 * - AUTOMAGIK_TELEMETRY_VERBOSE: Enable verbose logging (true/false/1/0/yes/no/on/off)
 * - AUTOMAGIK_TELEMETRY_TIMEOUT: HTTP timeout in seconds
 *
 * @returns Partial configuration from environment variables
 */
export function loadConfigFromEnv(): Partial<TelemetryConfig> {
  const config: Partial<TelemetryConfig> = {};

  // Parse enabled flag
  const enabledEnv = process.env[ENV_VARS.ENABLED];
  if (enabledEnv !== undefined) {
    config.enabled = parseBooleanEnv(enabledEnv);
  }

  // Parse endpoint
  const endpointEnv = process.env[ENV_VARS.ENDPOINT];
  if (endpointEnv) {
    config.endpoint = endpointEnv;
  }

  // Parse verbose flag
  const verboseEnv = process.env[ENV_VARS.VERBOSE];
  if (verboseEnv !== undefined) {
    config.verbose = parseBooleanEnv(verboseEnv);
  }

  // Parse timeout
  const timeoutEnv = process.env[ENV_VARS.TIMEOUT];
  if (timeoutEnv) {
    const timeout = parseInt(timeoutEnv, 10);
    if (!isNaN(timeout) && timeout > 0) {
      config.timeout = timeout;
    }
  }

  return config;
}

/**
 * Parse boolean value from environment variable string.
 *
 * @param value - Environment variable value
 * @returns Boolean value
 */
function parseBooleanEnv(value: string): boolean {
  const normalized = value.toLowerCase().trim();
  return ["true", "1", "yes", "on"].includes(normalized);
}

/**
 * Merge user configuration with defaults and environment variables.
 *
 * Priority (highest to lowest):
 * 1. User-provided config
 * 2. Environment variables
 * 3. Default values
 *
 * @param userConfig - User-provided configuration
 * @returns Validated configuration with all defaults applied
 */
export function mergeConfig(userConfig: TelemetryConfig): ValidatedConfig {
  const envConfig = loadConfigFromEnv();

  return {
    projectName: userConfig.projectName,
    version: userConfig.version,
    endpoint:
      userConfig.endpoint ?? envConfig.endpoint ?? DEFAULT_CONFIG.endpoint,
    organization: userConfig.organization ?? DEFAULT_CONFIG.organization,
    timeout: userConfig.timeout ?? envConfig.timeout ?? DEFAULT_CONFIG.timeout,
    enabled: userConfig.enabled ?? envConfig.enabled ?? DEFAULT_CONFIG.enabled,
    verbose: userConfig.verbose ?? envConfig.verbose ?? DEFAULT_CONFIG.verbose,
  };
}

/**
 * Validate configuration values and throw helpful errors.
 *
 * @param config - Configuration to validate
 * @throws Error if configuration is invalid
 */
export function validateConfig(config: TelemetryConfig): void {
  // Validate required fields
  if (!config.projectName || config.projectName.trim().length === 0) {
    throw new Error(
      "TelemetryConfig: projectName is required and cannot be empty",
    );
  }

  if (!config.version || config.version.trim().length === 0) {
    throw new Error("TelemetryConfig: version is required and cannot be empty");
  }

  // Validate endpoint URL format if provided
  if (config.endpoint !== undefined) {
    try {
      const url = new URL(config.endpoint);
      if (!["http:", "https:"].includes(url.protocol)) {
        throw new Error(
          "TelemetryConfig: endpoint must use http or https protocol",
        );
      }
    } catch (error: unknown) {
      // Handle URL parsing errors
      // Check both instanceof TypeError and error name for better compatibility
      if (
        error instanceof TypeError ||
        (error as Error)?.name === "TypeError"
      ) {
        throw new Error(
          `TelemetryConfig: endpoint must be a valid URL (got: ${config.endpoint})`,
        );
      }
      // Re-throw protocol errors and unknown errors
      throw error;
    }
  }

  // Validate timeout if provided (in seconds)
  if (config.timeout !== undefined) {
    if (typeof config.timeout !== "number" || config.timeout <= 0) {
      throw new Error(
        `TelemetryConfig: timeout must be a positive number in seconds (got: ${config.timeout})`,
      );
    }
    if (config.timeout > 60) {
      throw new Error(
        `TelemetryConfig: timeout should not exceed 60 seconds (got: ${config.timeout})`,
      );
    }
  }

  // Validate organization if provided
  if (
    config.organization !== undefined &&
    config.organization.trim().length === 0
  ) {
    throw new Error(
      "TelemetryConfig: organization cannot be empty if provided",
    );
  }
}

/**
 * Create and validate a complete configuration.
 *
 * This is the main entry point for configuration creation.
 *
 * @param userConfig - User-provided configuration
 * @returns Validated configuration ready for use
 * @throws Error if configuration is invalid
 */
export function createConfig(userConfig: TelemetryConfig): ValidatedConfig {
  validateConfig(userConfig);
  return mergeConfig(userConfig);
}
