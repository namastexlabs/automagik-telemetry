/**
 * Direct ClickHouse backend for telemetry data.
 *
 * Bypasses the OpenTelemetry Collector and writes directly to ClickHouse HTTP API.
 * Uses only Node.js standard library - no external dependencies.
 */

import * as http from "http";
import * as https from "https";
import * as url from "url";
import * as zlib from "zlib";
import * as crypto from "crypto";

/**
 * Configuration options for ClickHouse backend.
 * Exported as part of the public API for users who want to use ClickHouseBackend directly.
 */
export interface ClickHouseBackendConfig {
  /** ClickHouse HTTP endpoint (e.g. http://localhost:8123) */
  endpoint?: string;
  /** Database name (default: telemetry) */
  database?: string;
  /** Traces table name (default: traces) */
  tracesTable?: string;
  /** Metrics table name (default: metrics) */
  metricsTable?: string;
  /** Logs table name (default: logs) */
  logsTable?: string;
  /** ClickHouse username (default: default) */
  username?: string;
  /** ClickHouse password */
  password?: string;
  /** HTTP timeout in milliseconds (default: 5000) */
  timeout?: number;
  /** Number of rows to batch before inserting (default: 100) */
  batchSize?: number;
  /** Enable gzip compression (default: true) */
  compressionEnabled?: boolean;
  /** Maximum retry attempts (default: 3) */
  maxRetries?: number;
  /** Enable verbose console logging for debugging (default: false) */
  verbose?: boolean;
}

/**
 * ClickHouse trace row structure matching our schema.
 */
interface ClickHouseTraceRow {
  trace_id: string;
  span_id: string;
  parent_span_id: string;
  timestamp: string;
  timestamp_ns: number;
  duration_ms: number;
  service_name: string;
  span_name: string;
  span_kind: string;
  status_code: string;
  status_message: string;
  project_name: string;
  project_version: string;
  environment: string;
  hostname: string;
  attributes: Record<string, string>;
  user_id: string;
  session_id: string;
  os_type: string;
  os_version: string;
  runtime_name: string;
  runtime_version: string;
  cloud_provider: string;
  cloud_region: string;
  cloud_availability_zone: string;
  instrumentation_library_name: string;
  instrumentation_library_version: string;
}

/**
 * ClickHouse metric row structure matching our schema.
 */
interface ClickHouseMetricRow {
  metric_id: string;
  metric_name: string;
  metric_type: string;
  metric_unit: string;
  metric_description: string;
  timestamp: string;
  timestamp_ns: number;
  time_window_start: string;
  time_window_end: string;
  value_int: number;
  value_double: number;
  is_monotonic: number;
  aggregation_temporality: string;
  // Histogram fields
  histogram_count: number;
  histogram_sum: number;
  histogram_min: number;
  histogram_max: number;
  histogram_bucket_counts: number[];
  histogram_explicit_bounds: number[];
  // Summary fields
  summary_count: number;
  summary_sum: number;
  quantile_values: Record<string, number>;
  // Service and project info
  project_name: string;
  project_version: string;
  service_name: string;
  service_namespace: string;
  service_instance_id: string;
  environment: string;
  hostname: string;
  // Attributes and user context
  attributes: Record<string, string>;
  user_id: string;
  session_id: string;
  // System info
  os_type: string;
  os_version: string;
  runtime_name: string;
  runtime_version: string;
  // Cloud metadata
  cloud_provider: string;
  cloud_region: string;
  cloud_availability_zone: string;
  // Instrumentation
  instrumentation_library_name: string;
  instrumentation_library_version: string;
  schema_url: string;
}

/**
 * ClickHouse log row structure matching our schema.
 */
