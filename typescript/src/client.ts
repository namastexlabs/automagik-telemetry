/**
 * Production-ready telemetry client implementation.
 *
 * Based on battle-tested code from automagik-omni and automagik-spark.
 * Uses only Node.js standard library - no external dependencies.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as crypto from "crypto";

import { ClickHouseBackend } from "./backends/clickhouse";
import { OTLPBackend } from "./backends/otlp";
import type { TelemetryConfig } from "./config";
import packageJson from "../package.json";

/**
 * OTLP attribute value types.
 */
interface OTLPAttributeValue {
  stringValue?: string;
  boolValue?: boolean;
  intValue?: number;
  doubleValue?: number;
}

/**
 * OTLP attribute structure.
 */
interface OTLPAttribute {
  key: string;
  value: OTLPAttributeValue;
}

/**
 * System information structure.
 */
interface SystemInfo {
  os: string;
  os_version: string;
  node_version: string;
  architecture: string;
  is_docker: boolean;
  project_name: string;
  project_version: string;
  organization: string;
}

/**
 * Event types for batch processing.
 */
type EventType = "trace" | "metric" | "log";

/**
 * OTLP span structure for traces.
 */
interface OTLPSpan {
  traceId: string;
  spanId: string;
  name: string;
  kind: string;
  startTimeUnixNano: string;
  endTimeUnixNano: string;
  attributes: OTLPAttribute[];
  status: { code: number };
  resource: { attributes: OTLPAttribute[] };
  [key: string]: unknown;
}

/**
 * OTLP resource spans payload structure.
 */
interface OTLPResourceSpans {
  resourceSpans: Array<{
    resource: { attributes: OTLPAttribute[] };
    scopeSpans: Array<{
      scope: { name: string; version: string };
      spans: OTLPSpan[];
    }>;
  }>;
}

/**
 * OTLP metric data point structure.
 */
interface OTLPMetricDataPoint {
  attributes: OTLPAttribute[];
  timeUnixNano: string;
  asDouble?: number;
  count?: number;
  sum?: number;
  bucketCounts?: number[];
  explicitBounds?: number[];
}

/**
 * OTLP metric structure.
 */
interface OTLPMetric {
  name: string;
  unit: string;
  gauge?: { dataPoints: OTLPMetricDataPoint[] };
  sum?: {
    dataPoints: OTLPMetricDataPoint[];
    aggregationTemporality: string;
    isMonotonic: boolean;
  };
  histogram?: {
    dataPoints: OTLPMetricDataPoint[];
    aggregationTemporality: string;
  };
}

/**
 * OTLP resource metrics payload structure.
 */
interface OTLPResourceMetrics {
  resourceMetrics: Array<{
    resource: { attributes: OTLPAttribute[] };
    scopeMetrics: Array<{
      scope: { name: string; version: string };
      metrics: OTLPMetric[];
    }>;
  }>;
}

/**
 * OTLP log record structure.
 */
interface OTLPLogRecord {
  timeUnixNano: string;
  severityNumber: number;
  severityText: string;
  body: { stringValue: string };
  attributes: OTLPAttribute[];
}

/**
 * OTLP resource logs payload structure.
 */
interface OTLPResourceLogs {
  resourceLogs: Array<{
    resource: { attributes: OTLPAttribute[] };
    scopeLogs: Array<{
      scope: { name: string; version: string };
      logRecords: OTLPLogRecord[];
    }>;
  }>;
}

/**
 * Union type for all OTLP payloads.
 */
type OTLPPayload = OTLPResourceSpans | OTLPResourceMetrics | OTLPResourceLogs;

/**
 * Queued event structure for batch processing.
 */
interface QueuedEvent {
  type: EventType;
  payload: OTLPPayload;
  endpoint: string;
}

/**
 * Log severity levels (OTLP format).
 * All severity levels are exported as part of the public API,
 * following the OpenTelemetry specification for log severity numbers.
 */
export enum LogSeverity {
  TRACE = 1,
  DEBUG = 5,
  INFO = 9,
  WARN = 13,
  ERROR = 17,
  FATAL = 21,
}

/**
 * Metric types (OTLP format).
 */
export enum MetricType {
  GAUGE = "gauge",
  COUNTER = "counter",
  HISTOGRAM = "histogram",
}

