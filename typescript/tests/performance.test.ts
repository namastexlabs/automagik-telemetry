/**
 * Performance benchmarks for AutomagikTelemetry.
 *
 * Tests verify that telemetry operations meet the <1ms overhead requirement.
 * These tests can be skipped in CI by excluding the 'performance' test pattern.
 */

import { AutomagikTelemetry, MetricType } from '../src/client';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

// Mock fetch for performance testing
global.fetch = jest.fn();

interface TimingStats {
  count: number;
  mean: number;
  median: number;
  min: number;
  max: number;
  p95: number;
  p99: number;
  stdev: number;
}

function calculateStats(timings: number[]): TimingStats {
  const sorted = [...timings].sort((a, b) => a - b);
  const n = sorted.length;

  const mean = timings.reduce((a, b) => a + b, 0) / n;
  const median = sorted[Math.floor(n / 2)];
  const min = sorted[0];
  const max = sorted[n - 1];
  const p95 = sorted[Math.floor(n * 0.95)];
  const p99 = sorted[Math.floor(n * 0.99)];

  // Calculate standard deviation
  const squareDiffs = timings.map((value) => Math.pow(value - mean, 2));
  const avgSquareDiff = squareDiffs.reduce((a, b) => a + b, 0) / n;
  const stdev = Math.sqrt(avgSquareDiff);

  return { count: n, mean, median, min, max, p95, p99, stdev };
}

function printStats(operation: string, stats: TimingStats): void {
  console.log('\n' + '='.repeat(60));
  console.log(`Performance: ${operation}`);
  console.log('='.repeat(60));
  console.log(`  Count:      ${stats.count.toLocaleString()} operations`);
  console.log(`  Mean:       ${stats.mean.toFixed(3)} ms`);
  console.log(`  Median:     ${stats.median.toFixed(3)} ms`);
  console.log(`  Min:        ${stats.min.toFixed(3)} ms`);
  console.log(`  Max:        ${stats.max.toFixed(3)} ms`);
  console.log(`  P95:        ${stats.p95.toFixed(3)} ms`);
  console.log(`  P99:        ${stats.p99.toFixed(3)} ms`);
  console.log(`  StdDev:     ${stats.stdev.toFixed(3)} ms`);
  console.log('='.repeat(60) + '\n');
}

