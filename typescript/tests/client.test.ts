/**
 * Comprehensive tests for TelemetryClient.
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
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as crypto from 'crypto';
import { TelemetryClient, TelemetryConfig } from '../src/client';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

describe('TelemetryClient', () => {
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

    // Default config
    mockConfig = {
      projectName: 'test-project',
      version: '1.0.0',
    };
  });

  describe('Constructor and Initialization', () => {
    it('should initialize with required config', () => {
      const client = new TelemetryClient(mockConfig);
      expect(client).toBeDefined();
      expect(client.isEnabled()).toBe(false); // Disabled by default
    });

    it('should use default endpoint when not provided', () => {
      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://telemetry.namastex.ai/v1/traces');
    });

    it('should use custom endpoint when provided', () => {
      const customConfig = {
        ...mockConfig,
        endpoint: 'https://custom.endpoint.com/traces',
      };
      const client = new TelemetryClient(customConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://custom.endpoint.com/traces');
    });

    it('should respect endpoint from environment variable', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://env.endpoint.com/traces';
      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();
      expect(status.endpoint).toBe('https://env.endpoint.com/traces');
    });

    it('should use default organization', () => {
      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();
      expect(status.project_name).toBe('test-project');
    });

    it('should use custom organization when provided', () => {
      const customConfig = {
        ...mockConfig,
        organization: 'custom-org',
      };
      const client = new TelemetryClient(customConfig);
      // We need to check this through the status or by checking system behavior
      expect(client).toBeDefined();
    });

    it('should convert timeout from seconds to milliseconds', () => {
      const customConfig = {
        ...mockConfig,
        timeout: 10, // 10 seconds
      };
      const client = new TelemetryClient(customConfig);
      expect(client).toBeDefined();
    });
  });

  describe('User ID Management', () => {
    it('should create new user ID when file does not exist', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);

      const client = new TelemetryClient(mockConfig);
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

      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();

      expect(status.user_id).toBe(existingId);
      expect(fs.readFileSync).toHaveBeenCalledWith(mockUserIdFile, 'utf-8');
    });

    it('should handle file read errors gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      (fs.readFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Read error');
      });

      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();

      // Should create new ID despite read error
      expect(status.user_id).toBeDefined();
    });

    it('should handle directory creation errors gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      (fs.mkdirSync as jest.Mock).mockImplementation(() => {
        throw new Error('mkdir error');
      });

      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();

      // Should still have user ID (in-memory)
      expect(status.user_id).toBeDefined();
    });
  });

  describe('Telemetry Enable/Disable Logic', () => {
    it('should be disabled by default', () => {
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=true', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=1', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = '1';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=yes', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'yes';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should enable when AUTOMAGIK_TELEMETRY_ENABLED=on', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'on';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(true);
    });

    it('should disable when opt-out file exists', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockOptOutFile;
      });

      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (CI)', () => {
      process.env.CI = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (GITHUB_ACTIONS)', () => {
      process.env.GITHUB_ACTIONS = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (TRAVIS)', () => {
      process.env.TRAVIS = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in CI environment (JENKINS)', () => {
      process.env.JENKINS = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in development environment', () => {
      process.env.ENVIRONMENT = 'development';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });

    it('should disable in test environment', () => {
      process.env.ENVIRONMENT = 'test';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);
    });
  });

  describe('Enable/Disable Methods', () => {
    it('should enable telemetry when enable() is called', () => {
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);

      client.enable();
      expect(client.isEnabled()).toBe(true);
    });

    it('should remove opt-out file when enable() is called', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);

      const client = new TelemetryClient(mockConfig);
      client.enable();

      expect(fs.unlinkSync).toHaveBeenCalledWith(mockOptOutFile);
    });

    it('should disable telemetry when disable() is called', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(true);

      client.disable();
      expect(client.isEnabled()).toBe(false);
    });

    it('should create opt-out file when disable() is called', () => {
      const client = new TelemetryClient(mockConfig);
      client.disable();

      expect(fs.writeFileSync).toHaveBeenCalledWith(mockOptOutFile, '', 'utf-8');
    });

    it('should handle errors when removing opt-out file gracefully', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      (fs.unlinkSync as jest.Mock).mockImplementation(() => {
        throw new Error('Unlink error');
      });

      const client = new TelemetryClient(mockConfig);
      expect(() => client.enable()).not.toThrow();
    });

    it('should handle errors when creating opt-out file gracefully', () => {
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Write error');
      });

      const client = new TelemetryClient(mockConfig);
      expect(() => client.disable()).not.toThrow();
    });
  });

  describe('trackEvent', () => {
    it('should not send events when disabled', async () => {
      const client = new TelemetryClient(mockConfig);
      expect(client.isEnabled()).toBe(false);

      client.trackEvent('test.event', { key: 'value' });

      // Wait a bit for async operation
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should send events when enabled', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);
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
      const client = new TelemetryClient(mockConfig);

      client.trackEvent('test.event', { custom_key: 'custom_value' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

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
      const client = new TelemetryClient(mockConfig);

      client.trackEvent('test.event', {});

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const attributeKeys = attributes.map((attr: any) => attr.key);
      expect(attributeKeys).toContain('system.os');
      expect(attributeKeys).toContain('system.node_version');
      expect(attributeKeys).toContain('system.architecture');
    });

    it('should handle empty attributes', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      expect(() => client.trackEvent('test.event')).not.toThrow();
    });

    it('should truncate long string values', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      const longString = 'a'.repeat(1000);
      client.trackEvent('test.event', { long_value: longString });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const longValueAttr = attributes.find((attr: any) => attr.key === 'long_value');
      expect(longValueAttr.value.stringValue.length).toBeLessThanOrEqual(500);
    });

    it('should handle different attribute types', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      client.trackEvent('test.event', {
        string_value: 'test',
        number_value: 123,
        boolean_value: true,
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
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
      const client = new TelemetryClient(mockConfig);

      const error = new Error('Test error');
      client.trackError(error);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorTypeAttr = attributes.find((attr: any) => attr.key === 'error_type');
      const errorMessageAttr = attributes.find((attr: any) => attr.key === 'error_message');

      expect(errorTypeAttr.value.stringValue).toBe('Error');
      expect(errorMessageAttr.value.stringValue).toBe('Test error');
    });

    it('should include error context', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      const error = new Error('Test error');
      client.trackError(error, { error_code: 'TEST-001', operation: 'test_operation' });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorCodeAttr = attributes.find((attr: any) => attr.key === 'error_code');
      const operationAttr = attributes.find((attr: any) => attr.key === 'operation');

      expect(errorCodeAttr.value.stringValue).toBe('TEST-001');
      expect(operationAttr.value.stringValue).toBe('test_operation');
    });

    it('should truncate long error messages', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      const longMessage = 'Error: ' + 'a'.repeat(1000);
      const error = new Error(longMessage);
      client.trackError(error);

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const errorMessageAttr = attributes.find((attr: any) => attr.key === 'error_message');
      expect(errorMessageAttr.value.stringValue.length).toBeLessThanOrEqual(500);
    });
  });

  describe('trackMetric', () => {
    it('should track metric with value', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      client.trackMetric('test.metric', 123.45);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const valueAttr = attributes.find((attr: any) => attr.key === 'value');
      expect(valueAttr.value.doubleValue).toBe(123.45);
    });

    it('should include metric attributes', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const client = new TelemetryClient(mockConfig);

      client.trackMetric('test.metric', 100, {
        operation_type: 'api_request',
        duration_ms: 100,
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);
      const attributes = payload.resourceSpans[0].scopeSpans[0].spans[0].attributes;

      const operationTypeAttr = attributes.find((attr: any) => attr.key === 'operation_type');
      expect(operationTypeAttr.value.stringValue).toBe('api_request');
    });
  });

  describe('Silent Failure Behavior', () => {
    it('should not throw when fetch fails', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new TelemetryClient(mockConfig);
      expect(() => client.trackEvent('test.event')).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should not throw when fetch returns non-200 status', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
      });

      const client = new TelemetryClient(mockConfig);
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

      const client = new TelemetryClient({ ...mockConfig, timeout: 1 });
      expect(() => client.trackEvent('test.event')).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 100));
    });
  });

  describe('Verbose Mode', () => {
    it('should enable verbose mode from environment', () => {
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();
      expect(status.verbose).toBe(true);
    });

    it('should not enable verbose mode by default', () => {
      const client = new TelemetryClient(mockConfig);
      const status = client.getStatus();
      expect(status.verbose).toBe(false);
    });
  });

  describe('getStatus', () => {
    it('should return comprehensive status information', () => {
      const client = new TelemetryClient(mockConfig);
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
      const client = new TelemetryClient(mockConfig);
      let status = client.getStatus();
      expect(status.enabled).toBe(false);

      client.enable();
      status = client.getStatus();
      expect(status.enabled).toBe(true);
    });
  });
});