/**
 * Privacy-first telemetry client for Automagik projects.
 *
 * Features:
 * - Disabled by default - users must explicitly opt-in
 * - Uses only stdlib - no external dependencies
 * - Sends OTLP-compatible traces
 * - Silent failures - never crashes your app
 * - Auto-disables in CI/test environments
 *
 * @example
 * ```typescript
 * import { AutomagikTelemetry, StandardEvents } from 'automagik-telemetry';
 *
 * const telemetry = new AutomagikTelemetry({
 *   projectName: 'omni',
 *   version: '1.0.0'
 * });
 *
 * telemetry.trackEvent(StandardEvents.FEATURE_USED, {
 *   feature_name: 'list_contacts'
 * });
 * ```
 */
export class AutomagikTelemetry {
  private projectName: string;
  private projectVersion: string;
  private organization: string;
  private timeout: number;
  private endpoint: string;
  private metricsEndpoint: string;
  private logsEndpoint: string;
  private userId: string;
  private sessionId: string;
  private enabled: boolean;
  private verbose: boolean;

  // Backend selection
  private backendType: string;
  private clickhouseBackend?: ClickHouseBackend;
  private otlpBackend?: OTLPBackend;

  // Batch processing
  private eventQueue: QueuedEvent[];
  private batchSize: number;
  private flushInterval: number;
  private flushTimer?: NodeJS.Timeout;

  /**
   * Initialize telemetry client.
   *
   * @param config - Configuration options
   */
  constructor(config: TelemetryConfig) {
    this.projectName = config.projectName;
    this.projectVersion = config.version;
    this.organization = config.organization || "namastex";

    // Read timeout from environment variable if not provided via constructor
    let timeoutSeconds: number;
    if (config.timeout !== undefined) {
      timeoutSeconds = config.timeout;
    } else {
      const timeoutEnv = process.env.AUTOMAGIK_TELEMETRY_TIMEOUT;
      if (timeoutEnv !== undefined) {
        const parsed = parseFloat(timeoutEnv);
        timeoutSeconds = isNaN(parsed) ? 5 : parsed;
      } else {
        timeoutSeconds = 5; // Default timeout
      }
    }
    this.timeout = timeoutSeconds * 1000; // Convert to milliseconds

    // Determine backend from config or environment variable
    this.backendType = (
      process.env.AUTOMAGIK_TELEMETRY_BACKEND ||
      config.backend ||
      "otlp"
    ).toLowerCase();

    // Allow custom endpoint for self-hosting
    const baseEndpoint =
      config.endpoint ||
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT ||
      "https://telemetry.namastex.ai";

    // Remove trailing slash and /v1/traces if present
    const cleanBaseEndpoint = baseEndpoint
      .replace(/\/v1\/traces\/?$/, "")
      .replace(/\/$/, "");

    this.endpoint = `${cleanBaseEndpoint}/v1/traces`;
    this.metricsEndpoint =
      config.metricsEndpoint ||
      process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT ||
      `${cleanBaseEndpoint}/v1/metrics`;
    this.logsEndpoint =
      config.logsEndpoint ||
      process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT ||
      `${cleanBaseEndpoint}/v1/logs`;

    // User & session IDs
    this.userId = this.getOrCreateUserId();
    this.sessionId = crypto.randomUUID();

    // Enable/disable check
    this.enabled = this.isTelemetryEnabled();

    // Verbose mode (print events to console)
    this.verbose =
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE?.toLowerCase() === "true";

    // Initialize ClickHouse backend if selected
    if (this.backendType === "clickhouse") {
      const clickhouseEndpoint =
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT ||
        config.clickhouseEndpoint ||
        "http://localhost:8123";
      const clickhouseDatabase =
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE ||
        config.clickhouseDatabase ||
        "telemetry";
      const clickhouseTable =
        config.clickhouseTable ||
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE ||
        "traces";
      const clickhouseMetricsTable =
        config.clickhouseMetricsTable ||
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_METRICS_TABLE ||
        "metrics";
      const clickhouseLogsTable =
        config.clickhouseLogsTable ||
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_LOGS_TABLE ||
        "logs";
      const clickhouseUsername =
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME ||
        config.clickhouseUsername ||
        "default";
      const clickhousePassword =
        process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD ||
        config.clickhousePassword ||
        "";

      this.clickhouseBackend = new ClickHouseBackend({
        endpoint: clickhouseEndpoint,
        database: clickhouseDatabase,
        tracesTable: clickhouseTable,
        metricsTable: clickhouseMetricsTable,
        logsTable: clickhouseLogsTable,
        username: clickhouseUsername,
        password: clickhousePassword,
        timeout: this.timeout,
        batchSize: config.batchSize || 100,
        compressionEnabled: config.compressionEnabled !== false,
        maxRetries: config.maxRetries || 3,
        verbose: this.verbose,
      });
    } else {
      // Initialize OTLP backend (default)
      this.otlpBackend = new OTLPBackend({
        endpoint: this.endpoint,
        timeout: this.timeout,
        maxRetries: config.maxRetries || 3,
        retryBackoffBase: config.retryBackoffBase || 1000,
        compressionEnabled: config.compressionEnabled !== false,
        compressionThreshold: config.compressionThreshold || 1024,
        verbose: this.verbose,
      });
    }

    // Batch processing configuration
    this.eventQueue = [];
    this.batchSize = config.batchSize || 100;
    this.flushInterval = config.flushInterval || 5000;

    // Start periodic flush timer
    if (this.enabled) {
      this.startFlushTimer();
    }
  }

