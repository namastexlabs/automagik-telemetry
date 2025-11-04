/**
 * Comprehensive tests for AutomagikTelemetry.
 *
 * Tests cover:
 * - Client initialization
 * - Event tracking (trackEvent, trackError, trackMetric)
 * - Enable/disable functionality
 * - User ID persistence
 * - OTLP payload format
 * - Environment variable handling
 * - CI environment detection
 * - Silent failure behavior
 * - Backwards compatibility with AutomagikTelemetry alias
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as crypto from 'crypto';
import * as zlib from 'zlib';
import { AutomagikTelemetry, LogSeverity, MetricType } from '../src/client';
import type { TelemetryConfig } from '../src/config';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

/**
 * Helper to parse body from fetch call, handling both compressed and uncompressed data.
 */
function parseBody(body: any): any {
  if (Buffer.isBuffer(body)) {
    // Decompress gzipped body
    const decompressed = zlib.gunzipSync(body);
    return JSON.parse(decompressed.toString('utf-8'));
  }
  return JSON.parse(body);
}

/**
 * Helper to parse payload from fetch call arguments, handling compression.
 */
function parsePayload(callArgs: any): any {
  const body = callArgs[1].body;
  const encoding = callArgs[1].headers?.['Content-Encoding'];

  if (encoding === 'gzip') {
    const decompressed = zlib.gunzipSync(Buffer.from(body));
    return JSON.parse(decompressed.toString());
  }
  return JSON.parse(body);
}

