/**
 * Example: Using automagik-telemetry in Automagik Forge
 *
 * This shows real-world usage for tracking task execution, agent performance,
 * worktree usage, and errors in the Forge AI development environment.
 */

import { AutomagikTelemetry, StandardEvents, MetricType } from 'automagik-telemetry';

// Initialize telemetry client once at app startup
const telemetry = new AutomagikTelemetry({
  projectName: 'automagik-forge',
  version: '1.0.0',
});

// === Example 1: Track Task Execution ===
async function executeTask(taskId: string, taskType: string): Promise<void> {
  /**
   * Track when Claude executes tasks (code generation, file operations, etc.)
   */
  const startTime = Date.now();

  try {
    // Your business logic here
    await performTaskExecution(taskId, taskType);

    // Track successful task execution
    telemetry.trackEvent(StandardEvents.FEATURE_USED, {
      feature_name: 'task_execution',
      feature_category: 'agent_operations',
      task_type: taskType,
      duration_ms: Date.now() - startTime,
      status: 'success',
    });
  } catch (error) {
    // Track task failure
    telemetry.trackError(error as Error, {
      error_code: 'FORGE-1001',
      operation: 'task_execution',
      task_type: taskType,
      task_id: taskId, // Safe: internal identifier, not PII
    });
    throw error;
  }
}

// === Example 2: Track Agent Performance Metrics ===
async function trackAgentPerformance(
  agentType: string,
  tokenCount: number,
  responseTime: number
): Promise<void> {
  /**
   * Track AI agent performance metrics for optimization
   */
  telemetry.trackMetric(StandardEvents.OPERATION_LATENCY, responseTime, MetricType.HISTOGRAM, {
    operation_type: 'agent_invocation',
    agent_type: agentType,
    token_count: tokenCount,
    duration_ms: responseTime,
  });

  // Also track as a feature usage event
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'agent_invocation',
    feature_category: 'ai_operations',
    agent_type: agentType,
    token_count: tokenCount,
  });
}

// === Example 3: Track Worktree Usage ===
function trackWorktreeOperation(operation: string, branchCount: number): void {
  /**
   * Track git worktree operations for development workflows
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'worktree_operation',
    feature_category: 'git_operations',
    operation: operation,
    branch_count: branchCount,
  });
}

// === Example 4: Track File Operations ===
async function trackFileOperations(
  operationType: 'read' | 'write' | 'edit' | 'delete',
  fileCount: number,
  totalSize: number
): Promise<void> {
  /**
   * Track file operations performed by agents
   * Note: We track counts and sizes, not file names (privacy!)
   */
  const startTime = Date.now();

  try {
    // Perform file operations
    await performFileOperation(operationType, fileCount);

    telemetry.trackEvent(StandardEvents.FEATURE_USED, {
      feature_name: 'file_operation',
      feature_category: 'filesystem',
      operation_type: operationType,
      file_count: fileCount,
      total_size_bytes: totalSize,
      duration_ms: Date.now() - startTime,
    });
  } catch (error) {
    telemetry.trackError(error as Error, {
      error_code: 'FORGE-2001',
      operation: 'file_operation',
      operation_type: operationType,
      file_count: fileCount,
    });
    throw error;
  }
}

// === Example 5: Track Code Generation Events ===
async function generateCode(language: string, linesOfCode: number): Promise<void> {
  /**
   * Track code generation by AI agents
   */
  const startTime = Date.now();

  try {
    await performCodeGeneration(language);

    telemetry.trackEvent(StandardEvents.FEATURE_USED, {
      feature_name: 'code_generation',
      feature_category: 'ai_operations',
      programming_language: language,
      lines_of_code: linesOfCode,
      duration_ms: Date.now() - startTime,
    });
  } catch (error) {
    telemetry.trackError(error as Error, {
      error_code: 'FORGE-3001',
      operation: 'code_generation',
      programming_language: language,
    });
    throw error;
  }
}

// === Example 6: Track CLI Commands ===
function trackCliCommand(command: string, subcommand?: string): void {
  /**
   * Track CLI command execution for usage analytics
   */
  telemetry.trackEvent(StandardEvents.COMMAND_EXECUTED, {
    command: command,
    subcommand: subcommand || 'default',
  });
}

// === Example 7: Track Session Statistics ===
function trackSessionEnd(stats: {
  duration: number;
  tasksCompleted: number;
  filesModified: number;
  errorsEncountered: number;
}): void {
  /**
   * Track session statistics when user closes Forge
   */
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'session_end',
    feature_category: 'session_metrics',
    session_duration_ms: stats.duration,
    tasks_completed: stats.tasksCompleted,
    files_modified: stats.filesModified,
    errors_encountered: stats.errorsEncountered,
  });
}

// === Example 8: Track Performance Bottlenecks ===
async function trackSlowOperation(operationName: string, duration: number): Promise<void> {
  /**
   * Track operations that exceed performance thresholds
   */
  if (duration > 5000) {
    // Track slow operations (>5 seconds)
    telemetry.trackEvent(StandardEvents.OPERATION_LATENCY, {
      operation_type: 'slow_operation',
      operation_name: operationName,
      duration_ms: duration,
      threshold_exceeded: true,
    });
  }
}

// === Example 9: Check Telemetry Status ===
function showTelemetryStatus(): void {
  /**
   * CLI command to show telemetry status
   */
  const status = telemetry.getStatus();

  console.log('Telemetry Status:');
  console.log(`  Enabled: ${status.enabled}`);
  console.log(`  User ID: ${status.user_id}`);
  console.log(`  Session ID: ${status.session_id}`);
  console.log(`  Project: ${status.project_name} v${status.project_version}`);
  console.log(`  Endpoint: ${status.endpoint}`);
  console.log(`  Verbose: ${status.verbose}`);
  console.log(`  Opt-out file exists: ${status.opt_out_file_exists}`);
}

// === Example 10: Opt-In/Opt-Out ===
function disableTelemetry(): void {
  /**
   * CLI command to disable telemetry
   */
  telemetry.disable();
  console.log('✅ Telemetry disabled. Created ~/.automagik-no-telemetry');
  console.log('   No data will be collected.');
}

function enableTelemetry(): void {
  /**
   * CLI command to enable telemetry
   */
  telemetry.enable();
  console.log('✅ Telemetry enabled. Removed ~/.automagik-no-telemetry');
  console.log('   Anonymous usage data will help improve Automagik Forge!');
}

// === Dummy functions for example ===
async function performTaskExecution(taskId: string, taskType: string): Promise<void> {
  console.log(`Executing task ${taskId} of type ${taskType}`);
}

async function performFileOperation(
  operationType: string,
  fileCount: number
): Promise<void> {
  console.log(`Performing ${operationType} on ${fileCount} files`);
}

async function performCodeGeneration(language: string): Promise<void> {
  console.log(`Generating code in ${language}`);
}

// === Main Test Function ===
if (require.main === module) {
  // Test verbose mode
  process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';
  process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

  // Create test client
  const telemetryTest = new AutomagikTelemetry({
    projectName: 'forge',
    version: '1.0.0',
  });

  // Send a test event
  telemetryTest.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'test_forge_example',
    feature_category: 'example',
  });

  console.log('\n✅ If telemetry is enabled, you should see the event above!');
  console.log('   Check your OTel collector logs to verify it was received.\n');

  // Show status
  showTelemetryStatus();
}
