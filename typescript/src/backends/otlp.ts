/**
 * OTLP (OpenTelemetry Protocol) backend for telemetry data.
 *
 * Sends telemetry data to an OTLP-compatible endpoint using HTTP/JSON.
 * Uses only Node.js standard library - no external dependencies.
 */

import * as zlib from "zlib";
import { TelemetryBackend } from "./base";

/**
 * Configuration options for OTLP backend.
 * Exported as part of the public API for users who want to use OTLPBackend directly.
 */
export interface OTLPBackendConfig {
  /** OTLP HTTP endpoint (e.g. https://telemetry.namastex.ai/v1/traces) */
  endpoint: string;
  /** HTTP timeout in milliseconds (default: 5000) */
  timeout?: number;
  /** Maximum retry attempts (default: 3) */
  maxRetries?: number;
  /** Retry backoff base delay in milliseconds (default: 1000) */
  retryBackoffBase?: number;
  /** Enable gzip compression (default: true) */
  compressionEnabled?: boolean;
  /** Compression threshold in bytes (default: 1024) */
  compressionThreshold?: number;
  /** Enable verbose console logging for debugging (default: false) */
  verbose?: boolean;
}

/**
 * OTLP HTTP/JSON backend for sending telemetry data.
 *
 * Sends traces, metrics, and logs to an OTLP-compatible endpoint
 * with automatic retry logic and compression support.
 */
export class OTLPBackend implements TelemetryBackend {
  private endpoint: string;
  private timeout: number;
  private maxRetries: number;
  private retryBackoffBase: number;
  private compressionEnabled: boolean;
  private compressionThreshold: number;
  private verbose: boolean;

  constructor(config: OTLPBackendConfig) {
    this.endpoint = config.endpoint;
    this.timeout = config.timeout || 5000;
    this.maxRetries = config.maxRetries || 3;
    this.retryBackoffBase = config.retryBackoffBase || 1000;
    this.compressionEnabled = config.compressionEnabled !== false;
    this.compressionThreshold = config.compressionThreshold || 1024;
    this.verbose = config.verbose || false;
  }

  /**
   * Compress payload using gzip.
   *
   * @param data - Data to compress
   * @returns Compressed buffer
   */
  private async compressPayload(data: string): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      zlib.gzip(Buffer.from(data, "utf-8"), (error, result) => {
        if (error) {
          reject(error);
        } else {
          resolve(result);
        }
      });
    });
  }

  /**
   * Send HTTP request with retry logic.
   *
   * @param endpoint - Target endpoint
   * @param payload - Request payload
   * @param attempt - Current attempt number (internal)
   * @returns True if request succeeded, false otherwise
   */
  private async sendWithRetry(
    endpoint: string,
    payload: unknown,
    attempt: number = 0,
  ): Promise<boolean> {
    try {
      const payloadString = JSON.stringify(payload);
      let body: Buffer | string = payloadString;
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      // Apply compression if enabled and payload exceeds threshold
      if (
        this.compressionEnabled &&
        Buffer.byteLength(payloadString, "utf-8") > this.compressionThreshold
      ) {
        body = await this.compressPayload(payloadString);
        headers["Content-Encoding"] = "gzip";
      }

      // Send HTTP request using native fetch (Node.js 18+)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      timeoutId.unref(); // Allow process to exit

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers,
          body,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Check for retryable errors (5xx)
        if (response.status >= 500 && response.status < 600) {
          throw new Error(`Server error: ${response.status}`);
        }

        // Don't retry on 4xx errors (client errors)
        if (response.status >= 400 && response.status < 500) {
          if (this.verbose) {
            console.debug(
              `Telemetry event failed with status ${response.status}`,
            );
          }
          return false; // Don't retry
        }

        if (response.status !== 200) {
          if (this.verbose) {
            console.debug(
              `Telemetry event failed with status ${response.status}`,
            );
          }
          return false;
        }

        return true;
      } catch (error) {
        clearTimeout(timeoutId);
        throw error;
      }
    } catch (error) {
      // Retry logic for network errors or 5xx responses
      if (attempt < this.maxRetries) {
        const backoffDelay = this.retryBackoffBase * Math.pow(2, attempt);
        if (this.verbose) {
          console.debug(
            `Telemetry request failed (attempt ${attempt + 1}/${this.maxRetries + 1}), retrying in ${backoffDelay}ms...`,
          );
        }
        await new Promise((resolve) => {
          const timer = setTimeout(resolve, backoffDelay);
          timer.unref(); // Allow process to exit
        });
        return this.sendWithRetry(endpoint, payload, attempt + 1);
      }

      // Max retries exceeded
      if (this.verbose) {
        console.debug(
          `Telemetry event error after ${this.maxRetries + 1} attempts:`,
          error,
        );
      }
      return false;
    }
  }

  /**
   * Send a trace payload to the OTLP endpoint.
   *
   * @param payload - OTLP trace payload
   * @returns Promise that resolves to true if successful, false otherwise
   */
  async sendTrace(payload: unknown): Promise<boolean> {
    return this.sendWithRetry(this.endpoint, payload);
  }

  /**
   * Send a metric payload to the OTLP endpoint.
   *
   * @param payload - OTLP metric payload
   * @param metricsEndpoint - Optional metrics-specific endpoint
   * @returns Promise that resolves to true if successful, false otherwise
   */
  async sendMetric(
    payload: unknown,
    metricsEndpoint?: string,
  ): Promise<boolean> {
    const endpoint = metricsEndpoint || this.endpoint;
    return this.sendWithRetry(endpoint, payload);
  }

  /**
   * Send a log payload to the OTLP endpoint.
   *
   * @param payload - OTLP log payload
   * @param logsEndpoint - Optional logs-specific endpoint
   * @returns Promise that resolves to true if successful, false otherwise
   */
  async sendLog(payload: unknown, logsEndpoint?: string): Promise<boolean> {
    const endpoint = logsEndpoint || this.endpoint;
    return this.sendWithRetry(endpoint, payload);
  }

  /**
   * Flush any buffered data.
   *
   * OTLP backend does not buffer data - all sends are immediate.
   * This method is provided for interface compatibility and always returns true.
   *
   * @returns Promise that resolves to true
   */
  async flush(): Promise<boolean> {
    // OTLP backend sends data immediately, no buffering
    return true;
  }
}
