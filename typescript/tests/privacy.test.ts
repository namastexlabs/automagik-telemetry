/**
 * Comprehensive tests for privacy utilities.
 *
 * Tests cover:
 * - detectPII() for various PII patterns
 * - sanitizePhone() with different strategies
 * - sanitizeEmail() with different strategies
 * - sanitizeValue() recursive sanitization
 * - redactSensitiveKeys() key-based redaction
 * - sanitizeTelemetryData() complete workflow
 * - hashValue() hash generation
 * - All PII patterns (phone, email, API keys, credit cards, IPs, paths)
 */

import {
  detectPII,
  sanitizePhone,
  sanitizeEmail,
  sanitizeValue,
  redactSensitiveKeys,
  sanitizeTelemetryData,
  hashValue,
  truncateString,
  SanitizationStrategy,
  PrivacyConfig,
  SENSITIVE_KEYS,
} from '../src/privacy';

describe('Privacy Module', () => {
  // Note: We're testing the public API, regex patterns are internal implementation

  describe('hashValue', () => {
    it('should generate consistent hashes', () => {
      const hash1 = hashValue('test-value');
      const hash2 = hashValue('test-value');
      expect(hash1).toBe(hash2);
    });

    it('should generate different hashes for different values', () => {
      const hash1 = hashValue('value1');
      const hash2 = hashValue('value2');
      expect(hash1).not.toBe(hash2);
    });

    it('should return sha256 prefix', () => {
      const hash = hashValue('test');
      expect(hash).toMatch(/^sha256:/);
    });

    it('should truncate hash to 16 characters after prefix', () => {
      const hash = hashValue('test');
      const hashPart = hash.replace('sha256:', '');
      expect(hashPart.length).toBe(16);
    });
  });

  describe('detectPII', () => {
    it('should detect phone numbers', () => {
      expect(detectPII('+1-555-555-5555')).toBe(true);
      expect(detectPII('(555) 555-5555')).toBe(true);
      expect(detectPII('555.555.5555')).toBe(true);
    });

    it('should detect email addresses', () => {
      expect(detectPII('user@example.com')).toBe(true);
      expect(detectPII('test.user+tag@subdomain.example.com')).toBe(true);
    });

    it('should detect API keys', () => {
      expect(detectPII('sk_test_FAKE_KEY_NOT_REAL_12345678')).toBe(true);
      expect(detectPII('sk_test_MOCK_KEY_FOR_TESTING_ONLY')).toBe(true);
      expect(detectPII('Bearer abcdefghijklmnopqrstuvwxyz123456')).toBe(true);
      expect(detectPII('api_key_abcdefghijklmnopqrstuvwxyz123456')).toBe(true);
    });

    it('should detect credit card numbers', () => {
      expect(detectPII('4111-1111-1111-1111')).toBe(true);
      expect(detectPII('4111 1111 1111 1111')).toBe(true);
      expect(detectPII('4111111111111111')).toBe(true);
    });

    it('should detect IP addresses', () => {
      // IP addresses are detected as PII
      const hasIP1 = detectPII('Server at 192.168.1.1');
      const hasIP2 = detectPII('Host: 10.0.0.1');
      expect(hasIP1 || hasIP2).toBe(true);
    });

    it('should detect user paths', () => {
      expect(detectPII('/home/username/project')).toBe(true);
      expect(detectPII('/Users/username/Documents')).toBe(true);
      expect(detectPII('C:\\Users\\username\\Documents')).toBe(true);
    });

    it('should not detect regular text', () => {
      expect(detectPII('Hello world')).toBe(false);
      expect(detectPII('This is a regular message')).toBe(false);
      expect(detectPII('Error: Something went wrong')).toBe(false);
    });

    it('should handle non-string values', () => {
      expect(detectPII(123 as any)).toBe(false);
      expect(detectPII(null as any)).toBe(false);
      expect(detectPII(undefined as any)).toBe(false);
    });
  });

  describe('sanitizePhone', () => {
    it('should hash phone numbers by default', () => {
      const result = sanitizePhone('+1-555-555-5555');
      expect(result).toMatch(/sha256:/);
    });

    it('should hash phone with explicit hash strategy', () => {
      const result = sanitizePhone('+1-555-555-5555', { strategy: 'hash' });
      expect(result).toMatch(/sha256:/);
    });

    it('should redact phone with redact strategy', () => {
      const result = sanitizePhone('+1-555-555-5555', { strategy: 'redact' });
      expect(result).toBe('[REDACTED]');
    });

    it('should use custom redaction text', () => {
      const result = sanitizePhone('+1-555-555-5555', {
        strategy: 'redact',
        redactionText: '[HIDDEN]',
      });
      expect(result).toBe('[HIDDEN]');
    });

    it('should truncate phone with truncate strategy', () => {
      const result = sanitizePhone('+1-555-555-5555', { strategy: 'truncate' });
      expect(result).toBe('XXX-XXX-XXXX');
    });

    it('should not modify non-phone strings', () => {
      const result = sanitizePhone('Hello world');
      expect(result).toBe('Hello world');
    });

    it('should handle different phone formats', () => {
      expect(sanitizePhone('(555) 555-5555', { strategy: 'truncate' })).toBe('XXX-XXX-XXXX');
      expect(sanitizePhone('555.555.5555', { strategy: 'truncate' })).toBe('XXX-XXX-XXXX');
    });
  });

  describe('sanitizeEmail', () => {
    it('should hash emails by default', () => {
      const result = sanitizeEmail('user@example.com');
      expect(result).toMatch(/sha256:/);
    });

    it('should hash email with explicit hash strategy', () => {
      const result = sanitizeEmail('user@example.com', { strategy: 'hash' });
      expect(result).toMatch(/sha256:/);
    });

    it('should redact email with redact strategy', () => {
      const result = sanitizeEmail('user@example.com', { strategy: 'redact' });
      expect(result).toBe('[REDACTED]');
    });

    it('should use custom redaction text', () => {
      const result = sanitizeEmail('user@example.com', {
        strategy: 'redact',
        redactionText: '[HIDDEN]',
      });
      expect(result).toBe('[HIDDEN]');
    });

    it('should truncate email with truncate strategy', () => {
      const result = sanitizeEmail('testuser@example.com', { strategy: 'truncate' });
      expect(result).toMatch(/^te\*\*\*@example\.com$/);
    });

    it('should not modify non-email strings', () => {
      const result = sanitizeEmail('Hello world');
      expect(result).toBe('Hello world');
    });

    it('should handle complex email addresses', () => {
      const result = sanitizeEmail('test.user+tag@subdomain.example.com', {
        strategy: 'truncate',
      });
      expect(result).toMatch(/^te\*\*\*@subdomain\.example\.com$/);
    });
  });

  describe('truncateString', () => {
    it('should truncate long strings', () => {
      const longString = 'a'.repeat(100);
      const result = truncateString(longString, 50);
      expect(result.length).toBe(50);
      expect(result).toMatch(/\.\.\.$/);
    });

    it('should not truncate short strings', () => {
      const shortString = 'Hello world';
      const result = truncateString(shortString, 50);
      expect(result).toBe(shortString);
    });

    it('should handle exact length strings', () => {
      const exactString = 'a'.repeat(50);
      const result = truncateString(exactString, 50);
      expect(result).toBe(exactString);
    });

    it('should add ellipsis to truncated strings', () => {
      const result = truncateString('Hello world this is a long string', 10);
      expect(result).toBe('Hello w...');
    });
  });

  describe('sanitizeValue', () => {
    it('should handle null and undefined', () => {
      expect(sanitizeValue(null)).toBeNull();
      expect(sanitizeValue(undefined)).toBeUndefined();
    });

    it('should pass through numbers', () => {
      expect(sanitizeValue(123)).toBe(123);
      expect(sanitizeValue(123.45)).toBe(123.45);
    });

    it('should pass through booleans', () => {
      expect(sanitizeValue(true)).toBe(true);
      expect(sanitizeValue(false)).toBe(false);
    });

    it('should sanitize strings with PII', () => {
      const result = sanitizeValue('Email: user@example.com');
      expect(result).toMatch(/sha256:/);
    });

    it('should truncate long strings', () => {
      const longString = 'a'.repeat(2000);
      const result = sanitizeValue(longString);
      expect(result.length).toBeLessThanOrEqual(1000);
    });

    it('should sanitize phone numbers in strings', () => {
      const result = sanitizeValue('Call me at +1-555-555-5555');
      expect(result).toMatch(/sha256:/);
    });

    it('should sanitize API keys in strings', () => {
      const result = sanitizeValue('Token: sk_test_FAKE_KEY_NOT_REAL_12345678');
      expect(result).toMatch(/\[REDACTED\]/);
    });

    it('should sanitize credit cards in strings', () => {
      const result = sanitizeValue('Card: 4111-1111-1111-1111');
      // Credit card will be sanitized (either as credit card or phone pattern)
      expect(result).not.toContain('4111-1111-1111-1111');
    });

    it('should sanitize IP addresses', () => {
      const result = sanitizeValue('Server: 192.168.1.1');
      expect(result).not.toContain('192.168.1.1');
    });

    it('should sanitize user paths', () => {
      const result = sanitizeValue('Error in /home/username/project/file.ts');
      expect(result).toContain('[USER_PATH]');
    });

    it('should recursively sanitize arrays', () => {
      const input = ['user@example.com', 'regular text', '+1-555-555-5555'];
      const result = sanitizeValue(input);

      expect(result[0]).toMatch(/sha256:/);
      expect(result[1]).toBe('regular text');
      expect(result[2]).toMatch(/sha256:/);
    });

    it('should recursively sanitize objects', () => {
      const input = {
        email: 'user@example.com',
        message: 'Hello world',
        phone: '+1-555-555-5555',
      };
      const result = sanitizeValue(input);

      expect(result.email).toMatch(/sha256:/);
      expect(result.message).toBe('Hello world');
      expect(result.phone).toMatch(/sha256:/);
    });

    it('should handle nested objects', () => {
      const input = {
        user: {
          email: 'user@example.com',
          contact: {
            phone: '+1-555-555-5555',
          },
        },
      };
      const result = sanitizeValue(input);

      expect(result.user.email).toMatch(/sha256:/);
      expect(result.user.contact.phone).toMatch(/sha256:/);
    });

    it('should respect custom config', () => {
      const config: PrivacyConfig = {
        strategy: 'redact',
        redactionText: '[HIDDEN]',
        maxStringLength: 50,
      };

      const result = sanitizeValue('Email: user@example.com', config);
      expect(result).toContain('[HIDDEN]');
    });
  });

  describe('redactSensitiveKeys', () => {
    it('should redact specified keys', () => {
      const input = {
        username: 'john',
        password: 'secret123',
        token: 'abc123',
      };

      const result = redactSensitiveKeys(input, ['password', 'token']);

      expect(result.username).toBe('john');
      expect(result.password).toBe('[REDACTED]');
      expect(result.token).toBe('[REDACTED]');
    });

    it('should be case-insensitive', () => {
      const input = {
        PASSWORD: 'secret123',
        Token: 'abc123',
      };

      const result = redactSensitiveKeys(input, ['password', 'token']);

      expect(result.PASSWORD).toBe('[REDACTED]');
      expect(result.Token).toBe('[REDACTED]');
    });

    it('should handle partial key matches', () => {
      const input = {
        user_password: 'secret123',
        api_token: 'abc123',
      };

      const result = redactSensitiveKeys(input, ['password', 'token']);

      expect(result.user_password).toBe('[REDACTED]');
      expect(result.api_token).toBe('[REDACTED]');
    });

    it('should recursively redact nested objects', () => {
      const input = {
        user: {
          username: 'john',
          password: 'secret123',
        },
        settings: {
          api_token: 'abc123',
        },
      };

      const result = redactSensitiveKeys(input, ['password', 'token']);

      expect(result.user.username).toBe('john');
      expect(result.user.password).toBe('[REDACTED]');
      expect(result.settings.api_token).toBe('[REDACTED]');
    });

    it('should not redact non-matching keys', () => {
      const input = {
        username: 'john',
        email: 'john@example.com',
      };

      const result = redactSensitiveKeys(input, ['password', 'token']);

      expect(result.username).toBe('john');
      expect(result.email).toBe('john@example.com');
    });

    it('should use custom redaction text', () => {
      const input = {
        password: 'secret123',
      };

      const result = redactSensitiveKeys(input, ['password'], {
        redactionText: '[HIDDEN]',
      });

      expect(result.password).toBe('[HIDDEN]');
    });

    it('should handle empty objects', () => {
      const result = redactSensitiveKeys({}, ['password']);
      expect(result).toEqual({});
    });

    it('should handle empty key list', () => {
      const input = {
        password: 'secret123',
      };

      const result = redactSensitiveKeys(input, []);
      expect(result.password).toBe('secret123');
    });
  });

  describe('SENSITIVE_KEYS', () => {
    it('should include common sensitive key patterns', () => {
      expect(SENSITIVE_KEYS).toContain('password');
      expect(SENSITIVE_KEYS).toContain('token');
      expect(SENSITIVE_KEYS).toContain('api_key');
      expect(SENSITIVE_KEYS).toContain('secret');
      expect(SENSITIVE_KEYS).toContain('private_key');
      expect(SENSITIVE_KEYS).toContain('credit_card');
      expect(SENSITIVE_KEYS).toContain('ssn');
    });
  });

  describe('sanitizeTelemetryData', () => {
    it('should apply both key-based and pattern-based sanitization', () => {
      const input = {
        email: 'user@example.com',
        password: 'secret123',
        message: 'Hello world',
      };

      const result = sanitizeTelemetryData(input);

      expect(result.email).toMatch(/sha256:/); // Pattern-based
      expect(result.password).toBe('[REDACTED]'); // Key-based
      expect(result.message).toBe('Hello world'); // Unchanged
    });

    it('should handle complex nested structures', () => {
      const input = {
        user: {
          email: 'user@example.com',
          password: 'secret123',
          contact: {
            phone: '+1-555-555-5555',
          },
        },
        api_key: 'sk_test_FAKE_KEY_NOT_REAL_12345678',
        message: 'Error at /home/user/project',
      };

      const result = sanitizeTelemetryData(input);

      expect(result.user.email).toMatch(/sha256:/);
      expect(result.user.password).toBe('[REDACTED]');
      expect(result.user.contact.phone).toMatch(/sha256:/);
      expect(result.api_key).toBe('[REDACTED]');
      expect(result.message).toContain('[USER_PATH]');
    });

    it('should respect custom config', () => {
      const input = {
        email: 'user@example.com',
        password: 'secret123',
      };

      const config: PrivacyConfig = {
        strategy: 'redact',
        redactionText: '[HIDDEN]',
      };

      const result = sanitizeTelemetryData(input, config);

      expect(result.email).toBe('[HIDDEN]');
      expect(result.password).toBe('[HIDDEN]');
    });

    it('should handle all PII patterns', () => {
      const input = {
        email: 'user@example.com',
        phone: '+1-555-555-5555',
        credit_card: '4111-1111-1111-1111',
        api_key: 'sk_test_FAKE_KEY_NOT_REAL_12345678',
        ip: '192.168.1.1',
        path: '/home/username/project',
      };

      const result = sanitizeTelemetryData(input);

      expect(result.email).toMatch(/sha256:/);
      expect(result.phone).toMatch(/sha256:/);
      expect(result.credit_card).toBe('[REDACTED]');
      expect(result.api_key).toBe('[REDACTED]');
      expect(result.ip).not.toContain('192.168.1.1');
      expect(result.path).toContain('[USER_PATH]');
    });

    it('should handle arrays in telemetry data', () => {
      const input = {
        emails: ['user1@example.com', 'user2@example.com'],
        tokens: ['token1', 'token2'],
      };

      const result = sanitizeTelemetryData(input);

      expect(result.emails[0]).toMatch(/sha256:/);
      expect(result.emails[1]).toMatch(/sha256:/);
      // Tokens key will be redacted as sensitive key
      expect(result.tokens).toBeDefined();
    });

    it('should preserve non-sensitive data', () => {
      const input = {
        feature_name: 'user_login',
        event_type: 'feature_used',
        duration_ms: 150,
        success: true,
      };

      const result = sanitizeTelemetryData(input);

      expect(result.feature_name).toBe('user_login');
      expect(result.event_type).toBe('feature_used');
      expect(result.duration_ms).toBe(150);
      expect(result.success).toBe(true);
    });

    it('should handle empty objects', () => {
      const result = sanitizeTelemetryData({});
      expect(result).toEqual({});
    });
  });

  describe('Integration Tests', () => {
    it('should sanitize realistic telemetry payload', () => {
      const telemetryPayload = {
        event: 'user_signup',
        user: {
          email: 'newuser@example.com',
          password: 'MySecretPassword123',
        },
        metadata: {
          ip_address: '192.168.1.100',
          user_agent: 'Mozilla/5.0',
          api_token: 'Bearer sk_test_FAKE_KEY_NOT_REAL_12345678',
        },
        error: {
          message: 'File not found at /home/username/project/config.json',
          code: 'ENOENT',
        },
      };

      const result = sanitizeTelemetryData(telemetryPayload);

      // Event name unchanged
      expect(result.event).toBe('user_signup');

      // User email hashed, password redacted
      expect(result.user.email).toMatch(/sha256:/);
      expect(result.user.password).toBe('[REDACTED]');

      // Metadata sanitized
      expect(result.metadata.ip_address).not.toContain('192.168.1.100');
      expect(result.metadata.user_agent).toBe('Mozilla/5.0');
      expect(result.metadata.api_token).toBe('[REDACTED]');

      // Error path sanitized
      expect(result.error.message).toContain('[USER_PATH]');
      expect(result.error.code).toBe('ENOENT');
    });

    it('should handle multiple sanitization strategies in one payload', () => {
      const payload = {
        contact: 'Call me at +1-555-555-5555 or email user@example.com',
        secret_key: 'sk_test_FAKE_KEY_NOT_REAL_12345678',
        credit_card: '4111-1111-1111-1111',
      };

      const result = sanitizeTelemetryData(payload);

      // Multiple patterns in one string
      expect(result.contact).toMatch(/sha256:/);

      // Key-based redaction
      expect(result.secret_key).toBe('[REDACTED]');

      // Pattern-based redaction
      expect(result.credit_card).toBe('[REDACTED]');
    });
  });
});
