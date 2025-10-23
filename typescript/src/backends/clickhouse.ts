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
}

/**
 * ClickHouse metric row structure matching our schema.
 */
interface ClickHouseMetricRow {
  metric_id: string;
  timestamp: string;
  timestamp_ns: number;
  service_name: string;
  metric_name: string;
  metric_type: string;
  value: number;
  unit: string;
  project_name: string;
  project_version: string;
  environment: string;
  hostname: string;
  attributes: Record<string, string>;
}

/**
 * ClickHouse log row structure matching our schema.
 */
interface ClickHouseLogRow {
  log_id: string;
  timestamp: string;
  timestamp_ns: number;
  trace_id: string;
  span_id: string;
  severity_number: number;
  severity_text: string;
  body: string;
  service_name: string;
  project_name: string;
  project_version: string;
  environment: string;
  hostname: string;
  attributes: Record<string, string>;
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
  }

  /**
   * Generate a UUID v4.
   */
  private generateUUID(): string {
    return crypto.randomUUID();
  }

  /**
   * Transform OTLP span format to our ClickHouse schema.
   */
  private transformOTLPToClickHouse(otlpSpan: any): ClickHouseTraceRow {
    // Extract timestamp (use start time or current time)
    const timestampNs = otlpSpan.startTimeUnixNano || Date.now() * 1_000_000;
    const timestamp = new Date(Number(timestampNs) / 1_000_000);

    // Calculate duration in milliseconds
    const startNs = otlpSpan.startTimeUnixNano || 0;
    const endNs = otlpSpan.endTimeUnixNano || startNs;
    const durationMs =
      endNs > startNs ? Math.floor((endNs - startNs) / 1_000_000) : 0;

    // Extract status
    const status = otlpSpan.status || {};
    const statusCode = status.code === 1 ? "OK" : status.message || "OK";

    // Transform attributes from OTLP format to flat dict
    const attributes: Record<string, string> = {};
    for (const attr of otlpSpan.attributes || []) {
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
    const resource = otlpSpan.resource || {};
    for (const attr of resource.attributes || []) {
      const key = attr.key || "";
      const value = attr.value || {};
      if (value.stringValue !== undefined) {
        resourceAttrs[key] = value.stringValue;
      }
    }

    // Build ClickHouse row
    return {
      trace_id: otlpSpan.traceId || "",
      span_id: otlpSpan.spanId || "",
      parent_span_id: otlpSpan.parentSpanId || "",
      timestamp: timestamp.toISOString().replace("T", " ").substring(0, 19),
      timestamp_ns: timestampNs,
      duration_ms: durationMs,
      service_name: resourceAttrs["service.name"] || "unknown",
      span_name: otlpSpan.name || "unknown",
      span_kind: otlpSpan.kind || "INTERNAL",
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
    };
  }

  /**
   * Add a span to the trace batch queue.
   */
  public addToBatch(otlpSpan: any): void {
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
    tableName: string
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
        "base64"
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
          authHeader
        );

        if (success) {
          console.debug(
            `Inserted ${rows.length} rows to ClickHouse successfully`
          );
          return true;
        }
      } catch (error) {
        console.error(
          `Error inserting to ClickHouse (attempt ${attempt + 1}/${this.maxRetries}):`,
          error
        );

        if (attempt < this.maxRetries - 1) {
          await new Promise((resolve) =>
            setTimeout(resolve, Math.pow(2, attempt) * 1000)
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
    authHeader?: string
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
            console.warn(
              `ClickHouse returned status ${res.statusCode}: ${responseData}`
            );
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
  public sendTrace(otlpSpan: any): boolean {
    try {
      this.addToBatch(otlpSpan);
      return true;
    } catch (error) {
      console.error("Error adding span to batch:", error);
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
    attributes?: Record<string, any>,
    resourceAttributes?: Record<string, any>,
    timestamp?: Date
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
        console.warn(
          `Invalid metric type: ${metricType}. Using GAUGE as fallback.`
        );
        mappedType = "GAUGE";
      }

      // Generate timestamp
      const ts = timestamp || new Date();
      const timestampNs = ts.getTime() * 1_000_000;

      // Flatten attributes
      const flatAttrs: Record<string, string> = {};
      if (attributes) {
        for (const [key, val] of Object.entries(attributes)) {
          flatAttrs[key] = String(val);
        }
      }

      // Extract resource attributes
      const resAttrs = resourceAttributes || {};

      // Build metric row
      const metricRow: ClickHouseMetricRow = {
        metric_id: this.generateUUID(),
        timestamp: ts.toISOString().replace("T", " ").substring(0, 19),
        timestamp_ns: timestampNs,
        service_name:
          String(resAttrs["service.name"] || resAttrs.service_name) ||
          "unknown",
        metric_name: metricName,
        metric_type: mappedType,
        value: value,
        unit: unit,
        project_name:
          String(resAttrs["project.name"] || resAttrs.project_name) || "",
        project_version:
          String(resAttrs["project.version"] || resAttrs.project_version) ||
          "",
        environment:
          String(
            resAttrs["deployment.environment"] ||
              resAttrs.environment ||
              resAttrs.env
          ) || "production",
        hostname: String(resAttrs["host.name"] || resAttrs.hostname) || "",
        attributes: flatAttrs,
      };

      // Add to batch
      this.metricBatch.push(metricRow);

      // Auto-flush if batch size reached
      if (this.metricBatch.length >= this.batchSize) {
        this.flush();
      }

      return true;
    } catch (error) {
      console.error("Error adding metric to batch:", error);
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
    attributes?: Record<string, any>,
    resourceAttributes?: Record<string, any>,
    timestamp?: Date,
    traceId: string = "",
    spanId: string = ""
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

      // Generate timestamp
      const ts = timestamp || new Date();
      const timestampNs = ts.getTime() * 1_000_000;

      // Flatten attributes
      const flatAttrs: Record<string, string> = {};
      if (attributes) {
        for (const [key, val] of Object.entries(attributes)) {
          flatAttrs[key] = String(val);
        }
      }

      // Extract resource attributes
      const resAttrs = resourceAttributes || {};

      // Build log row
      const logRow: ClickHouseLogRow = {
        log_id: this.generateUUID(),
        timestamp: ts.toISOString().replace("T", " ").substring(0, 19),
        timestamp_ns: timestampNs,
        trace_id: traceId,
        span_id: spanId,
        severity_number: severityNumber,
        severity_text: upperLevel,
        body: message,
        service_name:
          String(resAttrs["service.name"] || resAttrs.service_name) ||
          "unknown",
        project_name:
          String(resAttrs["project.name"] || resAttrs.project_name) || "",
        project_version:
          String(resAttrs["project.version"] || resAttrs.project_version) ||
          "",
        environment:
          String(
            resAttrs["deployment.environment"] ||
              resAttrs.environment ||
              resAttrs.env
          ) || "production",
        hostname: String(resAttrs["host.name"] || resAttrs.hostname) || "",
        attributes: flatAttrs,
      };

      // Add to batch
      this.logBatch.push(logRow);

      // Auto-flush if batch size reached
      if (this.logBatch.length >= this.batchSize) {
        this.flush();
      }

      return true;
    } catch (error) {
      console.error("Error adding log to batch:", error);
      return false;
    }
  }
}
