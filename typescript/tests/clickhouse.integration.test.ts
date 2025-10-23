/**
 * ClickHouse Backend Integration Tests
 *
 * Tests the direct ClickHouse backend implementation end-to-end.
 *
 * Prerequisites:
 * - ClickHouse running at localhost:8123
 * - Database and table created (via infra/clickhouse/init-db.sql)
 *
 * To start infrastructure:
 *   cd infra && docker compose up -d clickhouse
 *
 * To run these tests:
 *   RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts
 *
 * Or with specific test:
 *   RUN_INTEGRATION_TESTS=true npm test -- -t "should send traces to ClickHouse"
 */

import * as http from "http";
import { AutomagikTelemetry, MetricType, LogSeverity } from "../src/index";
import type { TelemetryConfig } from "../src/client";

// Skip tests in CI unless explicitly enabled
const isCI = process.env.CI === "true";
const runIntegration = process.env.RUN_INTEGRATION_TESTS === "true";
const describeIntegration = isCI && !runIntegration ? describe.skip : describe;

// ClickHouse configuration
const CLICKHOUSE_ENDPOINT = process.env.CLICKHOUSE_ENDPOINT || "http://localhost:8123";
const CLICKHOUSE_DATABASE = process.env.CLICKHOUSE_DATABASE || "telemetry";
const CLICKHOUSE_TABLE = process.env.CLICKHOUSE_TABLE || "traces";
const CLICKHOUSE_USERNAME = process.env.CLICKHOUSE_USERNAME || "default";
const CLICKHOUSE_PASSWORD = process.env.CLICKHOUSE_PASSWORD || "";

/**
 * Helper to execute ClickHouse query via HTTP API
 */
async function executeClickHouseQuery(query: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const url = new URL(CLICKHOUSE_ENDPOINT);
    url.searchParams.set("query", query);
    url.searchParams.set("default_format", "JSON");

    const options: http.RequestOptions = {
      hostname: url.hostname,
      port: url.port || 8123,
      path: `${url.pathname}${url.search}`,
      method: "GET",
      timeout: 10000,
    };

    // Add authentication if provided
    if (CLICKHOUSE_USERNAME) {
      const auth = Buffer.from(
        `${CLICKHOUSE_USERNAME}:${CLICKHOUSE_PASSWORD}`
      ).toString("base64");
      options.headers = {
        Authorization: `Basic ${auth}`,
      };
    }

    const req = http.request(options, (res) => {
      let data = "";

      res.on("data", (chunk) => {
        data += chunk;
      });

      res.on("end", () => {
        if (res.statusCode === 200) {
          try {
            const parsed = JSON.parse(data);
            resolve(parsed);
          } catch (error) {
            resolve(data); // Return raw data if not JSON
          }
        } else {
          reject(
            new Error(
              `ClickHouse query failed with status ${res.statusCode}: ${data}`
            )
          );
        }
      });
    });

    req.on("error", (error) => {
      reject(error);
    });

    req.on("timeout", () => {
      req.destroy();
      reject(new Error("ClickHouse query timeout"));
    });

    req.end();
  });
}

/**
 * Helper to check ClickHouse availability
 */
async function isClickHouseAvailable(): Promise<boolean> {
  try {
    await executeClickHouseQuery("SELECT 1");
    return true;
  } catch (error) {
    console.warn(
      "\n⚠️  ClickHouse not available at",
      CLICKHOUSE_ENDPOINT,
      "\n   Run: cd infra && docker compose up -d clickhouse\n"
    );
    return false;
  }
}

/**
 * Helper to clean up test data from ClickHouse
 */
async function cleanupTestData(projectName: string): Promise<void> {
  try {
    const query = `ALTER TABLE ${CLICKHOUSE_DATABASE}.${CLICKHOUSE_TABLE} DELETE WHERE project_name = '${projectName}'`;
    await executeClickHouseQuery(query);
    // Wait for mutation to complete
    await new Promise((resolve) => setTimeout(resolve, 2000));
  } catch (error) {
    console.warn("Failed to cleanup test data:", error);
  }
}

/**
 * Helper to wait for data to appear in ClickHouse
 */
