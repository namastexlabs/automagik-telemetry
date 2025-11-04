/**
 * Example: Using automagik-telemetry in Automagik Tools
 *
 * This shows real-world usage for tracking tool invocations, MCP usage,
 * integration health, API requests, and performance monitoring.
 */

import { AutomagikTelemetry, StandardEvents, MetricType } from 'automagik-telemetry';

// Initialize telemetry client once at app startup
const telemetry = new AutomagikTelemetry({
  projectName: 'automagik-tools',
  version: '0.5.0',
});

// === Example 1: Track Tool Invocations ===
async function trackToolInvocation(
  toolName: string,
  toolCategory: string,
  executionTime: number
): Promise<void> {
  /**
   * Track when tools are invoked by Claude
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'tool_invocation',
    feature_category: toolCategory,
    tool_name: toolName,
    execution_time_ms: executionTime,
  });

  // Also track as performance metric
  telemetry.trackMetric(StandardEvents.OPERATION_LATENCY, executionTime, MetricType.HISTOGRAM, {
    operation_type: 'tool_execution',
    tool_name: toolName,
    duration_ms: executionTime,
  });
}

// === Example 2: Track MCP Server Operations ===
async function trackMcpOperation(
  serverName: string,
  operationType: 'list' | 'invoke' | 'connect' | 'disconnect',
  success: boolean
): Promise<void> {
  /**
   * Track MCP (Model Context Protocol) server operations
   */
  const startTime = Date.now();

  try {
    await performMcpOperation(serverName, operationType);

    telemetry.trackEvent(StandardEvents.FEATURE_USED, {
      feature_name: 'mcp_operation',
      feature_category: 'mcp',
      server_name: serverName,
      operation_type: operationType,
      success: success,
      duration_ms: Date.now() - startTime,
    });
  } catch (error) {
    telemetry.trackError(error as Error, {
      error_code: 'TOOLS-1001',
      operation: 'mcp_operation',
      server_name: serverName,
      operation_type: operationType,
    });
    throw error;
  }
}

// === Example 3: Track API Requests ===
async function trackApiRequest(
  endpoint: string,
  method: string,
  statusCode: number
): Promise<void> {
  /**
   * Track API requests made by tools
   */
  const startTime = Date.now();

  try {
    // Perform API request
    const response = await makeApiRequest(endpoint, method);

    telemetry.trackEvent(StandardEvents.API_REQUEST, {
      endpoint: endpoint,
      method: method,
      status: statusCode,
      duration_ms: Date.now() - startTime,
    });
  } catch (error) {
    telemetry.trackError(error as Error, {
      error_code: 'TOOLS-2001',
      operation: 'api_request',
      endpoint: endpoint,
      method: method,
    });
    throw error;
  }
}

// === Example 4: Track Integration Health ===
function trackIntegrationHealth(
  integrationName: string,
  status: 'healthy' | 'degraded' | 'down',
  responseTime?: number
): void {
  /**
   * Track health of external integrations (GitHub, Slack, etc.)
   */
  telemetry.trackEvent(StandardEvents.SERVICE_HEALTH, {
    service_name: integrationName,
    status: status,
    response_time_ms: responseTime || 0,
  });
}

// === Example 5: Track Tool Categories ===
function trackToolByCategory(
  category: 'file_ops' | 'git' | 'search' | 'web' | 'communication' | 'database'
): void {
  /**
   * Track tool usage by category for analytics
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'tool_category_usage',
    feature_category: 'tool_analytics',
    tool_category: category,
  });
}

// === Example 6: Track Search Operations ===
async function trackSearchOperation(
  searchType: 'grep' | 'glob' | 'semantic',
  resultCount: number,
  searchTime: number
): Promise<void> {
  /**
   * Track search operations (Grep, Glob, etc.)
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'search_operation',
    feature_category: 'search',
    search_type: searchType,
    result_count: resultCount,
    duration_ms: searchTime,
  });

  // Track performance for slow searches
  if (searchTime > 2000) {
    telemetry.trackEvent(StandardEvents.OPERATION_LATENCY, {
      operation_type: 'slow_search',
      search_type: searchType,
      duration_ms: searchTime,
      threshold_exceeded: true,
    });
  }
}

// === Example 7: Track File Read/Write Operations ===
async function trackFileOperation(
  operation: 'read' | 'write' | 'edit',
  fileExtension: string,
  sizeBytes: number
): Promise<void> {
  /**
   * Track file operations by tools
   * Note: We track file type and size, not file paths (privacy!)
   */
  const startTime = Date.now();

  try {
    await performFileOperation(operation, fileExtension);

    telemetry.trackEvent(StandardEvents.FEATURE_USED, {
      feature_name: 'file_operation',
      feature_category: 'filesystem',
      operation: operation,
      file_extension: fileExtension,
      size_bytes: sizeBytes,
      duration_ms: Date.now() - startTime,
    });
  } catch (error) {
    telemetry.trackError(error as Error, {
      error_code: 'TOOLS-3001',
      operation: 'file_operation',
      operation_type: operation,
      file_extension: fileExtension,
    });
    throw error;
  }
}