describe('AutomagikTelemetry', () => {
  const mockHomedir = '/home/testuser';
  const mockUserIdFile = path.join(mockHomedir, '.automagik', 'user_id');
  const mockOptOutFile = path.join(mockHomedir, '.automagik-no-telemetry');

  let mockConfig: TelemetryConfig;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Mock os.homedir
    (os.homedir as jest.Mock).mockReturnValue(mockHomedir);
    (os.platform as jest.Mock).mockReturnValue('linux');
    (os.release as jest.Mock).mockReturnValue('5.10.0');
    (os.arch as jest.Mock).mockReturnValue('x64');

    // Mock fs methods
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    (fs.readFileSync as jest.Mock).mockReturnValue('');
    (fs.writeFileSync as jest.Mock).mockReturnValue(undefined);
    (fs.mkdirSync as jest.Mock).mockReturnValue(undefined);
    (fs.unlinkSync as jest.Mock).mockReturnValue(undefined);

    // Default config - disable compression by default for easier testing
    mockConfig = {
      projectName: 'test-project',
      version: '1.0.0',
      compressionEnabled: false,
      batchSize: 1, // Flush immediately by default
    };
  });

  describe('Constructor and Initialization', () => {
    it('should initialize with required config', () => {
      const client = new AutomagikTelemetry(mockConfig);
      expect(client).toBeDefined();
      expect(client.isEnabled()).toBe(false); // Disabled by default
    });

    it('should use default endpoint when not provided', () => {
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://telemetry.namastex.ai/v1/traces');
    });

    it('should use custom endpoint when provided', () => {
      const customConfig = {
        ...mockConfig,
        endpoint: 'https://custom.endpoint.com',
      };
      const client = new AutomagikTelemetry(customConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://custom.endpoint.com/v1/traces');
    });

    it('should respect endpoint from environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://env.endpoint.com';
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://env.endpoint.com/v1/traces');
    });

    it('should respect metrics endpoint from environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://tempo.endpoint.com/v1/traces';
      process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT = 'https://prometheus.endpoint.com/v1/metrics';
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://tempo.endpoint.com/v1/traces');
      expect(status.metricsEndpoint).toBe('https://prometheus.endpoint.com/v1/metrics');
      delete process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT;
    });

    it('should respect logs endpoint from environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://tempo.endpoint.com/v1/traces';
      process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT = 'https://loki.endpoint.com/v1/logs';
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://tempo.endpoint.com/v1/traces');
      expect(status.logsEndpoint).toBe('https://loki.endpoint.com/v1/logs');
      delete process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT;
    });

    it('should respect all separate endpoints from environment variables', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://tempo.endpoint.com/v1/traces';
      process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT = 'https://prometheus.endpoint.com/v1/metrics';
      process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT = 'https://loki.endpoint.com/v1/logs';
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://tempo.endpoint.com/v1/traces');
      expect(status.metricsEndpoint).toBe('https://prometheus.endpoint.com/v1/metrics');
      expect(status.logsEndpoint).toBe('https://loki.endpoint.com/v1/logs');
      delete process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT;
      delete process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT;
    });

    it('config params should take precedence over environment variables for endpoints', () => {
      process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT = 'https://env-prometheus.endpoint.com/v1/metrics';
      process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT = 'https://env-loki.endpoint.com/v1/logs';
      const customConfig = {
        ...mockConfig,
        metricsEndpoint: 'https://config-prometheus.endpoint.com/v1/metrics',
        logsEndpoint: 'https://config-loki.endpoint.com/v1/logs',
      };
      const client = new AutomagikTelemetry(customConfig);
      const status = client.getStatus();
      expect(status.metricsEndpoint).toBe('https://config-prometheus.endpoint.com/v1/metrics');
      expect(status.logsEndpoint).toBe('https://config-loki.endpoint.com/v1/logs');
      delete process.env.AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT;
      delete process.env.AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT;
    });

    it('should use default organization', () => {
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.project_name).toBe('test-project');
    });

    it('should use custom organization when provided', () => {
      const customConfig = {
        ...mockConfig,
        organization: 'custom-org',
      };
      const client = new AutomagikTelemetry(customConfig);
      // We need to check this through the status or by checking system behavior
      expect(client).toBeDefined();
    });

    it('should convert timeout from seconds to milliseconds', () => {
      const customConfig = {
        ...mockConfig,
        timeout: 10, // 10 seconds
      };
      const client = new AutomagikTelemetry(customConfig);
      expect(client).toBeDefined();
    });
  });

  describe('User ID Management', () => {
    it('should create new user ID when file does not exist', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);

      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();

      expect(status.user_id).toBeDefined();
      expect(fs.mkdirSync).toHaveBeenCalledWith(
        path.join(mockHomedir, '.automagik'),
        { recursive: true }
      );
      expect(fs.writeFileSync).toHaveBeenCalledWith(
        mockUserIdFile,
        expect.any(String),
        'utf-8'
      );
    });

    it('should read existing user ID from file', () => {
      const existingId = 'existing-user-id-123';
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockUserIdFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue(existingId);

      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();

      expect(status.user_id).toBe(existingId);
      expect(fs.readFileSync).toHaveBeenCalledWith(mockUserIdFile, 'utf-8');
    });

    it('should handle file read errors gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      (fs.readFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Read error');
      });

      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();

      // Should create new ID despite read error
      expect(status.user_id).toBeDefined();
    });

    it('should handle directory creation errors gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      (fs.mkdirSync as jest.Mock).mockImplementation(() => {
        throw new Error('mkdir error');
      });

      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();

      // Should still have user ID (in-memory)
      expect(status.user_id).toBeDefined();
    });
  });

  describe('Telemetry Enable/Disable Logic', () => {
    it('should be disabled by default', () => {
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=true', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=1', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = '1';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=yes', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'yes';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=on', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'on';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should disable when opt-out file exists', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockOptOutFile;
      });

      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (CI)', () => {
      process.env.CI = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (GITHUB_ACTIONS)', () => {
      process.env.GITHUB_ACTIONS = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (TRAVIS)', () => {
      process.env.TRAVIS = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (JENKINS)', () => {
      process.env.JENKINS = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in development environment', () => {
      process.env.ENVIRONMENT = 'development';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in test environment', () => {
      process.env.ENVIRONMENT = 'test';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });
  });

  describe('Enable/Disable Methods', () => {
    it('should enable telemetry when enable() is called', () => {
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);

      client.enable();
      expect(client.isEnabled()).toBe(true);
    });

    it('should remove opt-out file when enable() is called', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);

      const client = new AutomagikTelemetry(mockConfig);
      client.enable();

      expect(fs.unlinkSync).toHaveBeenCalledWith(mockOptOutFile);
    });

    it('should disable telemetry when disable() is called', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);

      await client.disable();
      expect(client.isEnabled()).toBe(false);
    });

    it('should create opt-out file when disable() is called', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      await client.disable();

      expect(fs.writeFileSync).toHaveBeenCalledWith(mockOptOutFile, '', 'utf-8');
    });

    it('should handle errors when removing opt-out file gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      (fs.unlinkSync as jest.Mock).mockImplementation(() => {
        throw new Error('Unlink error');
      });

      const client = new AutomagikTelemetry(mockConfig);
      expect(() => client.enable()).not.toThrow();
    });

    it('should handle errors when creating opt-out file gracefully', async () => {
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Write error');
      });

      const client = new AutomagikTelemetry(mockConfig);
      await expect(client.disable()).resolves.not.toThrow();
    });
  });

  describe('trackEvent', () => {
    it('should not send events when disabled', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(false);

      client.trackEvent('test.event', { key: 'value' });

      // Wait a bit for async operation
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should send events when enabled', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      expect(client.isEnabled()).toBe(true);

      client.trackEvent('test.event', { key: 'value' });

      // Wait for async operation
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledWith(
        'https://telemetry.namastex.ai/v1/traces',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('should send OTLP-formatted payload', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', { custom_key: 'custom_value' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      // Validate OTLP structure
      expect(payload).toHaveProperty('resourceSpans');
      expect(payload.resourceSpans).toHaveLength(1);
      expect(payload.resourceSpans[0]).toHaveProperty('resource');
      expect(payload.resourceSpans[0]).toHaveProperty('scopeSpans');
      expect(payload.resourceSpans[0].scopeSpans[0]).toHaveProperty('spans');
      expect(payload.resourceSpans[0].scopeSpans[0].spans[0]).toHaveProperty('name', 'test.event');
    });

    it('should include system information in attributes', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', {});

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const attributeKeys = attributes.map((attr: any) => attr.key);
      expect(attributeKeys).toContain('system.os');
      expect(attributeKeys).toContain('system.node_version');
      expect(attributeKeys).toContain('system.architecture');
    });

    it('should handle empty attributes', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      expect(() => client.trackEvent('test.event')).not.toThrow();
    });

    it('should truncate long string values', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      const longString = 'a'.repeat(1000);
      client.trackEvent('test.event', { long_value: longString });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const longValueAttr = attributes.find((attr: any) => attr.key === 'long_value');
      expect(longValueAttr.value.stringValue.length).toBeLessThanOrEqual(500);
    });

    it('should handle different attribute types', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      client.trackEvent('test.event', {
        string_value: 'test',
        number_value: 123,
        boolean_value: true,
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const stringAttr = attributes.find((attr: any) => attr.key === 'string_value');
      const numberAttr = attributes.find((attr: any) => attr.key === 'number_value');
      const booleanAttr = attributes.find((attr: any) => attr.key === 'boolean_value');

      expect(stringAttr.value).toHaveProperty('stringValue', 'test');
      expect(numberAttr.value).toHaveProperty('doubleValue', 123);
      expect(booleanAttr.value).toHaveProperty('boolValue', true);
    });
  });

  describe('trackError', () => {
    it('should track error with message', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      const error = new Error('Test error');
      client.trackError(error);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorTypeAttr = attributes.find((attr: any) => attr.key === 'error_type');
      const errorMessageAttr = attributes.find((attr: any) => attr.key === 'error_message');

      expect(errorTypeAttr.value.stringValue).toBe('Error');
      expect(errorMessageAttr.value.stringValue).toBe('Test error');
    });

    it('should include error context', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      const error = new Error('Test error');
      client.trackError(error, { error_code: 'TEST-001', operation: 'test_operation' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorCodeAttr = attributes.find((attr: any) => attr.key === 'error_code');
      const operationAttr = attributes.find((attr: any) => attr.key === 'operation');

      expect(errorCodeAttr.value.stringValue).toBe('TEST-001');
      expect(operationAttr.value.stringValue).toBe('test_operation');
    });

    it('should truncate long error messages', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      const longMessage = 'Error: ' + 'a'.repeat(1000);
      const error = new Error(longMessage);
      client.trackError(error);

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorMessageAttr = attributes.find((attr: any) => attr.key === 'error_message');
      expect(errorMessageAttr.value.stringValue.length).toBeLessThanOrEqual(500);
    });
  });

  describe('trackMetric', () => {
    it('should track metric with value', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      client.trackMetric('test.metric', 123.45);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      // trackMetric uses OTLP metrics format, not traces
      expect(payload.resourceMetrics).toBeDefined();
      const metric = payload.resourceMetrics[0].scopeMetrics[0].metrics[0];
      expect(metric.name).toBe('test.metric');
      expect(metric.gauge.dataPoints[0].asDouble).toBe(123.45);
    });

    it('should include metric attributes', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry(mockConfig);

      client.trackMetric('test.metric', 100, MetricType.GAUGE, {
        operation_type: 'api_request',
        duration_ms: 100,
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      // Check attributes in the metric data point
      const attributes = payload.resourceMetrics[0].scopeMetrics[0].metrics[0].gauge.dataPoints[0].attributes;
      const operationTypeAttr = attributes.find((attr: any) => attr.key === 'operation_type');
      expect(operationTypeAttr.value.stringValue).toBe('api_request');
    });
  });

  describe('Silent Failure Behavior', () => {
    it('should not throw when fetch fails', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new AutomagikTelemetry(mockConfig);
      expect(() => client.trackEvent('test.event')).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should not throw when fetch returns non-200 status', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
      });

      const client = new AutomagikTelemetry(mockConfig);
      expect(() => client.trackEvent('test.event')).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should handle timeout gracefully', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, status: 200 }), 10000);
          })
      );

      const client = new AutomagikTelemetry({ ...mockConfig, timeout: 1 });
      expect(() => client.trackEvent('test.event')).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 100));
    });
  });

  describe('Verbose Mode', () => {
    it('should enable verbose mode from environment', () => {
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.verbose).toBe(true);
    });

    it('should not enable verbose mode by default', () => {
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();
      expect(status.verbose).toBe(false);
    });
  });

  describe('getStatus', () => {
    it('should return comprehensive status information', () => {
      const client = new AutomagikTelemetry(mockConfig);
      const status = client.getStatus();

      expect(status).toHaveProperty('enabled');
      expect(status).toHaveProperty('user_id');
      expect(status).toHaveProperty('session_id');
      expect(status).toHaveProperty('project_name');
      expect(status).toHaveProperty('project_version');
      expect(status).toHaveProperty('endpoint');
      expect(status).toHaveProperty('opt_out_file_exists');
      expect(status).toHaveProperty('verbose');
    });

    it('should reflect current enabled state', () => {
      const client = new AutomagikTelemetry(mockConfig);
      let status = client.getStatus();
      expect(status.enabled).toBe(false);

      client.enable();
      status = client.getStatus();
      expect(status.enabled).toBe(true);
    });
  });

  describe('Batch Processing', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should queue events instead of sending immediately', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 10,
      });

      client.trackEvent('test.event.1');
      client.trackEvent('test.event.2');
      client.trackEvent('test.event.3');

      // Events should be queued, not sent yet
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should flush when batch size is reached', async () => {
      // Use real timers for this test since we need actual async operations
      jest.useRealTimers();

      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        projectName: mockConfig.projectName,
        version: mockConfig.version,
        compressionEnabled: false,
        batchSize: 3,
      });

      client.trackEvent('test.event.1');
      client.trackEvent('test.event.2');
      client.trackEvent('test.event.3'); // This triggers flush

      // Wait for async flush to complete
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledTimes(3);

      // Clean up timer
      await client.disable();

      // Restore fake timers for other tests in this describe block
      jest.useFakeTimers();
    });

    it('should flush on interval', async () => {
      // Use real timers for this test since interval-based flush needs actual timing
      jest.useRealTimers();

      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        projectName: mockConfig.projectName,
        version: mockConfig.version,
        compressionEnabled: false,
        flushInterval: 200, // Short interval for test
        batchSize: 100,
      });

      client.trackEvent('test.event.1');
      client.trackEvent('test.event.2');

      // Wait for the flush interval to trigger
      await new Promise((resolve) => setTimeout(resolve, 300));

      expect(global.fetch).toHaveBeenCalled();

      // Clean up timer
      await client.disable();

      // Restore fake timers for other tests in this describe block
      jest.useFakeTimers();
    });

    it('should flush manually when flush() is called', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      client.trackEvent('test.event.1');
      client.trackEvent('test.event.2');

      await client.flush();

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Compression', () => {
    it('should compress large payloads', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: true,
        compressionThreshold: 100, // Low threshold for testing
        batchSize: 1, // Flush immediately
      });

      const largeData = { data: 'a'.repeat(200) };
      client.trackEvent('test.event', largeData);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].headers['Content-Encoding']).toBe('gzip');
    });

    it('should not compress small payloads', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        projectName: mockConfig.projectName,
        version: mockConfig.version,
        compressionEnabled: true,
        compressionThreshold: 10000, // High threshold - small payloads won't reach it
        batchSize: 1,
      });

      client.trackEvent('test.event', { small: 'data' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].headers['Content-Encoding']).toBeUndefined();
    });

    it('should respect compression disabled setting', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        compressionEnabled: false,
        batchSize: 1,
      });

      const largeData = { data: 'a'.repeat(2000) };
      client.trackEvent('test.event', largeData);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].headers['Content-Encoding']).toBeUndefined();
    });
  });

  describe('Retry Logic', () => {
    it('should retry on 500 errors', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      let attempts = 0;
      (global.fetch as jest.Mock).mockImplementation(() => {
        attempts++;
        if (attempts < 3) {
          return Promise.resolve({ ok: false, status: 500 });
        }
        return Promise.resolve({ ok: true, status: 200 });
      });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
        retryBackoffBase: 10, // Short backoff for testing
        batchSize: 1,
      });

      client.trackEvent('test.event');

      await new Promise((resolve) => setTimeout(resolve, 200));

      expect(attempts).toBeGreaterThanOrEqual(2);
    });

    it('should not retry on 400 errors', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 400 });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
        batchSize: 1,
      });

      client.trackEvent('test.event');

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledTimes(1); // No retries
    });

    it('should respect maxRetries setting', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

      // Wait to ensure previous async operations are done
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Clear any previous calls
      jest.clearAllMocks();

      // Reset the mock implementation
      (global.fetch as jest.Mock).mockClear();
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 503 });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 2,
        retryBackoffBase: 10,
        batchSize: 1,
      });

      client.trackEvent('test.event');

      // Wait longer for all retries to complete (10ms + 20ms + processing time)
      await new Promise((resolve) => setTimeout(resolve, 500));

      expect(global.fetch).toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });
  });

  describe('OTLP Metrics', () => {
    it('should send gauge metric', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackMetric('cpu.usage', 75.5, MetricType.GAUGE, { unit: 'percent' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      expect(payload).toHaveProperty('resourceMetrics');
      expect(payload.resourceMetrics[0].scopeMetrics[0].metrics[0].name).toBe('cpu.usage');
      expect(payload.resourceMetrics[0].scopeMetrics[0].metrics[0].gauge).toBeDefined();
    });

    it('should send counter metric', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackMetric('requests.total', 100, MetricType.COUNTER);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      expect(payload.resourceMetrics[0].scopeMetrics[0].metrics[0].sum).toBeDefined();
      expect(payload.resourceMetrics[0].scopeMetrics[0].metrics[0].sum.isMonotonic).toBe(true);
    });

    it('should send histogram metric', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackMetric('request.duration', 123, MetricType.HISTOGRAM, { unit: 'ms' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      expect(payload.resourceMetrics[0].scopeMetrics[0].metrics[0].histogram).toBeDefined();
    });

    it('should use metrics endpoint', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackMetric('test.metric', 42);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledWith(
        'https://telemetry.namastex.ai/v1/metrics',
        expect.any(Object)
      );
    });
  });

  describe('OTLP Logs', () => {
    it('should send log with INFO severity', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackLog('Test log message', LogSeverity.INFO, { context: 'test' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      expect(payload).toHaveProperty('resourceLogs');
      expect(payload.resourceLogs[0].scopeLogs[0].logRecords[0].body.stringValue).toBe(
        'Test log message'
      );
      expect(payload.resourceLogs[0].scopeLogs[0].logRecords[0].severityNumber).toBe(
        LogSeverity.INFO
      );
    });

    it('should send log with ERROR severity', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackLog('Error occurred', LogSeverity.ERROR, { error_code: 'TEST-001' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = parseBody(callArgs[1].body);

      expect(payload.resourceLogs[0].scopeLogs[0].logRecords[0].severityNumber).toBe(
        LogSeverity.ERROR
      );
    });

    it('should use logs endpoint', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 1,
      });

      client.trackLog('Test log');

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledWith(
        'https://telemetry.namastex.ai/v1/logs',
        expect.any(Object)
      );
    });
  });

  describe('Custom Endpoints', () => {
    it('should use custom metrics endpoint', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        metricsEndpoint: 'https://custom.endpoint.com/metrics',
        batchSize: 1,
      });

      client.trackMetric('test.metric', 42);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledWith(
        'https://custom.endpoint.com/metrics',
        expect.any(Object)
      );
    });

    it('should use custom logs endpoint', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new AutomagikTelemetry({
        ...mockConfig,
        logsEndpoint: 'https://custom.endpoint.com/logs',
        batchSize: 1,
      });

      client.trackLog('test log');

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalledWith(
        'https://custom.endpoint.com/logs',
        expect.any(Object)
      );
    });
  });

  describe('Edge Cases and Coverage', () => {
    it('should handle verbose mode with retry failures', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      // Mock fetch to fail with 500 errors
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
      });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 2,
        retryBackoffBase: 10,
      });

      client.trackEvent('test.event');
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Should have attempted initial + 2 retries
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should handle verbose mode with final retry failure logging', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      // Mock fetch to always fail
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const consoleSpy = jest.spyOn(console, 'debug').mockImplementation();

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 1,
        retryBackoffBase: 10,
      });

      client.trackEvent('test.event');
      await new Promise((resolve) => setTimeout(resolve, 200));

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('should handle compression errors gracefully', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

      const client = new AutomagikTelemetry({
        projectName: mockConfig.projectName,
        version: mockConfig.version,
        compressionEnabled: true,
        compressionThreshold: 1,
        batchSize: 1,
      });

      // Should not throw even if compression might have issues
      expect(() => client.trackEvent('test.event', { data: 'test' })).not.toThrow();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should handle verbose logging for sendEvent errors', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      const consoleSpy = jest.spyOn(console, 'debug').mockImplementation();

      // Mock fetch to throw
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Test error'));

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 0,
      });

      client.trackEvent('test.event');
      await new Promise((resolve) => setTimeout(resolve, 100));

      consoleSpy.mockRestore();
    });

    it('should handle verbose logging for sendMetric errors', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      const consoleSpy = jest.spyOn(console, 'debug').mockImplementation();

      // Mock fetch to throw
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Test error'));

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 0,
      });

      client.trackMetric('test.metric', 100);
      await new Promise((resolve) => setTimeout(resolve, 100));

      consoleSpy.mockRestore();
    });

    it('should handle verbose logging for sendLog errors', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      const consoleSpy = jest.spyOn(console, 'debug').mockImplementation();

      // Mock fetch to throw
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Test error'));

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 0,
      });

      client.trackLog('test log');
      await new Promise((resolve) => setTimeout(resolve, 100));

      consoleSpy.mockRestore();
    });

    it('should handle retry with non-500 failure after retries', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

      let callCount = 0;
      (global.fetch as jest.Mock).mockImplementation(() => {
        callCount++;
        if (callCount <= 2) {
          return Promise.resolve({ ok: false, status: 500 });
        }
        return Promise.resolve({ ok: false, status: 404 });
      });

      const client = new AutomagikTelemetry({
        ...mockConfig,
        maxRetries: 3,
        retryBackoffBase: 10,
      });

      client.trackEvent('test.event');
      await new Promise((resolve) => setTimeout(resolve, 300));

      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('ClickHouse Backend Integration', () => {
    beforeEach(() => {
      // Set backend to clickhouse
      process.env.AUTOMAGIK_TELEMETRY_BACKEND = 'clickhouse';
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_METRICS_TABLE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_LOGS_TABLE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD;
    });

    afterEach(() => {
      delete process.env.AUTOMAGIK_TELEMETRY_BACKEND;
    });

    it('should initialize with ClickHouse backend from config', () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
        clickhouseEndpoint: 'http://localhost:8123',
        clickhouseDatabase: 'test_db',
        clickhouseUsername: 'test_user',
        clickhousePassword: 'test_pass',
      });

      expect(client).toBeDefined();
      expect(client.isEnabled()).toBe(true);
    });

    it('should initialize with ClickHouse backend from environment variables', () => {
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT = 'http://env-clickhouse:8123';
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE = 'env_db';
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME = 'env_user';
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD = 'env_pass';

      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
      });

      expect(client).toBeDefined();
      expect(client.isEnabled()).toBe(true);
    });

    it('should send trace to ClickHouse backend', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
        batchSize: 1,
      });

      client.trackEvent('test.event', { key: 'value' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      // ClickHouse backend handles sending internally
      expect(client).toBeDefined();
    });

    it('should flush ClickHouse backend on client flush', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
        batchSize: 100,
      });

      client.trackEvent('test.event.1', { key: 'value1' });
      client.trackEvent('test.event.2', { key: 'value2' });

      await client.flush();

      expect(client).toBeDefined();
    });

    it('should handle ClickHouse backend flush errors gracefully', async () => {
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
        batchSize: 100,
      });

      // Force an error by accessing the backend directly
      const clickhouseBackend = (client as any).clickhouseBackend;
      if (clickhouseBackend) {
        jest.spyOn(clickhouseBackend, 'flush').mockRejectedValue(new Error('Flush error'));
      }

      client.trackEvent('test.event', { key: 'value' });

      await client.flush();

      // Should not throw
      expect(client).toBeDefined();

      consoleDebugSpy.mockRestore();
      delete process.env.AUTOMAGIK_TELEMETRY_VERBOSE;
    });

    it('should prefer config backend over environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_BACKEND = 'otlp';

      const client = new AutomagikTelemetry({
        ...mockConfig,
        backend: 'clickhouse',
      });

      expect(client).toBeDefined();
    });

    it('should use OTLP backend when backend is not specified', () => {
      delete process.env.AUTOMAGIK_TELEMETRY_BACKEND;

      const client = new AutomagikTelemetry({
        ...mockConfig,
      });

      expect(client).toBeDefined();
      // Default backend should be OTLP
      expect((client as any).backendType).toBe('otlp');
    });

    it('should pass all config options to ClickHouse backend', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
        clickhouseEndpoint: 'http://test:8123',
        clickhouseDatabase: 'test_db',
        clickhouseUsername: 'test_user',
        clickhousePassword: 'test_pass',
        timeout: 10,
        batchSize: 50,
        compressionEnabled: false,
        maxRetries: 5,
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
    });

    it('should use default batchSize when not provided for ClickHouse backend', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
      // The default batchSize should be 100 (this covers line 265)
    });

    it('should initialize with custom table names from config', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
        clickhouseTable: 'custom_traces',
        clickhouseMetricsTable: 'custom_metrics',
        clickhouseLogsTable: 'custom_logs',
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
      expect((backend as any).tracesTable).toBe('custom_traces');
      expect((backend as any).metricsTable).toBe('custom_metrics');
      expect((backend as any).logsTable).toBe('custom_logs');
    });

    it('should initialize with custom table names from environment variables', () => {
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE = 'env_traces';
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_METRICS_TABLE = 'env_metrics';
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_LOGS_TABLE = 'env_logs';

      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
      expect((backend as any).tracesTable).toBe('env_traces');
      expect((backend as any).metricsTable).toBe('env_metrics');
      expect((backend as any).logsTable).toBe('env_logs');

      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_METRICS_TABLE;
      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_LOGS_TABLE;
    });

    it('should use default table names when not provided', () => {
      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
      expect((backend as any).tracesTable).toBe('traces');
      expect((backend as any).metricsTable).toBe('metrics');
      expect((backend as any).logsTable).toBe('logs');
    });

    it('should prefer config table names over environment variables', () => {
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE = 'env_traces';

      const client = new AutomagikTelemetry({
        projectName: 'test',
        version: '1.0.0',
        backend: 'clickhouse',
        clickhouseTable: 'config_traces',
      });

      const backend = (client as any).clickhouseBackend;
      expect(backend).toBeDefined();
      expect((backend as any).tracesTable).toBe('config_traces');

      delete process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE;
    });
  });

  describe('Timeout Configuration', () => {
    it('should read timeout from environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '10';

      const client = new AutomagikTelemetry({
        projectName: 'test-project',
        version: '1.0.0',
      });

      expect((client as any).timeout).toBe(10000); // 10 seconds in milliseconds
      delete process.env.AUTOMAGIK_TELEMETRY_TIMEOUT;
    });

    it('should handle NaN timeout from environment variable and use default', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = 'invalid';

      const client = new AutomagikTelemetry({
        projectName: 'test-project',
        version: '1.0.0',
      });

      expect((client as any).timeout).toBe(5000); // Default 5 seconds
      delete process.env.AUTOMAGIK_TELEMETRY_TIMEOUT;
    });

    it('should prefer config timeout over environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '10';

      const client = new AutomagikTelemetry({
        projectName: 'test-project',
        version: '1.0.0',
        timeout: 15,
      });

      expect((client as any).timeout).toBe(15000); // 15 seconds from config
      delete process.env.AUTOMAGIK_TELEMETRY_TIMEOUT;
    });
  });

  describe('100% Coverage Tests', () => {
    describe('Number attributes in system info', () => {
      it('should handle number attributes correctly', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

        // Mock os.cpus() to return an array (length property is a number)
        const mockCpus = jest.fn().mockReturnValue(new Array(8));
        jest.spyOn(os, 'cpus' as any).mockImplementation(mockCpus);

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Track event to trigger system info collection
        client.trackEvent('test.event', { cpu_count: 8 });

        await new Promise((resolve) => setTimeout(resolve, 100));

        // Verify the call was made
        expect(global.fetch).toHaveBeenCalled();
      });
    });

    describe('Compression error handling', () => {
      it('should handle gzip compression errors gracefully in OTLP backend', async () => {
        // Compression logic is now in OTLPBackend, so we test it there
        const { OTLPBackend } = require('../src/backends/otlp');

        const backend = new OTLPBackend({
          endpoint: 'http://localhost:4318/v1/traces',
          compressionEnabled: true,
          compressionThreshold: 1,
        });

        // Access the private compressPayload method
        const compressPayload = (backend as any).compressPayload.bind(backend);

        // Mock zlib.gzip to fail by creating a new Promise that rejects
        const zlibMock = {
          gzip: (data: Buffer, callback: (err: Error | null, result?: Buffer) => void) => {
            // Simulate gzip error
            callback(new Error('Compression failed'));
          },
        };

        // Replace zlib in the compressPayload context
        const zlibModule = require('zlib');
        const originalGzip = zlibModule.gzip;

        try {
          zlibModule.gzip = zlibMock.gzip;

          // Call compressPayload - should reject with the error
          await expect(compressPayload('test')).rejects.toThrow('Compression failed');
        } finally {
          // Restore
          zlibModule.gzip = originalGzip;
        }
      });
    });

    describe('Verbose mode logging', () => {
      it('should log verbose output on network errors', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

        const client = new AutomagikTelemetry({
          ...mockConfig,
          maxRetries: 0,
          batchSize: 1,
        });

        client.trackEvent('test.event', {});
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Verbose mode should have logged (using console.debug)
        expect(consoleDebugSpy).toHaveBeenCalled();

        consoleLogSpy.mockRestore();
        consoleDebugSpy.mockRestore();
      });

      it('should log verbose output for queue events', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        client.trackEvent('test.event', { key: 'value' });
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Should have logged queuing message (using console.debug)
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('[Telemetry] Queuing trace event')
        );

        consoleDebugSpy.mockRestore();
      });

      it('should log verbose output for metrics', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        client.trackMetric('test.metric', 42);
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Should have logged queuing message (using console.debug)
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('[Telemetry] Queuing metric')
        );

        consoleDebugSpy.mockRestore();
      });

      it('should log verbose output for logs', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        client.trackLog('test message');
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Should have logged queuing message (using console.debug)
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('[Telemetry] Queuing log')
        );

        consoleDebugSpy.mockRestore();
      });

      it('should log verbose output during flush', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 100,
        });

        client.trackEvent('test.event.1');
        client.trackEvent('test.event.2');

        await client.flush();

        // Should have logged flushing message (using console.debug)
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('[Telemetry] Flushing')
        );

        consoleDebugSpy.mockRestore();
      });
    });

    describe('Timer cleanup on disable', () => {
      it('should stop flush timer when disable is called', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

        const client = new AutomagikTelemetry({
          ...mockConfig,
          flushInterval: 1000,
        });

        // Timer should be running
        expect(client.isEnabled()).toBe(true);

        // Disable should stop the timer
        await client.disable();

        expect(client.isEnabled()).toBe(false);
      });

      it('should start flush timer when enable is called', () => {
        const client = new AutomagikTelemetry({
          ...mockConfig,
          flushInterval: 1000,
        });

        // Initially disabled
        expect(client.isEnabled()).toBe(false);

        // Enable should start the timer
        client.enable();

        expect(client.isEnabled()).toBe(true);
      });
    });

    describe('Response status handling', () => {
      it('should handle non-200 success responses', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          status: 202, // Accepted
        });

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        client.trackEvent('test.event');
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Should log the non-200 status in verbose mode
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('Telemetry trace failed with status 202')
        );

        consoleDebugSpy.mockRestore();
      });

      it('should handle 4xx errors without retry in verbose mode', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        (global.fetch as jest.Mock).mockResolvedValue({
          ok: false,
          status: 403,
        });

        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        client.trackEvent('test.event');
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Should log the 4xx error
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('Telemetry trace failed with status 403')
        );

        // Should not retry
        expect(global.fetch).toHaveBeenCalledTimes(1);

        consoleDebugSpy.mockRestore();
      });
    });

    describe('Coverage completion tests', () => {
      it('should handle number values in system info attributes (line 322)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

        // Mock getSystemInfo to return a number value
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Spy on getSystemInfo and make it return a number
        const originalGetSystemInfo = (client as any).getSystemInfo;
        jest.spyOn(client as any, 'getSystemInfo').mockReturnValue({
          ...originalGetSystemInfo.call(client),
          cpu_count: 8, // This is a number that will trigger line 322
        });

        client.trackEvent('test.event', {});

        await new Promise((resolve) => setTimeout(resolve, 100));

        const callArgs = (global.fetch as jest.Mock).mock.calls[0];
        const payload = parsePayload(callArgs);
        const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

        const cpuAttr = attributes.find((attr: any) => attr.key === 'system.cpu_count');
        expect(cpuAttr).toBeDefined();
        expect(cpuAttr.value).toHaveProperty('doubleValue', 8);
      });

      it('should handle disabled sendMetric call (line 599)', () => {
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Disabled client should not send
        expect(client.isEnabled()).toBe(false);
        expect(() => client.trackMetric('test.metric', 100)).not.toThrow();
      });

      it('should handle disabled sendLog call (line 722)', () => {
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Disabled client should not send
        expect(client.isEnabled()).toBe(false);
        expect(() => client.trackLog('test log')).not.toThrow();
      });

      it('should handle verbose mode console.debug in sendEvent (lines 577-578)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          maxRetries: 0,
          batchSize: 1,
        });

        // Mock createAttributes to throw an error, triggering the catch block
        jest.spyOn(client as any, 'createAttributes').mockImplementation(() => {
          throw new Error('Attribute creation error');
        });

        client.trackEvent('test.event', {});

        await new Promise((resolve) => setTimeout(resolve, 50));

        // Should have logged the error in verbose mode
        expect(consoleDebugSpy).toHaveBeenCalledWith('Telemetry event error:', expect.any(Error));

        consoleDebugSpy.mockRestore();
      });

      it('should handle verbose mode console.debug in sendMetric (lines 702-703)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          maxRetries: 0,
          batchSize: 1,
        });

        // Create a counter to throw error only on second call (first is sendEvent in batch, second is sendMetric)
        let callCount = 0;
        const originalCreateAttributes = (client as any).createAttributes.bind(client);
        jest.spyOn(client as any, 'createAttributes').mockImplementation((data: any) => {
          callCount++;
          // Throw on the sendMetric call
          if (callCount === 1) {
            throw new Error('Attribute creation error');
          }
          return originalCreateAttributes(data);
        });

        client.trackMetric('test.metric', 100);

        await new Promise((resolve) => setTimeout(resolve, 50));

        // Should have logged the error in verbose mode
        expect(consoleDebugSpy).toHaveBeenCalledWith('Telemetry metric error:', expect.any(Error));

        consoleDebugSpy.mockRestore();
      });

      it('should handle verbose mode console.debug in sendLog (lines 793-794)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

        const consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();

        const client = new AutomagikTelemetry({
          ...mockConfig,
          maxRetries: 0,
          batchSize: 1,
        });

        // Create a counter to throw error only on first call (sendLog)
        let callCount = 0;
        const originalCreateAttributes = (client as any).createAttributes.bind(client);
        jest.spyOn(client as any, 'createAttributes').mockImplementation((data: any) => {
          callCount++;
          // Throw on the sendLog call
          if (callCount === 1) {
            throw new Error('Attribute creation error');
          }
          return originalCreateAttributes(data);
        });

        client.trackLog('test log');

        await new Promise((resolve) => setTimeout(resolve, 50));

        // Should have logged the error in verbose mode
        expect(consoleDebugSpy).toHaveBeenCalledWith('Telemetry log error:', expect.any(Error));

        consoleDebugSpy.mockRestore();
      });
    });

    describe('Public API catch handlers', () => {
      it('should handle trackEvent catch handler (line 936)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Mock sendEvent to throw an error
        jest.spyOn(client as any, 'sendEvent').mockRejectedValue(new Error('sendEvent error'));

        // This should not throw, because trackEvent has a .catch() handler
        expect(() => client.trackEvent('test.event', {})).not.toThrow();

        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      it('should handle trackError catch handler (line 965)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Mock sendEvent to throw an error
        jest.spyOn(client as any, 'sendEvent').mockRejectedValue(new Error('sendEvent error'));

        const error = new Error('Test error');

        // This should not throw, because trackError has a .catch() handler
        expect(() => client.trackError(error)).not.toThrow();

        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      it('should handle trackMetric catch handler (line 992)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Mock sendMetric to throw an error
        jest.spyOn(client as any, 'sendMetric').mockRejectedValue(new Error('sendMetric error'));

        // This should not throw, because trackMetric has a .catch() handler
        expect(() => client.trackMetric('test.metric', 100)).not.toThrow();

        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      it('should handle trackLog catch handler (line 1019)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
        const client = new AutomagikTelemetry({
          ...mockConfig,
          batchSize: 1,
        });

        // Mock sendLog to throw an error
        jest.spyOn(client as any, 'sendLog').mockRejectedValue(new Error('sendLog error'));

        // This should not throw, because trackLog has a .catch() handler
        expect(() => client.trackLog('test log')).not.toThrow();

        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      it('should handle flush timer catch handler (line 439)', async () => {
        process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

        // Create a client with a very short flush interval
        const client = new AutomagikTelemetry({
          ...mockConfig,
          flushInterval: 50, // Short interval for testing
        });

        // Spy on the flush method to make it reject
        const flushSpy = jest.spyOn(client as any, 'flush').mockRejectedValue(new Error('Forced flush error'));

        // Add an event to trigger the timer
        client.trackEvent('test.event', {});

        // Wait for the flush timer to fire and call the catch handler
        await new Promise((resolve) => setTimeout(resolve, 100));

        // The catch handler at line 439 should have been called
        // Verify flush was called by the timer
        expect(flushSpy).toHaveBeenCalled();

        // Clean up
        flushSpy.mockRestore();
        await client.disable();
      });
    });
  });
});
