/**
 * Test for backends index exports.
 */

import {
  TelemetryBackend,
  ClickHouseBackend,
  OTLPBackend,
} from "../index";

describe("Backends Index", () => {
  describe("Exports", () => {
    it("should export ClickHouseBackend", () => {
      expect(ClickHouseBackend).toBeDefined();
      expect(typeof ClickHouseBackend).toBe("function");
    });

    it("should export OTLPBackend", () => {
      expect(OTLPBackend).toBeDefined();
      expect(typeof OTLPBackend).toBe("function");
    });
  });

  describe("ClickHouseBackend", () => {
    it("should be able to instantiate ClickHouseBackend from index", () => {
      const backend = new ClickHouseBackend();
      expect(backend).toBeDefined();
    });

    it("should implement TelemetryBackend interface", () => {
      const backend = new ClickHouseBackend();
      expect(typeof backend.sendTrace).toBe("function");
      expect(typeof backend.sendMetric).toBe("function");
      expect(typeof backend.sendLog).toBe("function");
      expect(typeof backend.flush).toBe("function");
    });
  });

  describe("OTLPBackend", () => {
    it("should be able to instantiate OTLPBackend from index", () => {
      const backend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });
      expect(backend).toBeDefined();
    });

    it("should implement TelemetryBackend interface", () => {
      const backend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });
      expect(typeof backend.sendTrace).toBe("function");
      expect(typeof backend.sendMetric).toBe("function");
      expect(typeof backend.sendLog).toBe("function");
      expect(typeof backend.flush).toBe("function");
    });

    it("should have flush method that returns Promise<boolean>", async () => {
      const backend = new OTLPBackend({
        endpoint: "http://localhost:4318/v1/traces",
      });
      const result = await backend.flush();
      expect(result).toBe(true);
    });
  });
});
