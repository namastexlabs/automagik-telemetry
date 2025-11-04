#!/usr/bin/env tsx
/**
 * Basic Example - Automagik Telemetry TypeScript SDK
 *
 * This example demonstrates the simplest way to get started with the TypeScript SDK.
 * It shows how to initialize the client, track events, metrics, and logs.
 *
 * Prerequisites:
 *     npm install automagik-telemetry
 *     # or
 *     pnpm add automagik-telemetry
 *
 * Run with:
 *     tsx basic_example.ts
 *     # or
 *     ts-node basic_example.ts
 *
 * For local infrastructure testing:
 *     cd infra && make start
 */

import { AutomagikTelemetry, StandardEvents, MetricType } from 'automagik-telemetry';

// Configure for local infrastructure (uncomment to test locally)
// process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
// process.env.AUTOMAGIK_TELEMETRY_ENDPOINT = 'http://localhost:4318/v1/traces';
// process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

async function main(): Promise<void> {
  console.log('🚀 Basic Telemetry Example');
  console.log('='.repeat(50));

  // Initialize telemetry client
  const telemetry = new AutomagikTelemetry({
    projectName: 'basic-example',
    projectVersion: '1.0.0',
    // Optional: configure for local testing
    // endpoint: 'http://localhost:4318/v1/traces',
    // backend: 'otlp',  // or 'clickhouse'
    // batchSize: 1,  // Send immediately for testing
    // verbose: true,
  });

  // Example 1: Track a simple event
  console.log('\n1️⃣  Tracking a simple event...');
  telemetry.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'basic_example',
    user_action: 'started',
  });
  console.log('✅ Event tracked!');

  // Example 2: Track a metric
  console.log('\n2️⃣  Tracking a metric...');
  telemetry.trackMetric({
    name: 'example.response_time',
    value: 123.45,
    type: MetricType.GAUGE,
    attributes: {
      endpoint: '/api/example',
      status: 'success',
    },
  });
  console.log('✅ Metric tracked!');

  // Example 3: Track a log
  console.log('\n3️⃣  Tracking a log message...');
  telemetry.trackLog({
    message: 'Basic example completed successfully',
    level: 'info',
    attributes: {
      component: 'basic_example',
      duration_ms: 100,
    },
  });
  console.log('✅ Log tracked!');

  // Example 4: Track custom events
  console.log('\n4️⃣  Tracking custom events...');
  telemetry.trackEvent('custom.app.workflow_completed', {
    workflow_name: 'onboarding',
    steps_completed: 5,
    success: true,
  });
  console.log('✅ Custom event tracked!');

  // Flush all pending events
  console.log('\n5️⃣  Flushing all pending events...');
  await telemetry.flush();
  console.log('✅ All events flushed!');

  // Wait a moment for async operations
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // Check status
  console.log('\n📊 Telemetry Status:');
  const status = telemetry.getStatus();
  console.log(`   Enabled: ${status.enabled}`);
  console.log(`   User ID: ${status.userId}`);
  console.log(`   Endpoint: ${status.endpoint}`);
  console.log(`   Queue Size: ${status.queueSize}`);

  console.log('\n' + '='.repeat(50));
  console.log('✨ Example completed!');
  console.log('\nNext steps:');
  console.log('- Check Grafana at http://localhost:3000 (if using local infra)');
  console.log('- Try the forge_example.ts for real-world usage');
  console.log('- Read the docs at https://github.com/namastexlabs/automagik-telemetry');
}

// Run the example
main().catch((error) => {
  console.error('❌ Error running example:', error);
  process.exit(1);
});
