/**
 * Test for TelemetryBackend interface.
 *
 * This file verifies that the TelemetryBackend interface is properly defined
 * and that both OTLPBackend and ClickHouseBackend implement it correctly.
 */

import { TelemetryBackend } from "../base";
import { OTLPBackend } from "../otlp";
import { ClickHouseBackend } from "../clickhouse";

describe("TelemetryBackend Interface", () => {
  describe("Type checking", () => {
    it("OTLPBackend should satisfy TelemetryBackend interface", () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });
      expect(backend).toBeDefined();
    });

    it("ClickHouseBackend should satisfy TelemetryBackend interface", () => {
      const backend: TelemetryBackend = new ClickHouseBackend();
      expect(backend).toBeDefined();
    });
  });

  describe("Interface methods", () => {
    it("should define sendTrace method", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });

      // Mock fetch to avoid network calls
      global.fetch = jest.fn().mockResolvedValue({
        status: 200,
        ok: true,
      } as Response);

      const result = await backend.sendTrace({ test: "data" });
      expect(typeof result).toBe("boolean");
    });

    it("should define sendMetric method", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/metrics",
      });

      // Mock fetch to avoid network calls
      global.fetch = jest.fn().mockResolvedValue({
        status: 200,
        ok: true,
      } as Response);

      const result = await backend.sendMetric({ test: "data" });
      expect(typeof result).toBe("boolean");
    });

    it("should define sendLog method", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/logs",
      });

      // Mock fetch to avoid network calls
      global.fetch = jest.fn().mockResolvedValue({
        status: 200,
        ok: true,
      } as Response);

      const result = await backend.sendLog({ test: "data" });
      expect(typeof result).toBe("boolean");
    });

    it("should define flush method", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });

      const result = await backend.flush();
      expect(typeof result).toBe("boolean");
      expect(result).toBe(true);
    });
  });

  describe("Interface contract", () => {
    it("should allow both sync and async implementations", () => {
      // OTLPBackend returns Promise<boolean>
      const otlpBackend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });
      const otlpResult = otlpBackend.sendTrace({});
      expect(otlpResult).toBeInstanceOf(Promise);

      // ClickHouseBackend returns boolean for sendTrace
      const clickhouseBackend: TelemetryBackend = new ClickHouseBackend();
      const chResult = clickhouseBackend.sendTrace({});
      expect(typeof chResult).toBe("boolean");
    });

    it("should accept unknown payload types", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });

      // Mock fetch to avoid network calls
      global.fetch = jest.fn().mockResolvedValue({
        status: 200,
        ok: true,
      } as Response);

      // Test with various payload types
      await backend.sendTrace({ object: "payload" });
      await backend.sendTrace("string payload");
      await backend.sendTrace(123);
      await backend.sendTrace([1, 2, 3]);
      await backend.sendTrace(null);
    });

    it("should support variadic arguments", async () => {
      const backend: TelemetryBackend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/metrics",
      });

      // Mock fetch to avoid network calls
      global.fetch = jest.fn().mockResolvedValue({
        status: 200,
        ok: true,
      } as Response);

      // sendMetric can accept additional arguments (e.g., endpoint override)
      const result = await backend.sendMetric(
        { test: "data" },
        "http://custom-endpoint",
      );
      expect(typeof result).toBe("boolean");
    });
  });

  describe("Custom backend implementation", () => {
    it("should allow custom backends to implement the interface", async () => {
      class CustomBackend implements TelemetryBackend {
        sendTrace(): boolean {
          return true;
        }

        sendMetric(): boolean {
          return true;
        }

        sendLog(): boolean {
          return true;
        }

        flush(): boolean {
          return true;
        }
      }

      const backend: TelemetryBackend = new CustomBackend();
      expect(backend.sendTrace({})).toBe(true);
      expect(backend.sendMetric({})).toBe(true);
      expect(backend.sendLog({})).toBe(true);
      expect(backend.flush()).toBe(true);
    });

    it("should allow async custom backends", async () => {
      class AsyncCustomBackend implements TelemetryBackend {
        async sendTrace(): Promise<boolean> {
          return true;
        }

        async sendMetric(): Promise<boolean> {
          return true;
        }

        async sendLog(): Promise<boolean> {
          return true;
        }

        async flush(): Promise<boolean> {
          return true;
        }
      }

      const backend: TelemetryBackend = new AsyncCustomBackend();
      expect(await backend.sendTrace({})).toBe(true);
      expect(await backend.sendMetric({})).toBe(true);
      expect(await backend.sendLog({})).toBe(true);
      expect(await backend.flush()).toBe(true);
    });
  });
});
