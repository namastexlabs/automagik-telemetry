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

/**
 * Configuration options for ClickHouse backend.
 */
export interface ClickHouseBackendConfig {
  /** ClickHouse HTTP endpoint (e.g. http://localhost:8123) */
  endpoint?: string;
  /** Database name (default: telemetry) */
  database?: string;
  /** Table name (default: traces) */
  table?: string;
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
 * ClickHouse row structure matching our schema.
 */
interface ClickHouseRow {
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
 * Direct ClickHouse insertion backend.
 *
 * Transforms OTLP-format traces to our custom ClickHouse schema
 * and inserts via HTTP API.
 */
export class ClickHouseBackend {
  private endpoint: string;
  private database: string;
  private table: string;
  private username: string;
  private password: string;
  private timeout: number;
  private batchSize: number;
  private compressionEnabled: boolean;
  private maxRetries: number;
  private batch: ClickHouseRow[] = [];

  constructor(config: ClickHouseBackendConfig = {}) {
    this.endpoint = config.endpoint || "http://localhost:8123";
    this.database = config.database || "telemetry";
    this.table = config.table || "traces";
    this.username = config.username || "default";
    this.password = config.password || "";
    this.timeout = config.timeout || 5000;
    this.batchSize = config.batchSize || 100;
    this.compressionEnabled = config.compressionEnabled !== false;
    this.maxRetries = config.maxRetries || 3;
  }

  /**
   * Transform OTLP span format to our ClickHouse schema.
   */
  private transformOTLPToClickHouse(otlpSpan: any): ClickHouseRow {
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
   * Add a span to the batch queue.
   */
  public addToBatch(otlpSpan: any): void {
    const row = this.transformOTLPToClickHouse(otlpSpan);
    this.batch.push(row);

    // Auto-flush if batch size reached
    if (this.batch.length >= this.batchSize) {
      this.flush();
    }
  }

  /**
   * Flush the current batch to ClickHouse.
   */
  public async flush(): Promise<boolean> {
    if (this.batch.length === 0) {
      return true;
    }

    const rows = [...this.batch];
    this.batch = [];

    return this.insertBatch(rows);
  }

  /**
   * Insert a batch of rows into ClickHouse.
   */
  private async insertBatch(rows: ClickHouseRow[]): Promise<boolean> {
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
    const query = `INSERT INTO ${this.database}.${this.table} FORMAT JSONEachRow`;
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
}