interface ClickHouseLogRow {
  log_id: string;
  trace_id: string;
  span_id: string;
  timestamp: string;
  timestamp_ns: number;
  observed_timestamp: string;
  observed_timestamp_ns: number;
  severity_text: string;
  severity_number: number;
  body: string;
  body_type: string;
  // Service and project info
  project_name: string;
  project_version: string;
  service_name: string;
  service_namespace: string;
  service_instance_id: string;
  environment: string;
  hostname: string;
  // Attributes and user context
  attributes: Record<string, string>;
  user_id: string;
  session_id: string;
  // System info
  os_type: string;
  os_version: string;
  runtime_name: string;
  runtime_version: string;
  // Cloud metadata
  cloud_provider: string;
  cloud_region: string;
  cloud_availability_zone: string;
  // Instrumentation
  instrumentation_library_name: string;
  instrumentation_library_version: string;
  schema_url: string;
  // Exception tracking
  exception_type: string;
  exception_message: string;
  exception_stacktrace: string;
  is_exception: number;
}

/**
 * Direct ClickHouse insertion backend.
 *
 * Transforms OTLP-format traces to our custom ClickHouse schema
 * and inserts via HTTP API.
 */
export class ClickHouseBackend {
  private endpoint: string;
  private database: string;
  private tracesTable: string;
  private metricsTable: string;
  private logsTable: string;
  private username: string;
  private password: string;
  private timeout: number;
  private batchSize: number;
  private compressionEnabled: boolean;
  private maxRetries: number;
  private verbose: boolean;
  private traceBatch: ClickHouseTraceRow[] = [];
  private metricBatch: ClickHouseMetricRow[] = [];
  private logBatch: ClickHouseLogRow[] = [];

  constructor(config: ClickHouseBackendConfig = {}) {
    this.endpoint = config.endpoint || "http://localhost:8123";
    this.database = config.database || "telemetry";
    this.tracesTable = config.tracesTable || "traces";
    this.metricsTable = config.metricsTable || "metrics";
    this.logsTable = config.logsTable || "logs";
    this.username = config.username || "default";
    this.password = config.password || "";
    this.timeout = config.timeout || 5000;
    this.batchSize = config.batchSize || 100;
    this.compressionEnabled = config.compressionEnabled !== false;
    this.maxRetries = config.maxRetries || 3;
    this.verbose = config.verbose || false;
  }

  /**
   * Generate a UUID v4.
   */
  private generateUUID(): string {
    return crypto.randomUUID();
  }

  /**
   * Generate timestamp and nanosecond timestamp from optional Date.
   * @param timestamp - Optional timestamp (defaults to current time)
   * @returns Object with formatted timestamp string and nanosecond timestamp
   */
  private generateTimestamp(timestamp?: Date): {
    ts: Date;
    timestamp: string;
    timestampNs: number;
  } {
    const ts = timestamp || new Date();
    const timestampNs = ts.getTime() * 1_000_000;
    return {
      ts,
      timestamp: ts.toISOString().replace("T", " ").substring(0, 19),
      timestampNs,
    };
  }

  /**
   * Flatten attributes to string key-value pairs.
   * @param attributes - Optional attributes object
   * @returns Flattened attributes with string values
   */
  private flattenAttributes(
    attributes?: Record<string, unknown>,
  ): Record<string, string> {
    const flatAttrs: Record<string, string> = {};
    if (attributes) {
      for (const [key, val] of Object.entries(attributes)) {
        flatAttrs[key] = String(val);
      }
    }
    return flatAttrs;
  }