// === Example 8: Track Web Fetch Operations ===
async function trackWebFetch(url: string, success: boolean, fetchTime: number): Promise<void> {
  /**
   * Track web fetch operations
   * Note: We sanitize URLs to remove query params and sensitive data
   */
  const sanitizedUrl = sanitizeUrl(url);

  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'web_fetch',
    feature_category: 'web',
    domain: new URL(url).hostname, // Only track domain, not full URL
    success: success,
    duration_ms: fetchTime,
  });

  if (fetchTime > 5000) {
    telemetry.trackEvent(StandardEvents.OPERATION_LATENCY, {
      operation_type: 'slow_web_fetch',
      domain: new URL(url).hostname,
      duration_ms: fetchTime,
    });
  }
}

// === Example 9: Track Bash Command Execution ===
function trackBashCommand(
  commandCategory: 'git' | 'npm' | 'docker' | 'system' | 'other',
  exitCode: number,
  executionTime: number
): void {
  /**
   * Track bash command execution
   * Note: We track command category, not actual commands (privacy!)
   */
  telemetry.trackEvent(StandardEvents.COMMAND_EXECUTED, {
    command: 'bash',
    command_category: commandCategory,
    exit_code: exitCode,
    duration_ms: executionTime,
    success: exitCode === 0,
  });

  if (exitCode !== 0) {
    telemetry.trackEvent(StandardEvents.ERROR_OCCURRED, {
      error_category: 'command_execution',
      command_category: commandCategory,
      exit_code: exitCode,
      severity: 'warning',
    });
  }
}

// === Example 10: Track Concurrent Tool Usage ===
function trackConcurrentToolUsage(toolCount: number, duration: number): void {
  /**
   * Track when multiple tools are used in parallel
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'concurrent_tool_usage',
    feature_category: 'performance',
    concurrent_tool_count: toolCount,
    duration_ms: duration,
  });
}

// === Example 11: Track Error Recovery ===
function trackErrorRecovery(
  errorType: string,
  recoveryStrategy: string,
  recovered: boolean
): void {
  /**
   * Track error recovery attempts
   */
  telemetry.trackEvent(StandardEvents.ERROR_OCCURRED, {
    error_category: 'recovery_attempt',
    error_type: errorType,
    recovery_strategy: recoveryStrategy,
    recovered: recovered,
    severity: recovered ? 'info' : 'error',
  });
}

// === Example 12: Check Telemetry Status (Verbose Mode) ===
function showTelemetryStatus(): void {
  /**
   * Show detailed telemetry status for debugging
   */
  const status = telemetry.getStatus();

  console.log('\n=== Telemetry Status ===');
  console.log(`Enabled: ${status.enabled ? '✅' : '❌'}`);
  console.log(`User ID: ${status.user_id}`);
  console.log(`Session ID: ${status.session_id}`);
  console.log(`Project: ${status.project_name} v${status.project_version}`);
  console.log(`Endpoint: ${status.endpoint}`);
  console.log(`Verbose Mode: ${status.verbose ? '✅' : '❌'}`);
  console.log(`Opt-out file: ${status.opt_out_file_exists ? 'EXISTS' : 'NOT FOUND'}`);
  console.log(`Environment Variable: ${status.env_var || 'NOT SET'}`);
  console.log('========================\n');
}

// === Example 13: Opt-In/Opt-Out ===
async function disableTelemetry(): Promise<void> {
  /**
   * Disable telemetry collection
   */
  await telemetry.disable();
  console.log('✅ Telemetry disabled. Created ~/.automagik-no-telemetry');
  console.log('   No data will be collected.');
}

async function enableTelemetry(): Promise<void> {
  /**
   * Enable telemetry collection
   */
  await telemetry.enable();
  console.log('✅ Telemetry enabled. Removed ~/.automagik-no-telemetry');
  console.log('   Anonymous usage data will help improve Automagik Tools!');
}

// === Utility Functions ===
function sanitizeUrl(url: string): string {
  /**
   * Remove query params and sensitive data from URLs
   */
  try {
    const parsedUrl = new URL(url);
    return `${parsedUrl.protocol}//${parsedUrl.hostname}${parsedUrl.pathname}`;
  } catch {
    return 'invalid_url';
  }
}

// === Dummy functions for example ===
async function performMcpOperation(
  serverName: string,
  operationType: string
): Promise<void> {
  console.log(`Performing MCP ${operationType} on ${serverName}`);
}

async function makeApiRequest(endpoint: string, method: string): Promise<any> {
  console.log(`Making ${method} request to ${endpoint}`);
  return { status: 200 };
}

async function performFileOperation(operation: string, fileExtension: string): Promise<void> {
  console.log(`Performing ${operation} on .${fileExtension} file`);
}

// === Main Test Function ===
if (require.main === module) {
  // Enable verbose mode for testing
  process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
  process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

  // Create test client
  const telemetryTest = new AutomagikTelemetry({
    projectName: 'tools',
    version: '0.5.0',
  });

  // Test various tracking scenarios
  console.log('\n🧪 Testing Automagik Tools telemetry...\n');

  // Test 1: Track tool invocation
  trackToolInvocation('Grep', 'search', 150);

  // Test 2: Track MCP operation
  trackMcpOperation('omni-server', 'invoke', true);

  // Test 3: Track API request
  trackApiRequest('/api/v1/tools', 'GET', 200);

  // Test 4: Track integration health
  trackIntegrationHealth('github', 'healthy', 250);

  // Test 5: Track search operation
  trackSearchOperation('grep', 42, 180);

  console.log('\n✅ Test events sent! Check your OTel collector logs.\n');

  // Show status
  showTelemetryStatus();
}
