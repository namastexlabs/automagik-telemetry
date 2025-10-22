/**
 * Standard event schema for cross-repo telemetry
 */

export class StandardEvents {
  // Feature usage tracking
  static readonly FEATURE_USED = "automagik.feature.used";
  // Attributes: {project, feature_name, feature_category}

  // API request tracking
  static readonly API_REQUEST = "automagik.api.request";
  // Attributes: {project, endpoint, method, status}

  // CLI command execution
  static readonly COMMAND_EXECUTED = "automagik.cli.command";
  // Attributes: {project, command, subcommand}

  // Performance metrics
  static readonly OPERATION_LATENCY = "automagik.performance.latency";
  // Attributes: {project, operation_type, duration_ms}

  // Error tracking
  static readonly ERROR_OCCURRED = "automagik.error";
  // Attributes: {project, error_code, error_category, severity}

  // Service health
  static readonly SERVICE_HEALTH = "automagik.health";
  // Attributes: {project, service_name, status}
}
