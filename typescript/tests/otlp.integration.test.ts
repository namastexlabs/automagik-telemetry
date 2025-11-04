/**
 * Integration tests with OTLP protocol.
 *
 * Tests actual OTLP payload format and network communication patterns.
 * Uses mocked fetch to verify behavior without requiring real backend.
 *
 * Tests cover:
 * - Trace (span) payload format
 * - Metric payload format
 * - Log payload format
 * - Error tracking
 * - Batch sends
 * - Large payloads with compression
 * - Concurrent sends
 * - Retry logic
 * - Custom endpoint configuration
 *
 * Port of Python's test_integration_otlp.py to TypeScript
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as zlib from 'zlib';
import { AutomagikTelemetry, LogSeverity, MetricType } from '../src/client';
import type { TelemetryConfig } from '../src/config';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

// Mock fetch globally
global.fetch = jest.fn();

describe('OTLP Integration Tests', () => {
  const mockHomedir = '/home/testuser';
  const testEndpoint = 'https://telemetry.namastex.ai';

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock os methods
    (os.homedir as jest.Mock).mockReturnValue(mockHomedir);
    (os.platform as jest.Mock).mockReturnValue('linux');
    (os.release as jest.Mock).mockReturnValue('5.10.0');
    (os.arch as jest.Mock).mockReturnValue('x64');

    // Mock fs methods
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    (fs.readFileSync as jest.Mock).mockReturnValue('');
    (fs.writeFileSync as jest.Mock).mockReturnValue(undefined);
    (fs.mkdirSync as jest.Mock).mockReturnValue(undefined);

    // Setup fetch mock to succeed by default
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    // Enable telemetry
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
  });

  afterEach(() => {
    delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
  });

  describe('Trace (Span) Payload Format', () => {
    it('should send trace with correct OTLP format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackEvent('integration.test.trace', {
        test_type: 'trace',
        timestamp: Date.now(),
      });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];

      // Verify endpoint
      expect(callArgs[0]).toBe(`${testEndpoint}/v1/traces`);

      // Verify payload structure
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceSpans).toBeDefined();
      expect(body.resourceSpans[0].resource.attributes).toBeDefined();
      expect(body.resourceSpans[0].scopeSpans).toBeDefined();
      expect(body.resourceSpans[0].scopeSpans[0].spans).toBeDefined();
      expect(body.resourceSpans[0].scopeSpans[0].spans[0].name).toBe('integration.test.trace');
    });
  });

  describe('Metric Payload Format', () => {
    it('should send gauge metric with correct OTLP format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackMetric('integration.test.gauge', 42.5, MetricType.GAUGE, {
        test_type: 'gauge',
      });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];

      // Verify endpoint
      expect(callArgs[0]).toBe(`${testEndpoint}/v1/metrics`);

      // Verify payload structure
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceMetrics).toBeDefined();
      expect(body.resourceMetrics[0].scopeMetrics).toBeDefined();
      expect(body.resourceMetrics[0].scopeMetrics[0].metrics).toBeDefined();
      expect(body.resourceMetrics[0].scopeMetrics[0].metrics[0].name).toBe(
        'integration.test.gauge',
      );
      expect(body.resourceMetrics[0].scopeMetrics[0].metrics[0].gauge).toBeDefined();
    });

    it('should send counter metric with correct format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackMetric('integration.test.counter', 100, MetricType.COUNTER);

      await new Promise((resolve) => setTimeout(resolve, 10));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.resourceMetrics[0].scopeMetrics[0].metrics[0].sum).toBeDefined();
    });

    it('should send histogram metric with correct format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackMetric('integration.test.histogram', 123.45, MetricType.HISTOGRAM);

      await new Promise((resolve) => setTimeout(resolve, 10));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.resourceMetrics[0].scopeMetrics[0].metrics[0].histogram).toBeDefined();
    });
  });

  describe('Log Payload Format', () => {
    it('should send log with correct OTLP format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackLog('This is an info log', LogSeverity.INFO, {
        test_type: 'log',
      });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];

      // Verify endpoint
      expect(callArgs[0]).toBe(`${testEndpoint}/v1/logs`);

      // Verify payload structure
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceLogs).toBeDefined();
      expect(body.resourceLogs[0].scopeLogs).toBeDefined();
      expect(body.resourceLogs[0].scopeLogs[0].logRecords).toBeDefined();
      expect(body.resourceLogs[0].scopeLogs[0].logRecords[0].body.stringValue).toBe(
        'This is an info log',
      );
    });

    it('should send logs with different severity levels', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      const severities = [
        [LogSeverity.TRACE, 'trace log'],
        [LogSeverity.DEBUG, 'debug log'],
        [LogSeverity.INFO, 'info log'],
        [LogSeverity.WARN, 'warn log'],
        [LogSeverity.ERROR, 'error log'],
      ] as const;

      for (const [severity, message] of severities) {
        jest.clearAllMocks();
        client.trackLog(message, severity);
        await new Promise((resolve) => setTimeout(resolve, 10));

        const callArgs = (global.fetch as jest.Mock).mock.calls[0];
        const body = JSON.parse(callArgs[1].body);
        expect(body.resourceLogs[0].scopeLogs[0].logRecords[0].severityNumber).toBeDefined();
      }
    });
  });

  describe('Error Tracking', () => {
    it('should track error with correct format', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      try {
        throw new Error('Test error for integration');
      } catch (error) {
        client.trackError(error as Error, {
          test_context: 'integration_test',
        });
      }

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      // Error should be sent as a trace
      expect(body.resourceSpans).toBeDefined();
      const span = body.resourceSpans[0].scopeSpans[0].spans[0];
      expect(span.attributes.some((a: any) => a.key === 'error_type')).toBe(true);
      expect(span.attributes.some((a: any) => a.key === 'error_message')).toBe(true);
    });
  });

  describe('Batch Sends', () => {
    it('should handle batch of events', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 100,
        flushInterval: 60000,
        compressionEnabled: false,
      });

      const numEvents = 50;
      for (let i = 0; i < numEvents; i++) {
        client.trackEvent('integration.test.batch', {
          event_number: i,
        });
      }

      await client.flush();

      // Should send all 50 events (one request per event)
      expect(global.fetch).toHaveBeenCalledTimes(numEvents);
    });
  });

  describe('Large Payloads with Compression', () => {
    it('should compress large payloads', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: true,
        compressionThreshold: 100,
      });

      // Create large payload
      const largeData = {
        large_field_1: 'x'.repeat(1000),
        large_field_2: 'y'.repeat(1000),
        large_field_3: 'z'.repeat(1000),
      };

      client.trackEvent('integration.test.large_payload', largeData);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];

      // Should be compressed (gzip)
      expect(callArgs[1].headers['Content-Encoding']).toBe('gzip');
      expect(Buffer.isBuffer(callArgs[1].body)).toBe(true);

      // Verify can decompress
      const decompressed = zlib.gunzipSync(callArgs[1].body);
      const payload = JSON.parse(decompressed.toString());
      expect(payload.resourceSpans).toBeDefined();
    });
  });

  describe('Concurrent Sends', () => {
    it('should handle concurrent operations', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-otlp',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      // Send events concurrently
      const promises = Array.from({ length: 10 }, (_, i) =>
        Promise.resolve(
          client.trackEvent('integration.test.concurrent', {
            event_id: i,
          }),
        ),
      );

      await Promise.all(promises);
      await new Promise((resolve) => setTimeout(resolve, 20));

      // All events should be sent
      expect(global.fetch).toHaveBeenCalledTimes(10);
    });
  });

  describe('Retry Logic', () => {
    it('should retry on 5xx server errors', async () => {
      // Mock to return 500 errors
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' }),
      });

      const client = new AutomagikTelemetry({
        projectName: 'test-retry',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        maxRetries: 3,
        retryBackoffBase: 10, // Fast retries for testing
      });

      client.trackEvent('integration.test.retry');

      // Wait for retries to complete
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should retry: 1 initial + 3 retries = 4 total
      expect(global.fetch).toHaveBeenCalledTimes(4);
    });

    it('should not retry on 4xx client errors', async () => {
      // Mock to return 400 error
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Bad request' }),
      });

      const client = new AutomagikTelemetry({
        projectName: 'test-no-retry',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        maxRetries: 3,
      });

      client.trackEvent('integration.test.no_retry');

      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should only try once (no retries for 4xx)
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should retry on network errors', async () => {
      // Mock network error
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new AutomagikTelemetry({
        projectName: 'test-network-retry',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        maxRetries: 2,
        retryBackoffBase: 10,
      });

      client.trackEvent('integration.test.network_retry');

      // Wait for retries
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Should retry: 1 initial + 2 retries = 3 total
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('Custom Endpoint Configuration', () => {
    it('should use custom endpoint correctly', () => {
      const customEndpoint = 'https://custom.example.com';

      const client = new AutomagikTelemetry({
        projectName: 'test-custom',
        version: '1.0.0',
        endpoint: customEndpoint,
        batchSize: 1,
      });

      const status = client.getStatus();

      expect(status.endpoint).toBe(`${customEndpoint}/v1/traces`);
    });

    it('should handle endpoint with trailing slash', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-trailing',
        version: '1.0.0',
        endpoint: 'https://custom.example.com/',
        batchSize: 1,
      });

      const status = client.getStatus();

      expect(status.endpoint).toContain('/v1/traces');
    });
  });

  describe('All Signal Types', () => {
    it('should send all signal types successfully', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-all-signals',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      // 1. Trace
      client.trackEvent('integration.test.all_signals', {
        signal_type: 'trace',
      });

      // 2. Metric
      client.trackMetric('integration.test.all_signals', 456.78, MetricType.GAUGE, {
        signal_type: 'metric',
      });

      // 3. Log
      client.trackLog('All signals test', LogSeverity.INFO, {
        signal_type: 'log',
      });

      await new Promise((resolve) => setTimeout(resolve, 20));

      // All three signals should be sent
      expect(global.fetch).toHaveBeenCalledTimes(3);

      // Verify endpoints
      const calls = (global.fetch as jest.Mock).mock.calls;
      expect(calls[0][0]).toBe(`${testEndpoint}/v1/traces`);
      expect(calls[1][0]).toBe(`${testEndpoint}/v1/metrics`);
      expect(calls[2][0]).toBe(`${testEndpoint}/v1/logs`);
    });
  });

  describe('Telemetry Status', () => {
    it('should return correct status', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-status',
        version: '1.2.3',
        endpoint: testEndpoint,
        batchSize: 50,
      });

      const status = client.getStatus();

      expect(status.enabled).toBe(true);
      expect(status.project_name).toBe('test-status');
      expect(status.project_version).toBe('1.2.3');
      expect(status.endpoint).toContain('telemetry.namastex.ai');
      expect(status.user_id).toBeDefined();
      expect(status.session_id).toBeDefined();
    });
  });

  describe('Request Headers', () => {
    it('should send correct headers', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-headers',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: false,
      });

      client.trackEvent('integration.test.headers');

      await new Promise((resolve) => setTimeout(resolve, 10));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const headers = callArgs[1].headers;

      expect(headers['Content-Type']).toBe('application/json');
      expect(headers['Content-Encoding']).toBeUndefined(); // No compression
    });

    it('should send gzip header when compressed', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'test-gzip-header',
        version: '1.0.0',
        endpoint: testEndpoint,
        batchSize: 1,
        compressionEnabled: true,
        compressionThreshold: 10,
      });

      client.trackEvent('integration.test.gzip', {
        data: 'x'.repeat(500),
      });

      await new Promise((resolve) => setTimeout(resolve, 10));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const headers = callArgs[1].headers;

      expect(headers['Content-Encoding']).toBe('gzip');
    });
  });
});
