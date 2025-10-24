/**
 * Privacy utilities for sanitizing PII from telemetry data.
 *
 * Provides functions to detect and sanitize personally identifiable information
 * including phone numbers, emails, API keys, and other sensitive data.
 */

import { createHash } from "crypto";

/**
 * Sanitization strategy for handling PII.
 */
export type SanitizationStrategy = "hash" | "redact" | "truncate";

/**
 * Configuration for privacy utilities.
 */
export interface PrivacyConfig {
  strategy?: SanitizationStrategy;
  maxStringLength?: number;
  redactionText?: string;
}

const DEFAULT_CONFIG: Required<PrivacyConfig> = {
  strategy: "hash",
  maxStringLength: 1000,
  redactionText: "[REDACTED]",
};

// PII detection patterns
// Exported for testing purposes to allow mocking
export const PATTERNS = {
  // Phone: matches international formats like +1-555-555-5555, (555) 555-5555, 555.555.5555
  phone:
    /(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})|(\+?[0-9]{1,3}[-.\s]?)?(\([0-9]{2,4}\)|[0-9]{2,4})[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4}/g,

  // Email: standard email pattern
  email: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,

  // API keys: patterns like xxx-xxx-xxx, sk_live_xxx, Bearer xxx
  apiKey:
    /\b(sk_live_|sk_test_|pk_live_|pk_test_|Bearer\s+|api[_-]?key[_-]?)[a-zA-Z0-9_-]{20,}\b/gi,

  // Credit card: basic pattern (not perfect, but catches most)
  creditCard: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,

  // IPv4 addresses
  ipv4: /\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/g,

  // File paths with user info (Unix and Windows)
  userPath: /\/(?:home|Users)\/[a-zA-Z0-9_-]+|[A-Z]:\\Users\\[a-zA-Z0-9_-]+/gi,
};

/**
 * Hash a value using SHA-256.
 * Returns a truncated hash for readability while maintaining uniqueness.
 *
 * @example
 * ```typescript
 * const hashed = hashValue('sensitive-data');
 * // Returns: 'sha256:a1b2c3d4...' (first 16 chars of hash)
 * ```
 */
export function hashValue(value: string): string {
  const hash = createHash("sha256").update(value).digest("hex");
  return `sha256:${hash.substring(0, 16)}`;
}

/**
 * Detect if a value contains potential PII.
 *
 * @example
 * ```typescript
 * detectPII('user@example.com'); // true
 * detectPII('Hello world'); // false
 * ```
 */
export function detectPII(value: string): boolean {
  if (typeof value !== "string") return false;

  return Object.values(PATTERNS).some((pattern) => {
    // Reset regex state before testing
    pattern.lastIndex = 0;
    return pattern.test(value);
  });
}

/**
 * Sanitize a phone number.
 *
 * @example
 * ```typescript
 * sanitizePhone('+1-555-555-5555', { strategy: 'hash' });
 * // Returns: 'sha256:a1b2c3d4...'
 *
 * sanitizePhone('(555) 555-5555', { strategy: 'redact' });
 * // Returns: '[REDACTED]'
 * ```
 */
export function sanitizePhone(
  value: string,
  config: PrivacyConfig = {},
): string {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // Reset regex state
  PATTERNS.phone.lastIndex = 0;
  if (!PATTERNS.phone.test(value)) {
    return value;
  }

  // Reset again before replace
  PATTERNS.phone.lastIndex = 0;
  switch (cfg.strategy) {
    case "hash":
      return value.replace(PATTERNS.phone, (match) => hashValue(match));
    case "redact":
      return value.replace(PATTERNS.phone, cfg.redactionText);
    case "truncate":
      return value.replace(PATTERNS.phone, "XXX-XXX-XXXX");
    default:
      return value;
  }
}

/**
 * Sanitize an email address.
 *
 * @example
 * ```typescript
 * sanitizeEmail('user@example.com', { strategy: 'hash' });
 * // Returns: 'sha256:a1b2c3d4...'
 *
 * sanitizeEmail('test@test.com', { strategy: 'redact' });
 * // Returns: '[REDACTED]'
 * ```
 */
export function sanitizeEmail(
  value: string,
  config: PrivacyConfig = {},
): string {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // Reset regex state
  PATTERNS.email.lastIndex = 0;
  if (!PATTERNS.email.test(value)) {
    return value;
  }

  // Reset again before replace
  PATTERNS.email.lastIndex = 0;
  switch (cfg.strategy) {
    case "hash":
      return value.replace(PATTERNS.email, (match) => hashValue(match));
    case "redact":
      return value.replace(PATTERNS.email, cfg.redactionText);
    case "truncate":
      return value.replace(PATTERNS.email, (match) => {
        const [user, domain] = match.split("@");
        return `${user.substring(0, 2)}***@${domain}`;
      });
    default:
      return value;
  }
}

/**
 * Truncate a string to a maximum length.
 *
 * @example
 * ```typescript
 * truncateString('Very long string...', 10);
 * // Returns: 'Very lon...'
 * ```
 */
