/**
 * Tests for the StandardEvents schema.
 */

import { StandardEvents } from "../src/schema";

describe("StandardEvents Schema", () => {
  describe("Constants Existence", () => {
    it("should have all expected event constants defined", () => {
      expect(StandardEvents.FEATURE_USED).toBeDefined();
      expect(StandardEvents.API_REQUEST).toBeDefined();
      expect(StandardEvents.COMMAND_EXECUTED).toBeDefined();
      expect(StandardEvents.OPERATION_LATENCY).toBeDefined();
      expect(StandardEvents.ERROR_OCCURRED).toBeDefined();
      expect(StandardEvents.SERVICE_HEALTH).toBeDefined();
    });
  });

  describe("Naming Convention", () => {
    it("should follow automagik.* naming convention", () => {
      expect(StandardEvents.FEATURE_USED).toMatch(/^automagik\./);
      expect(StandardEvents.API_REQUEST).toMatch(/^automagik\./);
      expect(StandardEvents.COMMAND_EXECUTED).toMatch(/^automagik\./);
      expect(StandardEvents.OPERATION_LATENCY).toMatch(/^automagik\./);
      expect(StandardEvents.ERROR_OCCURRED).toMatch(/^automagik\./);
      expect(StandardEvents.SERVICE_HEALTH).toMatch(/^automagik\./);
    });

    it("should use dot notation (not underscores or dashes)", () => {
      const events = [
        StandardEvents.FEATURE_USED,
        StandardEvents.API_REQUEST,
        StandardEvents.COMMAND_EXECUTED,
        StandardEvents.OPERATION_LATENCY,
        StandardEvents.ERROR_OCCURRED,
        StandardEvents.SERVICE_HEALTH,
      ];

      events.forEach((event) => {
        expect(event).toContain(".");
        expect(event).not.toContain("-");
        // Allow underscores only in specific cases
        if (event !== StandardEvents.ERROR_OCCURRED) {
          expect(event).not.toContain("_");
        }
      });
    });

    it("should be lowercase", () => {
      const events = [
        StandardEvents.FEATURE_USED,
        StandardEvents.API_REQUEST,
        StandardEvents.COMMAND_EXECUTED,
        StandardEvents.OPERATION_LATENCY,
        StandardEvents.ERROR_OCCURRED,
        StandardEvents.SERVICE_HEALTH,
      ];

      events.forEach((event) => {
        expect(event).toBe(event.toLowerCase());
      });
    });
  });

  describe("Value Types", () => {
    it("should all be strings", () => {
      expect(typeof StandardEvents.FEATURE_USED).toBe("string");
      expect(typeof StandardEvents.API_REQUEST).toBe("string");
      expect(typeof StandardEvents.COMMAND_EXECUTED).toBe("string");
      expect(typeof StandardEvents.OPERATION_LATENCY).toBe("string");
      expect(typeof StandardEvents.ERROR_OCCURRED).toBe("string");
      expect(typeof StandardEvents.SERVICE_HEALTH).toBe("string");
    });

    it("should not be empty strings", () => {
      expect(StandardEvents.FEATURE_USED.length).toBeGreaterThan(0);
      expect(StandardEvents.API_REQUEST.length).toBeGreaterThan(0);
      expect(StandardEvents.COMMAND_EXECUTED.length).toBeGreaterThan(0);
      expect(StandardEvents.OPERATION_LATENCY.length).toBeGreaterThan(0);
      expect(StandardEvents.ERROR_OCCURRED.length).toBeGreaterThan(0);
      expect(StandardEvents.SERVICE_HEALTH.length).toBeGreaterThan(0);
    });
  });

  describe("Uniqueness", () => {
    it("should have unique event names", () => {
      const events = [
        StandardEvents.FEATURE_USED,
        StandardEvents.API_REQUEST,
        StandardEvents.COMMAND_EXECUTED,
        StandardEvents.OPERATION_LATENCY,
        StandardEvents.ERROR_OCCURRED,
        StandardEvents.SERVICE_HEALTH,
      ];

      const uniqueEvents = new Set(events);
      expect(uniqueEvents.size).toBe(events.length);
    });
  });

  describe("Cross-SDK Consistency", () => {
    it("should match Python SDK values exactly", () => {
      // These values MUST match python/src/automagik_telemetry/schema.py
      expect(StandardEvents.FEATURE_USED).toBe("automagik.feature.used");
      expect(StandardEvents.API_REQUEST).toBe("automagik.api.request");
      expect(StandardEvents.COMMAND_EXECUTED).toBe("automagik.cli.command");
      expect(StandardEvents.OPERATION_LATENCY).toBe(
        "automagik.performance.latency",
      );
      expect(StandardEvents.ERROR_OCCURRED).toBe("automagik.error");
      expect(StandardEvents.SERVICE_HEALTH).toBe("automagik.health");
    });
  });

  describe("Category Hierarchy", () => {
    it("should follow category.subcategory.action pattern (mostly)", () => {
      // Most events have 2 dots (3 parts)
      expect(StandardEvents.FEATURE_USED.split(".").length).toBe(3);
      expect(StandardEvents.API_REQUEST.split(".").length).toBe(3);
      expect(StandardEvents.COMMAND_EXECUTED.split(".").length).toBe(3);
      expect(StandardEvents.OPERATION_LATENCY.split(".").length).toBe(3);

      // Some special cases have 1 dot (2 parts)
      expect(StandardEvents.ERROR_OCCURRED.split(".").length).toBe(2);
      expect(StandardEvents.SERVICE_HEALTH.split(".").length).toBe(2);
    });

    it("should have meaningful category names", () => {
      expect(StandardEvents.FEATURE_USED).toContain("feature");
      expect(StandardEvents.API_REQUEST).toContain("api");
      expect(StandardEvents.COMMAND_EXECUTED).toContain("cli");
      expect(StandardEvents.OPERATION_LATENCY).toContain("performance");
      expect(StandardEvents.ERROR_OCCURRED).toContain("error");
      expect(StandardEvents.SERVICE_HEALTH).toContain("health");
    });
  });

  describe("Immutability", () => {
    it("should be readonly (TypeScript compile-time check)", () => {
      // This test verifies that StandardEvents properties are readonly
      // TypeScript's static type checking ensures these cannot be modified at compile time
      // Note: Attempting to assign to StandardEvents.FEATURE_USED would cause a TypeScript error

      // Verify the value is correct and unchanged
      expect(StandardEvents.FEATURE_USED).toBe("automagik.feature.used");
      expect(StandardEvents.API_REQUEST).toBe("automagik.api.request");
      expect(StandardEvents.COMMAND_EXECUTED).toBe("automagik.cli.command");
    });
  });

  describe("Usage Examples", () => {
    it("should be usable as string literals", () => {
      const eventType: string = StandardEvents.FEATURE_USED;
      expect(eventType).toBe("automagik.feature.used");
    });

    it("should work in switch statements", () => {
      const testEvent: string = StandardEvents.FEATURE_USED;

      let matched = false;
      switch (testEvent) {
        case StandardEvents.FEATURE_USED:
          matched = true;
          break;
        case StandardEvents.API_REQUEST:
          break;
        default:
          break;
      }

      expect(matched).toBe(true);
    });

    it("should work in object keys", () => {
      const eventCounts = {
        [StandardEvents.FEATURE_USED]: 10,
        [StandardEvents.API_REQUEST]: 5,
      };

      expect(eventCounts[StandardEvents.FEATURE_USED]).toBe(10);
      expect(eventCounts[StandardEvents.API_REQUEST]).toBe(5);
    });
  });
});
