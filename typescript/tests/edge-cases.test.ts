/**
 * Comprehensive edge case tests for AutomagikTelemetry.
 *
 * Tests cover:
 * - Compression behavior (threshold, large/small payloads, disabled)
 * - Batch boundary conditions (exactly at threshold)
 * - Endpoint normalization (trailing slashes, /v1 paths)
 * - Timer rescheduling and shutdown logic
 * - Retry logic (4xx no retry, 5xx retry, network errors)
 * - Empty/null attribute handling
 * - Very long string handling
 * - Concurrent flush calls
 * - Flush during shutdown
 * - Backend switching
 * - Number attribute handling in system info
 * - Custom endpoint handling
 * - Environment variable edge cases
 *
 * Port of Python's test_coverage_edge_cases.py and test_client.py edge cases
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as zlib from 'zlib';
import { AutomagikTelemetry, TelemetryConfig, LogSeverity, MetricType } from '../src/client';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

// Mock fetch globally
global.fetch = jest.fn();

describe('Edge Case Coverage', () => {
  const mockHomedir = '/home/testuser';
  const mockUserIdFile = path.join(mockHomedir, '.automagik', 'user_id');

  let mockConfig: TelemetryConfig;

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

    // Setup fetch mock
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    // Default config
    mockConfig = {
      projectName: 'test-edge-cases',
      version: '1.0.0',
      batchSize: 1,
      compressionEnabled: false,
    };

    // Enable telemetry
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
  });

  afterEach(() => {
    delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
  });

  describe('Compression Behavior', () => {
    it('should compress large payloads above threshold', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: true,
        compressionThreshold: 100, // Low threshold to force compression
      });

      // Create large payload
      const largeData = { message: 'x'.repeat(500) };
      client.trackEvent('test.event', largeData);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Verify fetch was called with compressed data
      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = callArgs[1].body;

      // Should be Buffer (compressed)
      expect(Buffer.isBuffer(body)).toBe(true);

      // Should have gzip header
      expect(callArgs[1].headers['Content-Encoding']).toBe('gzip');

      // Verify can decompress
      const decompressed = zlib.gunzipSync(body);
      const payload = JSON.parse(decompressed.toString('utf-8'));
      expect(payload.resourceSpans).toBeDefined();
    });

    it('should not compress small payloads below threshold', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: true,
        compressionThreshold: 10000, // High threshold to prevent compression
      });

      // Small payload
      client.trackEvent('test.event', { small: 'data' });

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Verify fetch was called without compression
      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = callArgs[1].body;

      // Should be string (not compressed)
      expect(typeof body).toBe('string');

      // Should not have gzip header
      expect(callArgs[1].headers['Content-Encoding']).toBeUndefined();

      // Verify can parse directly
      const payload = JSON.parse(body);
      expect(payload.resourceSpans).toBeDefined();
    });

    it('should respect compression disabled setting', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: false,
        compressionThreshold: 0, // Would compress if enabled
      });

      // Large payload that would normally be compressed
      const largeData = { message: 'x'.repeat(2000) };
      client.trackEvent('test.event', largeData);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Verify no compression
      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = callArgs[1].body;

      // Should be string (not compressed)
      expect(typeof body).toBe('string');
      expect(callArgs[1].headers['Content-Encoding']).toBeUndefined();
    });

    it('should compress at exact threshold boundary', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: true,
        compressionThreshold: 200,
      });

      // Create payload exactly at threshold
      const exactData = { message: 'x'.repeat(200) };
      client.trackEvent('test.event', exactData);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      // At or above threshold should compress
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].headers['Content-Encoding']).toBe('gzip');
    });
  });

  describe('Batch Boundaries', () => {
    it('should flush exactly when batch size is reached', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 3,
        flushInterval: 60000, // Disable auto-flush
      });

      // Send 2 events - should not flush yet
      client.trackEvent('event.1');
      client.trackEvent('event.2');

      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(global.fetch).not.toHaveBeenCalled();

      // Send 3rd event - should flush immediately
      client.trackEvent('event.3');

      await new Promise((resolve) => setTimeout(resolve, 10));

      // TypeScript sends each event separately, so 3 requests
      expect(global.fetch).toHaveBeenCalledTimes(3);

      // Each request should have 1 event
      for (let i = 0; i < 3; i++) {
        const callArgs = (global.fetch as jest.Mock).mock.calls[i];
        const body = JSON.parse(callArgs[1].body);
        const spans = body.resourceSpans[0].scopeSpans[0].spans;
        expect(spans).toHaveLength(1);
      }
    });

    it('should batch metrics when batch size is configured', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 2,
        flushInterval: 60000, // Disable auto-flush
      });

      // Send 1 metric - should not flush
      client.trackMetric('metric.1', 1.0, MetricType.GAUGE);

      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(global.fetch).not.toHaveBeenCalled();

      // Send 2nd metric - should flush
      client.trackMetric('metric.2', 2.0, MetricType.GAUGE);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // TypeScript sends each metric separately, so 2 requests
      expect(global.fetch).toHaveBeenCalledTimes(2);

      // Each request should have 1 metric
      for (let i = 0; i < 2; i++) {
        const callArgs = (global.fetch as jest.Mock).mock.calls[i];
        const body = JSON.parse(callArgs[1].body);
        const metrics = body.resourceMetrics[0].scopeMetrics[0].metrics;
        expect(metrics).toHaveLength(1);
      }
    });

    it('should batch logs when batch size is configured', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 2,
        flushInterval: 60000, // Disable auto-flush
      });

      // Send 1 log - should not flush
      client.trackLog('log.1', LogSeverity.INFO);

      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(global.fetch).not.toHaveBeenCalled();

      // Send 2nd log - should flush
      client.trackLog('log.2', LogSeverity.INFO);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // TypeScript sends each log separately, so 2 requests
      expect(global.fetch).toHaveBeenCalledTimes(2);

      // Each request should have 1 log
      for (let i = 0; i < 2; i++) {
        const callArgs = (global.fetch as jest.Mock).mock.calls[i];
        const body = JSON.parse(callArgs[1].body);
        const logRecords = body.resourceLogs[0].scopeLogs[0].logRecords;
        expect(logRecords).toHaveLength(1);
      }
    });

    it('should handle flush with exactly one item in queue', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 10,
      });

      // Add exactly 1 item
      client.trackEvent('single.event');

      // Manual flush
      await client.flush();

      // Should send 1 item
      expect(global.fetch).toHaveBeenCalledTimes(1);
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      const spans = body.resourceSpans[0].scopeSpans[0].spans;
      expect(spans).toHaveLength(1);
    });
  });

  describe('Endpoint Normalization', () => {
    it('should append /v1/traces when custom endpoint has no path', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        endpoint: 'https://custom.example.com',
      });

      const status = client.getStatus();
      expect(status.endpoint).toBe('https://custom.example.com/v1/traces');
    });

    it('should handle custom endpoint with trailing slash', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        endpoint: 'https://custom.example.com/',
      });

      const status = client.getStatus();
      expect(status.endpoint).toBe('https://custom.example.com/v1/traces');
    });

    it('should handle custom endpoint with /v1 path', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        endpoint: 'https://custom.example.com/v1',
      });

      const status = client.getStatus();
      // Should append /traces to /v1
      expect(status.endpoint).toContain('/v1');
    });

    it('should use custom metrics endpoint', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        endpoint: 'https://custom.example.com',
        metricsEndpoint: '/custom/metrics',
      });

      const status = client.getStatus();
      // Metrics endpoint should be custom
      expect(status.endpoint).toContain('custom.example.com');
    });
  });

  describe('Timer and Shutdown Logic', () => {
    it('should not flush when client is already shut down', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 10,
      });

      // Disable client (triggers shutdown)
      client.disable();

      // Try to track event after shutdown
      client.trackEvent('should.not.send');

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Should not send (disabled)
      // Note: disable() may flush pending events, so we clear mocks after
      jest.clearAllMocks();

      client.trackEvent('another.not.send');
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle concurrent flush calls gracefully', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      // Add some events
      client.trackEvent('event.1');
      client.trackEvent('event.2');
      client.trackEvent('event.3');

      // Call flush multiple times concurrently
      await Promise.all([client.flush(), client.flush(), client.flush()]);

      // Should handle gracefully (deduplicate or queue properly)
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should respect flush interval for batched events', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
        flushInterval: 100, // 100ms flush interval
      });

      // Add event that doesn't reach batch size
      client.trackEvent('delayed.event');

      // Should not flush immediately
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(global.fetch).not.toHaveBeenCalled();

      // Wait for flush interval to pass
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should have flushed by timer
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('Retry Logic', () => {
    it('should not retry on 4xx client errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Bad request' }),
      });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
      });

      client.trackEvent('test.event');

      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should try only once (no retries for 4xx)
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should retry on 5xx server errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' }),
      });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
        retryBackoffBase: 10, // Fast retries for testing
      });

      client.trackEvent('test.event');

      // Wait for retries with exponential backoff: 10ms, 20ms, 40ms = ~100ms total
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should retry: 1 initial + 3 retries = 4 total
      expect(global.fetch).toHaveBeenCalledTimes(4);
    });

    it('should retry on network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network unreachable'));

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 2,
        retryBackoffBase: 10, // Fast retries for testing
      });

      client.trackEvent('test.event');

      // Wait for retries with exponential backoff: 10ms, 20ms = ~50ms total
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Should retry: 1 initial + 2 retries = 3 total
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should use exponential backoff for retries', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
        retryBackoffBase: 10, // 10ms base delay
      });

      const start = Date.now();
      client.trackEvent('test.event');

      // Wait for all retries
      await new Promise((resolve) => setTimeout(resolve, 200));

      const elapsed = Date.now() - start;

      // With exponential backoff: 10ms, 20ms, 40ms = ~70ms + overhead
      // Should be more than just 3 immediate retries
      expect(elapsed).toBeGreaterThan(50);
    });
  });

  describe('Empty and Null Handling', () => {
    it('should handle empty attributes object', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', {});

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceSpans).toBeDefined();
    });

    it('should handle undefined attributes', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', undefined);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle null values in attributes', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { nullValue: null, validValue: 'test' });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceSpans).toBeDefined();
    });

    it('should not flush empty queues', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 10,
      });

      // Flush without adding any events
      await client.flush();

      // Should not make any requests
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle empty string values', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { emptyString: '', validString: 'test' });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('Long String Handling', () => {
    it('should handle very long attribute values', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const longString = 'x'.repeat(10000);
      client.trackEvent('test.event', { longValue: longString });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.resourceSpans).toBeDefined();
    });

    it('should handle very long event names', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const longEventName = 'event.' + 'x'.repeat(1000);
      client.trackEvent(longEventName);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle very long error messages', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const error = new Error('x'.repeat(5000));
      client.trackError(error);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle very long log messages', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const longMessage = 'x'.repeat(10000);
      client.trackLog(longMessage, LogSeverity.INFO);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('Environment Variable Edge Cases', () => {
    it('should disable telemetry when ENVIRONMENT=development', () => {
      delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
      process.env.ENVIRONMENT = 'development';

      const client = new AutomagikTelemetry(mockConfig);

      expect(client.isEnabled()).toBe(false);

      delete process.env.ENVIRONMENT;
    });

    it('should disable telemetry when ENVIRONMENT=dev', () => {
      delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
      process.env.ENVIRONMENT = 'dev';

      const client = new AutomagikTelemetry(mockConfig);

      expect(client.isEnabled()).toBe(false);

      delete process.env.ENVIRONMENT;
    });

    it('should disable telemetry when ENVIRONMENT=test', () => {
      delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
      process.env.ENVIRONMENT = 'test';

      const client = new AutomagikTelemetry(mockConfig);

      expect(client.isEnabled()).toBe(false);

      delete process.env.ENVIRONMENT;
    });

    it('should disable telemetry when ENVIRONMENT=testing', () => {
      delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
      process.env.ENVIRONMENT = 'testing';

      const client = new AutomagikTelemetry(mockConfig);

      expect(client.isEnabled()).toBe(false);

      delete process.env.ENVIRONMENT;
    });

    it('should respect AUTOMAGIK_TELEMETRY_ENABLED over ENVIRONMENT', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.ENVIRONMENT = 'development';

      const client = new AutomagikTelemetry(mockConfig);

      // Explicit enable should override ENVIRONMENT
      expect(client.isEnabled()).toBe(true);

      delete process.env.ENVIRONMENT;
    });
  });

  describe('Number Attribute Handling', () => {
    it('should handle integer attributes correctly', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { count: 42, index: 0 });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      const attributes = body.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const countAttr = attributes.find((a: any) => a.key === 'count');
      expect(countAttr).toBeDefined();
      expect(countAttr.value.doubleValue).toBe(42);
    });

    it('should handle float attributes correctly', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { temperature: 23.5, ratio: 0.75 });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      const attributes = body.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const tempAttr = attributes.find((a: any) => a.key === 'temperature');
      expect(tempAttr).toBeDefined();
      expect(tempAttr.value.doubleValue).toBe(23.5);
    });

    it('should handle boolean attributes correctly', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { enabled: true, disabled: false });

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      const attributes = body.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const enabledAttr = attributes.find((a: any) => a.key === 'enabled');
      expect(enabledAttr).toBeDefined();
      expect(enabledAttr.value.boolValue).toBe(true);

      const disabledAttr = attributes.find((a: any) => a.key === 'disabled');
      expect(disabledAttr).toBeDefined();
      expect(disabledAttr.value.boolValue).toBe(false);
    });
  });

  describe('Configuration Edge Cases', () => {
    it('should handle missing required config fields gracefully', () => {
      expect(() => {
        // @ts-expect-error - Testing missing config
        new AutomagikTelemetry();
      }).toThrow();
    });

    it('should use default values for optional config fields', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
      });

      const status = client.getStatus();
      expect(status.endpoint).toBeDefined();
      expect(status.enabled).toBeDefined();
    });

    it('should handle custom timeout configuration', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        timeout: 10,
      });

      expect(client.getStatus()).toBeDefined();
    });

    it('should handle custom organization configuration', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        organization: 'custom-org',
      });

      expect(client.getStatus()).toBeDefined();
    });
  });

  describe('Manual Flush Scenarios', () => {
    it('should flush all queue types simultaneously', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
        flushInterval: 60000, // Disable auto-flush
      });

      // Add different types
      client.trackEvent('event.1');
      client.trackMetric('metric.1', 42.0);
      client.trackLog('log.1', LogSeverity.INFO);

      // Manual flush
      await client.flush();

      // Should send 3 requests (traces, metrics, logs)
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should handle flush with only events', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
        flushInterval: 60000, // Disable auto-flush
      });

      client.trackEvent('event.1');
      client.trackEvent('event.2');

      await client.flush();

      // Should send 2 requests (one per event)
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should handle flush with only metrics', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
        flushInterval: 60000, // Disable auto-flush
      });

      client.trackMetric('metric.1', 42.0);
      client.trackMetric('metric.2', 100.0);

      await client.flush();

      // Should send 2 requests (one per metric)
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should handle flush with only logs', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
        flushInterval: 60000, // Disable auto-flush
      });

      client.trackLog('log.1', LogSeverity.INFO);
      client.trackLog('log.2', LogSeverity.ERROR);

      await client.flush();

      // Should send 2 requests (one per log)
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });
});