export function truncateString(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.substring(0, maxLength - 3)}...`;
}

/**
 * Auto-sanitize a value based on PII detection.
 * Handles strings, numbers, objects, and arrays recursively.
 *
 * @example
 * ```typescript
 * sanitizeValue('Contact: user@example.com');
 * // Returns: 'Contact: sha256:a1b2c3d4...'
 *
 * sanitizeValue({ email: 'test@test.com', phone: '555-555-5555' });
 * // Returns: { email: 'sha256:...', phone: 'sha256:...' }
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function sanitizeValue(value: any, config: PrivacyConfig = {}): any {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // Handle null/undefined
  if (value == null) return value;

  // Handle strings
  if (typeof value === "string") {
    // Truncate if too long
    let sanitized = truncateString(value, cfg.maxStringLength);

    // Apply pattern-based sanitization (reset regex state before each test)
    // Check API keys FIRST before phone numbers, as API keys are more specific
    // and phone patterns can match parts of API keys
    PATTERNS.apiKey.lastIndex = 0;
    if (PATTERNS.apiKey.test(sanitized)) {
      PATTERNS.apiKey.lastIndex = 0;
      sanitized = sanitized.replace(PATTERNS.apiKey, cfg.redactionText);
    }
    PATTERNS.phone.lastIndex = 0;
    if (PATTERNS.phone.test(sanitized)) {
      sanitized = sanitizePhone(sanitized, config);
    }
    PATTERNS.email.lastIndex = 0;
    if (PATTERNS.email.test(sanitized)) {
      sanitized = sanitizeEmail(sanitized, config);
    }
    PATTERNS.creditCard.lastIndex = 0;
    if (PATTERNS.creditCard.test(sanitized)) {
      PATTERNS.creditCard.lastIndex = 0;
      sanitized = sanitized.replace(PATTERNS.creditCard, cfg.redactionText);
    }
    PATTERNS.ipv4.lastIndex = 0;
    if (PATTERNS.ipv4.test(sanitized)) {
      PATTERNS.ipv4.lastIndex = 0;
      sanitized = sanitized.replace(PATTERNS.ipv4, (match) =>
        cfg.strategy === "hash" ? hashValue(match) : "X.X.X.X",
      );
    }
    PATTERNS.userPath.lastIndex = 0;
    if (PATTERNS.userPath.test(sanitized)) {
      PATTERNS.userPath.lastIndex = 0;
      sanitized = sanitized.replace(PATTERNS.userPath, "/[USER_PATH]");
    }

    return sanitized;
  }

  // Handle numbers (pass through)
  if (typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  // Handle arrays recursively
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeValue(item, config));
  }

  // Handle objects recursively
  if (typeof value === "object") {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sanitized: Record<string, any> = {};
    for (const [key, val] of Object.entries(value)) {
      sanitized[key] = sanitizeValue(val, config);
    }
    return sanitized;
  }

  return value;
}

/**
 * Redact specific keys from an object.
 * Useful for known sensitive fields like 'password', 'token', etc.
 *
 * @example
 * ```typescript
 * const data = { username: 'john', password: 'secret123', token: 'abc' };
 * redactSensitiveKeys(data, ['password', 'token']);
 * // Returns: { username: 'john', password: '[REDACTED]', token: '[REDACTED]' }
 * ```
 */
export function redactSensitiveKeys(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  obj: Record<string, any>,
  keys: string[],
  config: PrivacyConfig = {},
// eslint-disable-next-line @typescript-eslint/no-explicit-any
): Record<string, any> {
  const cfg = { ...DEFAULT_CONFIG, ...config };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result: Record<string, any> = {};

  for (const [key, value] of Object.entries(obj)) {
    if (keys.some((k) => key.toLowerCase().includes(k.toLowerCase()))) {
      result[key] = cfg.redactionText;
    } else if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value)
    ) {
      result[key] = redactSensitiveKeys(value, keys, config);
    } else {
      result[key] = value;
    }
  }

  return result;
}

/**
 * Common sensitive key patterns to redact.
 */
export const SENSITIVE_KEYS = [
  "password",
  "passwd",
  "pwd",
  "secret",
  "token",
  "api_key",
  "apikey",
  "access_token",
  "refresh_token",
  "private_key",
  "credit_card",
  "ssn",
  "social_security",
];

/**
 * Sanitize telemetry data before sending.
 * Combines multiple sanitization strategies for comprehensive privacy protection.
 *
 * @example
 * ```typescript
 * const data = {
 *   user: { email: 'test@example.com', password: 'secret' },
 *   message: 'Error at /home/user/project/file.ts',
 * };
 *
 * sanitizeTelemetryData(data);
 * // Returns: {
 * //   user: { email: 'sha256:...', password: '[REDACTED]' },
 * //   message: 'Error at /[USER_PATH]/project/file.ts',
 * // }
 * ```
 */
export function sanitizeTelemetryData(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>,
  config: PrivacyConfig = {},
// eslint-disable-next-line @typescript-eslint/no-explicit-any
): Record<string, any> {
  // First redact known sensitive keys
  let sanitized = redactSensitiveKeys(data, SENSITIVE_KEYS, config);

  // Then apply pattern-based sanitization
  sanitized = sanitizeValue(sanitized, config);

  return sanitized;
}
