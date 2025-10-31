/**
 * Integration tests for memory usage and leak detection.
 *
 * Tests long-running scenarios to verify:
 * - Memory doesn't leak over time
 * - Memory returns to baseline after flush
 * - No unclosed timers or resources
 * - Stable memory usage under sustained load
 *
 * Port of Python's test_integration_memory.py to TypeScript
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { AutomagikTelemetry, TelemetryConfig, LogSeverity, MetricType } from '../src/client';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

// Mock fetch globally
global.fetch = jest.fn();

// Helper to get memory usage in MB
function getMemoryMB(): number {
  const memUsage = process.memoryUsage();
  return memUsage.heapUsed / 1024 / 1024;
}

// Helper to force garbage collection (requires --expose-gc flag)
function forceGC(): void {
  if (global.gc) {
    global.gc();
  }
}

describe('Memory Leak Detection', () => {
  const mockHomedir = '/home/testuser';

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock os methods
    (os.homedir as jest.Mock).mockReturnValue(mockHomedir);
    (os.platform as jest.Mock).mockReturnValue('linux');
    (os.release as jest.Mock).mockReturnValue('5.10.0');
    (os.arch as jest.Mock).mockReturnValue('x64');

    // Mock fs methods
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    (fs.readFileSync as jest.Mock).mockReturnValue('');
    (fs.writeFileSync as jest.Mock).mockReturnValue(undefined);
    (fs.mkdirSync as jest.Mock).mockReturnValue(undefined);

    // Setup fetch mock
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    // Enable telemetry
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';

    // Force garbage collection before each test
    forceGC();
  });

  afterEach(() => {
    delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
    forceGC();
  });

  describe('Simple Event Memory Leaks', () => {
    it('should not leak memory with 10k simple events', async () => {
      console.log('\n=== Testing memory leaks with simple events ===');

      // Get baseline memory
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-memory',
        version: '1.0.0',
        batchSize: 50,
        flushInterval: 60000, // Disable auto-flush
        compressionEnabled: true,
      });

      // Send many events
      const numEvents = 10000;
      const memorySamples: number[] = [];

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent('test.memory.simple', { event_id: i });

        // Sample memory every 1000 events
        if (i % 1000 === 0 && i > 0) {
          forceGC();
          await new Promise((resolve) => setTimeout(resolve, 10));
          const currentMemory = getMemoryMB();
          memorySamples.push(currentMemory);
          console.log(
            `  After ${i.toString().padStart(5)} events: ${currentMemory.toFixed(2)} MB (+${(currentMemory - baselineMemory).toFixed(2)} MB)`,
          );
        }
      }

      // Flush all events
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Final memory check
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const finalMemory = getMemoryMB();
      const memoryGrowth = finalMemory - baselineMemory;

      console.log(`\nFinal memory: ${finalMemory.toFixed(2)} MB`);
      console.log(`Total growth: ${memoryGrowth.toFixed(2)} MB`);
      console.log(`Memory per event: ${((memoryGrowth / numEvents) * 1024).toFixed(3)} KB`);

      // Memory growth should be minimal (< 20 MB for 10k events)
      expect(memoryGrowth).toBeLessThan(20);

      // Memory should not grow linearly
      if (memorySamples.length > 1) {
        const earlyAvg = (memorySamples[0] + memorySamples[1]) / 2;
        const lateAvg =
          (memorySamples[memorySamples.length - 2] + memorySamples[memorySamples.length - 1]) /
          2;
        const growthRate = lateAvg - earlyAvg;
        console.log(`Memory growth rate: ${growthRate.toFixed(2)} MB`);
        expect(growthRate).toBeLessThan(10);
      }
    });

    it('should return memory to baseline after flush', async () => {
      console.log('\n=== Testing memory returns to baseline after flush ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-memory-baseline',
        version: '1.0.0',
        batchSize: 10000,
        flushInterval: 60000,
      });

      // Generate events
      const numEvents = 5000;
      for (let i = 0; i < numEvents; i++) {
        client.trackEvent('test.memory.baseline', {
          event_id: i,
          data: 'x'.repeat(100),
        });
      }

      // Check memory before flush
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const beforeFlush = getMemoryMB();
      console.log(
        `Before flush: ${beforeFlush.toFixed(2)} MB (+${(beforeFlush - baselineMemory).toFixed(2)} MB)`,
      );

      // Flush and wait
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Check memory after flush
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const afterFlush = getMemoryMB();
      console.log(
        `After flush: ${afterFlush.toFixed(2)} MB (+${(afterFlush - baselineMemory).toFixed(2)} MB)`,
      );

      // Memory should be closer to baseline (within 35 MB - Node.js GC is less aggressive)
      const memoryDiff = Math.abs(afterFlush - baselineMemory);
      expect(memoryDiff).toBeLessThan(35);
    });
  });

  describe('Sustained Load Memory Stability', () => {
    it('should maintain stable memory under sustained load', async () => {
      console.log('\n=== Testing memory stability under sustained load ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-memory-sustained',
        version: '1.0.0',
        batchSize: 100,
        flushInterval: 1000, // 1s flush interval
      });

      // Run for shorter period in tests (10s instead of 30s)
      const durationSeconds = 10;
      const memorySamples: Array<{ time: number; memory_mb: number; events: number }> = [];
      const startTime = Date.now();

      console.log(`\nRunning sustained load for ${durationSeconds}s...`);

      let eventCount = 0;
      while ((Date.now() - startTime) / 1000 < durationSeconds) {
        // Send batch of events
        for (let i = 0; i < 10; i++) {
          client.trackEvent('test.memory.sustained', {
            event_id: eventCount,
            timestamp: Date.now(),
          });
          eventCount++;
        }

        // Sample memory every second
        const elapsed = (Date.now() - startTime) / 1000;
        if (Math.floor(elapsed) > memorySamples.length) {
          forceGC();
          const currentMemory = getMemoryMB();
          memorySamples.push({
            time: elapsed,
            memory_mb: currentMemory,
            events: eventCount,
          });
          console.log(`  ${elapsed.toFixed(0)}s: ${currentMemory.toFixed(2)} MB, ${eventCount} events`);
        }

        await new Promise((resolve) => setTimeout(resolve, 10));
      }

      // Flush all events
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Final memory check
      forceGC();
      const finalMemory = getMemoryMB();

      console.log(`\nTotal events sent: ${eventCount}`);
      console.log(`Final memory: ${finalMemory.toFixed(2)} MB`);
      console.log(`Memory growth: ${(finalMemory - baselineMemory).toFixed(2)} MB`);

      // Analyze memory stability
      if (memorySamples.length > 3) {
        const memoryValues = memorySamples.map((s) => s.memory_mb);
        const maxMemory = Math.max(...memoryValues);
        const minMemory = Math.min(...memoryValues);
        const memoryRange = maxMemory - minMemory;

        console.log(
          `Memory range: ${memoryRange.toFixed(2)} MB (min: ${minMemory.toFixed(2)}, max: ${maxMemory.toFixed(2)})`,
        );

        // Memory should be relatively stable (< 70 MB variation - Node.js GC patterns)
        expect(memoryRange).toBeLessThan(70);
      }
    });
  });

  describe('Large Payload Memory Usage', () => {
    it('should handle large payloads without excessive memory growth', async () => {
      console.log('\n=== Testing large payload memory usage ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-memory-large',
        version: '1.0.0',
        batchSize: 100,
        flushInterval: 60000,
      });

      // Send events with large payloads
      const numEvents = 1000;
      for (let i = 0; i < numEvents; i++) {
        const largePayload = {
          event_id: i,
          large_field_1: 'a'.repeat(1000),
          large_field_2: 'b'.repeat(1000),
          large_field_3: 'c'.repeat(1000),
        };
        client.trackEvent('test.memory.large', largePayload);

        // Periodic flush
        if (i % 100 === 0 && i > 0) {
          await client.flush();
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      }

      // Final flush
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Check memory
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const finalMemory = getMemoryMB();
      const memoryGrowth = finalMemory - baselineMemory;

      console.log(`Final memory: ${finalMemory.toFixed(2)} MB`);
      console.log(`Memory growth: ${memoryGrowth.toFixed(2)} MB`);

      // Memory growth should be reasonable (< 25 MB)
      expect(memoryGrowth).toBeLessThan(25);
    });
  });

  describe('Mixed Signals Memory Usage', () => {
    it('should handle mixed signal types without memory leaks', async () => {
      console.log('\n=== Testing mixed signals memory usage ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-memory-mixed',
        version: '1.0.0',
        batchSize: 200,
        flushInterval: 60000,
      });

      // Send mixed signals
      const numIterations = 2000;
      for (let i = 0; i < numIterations; i++) {
        // Trace
        client.trackEvent('test.memory.mixed.trace', { id: i });

        // Metric
        client.trackMetric('test.memory.mixed.metric', i, MetricType.GAUGE);

        // Log
        client.trackLog(`Mixed signal test ${i}`, LogSeverity.INFO);

        // Periodic flush
        if (i % 200 === 0 && i > 0) {
          await client.flush();
        }
      }

      // Final flush
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Check memory
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const finalMemory = getMemoryMB();
      const memoryGrowth = finalMemory - baselineMemory;

      console.log(`Final memory: ${finalMemory.toFixed(2)} MB`);
      console.log(`Memory growth: ${memoryGrowth.toFixed(2)} MB`);

      // Memory growth should be reasonable (< 30 MB - Node.js memory management)
      expect(memoryGrowth).toBeLessThan(30);
    });
  });

  describe('Repeated Enable/Disable Cycles', () => {
    it('should not leak memory with repeated enable/disable', async () => {
      console.log('\n=== Testing repeated enable/disable ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      // Repeatedly create, use, and destroy clients
      const numCycles = 50;

      for (let i = 0; i < numCycles; i++) {
        const client = new AutomagikTelemetry({
          projectName: 'test-cycle',
          version: '1.0.0',
          batchSize: 10,
          flushInterval: 60000,
        });

        // Send some events
        for (let j = 0; j < 10; j++) {
          client.trackEvent('test.cycle', { cycle: i, event: j });
        }

        // Flush and disable
        await client.flush();
        client.disable();

        // Periodic garbage collection
        if (i % 10 === 0 && i > 0) {
          forceGC();
          await new Promise((resolve) => setTimeout(resolve, 10));
          const currentMemory = getMemoryMB();
          console.log(`  Cycle ${i}: ${currentMemory.toFixed(2)} MB`);
        }
      }

      // Final check
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const finalMemory = getMemoryMB();
      const memoryGrowth = finalMemory - baselineMemory;

      console.log(`\nAfter ${numCycles} cycles:`);
      console.log(`  Memory: ${finalMemory.toFixed(2)} MB (+${memoryGrowth.toFixed(2)} MB)`);

      // Memory growth should be minimal (< 10 MB)
      expect(memoryGrowth).toBeLessThan(10);
    });
  });

  describe('Queue Memory Bounds', () => {
    it('should not grow queues unbounded in memory', async () => {
      console.log('\n=== Testing queue memory bounds ===');

      // Get baseline
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baselineMemory = getMemoryMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const client = new AutomagikTelemetry({
        projectName: 'test-queue-bounds',
        version: '1.0.0',
        batchSize: 10000, // Large batch to accumulate events
        flushInterval: 3600000, // Very long interval
      });

      // Send many events without flushing
      const numEvents = 5000;

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent('test.queue.bounds', {
          event_id: i,
          data: 'x'.repeat(50),
        });
      }

      // Check memory with queued events
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const queuedMemory = getMemoryMB();
      const queuedGrowth = queuedMemory - baselineMemory;

      console.log(
        `Memory with ${numEvents} queued events: ${queuedMemory.toFixed(2)} MB (+${queuedGrowth.toFixed(2)} MB)`,
      );

      // Flush and check memory returns
      await client.flush();
      await new Promise((resolve) => setTimeout(resolve, 100));
      forceGC();
      await new Promise((resolve) => setTimeout(resolve, 100));

      const flushedMemory = getMemoryMB();
      const flushedGrowth = flushedMemory - baselineMemory;

      console.log(
        `Memory after flush: ${flushedMemory.toFixed(2)} MB (+${flushedGrowth.toFixed(2)} MB)`,
      );

      const memoryFreed = queuedMemory - flushedMemory;
      console.log(`Memory freed by flush: ${memoryFreed.toFixed(2)} MB`);

      // Memory should drop after flush (or at least not grow)
      // Note: V8's GC may not immediately release memory
      expect(flushedMemory).toBeLessThanOrEqual(queuedMemory + 5);
    });
  });
});
