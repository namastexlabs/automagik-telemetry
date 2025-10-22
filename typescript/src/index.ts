/**
 * @automagik/telemetry
 *
 * Privacy-first, opt-in telemetry SDK for the Automagik ecosystem
 */

export { TelemetryClient } from './client';
export { TelemetryOptIn, promptUserIfNeeded, shouldPromptUser } from './opt-in';
export { StandardEvents } from './schema';
export type { TelemetryConfig, ValidatedConfig } from './config';
export {
  DEFAULT_CONFIG,
  ENV_VARS,
  createConfig,
  mergeConfig,
  validateConfig,
  loadConfigFromEnv,
} from './config';
export type { SanitizationStrategy, PrivacyConfig } from './privacy';
export {
  hashValue,
  detectPII,
  sanitizePhone,
  sanitizeEmail,
  truncateString,
  sanitizeValue,
  redactSensitiveKeys,
  sanitizeTelemetryData,
  SENSITIVE_KEYS,
} from './privacy';

export const VERSION = '0.1.0';
