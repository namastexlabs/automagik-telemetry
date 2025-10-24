/**
 * Test for backends index exports.
 */

import { ClickHouseBackend } from "../index";

describe("Backends Index", () => {
  it("should export ClickHouseBackend", () => {
    expect(ClickHouseBackend).toBeDefined();
    expect(typeof ClickHouseBackend).toBe("function");
  });

  it("should be able to instantiate ClickHouseBackend from index", () => {
    const backend = new ClickHouseBackend();
    expect(backend).toBeDefined();
  });
});