  /**
   * Extract extended resource attributes including OS, runtime, cloud, and instrumentation info.
   * @param resourceAttributes - Optional resource attributes
   * @returns Object with all extended resource attributes
   */
  private extractExtendedResourceAttributes(
    resourceAttributes?: Record<string, unknown>,
  ): {
    serviceName: string;
    serviceNamespace: string;
    serviceInstanceId: string;
    projectName: string;
    projectVersion: string;
    environment: string;
    hostname: string;
    osType: string;
    osVersion: string;
    runtimeName: string;
    runtimeVersion: string;
    cloudProvider: string;
    cloudRegion: string;
    cloudAvailabilityZone: string;
    instrumentationLibraryName: string;
    instrumentationLibraryVersion: string;
  } {
    const resAttrs = resourceAttributes || {};
    return {
      serviceName:
        String(resAttrs["service.name"] || resAttrs.service_name) || "unknown",
      serviceNamespace:
        String(resAttrs["service.namespace"] || resAttrs.service_namespace) ||
        "",
      serviceInstanceId:
        String(
          resAttrs["service.instance.id"] || resAttrs.service_instance_id,
        ) || "",
      projectName:
        String(resAttrs["project.name"] || resAttrs.project_name) || "",
      projectVersion:
        String(resAttrs["project.version"] || resAttrs.project_version) || "",
      environment:
        String(
          resAttrs["deployment.environment"] ||
            resAttrs.environment ||
            resAttrs.env,
        ) || "production",
      hostname: String(resAttrs["host.name"] || resAttrs.hostname) || "",
      osType: String(resAttrs["os.type"] || resAttrs.os_type) || "",
      osVersion: String(resAttrs["os.version"] || resAttrs.os_version) || "",
      runtimeName:
        String(
          resAttrs["process.runtime.name"] || resAttrs.process_runtime_name,
        ) || "",
      runtimeVersion:
        String(
          resAttrs["process.runtime.version"] ||
            resAttrs.process_runtime_version,
        ) || "",
      cloudProvider:
        String(resAttrs["cloud.provider"] || resAttrs.cloud_provider) || "",
      cloudRegion:
        String(resAttrs["cloud.region"] || resAttrs.cloud_region) || "",
      cloudAvailabilityZone:
        String(
          resAttrs["cloud.availability_zone"] ||
            resAttrs.cloud_availability_zone,
        ) || "",
      instrumentationLibraryName:
        String(resAttrs["telemetry.sdk.name"] || resAttrs.telemetry_sdk_name) ||
        "",
      instrumentationLibraryVersion:
        String(
          resAttrs["telemetry.sdk.version"] || resAttrs.telemetry_sdk_version,
        ) || "",
    };
  }

  /**
   * Detect if a string contains valid JSON.
   * @param body - The string to check
   * @returns "JSON" if valid JSON, "STRING" otherwise
   */
  private detectBodyType(body: string): string {
    try {
      JSON.parse(body);
      return "JSON";
    } catch {
      return "STRING";
    }
  }

  /**
   * Transform OTLP span format to our ClickHouse schema.
   */
  private transformOTLPToClickHouse(
    otlpSpan: Record<string, unknown>,
  ): ClickHouseTraceRow {
    // Extract timestamp (use start time or current time)
    const timestampNs = otlpSpan.startTimeUnixNano || Date.now() * 1_000_000;
    const timestamp = new Date(Number(timestampNs) / 1_000_000);

    // Calculate duration in milliseconds
    const startNs = Number(otlpSpan.startTimeUnixNano) || 0;
    const endNs = Number(otlpSpan.endTimeUnixNano) || startNs;
    const durationMs =
      endNs > startNs ? Math.floor((endNs - startNs) / 1_000_000) : 0;

    // Extract status
    const status = (otlpSpan.status || {}) as {
      code?: number;
      message?: string;
    };
    const statusCode = status.code === 1 ? "OK" : status.message || "OK";

    // Transform attributes from OTLP format to flat dict
    const attributes: Record<string, string> = {};
    const attrs = (otlpSpan.attributes || []) as Array<{
      key?: string;
      value?: {
        stringValue?: string;
        intValue?: number;
        doubleValue?: number;
        boolValue?: boolean;
      };
    }>;
    for (const attr of attrs) {
      const key = attr.key || "";
      const value = attr.value || {};

      // Extract value based on type
      if (value.stringValue !== undefined) {
        attributes[key] = value.stringValue;
      } else if (value.intValue !== undefined) {
        attributes[key] = String(value.intValue);
      } else if (value.doubleValue !== undefined) {
        attributes[key] = String(value.doubleValue);
      } else if (value.boolValue !== undefined) {
        attributes[key] = String(value.boolValue);
      }
    }

    // Extract resource attributes
    const resourceAttrs: Record<string, string> = {};
    const resource = (otlpSpan.resource || {}) as {
      attributes?: Array<{ key?: string; value?: { stringValue?: string } }>;
    };
    const resourceAttributes = resource.attributes || [];
    for (const attr of resourceAttributes) {
      const key = attr.key || "";
      const value = attr.value || {};
      if (value.stringValue !== undefined) {
        resourceAttrs[key] = value.stringValue;
      }
    }

    // Build ClickHouse row
    return {
      trace_id: String(otlpSpan.traceId || ""),
      span_id: String(otlpSpan.spanId || ""),
      parent_span_id: String(otlpSpan.parentSpanId || ""),
      timestamp: timestamp.toISOString().replace("T", " ").substring(0, 19),
      timestamp_ns: Number(timestampNs),
      duration_ms: durationMs,
      service_name: resourceAttrs["service.name"] || "unknown",
      span_name: String(otlpSpan.name || "unknown"),
      span_kind: String(otlpSpan.kind || "INTERNAL"),
      status_code: statusCode,
      status_message: status.message || "",
      project_name: resourceAttrs["project.name"] || "",
      project_version: resourceAttrs["project.version"] || "",
      environment: resourceAttrs["deployment.environment"] || "production",
      hostname: resourceAttrs["host.name"] || "",
      attributes,
      user_id: attributes["user.id"] || "",
      session_id: attributes["session.id"] || "",
      os_type: resourceAttrs["os.type"] || "",
      os_version: resourceAttrs["os.version"] || "",
      runtime_name: resourceAttrs["process.runtime.name"] || "",
      runtime_version: resourceAttrs["process.runtime.version"] || "",
      cloud_provider: resourceAttrs["cloud.provider"] || "",
      cloud_region: resourceAttrs["cloud.region"] || "",
      cloud_availability_zone: resourceAttrs["cloud.availability_zone"] || "",
      instrumentation_library_name: resourceAttrs["telemetry.sdk.name"] || "",
      instrumentation_library_version:
        resourceAttrs["telemetry.sdk.version"] || "",
    };
  }

