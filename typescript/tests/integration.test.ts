/**
 * Comprehensive integration tests for TypeScript SDK.
 *
 * Tests real-world scenarios including:
 * - Express/Fastify integration
 * - High-throughput scenarios
 * - Real OTLP collector integration
 * - Memory leak detection
 * - Concurrent request handling
 *
 * Run with: npm test -- integration.test.ts
 * Or with integration marker: npm test -- --testNamePattern="integration"
 */

import { AutomagikTelemetry, MetricType, LogSeverity } from "../src";
import type { TelemetryConfig } from "../src/config";

// Helper to skip tests in CI unless explicitly enabled
const isCI = process.env.CI === "true";
const runIntegration = process.env.RUN_INTEGRATION_TESTS === "true";
const describeIntegration = isCI && !runIntegration ? describe.skip : describe;

// Helper to get memory usage in MB
function getMemoryUsageMB(): number {
  const usage = process.memoryUsage();
  return usage.heapUsed / 1024 / 1024;
}

// Helper to sleep
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describeIntegration("Integration Tests", () => {
  let client: InstanceType<typeof AutomagikTelemetry>;

  beforeEach(() => {
    // Enable telemetry for integration tests
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
  });

  afterEach(async () => {
    if (client) {
      await client.flush();
      await client.disable();
    }
  });

  describe("Express/Fastify Integration", () => {
    test("should work with Express middleware pattern", async () => {
      const config: TelemetryConfig = {
        projectName: "test-express",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 10,
        flushInterval: 1000,
      };
      client = new AutomagikTelemetry(config);

      // Simulate middleware that tracks requests
      const simulateRequest = async (path: string, method: string) => {
        const startTime = Date.now();

        // Track request start
        client.trackEvent("api.request.start", {
          path,
          method,
        });

        // Simulate request processing
        await sleep(10);

        const latency = Date.now() - startTime;

        // Track request completion
        client.trackMetric(
          "api.request.latency",
          latency,
          MetricType.HISTOGRAM,
          { path, method },
        );
        client.trackEvent("api.request.complete", { path, method, latency });
      };

      // Simulate multiple requests
      const requests = [
        simulateRequest("/", "GET"),
        simulateRequest("/api/users", "GET"),
        simulateRequest("/api/users", "POST"),
        simulateRequest("/api/data", "GET"),
      ];

      await Promise.all(requests);
      await client.flush();

      expect(client.isEnabled()).toBe(true);
    }, 10000);

    test("should handle concurrent Express requests", async () => {
      const config: TelemetryConfig = {
        projectName: "test-concurrent-express",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 50,
      };
      client = new AutomagikTelemetry(config);

      const numRequests = 100;
      const startTime = Date.now();

      const requests = Array.from({ length: numRequests }, (_, i) =>
        client.trackEvent("api.concurrent", { requestId: i }),
      );

      await Promise.all(requests);
      await client.flush();

      const duration = Date.now() - startTime;
      const requestsPerSecond = numRequests / (duration / 1000);

      console.log(`\nConcurrent requests: ${numRequests}`);
      console.log(`Duration: ${duration}ms`);
      console.log(`Requests/sec: ${requestsPerSecond.toFixed(1)}`);

      expect(duration).toBeLessThan(2000); // Should complete in < 2s
    }, 15000);
  });

  describe("High-Throughput Tests", () => {
    test("should handle burst of 1000 events", async () => {
      const config: TelemetryConfig = {
        projectName: "test-burst",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 100,
        flushInterval: 1000,
        compressionEnabled: true,
      };
      client = new AutomagikTelemetry(config);

      const numEvents = 1000;
      const startTime = Date.now();

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.burst", {
          eventNumber: i,
          category: `category_${i % 10}`,
        });
      }

      const generationTime = Date.now() - startTime;
      await client.flush();
      const totalTime = Date.now() - startTime;

      console.log(`\nBurst test: ${numEvents} events`);
      console.log(`Generation time: ${generationTime}ms`);
      console.log(`Total time (with flush): ${totalTime}ms`);
      console.log(`Events/sec: ${(numEvents / (totalTime / 1000)).toFixed(1)}`);

      expect(generationTime).toBeLessThan(1000); // Generation < 1s
      expect(totalTime).toBeLessThan(5000); // Total < 5s
    }, 15000);

    test("should handle sustained throughput", async () => {
      const config: TelemetryConfig = {
        projectName: "test-sustained",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 100,
        compressionEnabled: true,
      };
      client = new AutomagikTelemetry(config);

      const durationSeconds = 5;
      const targetRate = 500; // events per second
      const totalEvents = durationSeconds * targetRate;

      const startTime = Date.now();
      let eventCount = 0;

      while (eventCount < totalEvents) {
        client.trackEvent("test.sustained", {
          eventId: eventCount,
          timestamp: Date.now(),
        });
        eventCount++;

        // Small delay to maintain rate
        if (eventCount % 50 === 0) {
          await sleep(10);
        }
      }

      const duration = (Date.now() - startTime) / 1000;
      await client.flush();

      const actualRate = totalEvents / duration;

      console.log(`\nSustained throughput test:`);
      console.log(`  Total events: ${totalEvents}`);
      console.log(`  Duration: ${duration.toFixed(2)}s`);
      console.log(`  Average rate: ${actualRate.toFixed(1)} events/sec`);
      console.log(`  Target rate: ${targetRate} events/sec`);

      expect(actualRate).toBeGreaterThan(targetRate * 0.8); // Within 20% of target
    }, 20000);

    test("should handle mixed signal types at high volume", async () => {
      const config: TelemetryConfig = {
        projectName: "test-mixed",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 100,
      };
      client = new AutomagikTelemetry(config);

      const numIterations = 500;
      const startTime = Date.now();

      for (let i = 0; i < numIterations; i++) {
        // Trace
        client.trackEvent("test.mixed.event", { iteration: i });

        // Metric
        client.trackMetric("test.mixed.counter", i, MetricType.COUNTER, {
          iteration: i,
        });

        // Log
        client.trackLog(`Mixed signal iteration ${i}`, LogSeverity.INFO, {
          iteration: i,
        });
      }

      await client.flush();
      const duration = Date.now() - startTime;
      const totalSignals = numIterations * 3;

      console.log(`\nMixed signal types test:`);
      console.log(`  Iterations: ${numIterations}`);
      console.log(`  Total signals: ${totalSignals}`);
      console.log(`  Duration: ${duration}ms`);
      console.log(
        `  Rate: ${(totalSignals / (duration / 1000)).toFixed(1)} signals/sec`,
      );

      expect(duration).toBeLessThan(10000); // < 10s
    }, 15000);
  });

  describe("Real OTLP Collector Integration", () => {
    beforeEach(() => {
      const endpoint =
        process.env.AUTOMAGIK_TELEMETRY_ENDPOINT ||
        "https://telemetry.namastex.ai";
      const config: TelemetryConfig = {
        projectName: "test-otlp-integration",
        version: "1.0.0",
        endpoint,
        batchSize: 1, // Immediate send for integration tests
        timeout: 10,
        maxRetries: 2,
      };
      client = new AutomagikTelemetry(config);
      process.env.AUTOMAGIK_TELEMETRY_VERBOSE = "true";
    });

    test("should send trace to real collector", async () => {
      console.log("\n=== Testing trace to OTLP collector ===");

      client.trackEvent("integration.test.trace", {
        testType: "trace",
        timestamp: Date.now(),
        environment: "integration_test",
      });

      await client.flush();
      await sleep(500);

      console.log("Trace sent successfully (no exceptions)");
    }, 15000);

    test("should send metrics to real collector", async () => {
      console.log("\n=== Testing metrics to OTLP collector ===");

      // Gauge
      client.trackMetric("integration.test.gauge", 42.5, MetricType.GAUGE, {
        testType: "gauge",
      });

      // Counter
      client.trackMetric("integration.test.counter", 100, MetricType.COUNTER, {
        testType: "counter",
      });

      // Histogram
      client.trackMetric(
        "integration.test.histogram",
        123.45,
        MetricType.HISTOGRAM,
        { testType: "histogram" },
      );

      await client.flush();
      await sleep(500);

      console.log("Metrics sent successfully (no exceptions)");
    }, 15000);

    test("should send logs to real collector", async () => {
      console.log("\n=== Testing logs to OTLP collector ===");

      const severities = [
        { level: LogSeverity.TRACE, message: "This is a trace log" },
        { level: LogSeverity.DEBUG, message: "This is a debug log" },
        { level: LogSeverity.INFO, message: "This is an info log" },
        { level: LogSeverity.WARN, message: "This is a warning log" },
        { level: LogSeverity.ERROR, message: "This is an error log" },
      ];

      for (const { level, message } of severities) {
        client.trackLog(message, level, { testType: "log" });
      }

      await client.flush();
      await sleep(500);

      console.log("Logs sent successfully (no exceptions)");
    }, 15000);

    test("should send all signal types", async () => {
      console.log("\n=== Testing all signal types to OTLP collector ===");

      // Trace
      client.trackEvent("integration.test.all_signals", {
        signalType: "trace",
        step: 1,
      });

      // Metric
      client.trackMetric(
        "integration.test.all_signals",
        456.78,
        MetricType.GAUGE,
        { signalType: "metric", step: 2 },
      );

      // Log
      client.trackLog("All signals test completed", LogSeverity.INFO, {
        signalType: "log",
        step: 3,
      });

      await client.flush();
      await sleep(500);

      console.log("All signal types sent successfully");
    }, 15000);

    test("should handle large payloads with compression", async () => {
      console.log("\n=== Testing large payload to OTLP collector ===");

      const largeData = {
        largeField1: "x".repeat(1000),
        largeField2: "y".repeat(1000),
        largeField3: "z".repeat(1000),
        testType: "large_payload",
      };

      client.trackEvent("integration.test.large_payload", largeData);

      await client.flush();
      await sleep(500);

      console.log("Large payload sent successfully (likely compressed)");
    }, 15000);
  });

  describe("Memory Leak Detection", () => {
    test("should not leak memory with simple events", async () => {
      console.log("\n=== Testing memory leaks with simple events ===");

      const config: TelemetryConfig = {
        projectName: "test-memory",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 50,
        flushInterval: 2000,
      };
      client = new AutomagikTelemetry(config);

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const baselineMemory = getMemoryUsageMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const numEvents = 5000;
      const memorySamples: number[] = [];

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.memory.simple", { eventId: i });

        // Sample memory every 500 events
        if (i % 500 === 0) {
          if (global.gc) global.gc();
          const currentMemory = getMemoryUsageMB();
          memorySamples.push(currentMemory);
          console.log(`  After ${i} events: ${currentMemory.toFixed(2)} MB`);
        }
      }

      await client.flush();
      await sleep(1000);

      if (global.gc) global.gc();
      const finalMemory = getMemoryUsageMB();
      const memoryGrowth = finalMemory - baselineMemory;

      console.log(`Final memory: ${finalMemory.toFixed(2)} MB`);
      console.log(`Total growth: ${memoryGrowth.toFixed(2)} MB`);

      // Memory growth should be reasonable (< 50 MB for 5k events in CI)
      expect(memoryGrowth).toBeLessThan(50);
    }, 30000);

    test("should return memory to baseline after flush", async () => {
      console.log("\n=== Testing memory returns to baseline after flush ===");

      const config: TelemetryConfig = {
        projectName: "test-memory-baseline",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 100,
      };
      client = new AutomagikTelemetry(config);

      if (global.gc) global.gc();
      const baselineMemory = getMemoryUsageMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      // Generate events
      const numEvents = 2000;
      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.memory.baseline", {
          eventId: i,
          data: "x".repeat(100),
        });
      }

      if (global.gc) global.gc();
      const beforeFlush = getMemoryUsageMB();
      console.log(
        `Before flush: ${beforeFlush.toFixed(2)} MB (+${(beforeFlush - baselineMemory).toFixed(2)} MB)`,
      );

      // Flush and wait
      await client.flush();
      await sleep(2000);

      if (global.gc) global.gc();
      const afterFlush = getMemoryUsageMB();
      console.log(
        `After flush: ${afterFlush.toFixed(2)} MB (+${(afterFlush - baselineMemory).toFixed(2)} MB)`,
      );

      // Memory should be close to baseline (within 40 MB in CI)
      const memoryDiff = Math.abs(afterFlush - baselineMemory);
      expect(memoryDiff).toBeLessThan(40);
    }, 30000);

    test("should handle sustained load without memory leak", async () => {
      console.log("\n=== Testing memory stability under sustained load ===");

      const config: TelemetryConfig = {
        projectName: "test-memory-sustained",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 50,
      };
      client = new AutomagikTelemetry(config);

      if (global.gc) global.gc();
      const baselineMemory = getMemoryUsageMB();
      console.log(`Baseline memory: ${baselineMemory.toFixed(2)} MB`);

      const durationSeconds = 10;
      const eventsPerSecond = 100;
      const totalEvents = durationSeconds * eventsPerSecond;

      const memorySamples: Array<{
        time: number;
        memory: number;
        events: number;
      }> = [];
      const startTime = Date.now();
      let eventCount = 0;

      console.log(
        `\nRunning sustained load for ${durationSeconds}s at ${eventsPerSecond} events/sec...`,
      );

      while (eventCount < totalEvents) {
        client.trackEvent("test.memory.sustained", {
          eventId: eventCount,
          timestamp: Date.now(),
        });
        eventCount++;

        // Sample memory every second
        const elapsed = (Date.now() - startTime) / 1000;
        if (
          Math.floor(elapsed) > memorySamples.length &&
          memorySamples.length < durationSeconds
        ) {
          if (global.gc) global.gc();
          const currentMemory = getMemoryUsageMB();
          memorySamples.push({
            time: elapsed,
            memory: currentMemory,
            events: eventCount,
          });
          console.log(
            `  ${elapsed.toFixed(0)}s: ${currentMemory.toFixed(2)} MB, ${eventCount} events`,
          );
        }

        // Maintain rate
        if (eventCount % 10 === 0) {
          await sleep(5);
        }
      }

      await client.flush();
      await sleep(1000);

      if (global.gc) global.gc();
      const finalMemory = getMemoryUsageMB();

      console.log(`\nTotal events sent: ${eventCount}`);
      console.log(`Final memory: ${finalMemory.toFixed(2)} MB`);
      console.log(
        `Memory growth: ${(finalMemory - baselineMemory).toFixed(2)} MB`,
      );

      // Analyze memory stability
      if (memorySamples.length > 3) {
        const memoryValues = memorySamples.map((s) => s.memory);
        const maxMemory = Math.max(...memoryValues);
        const minMemory = Math.min(...memoryValues);
        const memoryRange = maxMemory - minMemory;

        console.log(
          `Memory range: ${memoryRange.toFixed(2)} MB (min: ${minMemory.toFixed(2)}, max: ${maxMemory.toFixed(2)})`,
        );

        // Memory should be relatively stable (< 30 MB variation)
        expect(memoryRange).toBeLessThan(30);
      }
    }, 60000);
  });

  describe("Error Handling", () => {
    test("should handle network errors gracefully", async () => {
      const config: TelemetryConfig = {
        projectName: "test-error",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 1,
        timeout: 5,
        maxRetries: 2,
      };
      client = new AutomagikTelemetry(config);

      // Should not throw even if there are network issues
      expect(() => {
        client.trackEvent("test.error.network", { test: true });
      }).not.toThrow();

      await client.flush();
    }, 15000);

    test("should track errors correctly", async () => {
      const config: TelemetryConfig = {
        projectName: "test-error-tracking",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 1,
      };
      client = new AutomagikTelemetry(config);

      const error = new Error("Test error for integration");
      client.trackError(error, { context: "integration_test" });

      await client.flush();
      await sleep(500);
    }, 15000);
  });

  describe("Configuration", () => {
    test("should respect custom endpoints", () => {
      const customEndpoint = "https://telemetry.namastex.ai";
      const config: TelemetryConfig = {
        projectName: "test-custom",
        version: "1.0.0",
        endpoint: customEndpoint,
      };
      client = new AutomagikTelemetry(config);

      const status = client.getStatus();
      expect(status.endpoint).toContain("telemetry.namastex.ai");
    });

    test("should handle batch configuration", async () => {
      const config: TelemetryConfig = {
        projectName: "test-batch",
        version: "1.0.0",
        endpoint: "https://telemetry.namastex.ai",
        batchSize: 10,
      };
      client = new AutomagikTelemetry(config);

      // Send events less than batch size
      for (let i = 0; i < 5; i++) {
        client.trackEvent("test.batch", { id: i });
      }

      // Events should be queued, not sent yet
      await sleep(100);

      // Manual flush should send them
      await client.flush();
    }, 10000);
  });
});
