/**
 * Comprehensive tests for configuration management.
 *
 * Tests cover:
 * - createConfig() functionality
 * - mergeConfig() behavior
 * - validateConfig() validation rules
 * - loadConfigFromEnv() environment parsing
 * - Environment variable handling
 * - Validation error messages
 * - Default values
 */

import {
  TelemetryConfig,
  ValidatedConfig,
  createConfig,
  mergeConfig,
  validateConfig,
  loadConfigFromEnv,
  DEFAULT_CONFIG,
  ENV_VARS,
} from '../src/config';

describe('Config Module', () => {
  let baseConfig: TelemetryConfig;

  beforeEach(() => {
    baseConfig = {
      projectName: 'test-project',
      version: '1.0.0',
    };
  });

  describe('DEFAULT_CONFIG', () => {
    it('should have correct default values', () => {
      expect(DEFAULT_CONFIG.endpoint).toBe('https://telemetry.namastex.ai/v1/traces');
      expect(DEFAULT_CONFIG.organization).toBe('namastex');
      expect(DEFAULT_CONFIG.timeout).toBe(5); // Timeout is in seconds
      expect(DEFAULT_CONFIG.enabled).toBe(false);
      expect(DEFAULT_CONFIG.verbose).toBe(false);
    });
  });

  describe('ENV_VARS', () => {
    it('should have correct environment variable names', () => {
      expect(ENV_VARS.ENABLED).toBe('AUTOMAGIK_TELEMETRY_ENABLED');
      expect(ENV_VARS.ENDPOINT).toBe('AUTOMAGIK_TELEMETRY_ENDPOINT');
      expect(ENV_VARS.VERBOSE).toBe('AUTOMAGIK_TELEMETRY_VERBOSE');
      expect(ENV_VARS.TIMEOUT).toBe('AUTOMAGIK_TELEMETRY_TIMEOUT');
    });
  });

  describe('loadConfigFromEnv', () => {
    it('should return empty config when no env vars set', () => {
      const config = loadConfigFromEnv();
      expect(config).toEqual({});
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=true', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=1', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = '1';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=yes', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'yes';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=on', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'on';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=false', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'false';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(false);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENABLED=0', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = '0';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(false);
    });

    it('should be case-insensitive for enabled flag', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'TRUE';
      const config = loadConfigFromEnv();
      expect(config.enabled).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_ENDPOINT', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://custom.endpoint.com/traces';
      const config = loadConfigFromEnv();
      expect(config.endpoint).toBe('https://custom.endpoint.com/traces');
    });

    it('should parse AUTOMAGIK_TELEMETRY_VERBOSE=true', () => {
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
      const config = loadConfigFromEnv();
      expect(config.verbose).toBe(true);
    });

    it('should parse AUTOMAGIK_TELEMETRY_VERBOSE=false', () => {
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'false';
      const config = loadConfigFromEnv();
      expect(config.verbose).toBe(false);
    });

    it('should parse AUTOMAGIK_TELEMETRY_TIMEOUT in seconds', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '10';
      const config = loadConfigFromEnv();
      expect(config.timeout).toBe(10);
    });

    it('should ignore invalid timeout value', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = 'invalid';
      const config = loadConfigFromEnv();
      expect(config.timeout).toBeUndefined();
    });

    it('should ignore negative timeout value', () => {
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '-100';
      const config = loadConfigFromEnv();
      expect(config.timeout).toBeUndefined();
    });

    it('should parse all environment variables together', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://custom.com';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '8000';

      const config = loadConfigFromEnv();

      expect(config.enabled).toBe(true);
      expect(config.endpoint).toBe('https://custom.com');
      expect(config.verbose).toBe(true);
      expect(config.timeout).toBe(8000);
    });
  });

  describe('validateConfig', () => {
    it('should not throw for valid config', () => {
      expect(() => validateConfig(baseConfig)).not.toThrow();
    });

    it('should throw when projectName is missing', () => {
      const invalidConfig = { ...baseConfig, projectName: '' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: projectName is required and cannot be empty'
      );
    });

    it('should throw when projectName is whitespace only', () => {
      const invalidConfig = { ...baseConfig, projectName: '   ' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: projectName is required and cannot be empty'
      );
    });

    it('should throw when version is missing', () => {
      const invalidConfig = { ...baseConfig, version: '' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: version is required and cannot be empty'
      );
    });

    it('should throw when version is whitespace only', () => {
      const invalidConfig = { ...baseConfig, version: '   ' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: version is required and cannot be empty'
      );
    });

    it('should throw for invalid endpoint URL', () => {
      const invalidConfig = { ...baseConfig, endpoint: 'not-a-url' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: endpoint must be a valid URL (got: not-a-url)'
      );
    });

    it('should throw for non-HTTP endpoint protocol', () => {
      const invalidConfig = { ...baseConfig, endpoint: 'ftp://example.com' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: endpoint must use http or https protocol'
      );
    });

    it('should throw for websocket protocol', () => {
      const invalidConfig = { ...baseConfig, endpoint: 'ws://example.com' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: endpoint must use http or https protocol'
      );
    });

    it('should accept valid HTTP endpoint', () => {
      const validConfig = { ...baseConfig, endpoint: 'http://localhost:8080/traces' };
      expect(() => validateConfig(validConfig)).not.toThrow();
    });

    it('should accept valid HTTPS endpoint', () => {
      const validConfig = { ...baseConfig, endpoint: 'https://telemetry.example.com/v1/traces' };
      expect(() => validateConfig(validConfig)).not.toThrow();
    });

    it('should accept decimal timeout values (fractional seconds)', () => {
      const validConfig = { ...baseConfig, timeout: 5.5 };
      expect(() => validateConfig(validConfig)).not.toThrow();
    });

    it('should throw for negative timeout', () => {
      const invalidConfig = { ...baseConfig, timeout: -100 };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: timeout must be a positive number in seconds'
      );
    });

    it('should throw for zero timeout', () => {
      const invalidConfig = { ...baseConfig, timeout: 0 };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: timeout must be a positive number in seconds'
      );
    });

    it('should throw for timeout exceeding maximum (60 seconds)', () => {
      const invalidConfig = { ...baseConfig, timeout: 70 };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: timeout should not exceed 60 seconds'
      );
    });

    it('should accept valid timeout values in seconds', () => {
      const validConfig1 = { ...baseConfig, timeout: 1 };
      const validConfig2 = { ...baseConfig, timeout: 30 };
      const validConfig3 = { ...baseConfig, timeout: 60 };
      const validConfig4 = { ...baseConfig, timeout: 5.5 }; // Fractional seconds allowed

      expect(() => validateConfig(validConfig1)).not.toThrow();
      expect(() => validateConfig(validConfig2)).not.toThrow();
      expect(() => validateConfig(validConfig3)).not.toThrow();
      expect(() => validateConfig(validConfig4)).not.toThrow();
    });

    it('should throw for empty organization', () => {
      const invalidConfig = { ...baseConfig, organization: '   ' };
      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: organization cannot be empty if provided'
      );
    });

    it('should accept valid organization', () => {
      const validConfig = { ...baseConfig, organization: 'custom-org' };
      expect(() => validateConfig(validConfig)).not.toThrow();
    });

    it('should accept config without optional fields', () => {
      const minimalConfig = {
        projectName: 'test',
        version: '1.0.0',
      };
      expect(() => validateConfig(minimalConfig)).not.toThrow();
    });
  });

  describe('mergeConfig', () => {
    it('should merge user config with defaults', () => {
      const merged = mergeConfig(baseConfig);

      expect(merged.projectName).toBe('test-project');
      expect(merged.version).toBe('1.0.0');
      expect(merged.endpoint).toBe(DEFAULT_CONFIG.endpoint);
      expect(merged.organization).toBe(DEFAULT_CONFIG.organization);
      expect(merged.timeout).toBe(DEFAULT_CONFIG.timeout);
      expect(merged.enabled).toBe(DEFAULT_CONFIG.enabled);
      expect(merged.verbose).toBe(DEFAULT_CONFIG.verbose);
    });

    it('should prefer user-provided values over defaults', () => {
      const customConfig = {
        ...baseConfig,
        endpoint: 'https://custom.endpoint.com',
        organization: 'custom-org',
        timeout: 10, // seconds
        enabled: true,
        verbose: true,
      };

      const merged = mergeConfig(customConfig);

      expect(merged.endpoint).toBe('https://custom.endpoint.com');
      expect(merged.organization).toBe('custom-org');
      expect(merged.timeout).toBe(10); // seconds
      expect(merged.enabled).toBe(true);
      expect(merged.verbose).toBe(true);
    });

    it('should prefer user config over env vars', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://env.endpoint.com';

      const customConfig = {
        ...baseConfig,
        enabled: false,
        endpoint: 'https://user.endpoint.com',
      };

      const merged = mergeConfig(customConfig);

      expect(merged.enabled).toBe(false);
      expect(merged.endpoint).toBe('https://user.endpoint.com');
    });

    it('should prefer env vars over defaults', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '8';

      const merged = mergeConfig(baseConfig);

      expect(merged.enabled).toBe(true);
      expect(merged.verbose).toBe(true);
      expect(merged.timeout).toBe(8); // seconds
    });

    it('should handle all priority levels correctly', () => {
      // Setup: Default (5 seconds) < Env (8 seconds) < User (10 seconds)
      process.env.AUTOMAGIK_TELEMETRY_TIMEOUT = '8';

      const configWithTimeout = {
        ...baseConfig,
        timeout: 10, // User override (seconds)
      };

      const merged = mergeConfig(configWithTimeout);
      expect(merged.timeout).toBe(10); // User value wins

      const configWithoutTimeout = baseConfig;
      const mergedWithEnv = mergeConfig(configWithoutTimeout);
      expect(mergedWithEnv.timeout).toBe(8); // Env value wins over default
    });

    it('should preserve all required fields', () => {
      const merged = mergeConfig(baseConfig);

      expect(merged).toHaveProperty('projectName');
      expect(merged).toHaveProperty('version');
      expect(merged).toHaveProperty('endpoint');
      expect(merged).toHaveProperty('organization');
      expect(merged).toHaveProperty('timeout');
      expect(merged).toHaveProperty('enabled');
      expect(merged).toHaveProperty('verbose');
    });
  });

  describe('createConfig', () => {
    it('should create valid config from minimal input', () => {
      const config = createConfig(baseConfig);

      expect(config.projectName).toBe('test-project');
      expect(config.version).toBe('1.0.0');
      expect(config.endpoint).toBe(DEFAULT_CONFIG.endpoint);
      expect(config.organization).toBe(DEFAULT_CONFIG.organization);
      expect(config.timeout).toBe(DEFAULT_CONFIG.timeout);
      expect(config.enabled).toBe(DEFAULT_CONFIG.enabled);
      expect(config.verbose).toBe(DEFAULT_CONFIG.verbose);
    });

    it('should validate and merge config', () => {
      const customConfig = {
        projectName: 'my-project',
        version: '2.0.0',
        endpoint: 'https://custom.endpoint.com',
        timeout: 10, // seconds
      };

      const config = createConfig(customConfig);

      expect(config.projectName).toBe('my-project');
      expect(config.version).toBe('2.0.0');
      expect(config.endpoint).toBe('https://custom.endpoint.com');
      expect(config.timeout).toBe(10); // seconds
    });

    it('should throw validation errors', () => {
      const invalidConfig = {
        projectName: '',
        version: '1.0.0',
      };

      expect(() => createConfig(invalidConfig)).toThrow(
        'TelemetryConfig: projectName is required and cannot be empty'
      );
    });

    it('should throw for invalid endpoint in complete flow', () => {
      const invalidConfig = {
        ...baseConfig,
        endpoint: 'invalid-url',
      };

      expect(() => createConfig(invalidConfig)).toThrow();
    });

    it('should throw for invalid timeout in complete flow', () => {
      const invalidConfig = {
        ...baseConfig,
        timeout: -100,
      };

      expect(() => createConfig(invalidConfig)).toThrow();
    });

    it('should respect environment variables', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'https://env.endpoint.com';

      const config = createConfig(baseConfig);

      expect(config.enabled).toBe(true);
      expect(config.endpoint).toBe('https://env.endpoint.com');
    });

    it('should create consistent config objects', () => {
      const config1 = createConfig(baseConfig);
      const config2 = createConfig(baseConfig);

      expect(config1).toEqual(config2);
    });

    it('should handle all optional fields', () => {
      const fullConfig = {
        projectName: 'test',
        version: '1.0.0',
        endpoint: 'https://custom.com',
        organization: 'custom-org',
        timeout: 15, // seconds
        enabled: true,
        verbose: true,
      };

      const config = createConfig(fullConfig);

      expect(config.endpoint).toBe('https://custom.com');
      expect(config.organization).toBe('custom-org');
      expect(config.timeout).toBe(15); // seconds
      expect(config.enabled).toBe(true);
      expect(config.verbose).toBe(true);
    });

    it('should throw TypeError with helpful message for malformed URL', () => {
      // Mock URL constructor to throw TypeError
      const originalURL = global.URL;
      global.URL = jest.fn().mockImplementation(() => {
        throw new TypeError('Invalid URL');
      }) as any;

      const invalidConfig = { ...baseConfig, endpoint: 'totally-invalid-url' };

      expect(() => validateConfig(invalidConfig)).toThrow(
        'TelemetryConfig: endpoint must be a valid URL (got: totally-invalid-url)'
      );

      // Restore original URL
      global.URL = originalURL;
    });

    it('should rethrow non-TypeError errors from URL constructor', () => {
      // Mock URL constructor to throw a non-TypeError
      const originalURL = global.URL;
      global.URL = jest.fn().mockImplementation(() => {
        throw new Error('Some other error');
      }) as any;

      const invalidConfig = { ...baseConfig, endpoint: 'test' };

      expect(() => validateConfig(invalidConfig)).toThrow('Some other error');

      // Restore original URL
      global.URL = originalURL;
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete workflow with env vars', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

      const userConfig = {
        projectName: 'integration-test',
        version: '1.0.0',
        timeout: 8, // seconds
      };

      const config = createConfig(userConfig);

      expect(config.projectName).toBe('integration-test');
      expect(config.version).toBe('1.0.0');
      expect(config.timeout).toBe(8); // seconds
      expect(config.enabled).toBe(true);
      expect(config.verbose).toBe(true);
      expect(config.organization).toBe(DEFAULT_CONFIG.organization);
      expect(config.endpoint).toBe(DEFAULT_CONFIG.endpoint);
    });

    it('should handle complete workflow without env vars', () => {
      const userConfig = {
        projectName: 'integration-test',
        version: '1.0.0',
      };

      const config = createConfig(userConfig);

      expect(config.projectName).toBe('integration-test');
      expect(config.version).toBe('1.0.0');
      expect(config.enabled).toBe(false);
      expect(config.verbose).toBe(false);
      expect(config.timeout).toBe(DEFAULT_CONFIG.timeout);
    });
  });
});