  /**
   * Add a span to the trace batch queue.
   */
  public addToBatch(otlpSpan: Record<string, unknown>): void {
    const row = this.transformOTLPToClickHouse(otlpSpan);
    this.traceBatch.push(row);

    // Auto-flush if batch size reached
    if (this.traceBatch.length >= this.batchSize) {
      this.flush();
    }
  }

  /**
   * Flush all batches (traces, metrics, logs) to ClickHouse.
   */
  public async flush(): Promise<boolean> {
    const promises: Promise<boolean>[] = [];

    // Flush traces
    if (this.traceBatch.length > 0) {
      const rows = [...this.traceBatch];
      this.traceBatch = [];
      promises.push(this.insertBatch(rows, this.tracesTable));
    }

    // Flush metrics
    if (this.metricBatch.length > 0) {
      const rows = [...this.metricBatch];
      this.metricBatch = [];
      promises.push(this.insertBatch(rows, this.metricsTable));
    }

    // Flush logs
    if (this.logBatch.length > 0) {
      const rows = [...this.logBatch];
      this.logBatch = [];
      promises.push(this.insertBatch(rows, this.logsTable));
    }

    if (promises.length === 0) {
      return true;
    }

    const results = await Promise.all(promises);
    return results.every((result) => result);
  }

  /**
   * Insert a batch of rows into ClickHouse.
   */
  private async insertBatch(
    rows: Array<ClickHouseTraceRow | ClickHouseMetricRow | ClickHouseLogRow>,
    tableName: string,
  ): Promise<boolean> {
    if (rows.length === 0) {
      return true;
    }

    // Convert rows to JSONEachRow format (one JSON object per line)
    let data = Buffer.from(rows.map((row) => JSON.stringify(row)).join("\n"));

    // Compress if enabled and data is large enough
    const contentEncoding =
      this.compressionEnabled && data.length > 1024 ? "gzip" : undefined;
    if (contentEncoding) {
      data = zlib.gzipSync(data);
    }

    // Build URL with query
    const query = `INSERT INTO ${this.database}.${tableName} FORMAT JSONEachRow`;
    const parsedUrl = new url.URL(this.endpoint);
    parsedUrl.searchParams.set("query", query);

    // Add authentication if provided
    let authHeader: string | undefined;
    if (this.username) {
      const auth = Buffer.from(`${this.username}:${this.password}`).toString(
        "base64",
      );
      authHeader = `Basic ${auth}`;
    }

    // Retry logic with exponential backoff
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const success = await this.httpPost(
          parsedUrl.toString(),
          data,
          contentEncoding,
          authHeader,
        );

        if (success) {
          if (this.verbose) {
            console.debug(
              `Inserted ${rows.length} rows to ClickHouse successfully`,
            );
          }
          return true;
        }
      } catch (error) {
        if (this.verbose) {
          console.error(
            `Error inserting to ClickHouse (attempt ${attempt + 1}/${this.maxRetries}):`,
            error,
          );
        }

        if (attempt < this.maxRetries - 1) {
          await new Promise((resolve) =>
            setTimeout(resolve, Math.pow(2, attempt) * 1000),
          );
          continue;
        }
      }
    }

    return false;
  }

  /**
   * Make HTTP POST request to ClickHouse.
   */
  private httpPost(
    url: string,
    data: Buffer,
    contentEncoding?: string,
    authHeader?: string,
  ): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(url);
      const isHttps = parsedUrl.protocol === "https:";
      const httpModule = isHttps ? https : http;

      const headers: Record<string, string> = {
        "Content-Type": "application/x-ndjson",
        "Content-Length": String(data.length),
      };

      if (contentEncoding) {
        headers["Content-Encoding"] = contentEncoding;
      }
      if (authHeader) {
        headers["Authorization"] = authHeader;
      }

      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: `${parsedUrl.pathname}${parsedUrl.search}`,
        method: "POST",
        headers,
        timeout: this.timeout,
      };

      const req = httpModule.request(options, (res) => {
        let responseData = "";

        res.on("data", (chunk) => {
          responseData += chunk;
        });

        res.on("end", () => {
          if (res.statusCode === 200) {
            resolve(true);
          } else {
            if (this.verbose) {
              console.warn(
                `ClickHouse returned status ${res.statusCode}: ${responseData}`,
              );
            }
            resolve(false);
          }
        });
      });

      req.on("error", (error) => {
        reject(error);
      });

      req.on("timeout", () => {
        req.destroy();
        reject(new Error("Request timeout"));
      });

      req.write(data);
      req.end();
    });
  }

  /**
   * Send a single trace span to ClickHouse.
   *
   * This is a convenience method that batches internally.
   */
  public sendTrace(otlpSpan: Record<string, unknown>): boolean {
    try {
      this.addToBatch(otlpSpan);
      return true;
    } catch (error) {
      if (this.verbose) {
        console.error("Error adding span to batch:", error);
      }
      return false;
    }
  }

  /**
   * Send a single metric to ClickHouse.
   *
   * @param metricName - Name of the metric (e.g., "http.request.duration")
   * @param value - Numeric value of the metric
   * @param metricType - Type of metric: "GAUGE", "COUNTER", "HISTOGRAM", "SUMMARY"
   * @param unit - Unit of measurement (e.g., "ms", "bytes", "count")
   * @param attributes - Additional metric attributes
   * @param resourceAttributes - Resource-level attributes (service name, environment, etc.)
   * @param timestamp - Optional timestamp (defaults to current time)
   * @returns true if successfully added to batch, false otherwise
   */
  public sendMetric(
    metricName: string,
    value: number,
    metricType: string = "GAUGE",
    unit: string = "",
    attributes?: Record<string, unknown>,
    resourceAttributes?: Record<string, unknown>,
    timestamp?: Date,
  ): boolean {
    try {
      // Map COUNTER to SUM for ClickHouse enum compatibility
      let mappedType = metricType.toUpperCase();
      if (mappedType === "COUNTER") {
        mappedType = "SUM";
      }

      // Validate metric type
      const validTypes = ["GAUGE", "SUM", "HISTOGRAM", "SUMMARY"];
      if (!validTypes.includes(mappedType)) {
        if (this.verbose) {
          console.warn(
            `Invalid metric type: ${metricType}. Using GAUGE as fallback.`,
          );
        }
        mappedType = "GAUGE";
      }

      // Generate timestamp using helper
      const { timestamp: formattedTimestamp, timestampNs } =
        this.generateTimestamp(timestamp);

      // Flatten attributes using helper
      const flatAttrs = this.flattenAttributes(attributes);

      // Extract extended resource attributes
      const {
        serviceName,
        serviceNamespace,
        serviceInstanceId,
        projectName,
        projectVersion,
        environment,
        hostname,
        osType,
        osVersion,
        runtimeName,
        runtimeVersion,
        cloudProvider,
        cloudRegion,
        cloudAvailabilityZone,
        instrumentationLibraryName,
        instrumentationLibraryVersion,
      } = this.extractExtendedResourceAttributes(resourceAttributes);

      // Determine if value is int or float
      const isInt = Number.isInteger(value);
      const valueInt = isInt ? value : 0;
      const valueDouble = isInt ? 0.0 : value;

      // Extract histogram/summary data from attributes (if present)
      const histogramBucketCounts =
        attributes && Array.isArray(attributes["histogram.bucket_counts"])
          ? (attributes["histogram.bucket_counts"] as number[])
          : [];
      const histogramExplicitBounds =
        attributes && Array.isArray(attributes["histogram.explicit_bounds"])
          ? (attributes["histogram.explicit_bounds"] as number[])
          : [];
      const summaryCount = Number(
        (attributes && attributes["summary.count"]) || 0,
      );
      const summarySum = Number((attributes && attributes["summary.sum"]) || 0);
      const quantileValues =
        attributes && typeof attributes["quantile.values"] === "object"
          ? (attributes["quantile.values"] as Record<string, number>)
          : {};

      // Extract user/session IDs from attributes
      const userId = String((attributes && attributes["user.id"]) || "");
      const sessionId = String((attributes && attributes["session.id"]) || "");

      // Build metric row
      const metricRow: ClickHouseMetricRow = {
        metric_id: this.generateUUID(),
        metric_name: metricName,
        metric_type: mappedType,
        metric_unit: unit,
        metric_description: "",
        timestamp: formattedTimestamp,
        timestamp_ns: timestampNs,
        time_window_start: formattedTimestamp,
        time_window_end: formattedTimestamp,
        value_int: valueInt,
        value_double: valueDouble,
        is_monotonic: mappedType === "SUM" ? 1 : 0,
        aggregation_temporality: mappedType === "SUM" ? "DELTA" : "UNSPECIFIED",
        histogram_count: 0,
        histogram_sum: 0.0,
        histogram_min: 0.0,
        histogram_max: 0.0,
        histogram_bucket_counts: histogramBucketCounts,
        histogram_explicit_bounds: histogramExplicitBounds,
        summary_count: summaryCount,
        summary_sum: summarySum,
        quantile_values: quantileValues,
        project_name: projectName,
        project_version: projectVersion,
        service_name: serviceName,
        service_namespace: serviceNamespace,
        service_instance_id: serviceInstanceId,
        environment: environment,
        hostname: hostname,
        attributes: flatAttrs,
        user_id: userId,
        session_id: sessionId,
        os_type: osType,
        os_version: osVersion,
        runtime_name: runtimeName,
        runtime_version: runtimeVersion,
        cloud_provider: cloudProvider,
        cloud_region: cloudRegion,
        cloud_availability_zone: cloudAvailabilityZone,
        instrumentation_library_name: instrumentationLibraryName,
        instrumentation_library_version: instrumentationLibraryVersion,
        schema_url: "",
      };

      // Add to batch
      this.metricBatch.push(metricRow);

      // Auto-flush if batch size reached
      if (this.metricBatch.length >= this.batchSize) {
        this.flush();
      }

      return true;
    } catch (error) {
      if (this.verbose) {
        console.error("Error adding metric to batch:", error);
      }
      return false;
    }
  }

  /**
   * Send a single log entry to ClickHouse.
   *
   * @param message - Log message body
   * @param level - Log level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
   * @param attributes - Additional log attributes
   * @param resourceAttributes - Resource-level attributes (service name, environment, etc.)
   * @param timestamp - Optional timestamp (defaults to current time)
   * @param traceId - Optional trace ID to correlate with traces
   * @param spanId - Optional span ID to correlate with traces
   * @returns true if successfully added to batch, false otherwise
   */
  public sendLog(
    message: string,
    level: string = "INFO",
    attributes?: Record<string, unknown>,
    resourceAttributes?: Record<string, unknown>,
    timestamp?: Date,
    traceId: string = "",
    spanId: string = "",
  ): boolean {
    try {
      // Map severity level to number (OpenTelemetry severity numbers)
      const severityMap: Record<string, number> = {
        TRACE: 1,
        DEBUG: 5,
        INFO: 9,
        WARN: 13,
        WARNING: 13,
        ERROR: 17,
        FATAL: 21,
        CRITICAL: 21,
      };

      const upperLevel = level.toUpperCase();
      const severityNumber = severityMap[upperLevel] || 9; // Default to INFO

      // Generate event timestamp
      const { timestamp: formattedTimestamp, timestampNs } =
        this.generateTimestamp(timestamp);

      // Generate observed timestamp (when log was received)
      const {
        timestamp: observedFormattedTimestamp,
        timestampNs: observedTimestampNs,
      } = this.generateTimestamp(new Date());

      // Detect if message is JSON
      const bodyType = this.detectBodyType(message);

      // Flatten attributes using helper
      const flatAttrs = this.flattenAttributes(attributes);

      // Extract extended resource attributes
      const {
        serviceName,
        serviceNamespace,
        serviceInstanceId,
        projectName,
        projectVersion,
        environment,
        hostname,
        osType,
        osVersion,
        runtimeName,
        runtimeVersion,
        cloudProvider,
        cloudRegion,
        cloudAvailabilityZone,
        instrumentationLibraryName,
        instrumentationLibraryVersion,
      } = this.extractExtendedResourceAttributes(resourceAttributes);

      // Extract exception info from attributes (if present)
      const exceptionType = String(
        (attributes && attributes["exception.type"]) || "",
      );
      const exceptionMessage = String(
        (attributes && attributes["exception.message"]) || "",
      );
      const exceptionStacktrace = String(
        (attributes && attributes["exception.stacktrace"]) || "",
      );
      const isException = exceptionType ? 1 : 0;

      // Extract user/session IDs from attributes
      const userId = String((attributes && attributes["user.id"]) || "");
      const sessionId = String((attributes && attributes["session.id"]) || "");

      // Build log row
      const logRow: ClickHouseLogRow = {
        log_id: this.generateUUID(),
        trace_id: traceId,
        span_id: spanId,
        timestamp: formattedTimestamp,
        timestamp_ns: timestampNs,
        observed_timestamp: observedFormattedTimestamp,
        observed_timestamp_ns: observedTimestampNs,
        severity_text: upperLevel,
        severity_number: severityNumber,
        body: message,
        body_type: bodyType,
        project_name: projectName,
        project_version: projectVersion,
        service_name: serviceName,
        service_namespace: serviceNamespace,
        service_instance_id: serviceInstanceId,
        environment: environment,
        hostname: hostname,
        attributes: flatAttrs,
        user_id: userId,
        session_id: sessionId,
        os_type: osType,
        os_version: osVersion,
        runtime_name: runtimeName,
        runtime_version: runtimeVersion,
        cloud_provider: cloudProvider,
        cloud_region: cloudRegion,
        cloud_availability_zone: cloudAvailabilityZone,
        instrumentation_library_name: instrumentationLibraryName,
        instrumentation_library_version: instrumentationLibraryVersion,
        schema_url: "",
        exception_type: exceptionType,
        exception_message: exceptionMessage,
        exception_stacktrace: exceptionStacktrace,
        is_exception: isException,
      };

      // Add to batch
      this.logBatch.push(logRow);

      // Auto-flush if batch size reached
      if (this.logBatch.length >= this.batchSize) {
        this.flush();
      }

      return true;
    } catch (error) {
      if (this.verbose) {
        console.error("Error adding log to batch:", error);
      }
      return false;
    }
  }
}