  /**
   * Generate or retrieve anonymous user identifier.
   *
   * @returns Persistent anonymous user ID
   */
  private getOrCreateUserId(): string {
    const userIdFile = path.join(os.homedir(), ".automagik", "user_id");

    // Try to read existing ID
    if (fs.existsSync(userIdFile)) {
      try {
        return fs.readFileSync(userIdFile, "utf-8").trim();
      } catch (error) {
        // Continue to create new ID if read fails
      }
    }

    // Create new anonymous UUID
    const userId = crypto.randomUUID();
    try {
      const dir = path.dirname(userIdFile);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(userIdFile, userId, "utf-8");
    } catch (error) {
      // Continue with in-memory ID if file creation fails
    }

    return userId;
  }

  /**
   * Check if telemetry is enabled based on various opt-out mechanisms.
   *
   * @returns True if telemetry should be enabled
   */
  private isTelemetryEnabled(): boolean {
    // Explicit enable/disable via environment variable
    const envVar = process.env.AUTOMAGIK_TELEMETRY_ENABLED;
    if (envVar !== undefined) {
      return ["true", "1", "yes", "on"].includes(envVar.toLowerCase());
    }

    // Check for opt-out file
    const optOutFile = path.join(os.homedir(), ".automagik-no-telemetry");
    if (fs.existsSync(optOutFile)) {
      return false;
    }

    // Auto-disable in CI/testing environments
    const ciEnvironments = [
      "CI",
      "GITHUB_ACTIONS",
      "TRAVIS",
      "JENKINS",
      "GITLAB_CI",
      "CIRCLECI",
    ];
    if (ciEnvironments.some((varName) => process.env[varName])) {
      return false;
    }

    // Check for development indicators
    const environment = process.env.ENVIRONMENT;
    if (
      environment &&
      ["development", "dev", "test", "testing"].includes(environment)
    ) {
      return false;
    }

    // Default: disabled (opt-in only)
    return false;
  }

  /**
   * Collect basic system information (no PII).
   *
   * @returns System information object
   */
  private getSystemInfo(): SystemInfo {
    return {
      os: os.platform(),
      os_version: os.release(),
      node_version: process.version,
      architecture: os.arch(),
      is_docker: fs.existsSync("/.dockerenv"),
      project_name: this.projectName,
      project_version: this.projectVersion,
      organization: this.organization,
    };
  }

  /**
   * Convert data to OTLP attribute format with type safety.
   *
   * @param data - Event data to convert
   * @returns OTLP-formatted attributes
   */
  private createAttributes(data: Record<string, unknown>): OTLPAttribute[] {
    const attributes: OTLPAttribute[] = [];

    // Add system information
    const systemInfo = this.getSystemInfo();
    for (const [key, value] of Object.entries(systemInfo)) {
      if (typeof value === "boolean") {
        attributes.push({ key: `system.${key}`, value: { boolValue: value } });
      } else if (typeof value === "number") {
        attributes.push({
          key: `system.${key}`,
          value: { doubleValue: value },
        });
      } else {
        attributes.push({
          key: `system.${key}`,
          value: { stringValue: String(value) },
        });
      }
    }

    // Add event data
    for (const [key, value] of Object.entries(data)) {
      if (typeof value === "boolean") {
        attributes.push({ key, value: { boolValue: value } });
      } else if (typeof value === "number") {
        attributes.push({ key, value: { doubleValue: value } });
      } else {
        // Truncate long strings to prevent payload bloat
        const sanitizedValue = String(value).slice(0, 500);
        attributes.push({ key, value: { stringValue: sanitizedValue } });
      }
    }

    return attributes;
  }

