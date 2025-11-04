/**
 * Base interface for telemetry backends.
 *
 * Defines the contract that all telemetry backends must implement.
 * Backends can be either synchronous or asynchronous, and can handle
 * different payload formats (OTLP, raw data, etc.).
 */

/**
 * Interface for telemetry backend implementations.
 *
 * All telemetry backends (OTLP, ClickHouse, etc.) must implement this interface
 * to ensure consistent behavior and API across different storage systems.
 *
 * @remarks
 * - Methods can return either `boolean` or `Promise<boolean>` to support both sync and async implementations
 * - The `unknown` type for payloads allows flexibility in data formats
 * - Backends should handle errors gracefully and return `false` on failure
 *
 * @example
 * ```typescript
 * class CustomBackend implements TelemetryBackend {
 *   async sendTrace(payload: unknown): Promise<boolean> {
 *     // Send trace to custom storage
 *     return true;
 *   }
 *
 *   async sendMetric(payload: unknown): Promise<boolean> {
 *     // Send metric to custom storage
 *     return true;
 *   }
 *
 *   async sendLog(payload: unknown): Promise<boolean> {
 *     // Send log to custom storage
 *     return true;
 *   }
 *
 *   async flush(): Promise<boolean> {
 *     // Flush any buffered data
 *     return true;
 *   }
 * }
 * ```
 */
export interface TelemetryBackend {
  /**
   * Send a trace payload to the backend.
   *
   * @param payload - Trace data in backend-specific format (e.g., OTLP span, custom schema)
   * @param args - Additional backend-specific arguments
   * @returns Promise or boolean indicating success (true) or failure (false)
   *
   * @remarks
   * - For OTLP backend: payload is OTLP JSON format
   * - For ClickHouse backend: payload is OTLP span converted to ClickHouse schema
   * - Implementations should handle serialization, compression, and retries
   */
  sendTrace(payload: unknown, ...args: unknown[]): Promise<boolean> | boolean;

  /**
   * Send a metric payload to the backend.
   *
   * @param payload - Metric data in backend-specific format
   * @param args - Additional backend-specific arguments (e.g., metric type, unit, timestamp)
   * @returns Promise or boolean indicating success (true) or failure (false)
   *
   * @remarks
   * - OTLP backend: payload is OTLP metric JSON format
   * - ClickHouse backend: accepts metric name, value, type, and attributes
   * - Implementations should validate metric types and handle aggregation
   */
  sendMetric(payload: unknown, ...args: unknown[]): Promise<boolean> | boolean;

  /**
   * Send a log payload to the backend.
   *
   * @param payload - Log data in backend-specific format
   * @param args - Additional backend-specific arguments (e.g., log level, timestamp)
   * @returns Promise or boolean indicating success (true) or failure (false)
   *
   * @remarks
   * - OTLP backend: payload is OTLP log JSON format
   * - ClickHouse backend: accepts log message, level, and attributes
   * - Implementations should handle log severity mapping and correlation
   */
  sendLog(payload: unknown, ...args: unknown[]): Promise<boolean> | boolean;

  /**
   * Flush any buffered data to the backend.
   *
   * @returns Promise or boolean indicating success (true) or failure (false)
   *
   * @remarks
   * - Batching backends (e.g., ClickHouse) must implement this to flush pending data
   * - Non-batching backends (e.g., OTLP with immediate send) can return true immediately
   * - Should be called before application shutdown to prevent data loss
   * - Can be called multiple times safely
   */
  flush(): Promise<boolean> | boolean;
}