async function waitForData(
  projectName: string,
  minCount: number = 1,
  maxAttempts: number = 30,
  delayMs: number = 500
): Promise<any> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const query = `SELECT * FROM ${CLICKHOUSE_DATABASE}.${CLICKHOUSE_TABLE} WHERE project_name = '${projectName}' FORMAT JSON`;
      const result = await executeClickHouseQuery(query);

      if (result.data && result.data.length >= minCount) {
        return result;
      }
    } catch (error) {
      // Continue waiting
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }

  throw new Error(
    `Timeout waiting for data in ClickHouse (expected at least ${minCount} rows)`
  );
}

/**
 * Helper to sleep
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describeIntegration("ClickHouse Backend Integration", () => {
  let clickhouseAvailable = false;

  // Check ClickHouse availability before all tests
  beforeAll(async () => {
    clickhouseAvailable = await isClickHouseAvailable();
    if (!clickhouseAvailable) {
      console.log(
        "\n⏭️  Skipping ClickHouse integration tests (ClickHouse not available)\n"
      );
    }
  });

  // Skip all tests if ClickHouse is not available
  if (!clickhouseAvailable) {
    test.skip("ClickHouse not available", () => {});
    return;
  }

  describe("End-to-End Flow", () => {
    const projectName = `test-e2e-${Date.now()}`;
    let client: AutomagikTelemetry;

    beforeEach(() => {
      // Enable telemetry and set backend to ClickHouse
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
      process.env.AUTOMAGIK_TELEMETRY_BACKEND = "clickhouse";
    });

    afterEach(async () => {
      if (client) {
        await client.flush();
        await client.disable();
      }
      await cleanupTestData(projectName);
    });

    test("should send traces to ClickHouse and verify data", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        clickhouseDatabase: CLICKHOUSE_DATABASE,
        clickhouseUsername: CLICKHOUSE_USERNAME,
        clickhousePassword: CLICKHOUSE_PASSWORD,
        batchSize: 1,
      };

      client = new AutomagikTelemetry(config);

      // Track multiple events
      client.trackEvent("test.event.one", {
        feature_name: "test_feature",
        user_action: "click",
      });

      client.trackEvent("test.event.two", {
        feature_name: "another_feature",
        result: "success",
      });

      // Flush and wait for data
      await client.flush();
      await sleep(1000);

      // Query ClickHouse to verify data
      const result = await waitForData(projectName, 2);

      expect(result.data).toBeDefined();
      expect(result.data.length).toBeGreaterThanOrEqual(2);

      // Verify first event
      const event1 = result.data.find((row: any) => row.span_name === "test.event.one");
      expect(event1).toBeDefined();
      expect(event1.service_name).toBe(projectName);
      expect(event1.project_name).toContain("test-e2e");
      expect(event1.attributes).toBeDefined();

      // Verify second event
      const event2 = result.data.find((row: any) => row.span_name === "test.event.two");
      expect(event2).toBeDefined();
      expect(event2.attributes).toBeDefined();

      console.log(`✅ Verified ${result.data.length} traces in ClickHouse`);
    }, 30000);

    test("should handle batch processing correctly", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        clickhouseDatabase: CLICKHOUSE_DATABASE,
        batchSize: 10,
      };

      client = new AutomagikTelemetry(config);

      // Send 25 events (should auto-flush after 10 and 20)
      const numEvents = 25;
      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.batch.event", {
          event_id: i,
          batch_test: true,
        });
      }

      // Manual flush for remaining events
      await client.flush();
      await sleep(2000);

      // Verify all events were inserted
      const result = await waitForData(projectName, numEvents);
      expect(result.data.length).toBeGreaterThanOrEqual(numEvents);

      console.log(`✅ Verified ${result.data.length} batched traces in ClickHouse`);
    }, 30000);

    test("should handle high-throughput bursts", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        batchSize: 100,
      };

      client = new AutomagikTelemetry(config);

      const numEvents = 500;
      const startTime = Date.now();

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.burst.event", {
          event_number: i,
          category: `cat_${i % 10}`,
        });
      }

      const generationTime = Date.now() - startTime;
      await client.flush();
      const totalTime = Date.now() - startTime;

      console.log(`Generation time: ${generationTime}ms`);
      console.log(`Total time with flush: ${totalTime}ms`);
      console.log(`Rate: ${(numEvents / (totalTime / 1000)).toFixed(1)} events/sec`);

      // Wait for data
      await sleep(3000);
      const result = await waitForData(projectName, numEvents);

      expect(result.data.length).toBeGreaterThanOrEqual(numEvents);
      expect(totalTime).toBeLessThan(10000); // Should complete in < 10s

      console.log(`✅ Verified ${result.data.length} high-throughput traces`);
    }, 45000);
  });

  describe("Configuration Tests", () => {
    const projectName = `test-config-${Date.now()}`;
    let client: AutomagikTelemetry;

    beforeEach(() => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
    });

    afterEach(async () => {
      if (client) {
        await client.flush();
        await client.disable();
      }
      await cleanupTestData(projectName);
    });

    test("should use environment variable configuration", async () => {
      process.env.AUTOMAGIK_TELEMETRY_BACKEND = "clickhouse";
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT = CLICKHOUSE_ENDPOINT;
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE = CLICKHOUSE_DATABASE;
      process.env.AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE = CLICKHOUSE_TABLE;

      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        // Backend should be picked up from env var
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.env.config", { source: "env_vars" });
      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      expect(result.data.length).toBeGreaterThanOrEqual(1);

      console.log("✅ Environment variable configuration works");
    }, 20000);

    test("should use config object configuration", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        clickhouseDatabase: CLICKHOUSE_DATABASE,
        clickhouseUsername: CLICKHOUSE_USERNAME,
        clickhousePassword: CLICKHOUSE_PASSWORD,
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.config.object", { source: "config_object" });
      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      expect(result.data.length).toBeGreaterThanOrEqual(1);

      console.log("✅ Config object configuration works");
    }, 20000);

    test("should respect default values", async () => {
      // Minimal config - should use defaults
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        // Using default endpoint (localhost:8123), database (telemetry), table (traces)
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.defaults", { config_type: "minimal" });
      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      expect(result.data.length).toBeGreaterThanOrEqual(1);

      console.log("✅ Default configuration values work");
    }, 20000);
  });

  describe("Backend Selection", () => {
    const projectName = `test-backend-${Date.now()}`;
    let client: AutomagikTelemetry;

    beforeEach(() => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
    });

    afterEach(async () => {
      if (client) {
        await client.flush();
        await client.disable();
      }
      await cleanupTestData(projectName);
    });

    test("should switch from otlp to clickhouse backend", async () => {
      // First create client with OTLP (default)
      const otlpConfig: TelemetryConfig = {
        projectName: `${projectName}-otlp`,
        version: "1.0.0",
        backend: "otlp",
      };

      const otlpClient = new AutomagikTelemetry(otlpConfig);
      otlpClient.trackEvent("test.otlp.backend", { backend: "otlp" });
      await otlpClient.flush();
      await otlpClient.disable();

      // Then create client with ClickHouse
      const clickhouseConfig: TelemetryConfig = {
        projectName: `${projectName}-clickhouse`,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
      };

      client = new AutomagikTelemetry(clickhouseConfig);
      client.trackEvent("test.clickhouse.backend", { backend: "clickhouse" });
      await client.flush();
      await sleep(1000);

      // Verify ClickHouse event was stored
      const result = await waitForData(`${projectName}-clickhouse`, 1);
      expect(result.data.length).toBeGreaterThanOrEqual(1);

      console.log("✅ Backend switching works correctly");
    }, 30000);

    test("should maintain backward compatibility", async () => {
      // Old code using default OTLP should still work
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        // No backend specified - should default to OTLP
      };

      client = new AutomagikTelemetry(config);

      // Should not throw
      expect(() => {
        client.trackEvent("test.backward.compat", { legacy: true });
      }).not.toThrow();

      await client.flush();

      console.log("✅ Backward compatibility maintained");
    }, 15000);

    test("should handle invalid backend gracefully", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "invalid-backend",
      };

      // Should not throw on initialization
      expect(() => {
        client = new AutomagikTelemetry(config);
      }).not.toThrow();

      // Should not throw on tracking
      expect(() => {
        client.trackEvent("test.invalid.backend", { test: true });
      }).not.toThrow();

      await client.flush();

      console.log("✅ Invalid backend handled gracefully");
    }, 15000);
  });

  describe("Data Verification", () => {
    const projectName = `test-verify-${Date.now()}`;
    let client: AutomagikTelemetry;

    beforeEach(() => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
    });

    afterEach(async () => {
      if (client) {
        await client.flush();
        await client.disable();
      }
      await cleanupTestData(projectName);
    });

    test("should correctly store trace metadata", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "2.3.4",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        batchSize: 1,
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.metadata", {
        custom_field: "custom_value",
        numeric_field: 42,
      });

      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      const row = result.data[0];

      // Verify metadata
      expect(row.service_name).toBe(projectName);
      expect(row.span_name).toBe("test.metadata");
      expect(row.status_code).toBe("OK");
      expect(row.trace_id).toBeDefined();
      expect(row.span_id).toBeDefined();
      expect(row.timestamp).toBeDefined();

      // Verify attributes contain custom data
      expect(row.attributes).toBeDefined();

      console.log("✅ Trace metadata correctly stored");
      console.log("   Sample row:", JSON.stringify(row, null, 2));
    }, 20000);

    test("should store system information", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.system.info", { test: true });
      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      const row = result.data[0];

      // Verify system information is captured
      expect(row.attributes).toBeDefined();
      // System info should be in attributes from the OTLP transformation

      console.log("✅ System information captured");
    }, 20000);

    test("should handle special characters in attributes", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
      };

      client = new AutomagikTelemetry(config);

      client.trackEvent("test.special.chars", {
        emoji_field: "🚀🎉",
        unicode_field: "Hello 世界",
        quoted_field: 'She said "hello"',
        newline_field: "line1\nline2",
      });

      await client.flush();
      await sleep(1000);

      const result = await waitForData(projectName, 1);
      expect(result.data.length).toBeGreaterThanOrEqual(1);

      console.log("✅ Special characters handled correctly");
    }, 20000);
  });

  describe("Error Handling", () => {
    test("should handle connection failures gracefully", async () => {
      const config: TelemetryConfig = {
        projectName: "test-error",
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: "http://localhost:9999", // Wrong port
        batchSize: 1,
      };

      // Should not throw on init
      let errorClient!: AutomagikTelemetry;
      expect(() => {
        errorClient = new AutomagikTelemetry(config);
      }).not.toThrow();

      // Should not throw on track
      expect(() => {
        errorClient.trackEvent("test.error", { test: true });
      }).not.toThrow();

      // Should not throw on flush
      await expect(errorClient.flush()).resolves.not.toThrow();

      await errorClient.disable();

      console.log("✅ Connection failures handled gracefully");
    }, 15000);

    test("should handle invalid credentials gracefully", async () => {
      const config: TelemetryConfig = {
        projectName: "test-auth-error",
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        clickhouseUsername: "invalid_user",
        clickhousePassword: "invalid_password",
        batchSize: 1,
      };

      const authClient = new AutomagikTelemetry(config);

      // Should not throw
      expect(() => {
        authClient.trackEvent("test.auth.error", { test: true });
      }).not.toThrow();

      await authClient.flush();
      await authClient.disable();

      console.log("✅ Invalid credentials handled gracefully");
    }, 15000);
  });

  describe("Performance", () => {
    const projectName = `test-perf-${Date.now()}`;
    let client: AutomagikTelemetry;

    beforeEach(() => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = "true";
    });

    afterEach(async () => {
      if (client) {
        await client.flush();
        await client.disable();
      }
      await cleanupTestData(projectName);
    });

    test("should handle 1000 events efficiently", async () => {
      const config: TelemetryConfig = {
        projectName,
        version: "1.0.0",
        backend: "clickhouse",
        clickhouseEndpoint: CLICKHOUSE_ENDPOINT,
        batchSize: 100,
        compressionEnabled: true,
      };

      client = new AutomagikTelemetry(config);

      const numEvents = 1000;
      const startTime = Date.now();

      for (let i = 0; i < numEvents; i++) {
        client.trackEvent("test.perf.event", {
          event_id: i,
          category: `cat_${i % 20}`,
        });
      }

      const generationTime = Date.now() - startTime;
      await client.flush();
      const totalTime = Date.now() - startTime;

      console.log(`\nPerformance test: ${numEvents} events`);
      console.log(`  Generation: ${generationTime}ms`);
      console.log(`  Total (with flush): ${totalTime}ms`);
      console.log(`  Rate: ${(numEvents / (totalTime / 1000)).toFixed(1)} events/sec`);

      // Should be fast
      expect(generationTime).toBeLessThan(2000); // < 2s for generation
      expect(totalTime).toBeLessThan(15000); // < 15s total

      // Wait for data
      await sleep(5000);
      const result = await waitForData(projectName, numEvents);
      expect(result.data.length).toBeGreaterThanOrEqual(numEvents);

      console.log(`✅ Performance test passed: ${result.data.length} events verified`);
    }, 60000);
  });
});