  /**
   * Start periodic flush timer.
   */
  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flush().catch(() => {
        // Silent failure
      });
    }, this.flushInterval);

    // Allow process to exit even with this timer running (important for tests)
    this.flushTimer.unref();
  }

  /**
   * Stop periodic flush timer.
   */
  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = undefined;
    }
  }


  /**
   * Add event to queue and flush if batch size reached.
   *
   * @param event - Event to queue
   */
  private async queueEvent(event: QueuedEvent): Promise<void> {
    this.eventQueue.push(event);

    // Flush if batch size reached
    if (this.eventQueue.length >= this.batchSize) {
      await this.flush();
    }
  }

  /**
   * Get SDK version from package.json (single source of truth).
   */
  private getSDKVersion(): string {
    return packageJson.version;
  }

  /**
   * Send telemetry event to the endpoint (internal method).
   *
   * @param eventType - Event type name
   * @param data - Event data
   */
  private async sendEvent(
    eventType: string,
    data: Record<string, unknown>,
  ): Promise<void> {
    if (!this.enabled) {
      return; // Silent no-op when disabled
    }

    try {
      // Generate trace and span IDs (32 and 16 hex chars respectively)
      const traceId =
        crypto.randomUUID().replace(/-/g, "") +
        crypto.randomUUID().replace(/-/g, "");
      const spanId = crypto.randomUUID().replace(/-/g, "").slice(0, 16);

      // Get current time in nanoseconds
      const timeNano = BigInt(Date.now()) * BigInt(1_000_000);

      // Resource attributes
      const resourceAttributes = [
        {
          key: "service.name",
          value: { stringValue: this.projectName },
        },
        {
          key: "service.version",
          value: { stringValue: this.projectVersion },
        },
        {
          key: "project.name", // ClickHouse backend uses this
          value: { stringValue: this.projectName },
        },
        {
          key: "project.version", // ClickHouse backend uses this
          value: { stringValue: this.projectVersion },
        },
        {
          key: "service.organization",
          value: { stringValue: this.organization },
        },
        {
          key: "user.id",
          value: { stringValue: this.userId },
        },
        {
          key: "session.id",
          value: { stringValue: this.sessionId },
        },
        {
          key: "telemetry.sdk.name",
          value: { stringValue: "automagik-telemetry" },
        },
        {
          key: "telemetry.sdk.version",
          value: { stringValue: this.getSDKVersion() },
        },
      ];

      // Create OTLP-compatible span
      const span: OTLPSpan = {
        traceId: traceId,
        spanId: spanId,
        name: eventType,
        kind: "SPAN_KIND_INTERNAL",
        startTimeUnixNano: timeNano.toString(),
        endTimeUnixNano: timeNano.toString(),
        attributes: this.createAttributes(data),
        status: { code: 1 }, // STATUS_CODE_OK = 1
        resource: { attributes: resourceAttributes },
      };

      // Verbose mode: print event to console
      if (this.verbose) {
        console.log(`\n[Telemetry] Queuing trace event: ${eventType}`);
        console.log(`  Project: ${this.projectName}`);
        console.log(`  Backend: ${this.backendType}`);
        console.log(`  Data: ${JSON.stringify(data, null, 2)}\n`);
      }

      // Route to appropriate backend
      if (this.backendType === "clickhouse" && this.clickhouseBackend) {
        // Send directly to ClickHouse backend
        this.clickhouseBackend.sendTrace(span);
      } else {
        // Use OTLP backend (default)
        const payload = {
          resourceSpans: [
            {
              resource: { attributes: resourceAttributes },
              scopeSpans: [
                {
                  scope: {
                    name: `${this.projectName}.telemetry`,
                    version: this.projectVersion,
                  },
                  spans: [span],
                },
              ],
            },
          ],
        };

        // Queue event for batch processing
        await this.queueEvent({
          type: "trace",
          payload,
          endpoint: this.endpoint,
        });
      }
    } catch (error) {
      // Log any errors in debug mode only
      if (this.verbose) {
        console.debug(`Telemetry event error:`, error);
      }
      // Silent failure - never crash the application
    }
  }

  /**
   * Send OTLP metric (internal method).
   *
   * @param metricName - Metric name
   * @param value - Metric value
   * @param metricType - Metric type (gauge, counter, histogram)
   * @param data - Additional metric attributes
   */
  private async sendMetric(
    metricName: string,
    value: number,
    metricType: MetricType,
    data: Record<string, unknown>,
  ): Promise<void> {
    if (!this.enabled) {
      return; // Silent no-op when disabled
    }

    try {
      // Get current time in nanoseconds
      const timeNano = BigInt(Date.now()) * BigInt(1_000_000);

      // Create OTLP-compatible metric payload
      const dataPoint: OTLPMetricDataPoint = {
        attributes: this.createAttributes(data),
        timeUnixNano: timeNano.toString(),
      };

      // Add value based on metric type
      if (metricType === MetricType.GAUGE) {
        dataPoint.asDouble = value;
      } else if (metricType === MetricType.COUNTER) {
        dataPoint.asDouble = value;
      } else if (metricType === MetricType.HISTOGRAM) {
        // Histogram requires count, sum, and bucket counts
        dataPoint.count = 1;
        dataPoint.sum = value;
        dataPoint.bucketCounts = [1];
        dataPoint.explicitBounds = [];
      }

      const metricData: OTLPMetric = {
        name: metricName,
        unit: (typeof data.unit === "string" ? data.unit : "") || "",
      };

      // Set metric type-specific structure
      if (metricType === MetricType.GAUGE) {
        metricData.gauge = { dataPoints: [dataPoint] };
      } else if (metricType === MetricType.COUNTER) {
        metricData.sum = {
          dataPoints: [dataPoint],
          aggregationTemporality: "AGGREGATION_TEMPORALITY_CUMULATIVE",
          isMonotonic: true,
        };
      } else if (metricType === MetricType.HISTOGRAM) {
        metricData.histogram = {
          dataPoints: [dataPoint],
          aggregationTemporality: "AGGREGATION_TEMPORALITY_CUMULATIVE",
        };
      }

      const payload = {
        resourceMetrics: [
          {
            resource: {
              attributes: [
                {
                  key: "service.name",
                  value: { stringValue: this.projectName },
                },
                {
                  key: "service.version",
                  value: { stringValue: this.projectVersion },
                },
                {
                  key: "project.name", // ClickHouse backend uses this
                  value: { stringValue: this.projectName },
                },
                {
                  key: "project.version", // ClickHouse backend uses this
                  value: { stringValue: this.projectVersion },
                },
                {
                  key: "service.organization",
                  value: { stringValue: this.organization },
                },
                {
                  key: "user.id",
                  value: { stringValue: this.userId },
                },
                {
                  key: "session.id",
                  value: { stringValue: this.sessionId },
                },
                {
                  key: "telemetry.sdk.name",
                  value: { stringValue: "automagik-telemetry" },
                },
                {
                  key: "telemetry.sdk.version",
                  value: { stringValue: this.getSDKVersion() },
                },
              ],
            },
            scopeMetrics: [
              {
                scope: {
                  name: `${this.projectName}.telemetry`,
                  version: this.projectVersion,
                },
                metrics: [metricData],
              },
            ],
          },
        ],
      };

      // Verbose mode: print metric to console
      if (this.verbose) {
        console.log(`\n[Telemetry] Queuing metric: ${metricName}`);
        console.log(`  Type: ${metricType}`);
        console.log(`  Value: ${value}`);
        console.log(`  Endpoint: ${this.metricsEndpoint}\n`);
      }

      // Queue metric for batch processing
      await this.queueEvent({
        type: "metric",
        payload,
        endpoint: this.metricsEndpoint,
      });
    } catch (error) {
      // Log any errors in debug mode only
      if (this.verbose) {
        console.debug(`Telemetry metric error:`, error);
      }
      // Silent failure - never crash the application
    }
  }

  /**
   * Send OTLP log (internal method).
   *
   * @param message - Log message
   * @param severity - Log severity level
   * @param data - Additional log attributes
   */
  private async sendLog(
    message: string,
    severity: LogSeverity,
    data: Record<string, unknown>,
  ): Promise<void> {
    if (!this.enabled) {
      return; // Silent no-op when disabled
    }

    try {
      // Get current time in nanoseconds
      const timeNano = BigInt(Date.now()) * BigInt(1_000_000);

      // Create OTLP-compatible log payload
      const payload = {
        resourceLogs: [
          {
            resource: {
              attributes: [
                {
                  key: "service.name",
                  value: { stringValue: this.projectName },
                },
                {
                  key: "service.version",
                  value: { stringValue: this.projectVersion },
                },
                {
                  key: "project.name", // ClickHouse backend uses this
                  value: { stringValue: this.projectName },
                },
                {
                  key: "project.version", // ClickHouse backend uses this
                  value: { stringValue: this.projectVersion },
                },
                {
                  key: "service.organization",
                  value: { stringValue: this.organization },
                },
                {
                  key: "user.id",
                  value: { stringValue: this.userId },
                },
                {
                  key: "session.id",
                  value: { stringValue: this.sessionId },
                },
                {
                  key: "telemetry.sdk.name",
                  value: { stringValue: "automagik-telemetry" },
                },
                {
                  key: "telemetry.sdk.version",
                  value: { stringValue: this.getSDKVersion() },
                },
              ],
            },
            scopeLogs: [
              {
                scope: {
                  name: `${this.projectName}.telemetry`,
                  version: this.projectVersion,
                },
                logRecords: [
                  {
                    timeUnixNano: timeNano.toString(),
                    severityNumber: severity,
                    severityText: LogSeverity[severity],
                    body: { stringValue: message },
                    attributes: this.createAttributes(data),
                  },
                ],
              },
            ],
          },
        ],
      };

      // Verbose mode: print log to console
      if (this.verbose) {
        console.log(`\n[Telemetry] Queuing log: ${message}`);
        console.log(`  Severity: ${LogSeverity[severity]}`);
        console.log(`  Endpoint: ${this.logsEndpoint}\n`);
      }

      // Queue log for batch processing
      await this.queueEvent({
        type: "log",
        payload,
        endpoint: this.logsEndpoint,
      });
    } catch (error) {
      // Log any errors in debug mode only
      if (this.verbose) {
        console.debug(`Telemetry log error:`, error);
      }
      // Silent failure - never crash the application
    }
  }

  // === Public API ===

  /**
   * Track a telemetry event.
   *
   * @param eventName - Event name (use StandardEvents constants)
   * @param attributes - Event attributes (automatically sanitized for privacy)
   *
   * @example
   * ```typescript
   * telemetry.trackEvent(StandardEvents.FEATURE_USED, {
   *   feature_name: 'list_contacts',
   *   feature_category: 'api_endpoint'
   * });
   * ```
   */
  trackEvent(eventName: string, attributes?: Record<string, unknown>): void {
    this.sendEvent(eventName, attributes || {}).catch(() => {
      // Silent failure
    });
  }

  /**
   * Track an error with context.
   *
   * @param error - The error that occurred
   * @param context - Additional context about the error
   *
   * @example
   * ```typescript
   * try {
   *   riskyOperation();
   * } catch (error) {
   *   telemetry.trackError(error as Error, {
   *     error_code: 'OMNI-1001',
   *     operation: 'message_send'
   *   });
   * }
   * ```
   */
  trackError(error: Error, context?: Record<string, unknown>): void {
    const data = {
      error_type: error.name,
      error_message: error.message.slice(0, 500), // Truncate long errors
      ...(context || {}),
    };
    this.sendEvent("automagik.error", data).catch(() => {
      // Silent failure
    });
  }

  /**
   * Track a numeric metric using OTLP metrics format.
   *
   * @param metricName - Metric name
   * @param value - Metric value
   * @param metricType - Metric type (default: GAUGE)
   * @param attributes - Metric attributes
   *
   * @example
   * ```typescript
   * telemetry.trackMetric('api.request.latency', 123, MetricType.HISTOGRAM, {
   *   operation_type: 'api_request',
   *   unit: 'ms'
   * });
   * ```
   */
  trackMetric(
    metricName: string,
    value: number,
    metricType: MetricType = MetricType.GAUGE,
    attributes?: Record<string, unknown>,
  ): void {
    this.sendMetric(metricName, value, metricType, attributes || {}).catch(
      () => {
        // Silent failure
      },
    );
  }

  /**
   * Track a log message using OTLP logs format.
   *
   * @param message - Log message
   * @param severity - Log severity level (default: INFO)
   * @param attributes - Log attributes
   *
   * @example
   * ```typescript
   * telemetry.trackLog('User action completed', LogSeverity.INFO, {
   *   action: 'file_upload',
   *   file_size: 1024
   * });
   * ```
   */
  trackLog(
    message: string,
    severity: LogSeverity = LogSeverity.INFO,
    attributes?: Record<string, unknown>,
  ): void {
    this.sendLog(message, severity, attributes || {}).catch(() => {
      // Silent failure
    });
  }

  /**
   * Manually flush all queued events.
   * This sends all pending events immediately.
   *
   * @returns Promise that resolves when flush is complete
   *
   * @example
   * ```typescript
   * await telemetry.flush();
   * ```
   */
  async flush(): Promise<void> {
    if (!this.enabled) {
      return;
    }

    // Flush ClickHouse backend if active
    if (this.backendType === "clickhouse" && this.clickhouseBackend) {
      try {
        await this.clickhouseBackend.flush();
      } catch (error) {
        if (this.verbose) {
          console.debug("ClickHouse flush error:", error);
        }
      }
    }

    // Flush OTLP event queue
    if (this.eventQueue.length === 0) {
      return;
    }

    // Get current queue and clear it
    const eventsToSend = [...this.eventQueue];
    this.eventQueue = [];

    if (this.verbose) {
      console.log(
        `\n[Telemetry] Flushing ${eventsToSend.length} queued events\n`,
      );
    }

    // Group events by type and endpoint for efficient batch sending
    const eventsByEndpoint = new Map<string, QueuedEvent[]>();
    for (const event of eventsToSend) {
      const existing = eventsByEndpoint.get(event.endpoint) || [];
      existing.push(event);
      eventsByEndpoint.set(event.endpoint, existing);
    }

    // Send all events with retry logic using OTLP backend
    if (this.otlpBackend) {
      const sendPromises: Promise<boolean>[] = [];
      for (const [endpoint, events] of eventsByEndpoint.entries()) {
        for (const event of events) {
          // Route to appropriate OTLP backend method based on event type
          if (event.type === "trace") {
            sendPromises.push(this.otlpBackend.sendTrace(event.payload));
          } else if (event.type === "metric") {
            sendPromises.push(this.otlpBackend.sendMetric(event.payload, endpoint));
          } else if (event.type === "log") {
            sendPromises.push(this.otlpBackend.sendLog(event.payload, endpoint));
          }
        }
      }

      try {
        await Promise.all(sendPromises);
      } catch (error) {
        // Silent failure - errors already logged in OTLP backend
      }
    }
  }

  // === Control Methods ===

  /**
   * Enable telemetry and save preference.
   * Removes the opt-out file if it exists.
   */
  enable(): void {
    this.enabled = true;
    // Remove opt-out file if it exists
    const optOutFile = path.join(os.homedir(), ".automagik-no-telemetry");
    if (fs.existsSync(optOutFile)) {
      try {
        fs.unlinkSync(optOutFile);
      } catch (error) {
        // Silent failure
      }
    }
    // Start flush timer
    this.startFlushTimer();
  }

  /**
   * Disable telemetry permanently.
   * Creates an opt-out file in the user's home directory.
   * Flushes any pending events before disabling.
   */
  async disable(): Promise<void> {
    // Flush pending events before disabling
    await this.flush();

    this.enabled = false;

    // Stop flush timer
    this.stopFlushTimer();

    // Create opt-out file
    try {
      const optOutFile = path.join(os.homedir(), ".automagik-no-telemetry");
      fs.writeFileSync(optOutFile, "", "utf-8");
    } catch (error) {
      // Silent failure
    }
  }

  /**
   * Check if telemetry is enabled.
   *
   * @returns True if telemetry is currently enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Get telemetry status information.
   *
   * @returns Status object with configuration and state
   */
  getStatus(): Record<string, unknown> {
    const optOutFile = path.join(os.homedir(), ".automagik-no-telemetry");
    return {
      enabled: this.enabled,
      user_id: this.userId,
      session_id: this.sessionId,
      project_name: this.projectName,
      project_version: this.projectVersion,
      endpoint: this.endpoint,
      metricsEndpoint: this.metricsEndpoint,
      logsEndpoint: this.logsEndpoint,
      opt_out_file_exists: fs.existsSync(optOutFile),
      env_var: process.env.AUTOMAGIK_TELEMETRY_ENABLED,
      verbose: this.verbose,
    };
  }
}