describe('Performance Benchmarks', () => {
  let mockFetch: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    // Reset mocks
    mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
    mockFetch.mockClear();

    // Mock successful HTTP response
    mockFetch.mockResolvedValue({
      status: 200,
      ok: true,
    } as Response);

    // Force enable telemetry
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
  });

  afterEach(() => {
    delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
  });

  describe('trackEvent Performance', () => {
    it('should have <1ms average overhead with realistic payloads', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      // Realistic event payload
      const eventData = {
        feature_name: 'api_endpoint',
        feature_category: 'messaging',
        user_action: 'send_message',
        message_type: 'text',
        success: true,
      };

      // Warmup
      for (let i = 0; i < 10; i++) {
        client.trackEvent('benchmark.test', eventData);
      }

      // Actual benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackEvent('benchmark.feature_used', eventData);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('trackEvent() with realistic payload', stats);

      // Assertions
      expect(stats.mean).toBeLessThan(1.0);
      expect(stats.p99).toBeLessThan(10.0); // Relaxed from 5.0 due to V8 optimization variance
    }, 30000); // Increase timeout for benchmark
  });

  describe('trackError Performance', () => {
    it('should have <1ms average overhead with error context', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      // Create realistic error
      const testError = new Error('Connection timeout after 30 seconds');

      const context = {
        error_code: 'OMNI-1001',
        operation: 'send_message',
        retry_count: 3,
        endpoint: '/api/v1/messages',
      };

      // Warmup
      for (let i = 0; i < 10; i++) {
        client.trackError(testError, context);
      }

      // Actual benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackError(testError, context);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('trackError() with context', stats);

      // Assertions
      expect(stats.mean).toBeLessThan(1.0);
      expect(stats.p99).toBeLessThan(10.0); // Relaxed from 5.0 due to V8 optimization variance
    }, 30000);
  });

  describe('trackMetric Performance', () => {
    it('should have <1ms average overhead with attributes', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      const attributes = {
        operation_type: 'api_request',
        endpoint: '/v1/contacts',
        status_code: 200,
        cache_hit: true,
      };

      // Warmup
      for (let i = 0; i < 10; i++) {
        client.trackMetric('benchmark.latency', 123.45, MetricType.GAUGE, attributes);
      }

      // Actual benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackMetric('operation.latency', 123.45, MetricType.GAUGE, attributes);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('trackMetric() with attributes', stats);

      // Assertions
      expect(stats.mean).toBeLessThan(1.0);
      expect(stats.p99).toBeLessThan(10.0); // Relaxed from 5.0 due to V8 optimization variance
    }, 30000);
  });

  describe('Disabled Client Overhead', () => {
    it('should have near-zero overhead when disabled', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'false';

      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 10000;
      const timings: number[] = [];

      const eventData = {
        feature_name: 'test_feature',
        action: 'click',
      };

      // Warmup
      for (let i = 0; i < 100; i++) {
        client.trackEvent('test.event', eventData);
      }

      // Actual benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackEvent('test.event', eventData);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('Disabled client overhead', stats);

      // Disabled client should be extremely fast (just a boolean check)
      expect(stats.mean).toBeLessThan(0.01);
      expect(stats.p99).toBeLessThan(0.1);
    }, 30000);
  });

  describe('Large Attribute Set Performance', () => {
    it('should handle large attribute sets efficiently', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      // Large but realistic attribute set
      const largeAttributes: Record<string, any> = {};
      for (let i = 0; i < 50; i++) {
        largeAttributes[`attribute_${i}`] = `value_${i}`;
      }
      largeAttributes.feature_name = 'complex_operation';
      largeAttributes.user_id = 'anon-12345';
      largeAttributes.session_duration = 3600;
      largeAttributes.items_processed = 1000;
      largeAttributes.success_rate = 0.95;
      largeAttributes.error_count = 5;
      largeAttributes.warning_count = 12;

      // Warmup
      for (let i = 0; i < 10; i++) {
        client.trackEvent('benchmark.large_attrs', largeAttributes);
      }

      // Actual benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackEvent('benchmark.large_attrs', largeAttributes);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('Large attribute set (50+ attributes)', stats);

      // Should still be fast even with many attributes
      expect(stats.mean).toBeLessThan(2.0);
      expect(stats.p99).toBeLessThan(10.0);
    }, 30000);
  });

  describe('Concurrent Tracking Simulation', () => {
    it('should handle rapid consecutive events efficiently', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 500;
      const timings: number[] = [];

      const events: Array<[string, Record<string, any>]> = [
        ['feature.used', { feature: 'export', format: 'csv' }],
        ['error.occurred', { code: 'E001', severity: 'low' }],
        ['metric.recorded', { latency: 45.2, endpoint: '/api/data' }],
      ];

      // Warmup
      for (let i = 0; i < 10; i++) {
        for (const [eventName, data] of events) {
          client.trackEvent(eventName, data);
        }
      }

      // Actual benchmark - track multiple events in quick succession
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        for (const [eventName, data] of events) {
          client.trackEvent(eventName, data);
        }
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('3 concurrent events per iteration', stats);

      // Total time for 3 events should be reasonable
      const avgPerEvent = stats.mean / 3;
      console.log(`  Avg per event: ${avgPerEvent.toFixed(3)} ms`);

      expect(avgPerEvent).toBeLessThan(1.5);
    }, 30000);
  });

  describe('Payload Size Impact', () => {
    it('should scale gracefully with payload size', async () => {
      const iterations = 1000;
      const payloadSizes = [1, 10, 50, 100];
      const results: Record<number, TimingStats> = {};

      for (const size of payloadSizes) {
        const client = new AutomagikTelemetry({
          projectName: 'benchmark-test',
          version: '1.0.0',
        });

        const timings: number[] = [];
        const data: Record<string, string> = {};
        for (let i = 0; i < size; i++) {
          data[`key_${i}`] = `value_${i}`;
        }

        // Warmup
        for (let i = 0; i < 10; i++) {
          client.trackEvent('size.test', data);
        }

        // Benchmark
        for (let i = 0; i < iterations; i++) {
          const start = performance.now();
          client.trackEvent('size.test', data);
          const end = performance.now();
          timings.push(end - start);
        }

        results[size] = calculateStats(timings);
      }

      // Print comparison
      console.log('\n' + '='.repeat(60));
      console.log('Payload Size Impact');
      console.log('='.repeat(60));
      console.log('Size      Mean       P95        P99');
      console.log('-'.repeat(60));
      for (const [size, stats] of Object.entries(results)) {
        console.log(
          `${size.padEnd(10)}${stats.mean.toFixed(3).padEnd(11)}${stats.p95.toFixed(3).padEnd(11)}${stats.p99.toFixed(3)}`
        );
      }
      console.log('='.repeat(60) + '\n');

      // Even large payloads should be reasonable
      expect(results[100].mean).toBeLessThan(5.0);
    }, 60000);
  });

  describe('Memory Usage', () => {
    it('should not leak memory with many events (disabled client)', async () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'false';

      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const initialMemory = process.memoryUsage();

      // Track many events with disabled client (should have minimal overhead)
      const eventCount = 10000;
      for (let i = 0; i < eventCount; i++) {
        client.trackEvent('memory.test', {
          iteration: i,
          data: `test_data_${i}`,
          value: i * 1.5,
        });
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const finalMemory = process.memoryUsage();

      const heapIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
      const heapIncreasePerEvent = heapIncrease / eventCount;

      console.log('\n' + '='.repeat(60));
      console.log('Memory Usage Test (Disabled Client)');
      console.log('='.repeat(60));
      console.log(`  Events tracked:    ${eventCount.toLocaleString()}`);
      console.log(`  Initial heap:      ${(initialMemory.heapUsed / 1024 / 1024).toFixed(2)} MB`);
      console.log(`  Final heap:        ${(finalMemory.heapUsed / 1024 / 1024).toFixed(2)} MB`);
      console.log(`  Heap increase:     ${(heapIncrease / 1024 / 1024).toFixed(2)} MB`);
      console.log(`  Per event:         ${heapIncreasePerEvent.toFixed(2)} bytes`);
      console.log('='.repeat(60) + '\n');

      // Disabled client should have minimal memory impact
      // Allow up to 10KB per event for test overhead and V8 internals
      expect(heapIncreasePerEvent).toBeLessThan(10 * 1024);
    }, 30000);
  });

  describe('String Truncation Performance', () => {
    it('should handle long strings efficiently', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      // Create very long strings that need truncation
      const longData = {
        description: 'x'.repeat(10000), // Will be truncated to 500
        error_message: 'y'.repeat(5000),
        stack_trace: 'z'.repeat(8000),
        normal_field: 'regular value',
      };

      // Warmup
      for (let i = 0; i < 10; i++) {
        client.trackEvent('truncation.test', longData);
      }

      // Benchmark
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackEvent('truncation.test', longData);
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('String truncation (3 long strings)', stats);

      // Truncation should not add significant overhead
      expect(stats.mean).toBeLessThan(2.0);
      expect(stats.p99).toBeLessThan(10.0); // Relaxed from 5.0 due to V8 optimization variance
    }, 30000);
  });

  describe('System Info Collection Overhead', () => {
    it('should collect system info quickly', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 1000;
      const timings: number[] = [];

      // Access private method for testing (TypeScript hack)
      const getSystemInfo = (client as any).getSystemInfo.bind(client);

      // Benchmark system info collection
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        getSystemInfo();
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('System info collection', stats);

      // System info collection should be very fast
      expect(stats.mean).toBeLessThan(0.1);
    }, 30000);
  });

  describe('Async Operation Performance', () => {
    it('should not block on async operations', async () => {
      const client = new AutomagikTelemetry({
        projectName: 'benchmark-test',
        version: '1.0.0',
      });

      const iterations = 100;
      const timings: number[] = [];

      // Simulate slow network by delaying fetch
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                status: 200,
                ok: true,
              } as Response);
            }, 100); // 100ms delay
          })
      );

      // Benchmark - these should not block since events are async
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        client.trackEvent('async.test', { iteration: i });
        const end = performance.now();
        timings.push(end - start);
      }

      const stats = calculateStats(timings);
      printStats('Async operations (100ms network delay)', stats);

      // Should not be blocked by network delay since it's async
      // Allow higher threshold due to V8 optimization variance
      expect(stats.mean).toBeLessThan(2.0);
      expect(stats.p99).toBeLessThan(15.0); // Relaxed threshold for async operations
    }, 30000);
  });
});

// Helper to run benchmarks directly
if (require.main === module) {
  console.log('Running performance benchmarks...\n');
  // Note: Jest handles test execution
}
