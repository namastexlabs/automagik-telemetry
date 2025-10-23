/**
 * Unit tests for ClickHouse backend.
 *
 * Tests transformation, batching, compression, and error handling.
 */

import * as http from "http";
import * as https from "https";
import * as zlib from "zlib";
import { ClickHouseBackend } from "../clickhouse";

// Mock Node.js modules
jest.mock("http");
jest.mock("https");
jest.mock("zlib");

describe("ClickHouseBackend", () => {
  let backend: ClickHouseBackend;
  let mockRequest: jest.Mock;
  let mockRequestObject: any;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Create mock request object
    mockRequestObject = {
      write: jest.fn(),
      end: jest.fn(),
      on: jest.fn(),
      destroy: jest.fn(),
    };

    // Create mock request function
    mockRequest = jest.fn(() => mockRequestObject);

    // Mock http.request and https.request
    jest.spyOn(http, "request").mockImplementation(mockRequest as any);
    jest.spyOn(https, "request").mockImplementation(mockRequest as any);

    // Mock gzipSync
    jest.spyOn(zlib, "gzipSync").mockImplementation(
      ((data: any) => Buffer.from("gzipped-" + data.toString())) as any
    );

    // Initialize backend with default config
    backend = new ClickHouseBackend();
  });

  describe("constructor", () => {
    it("should initialize with default configuration", () => {
      const backend = new ClickHouseBackend();
      expect(backend).toBeDefined();
    });

    it("should accept custom configuration", () => {
      const config = {
        endpoint: "http://custom:8123",
        database: "custom_db",
        username: "custom_user",
        password: "custom_pass",
        timeout: 10000,
        batchSize: 50,
        compressionEnabled: false,
        maxRetries: 5,
      };

      const backend = new ClickHouseBackend(config);
      expect(backend).toBeDefined();
    });
  });

  describe("transformOTLPToClickHouse", () => {
    it("should transform trace_id and span_id correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        parentSpanId: "parent789",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        endTimeUnixNano: 1000000000100000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData).toHaveLength(1);
      expect(batchData[0].trace_id).toBe("abc123");
      expect(batchData[0].span_id).toBe("span456");
      expect(batchData[0].parent_span_id).toBe("parent789");
    });

    it("should handle missing IDs gracefully", () => {
      const otlpSpan = {
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].trace_id).toBe("");
      expect(batchData[0].span_id).toBe("");
      expect(batchData[0].parent_span_id).toBe("");
    });

    it("should convert timestamp from nanoseconds to ISO format", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1609459200000000000, // 2021-01-01 00:00:00 UTC
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].timestamp).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
      expect(batchData[0].timestamp_ns).toBe(1609459200000000000);
    });

    it("should use current time if startTimeUnixNano is missing", () => {
      const beforeTime = Date.now() * 1_000_000;

      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      const afterTime = Date.now() * 1_000_000;

      expect(batchData[0].timestamp_ns).toBeGreaterThanOrEqual(beforeTime);
      expect(batchData[0].timestamp_ns).toBeLessThanOrEqual(afterTime);
    });

    it("should calculate duration in milliseconds correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        endTimeUnixNano: 1000000000500000, // 0.5ms later
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].duration_ms).toBe(0); // Floors to 0
    });

    it("should calculate duration for longer spans", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        endTimeUnixNano: 1000000005000000, // 5ms later
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].duration_ms).toBe(5);
    });

    it("should handle missing endTimeUnixNano", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].duration_ms).toBe(0);
    });

    it("should flatten string attributes correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "http.method", value: { stringValue: "GET" } },
          { key: "http.url", value: { stringValue: "http://example.com" } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].attributes).toEqual({
        "http.method": "GET",
        "http.url": "http://example.com",
      });
    });

    it("should flatten integer attributes correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "http.status_code", value: { intValue: 200 } },
          { key: "retry.count", value: { intValue: 3 } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].attributes).toEqual({
        "http.status_code": "200",
        "retry.count": "3",
      });
    });

    it("should flatten double attributes correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "cpu.usage", value: { doubleValue: 45.67 } },
          { key: "memory.usage", value: { doubleValue: 89.12 } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].attributes).toEqual({
        "cpu.usage": "45.67",
        "memory.usage": "89.12",
      });
    });

    it("should flatten boolean attributes correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "is.cached", value: { boolValue: true } },
          { key: "is.error", value: { boolValue: false } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].attributes).toEqual({
        "is.cached": "true",
        "is.error": "false",
      });
    });

    it("should handle mixed attribute types", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "str_attr", value: { stringValue: "hello" } },
          { key: "int_attr", value: { intValue: 42 } },
          { key: "double_attr", value: { doubleValue: 3.14 } },
          { key: "bool_attr", value: { boolValue: true } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].attributes).toEqual({
        str_attr: "hello",
        int_attr: "42",
        double_attr: "3.14",
        bool_attr: "true",
      });
    });

    it("should extract resource attributes correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        resource: {
          attributes: [
            { key: "service.name", value: { stringValue: "my-service" } },
            { key: "project.name", value: { stringValue: "my-project" } },
            { key: "project.version", value: { stringValue: "1.0.0" } },
            {
              key: "deployment.environment",
              value: { stringValue: "staging" },
            },
            { key: "host.name", value: { stringValue: "server-01" } },
            { key: "os.type", value: { stringValue: "linux" } },
            { key: "os.version", value: { stringValue: "5.10" } },
            {
              key: "process.runtime.name",
              value: { stringValue: "node" },
            },
            {
              key: "process.runtime.version",
              value: { stringValue: "18.0.0" },
            },
          ],
        },
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].service_name).toBe("my-service");
      expect(batchData[0].project_name).toBe("my-project");
      expect(batchData[0].project_version).toBe("1.0.0");
      expect(batchData[0].environment).toBe("staging");
      expect(batchData[0].hostname).toBe("server-01");
      expect(batchData[0].os_type).toBe("linux");
      expect(batchData[0].os_version).toBe("5.10");
      expect(batchData[0].runtime_name).toBe("node");
      expect(batchData[0].runtime_version).toBe("18.0.0");
    });

    it("should use default values for missing resource attributes", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].service_name).toBe("unknown");
      expect(batchData[0].project_name).toBe("");
      expect(batchData[0].project_version).toBe("");
      expect(batchData[0].environment).toBe("production");
      expect(batchData[0].hostname).toBe("");
      expect(batchData[0].os_type).toBe("");
      expect(batchData[0].os_version).toBe("");
      expect(batchData[0].runtime_name).toBe("");
      expect(batchData[0].runtime_version).toBe("");
    });

    it("should map status code OK correctly", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        status: {
          code: 1, // OK status
          message: "",
        },
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].status_code).toBe("OK");
      expect(batchData[0].status_message).toBe("");
    });

    it("should map status code ERROR with message", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        status: {
          code: 2, // ERROR status
          message: "Internal error",
        },
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].status_code).toBe("Internal error");
      expect(batchData[0].status_message).toBe("Internal error");
    });

    it("should handle missing status gracefully", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].status_code).toBe("OK");
      expect(batchData[0].status_message).toBe("");
    });

    it("should extract user_id from attributes", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [{ key: "user.id", value: { stringValue: "user-123" } }],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].user_id).toBe("user-123");
    });

    it("should extract session_id from attributes", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
        attributes: [
          { key: "session.id", value: { stringValue: "session-xyz" } },
        ],
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData[0].session_id).toBe("session-xyz");
    });
  });

  describe("batch processing", () => {
    it("should add spans to batch", () => {
      const otlpSpan = {
        traceId: "abc123",
        spanId: "span456",
        name: "test-span",
        startTimeUnixNano: 1000000000000000,
      };

      backend.addToBatch(otlpSpan);
      const batchData = (backend as any).batch;

      expect(batchData).toHaveLength(1);
    });

    it("should accumulate multiple spans", () => {
      for (let i = 0; i < 5; i++) {
        backend.addToBatch({
          traceId: `trace-${i}`,
          spanId: `span-${i}`,
          name: `span-${i}`,
          startTimeUnixNano: 1000000000000000,
        });
      }

      const batchData = (backend as any).batch;
      expect(batchData).toHaveLength(5);
    });

    it("should auto-flush when batch size is reached", () => {
      // Create backend with small batch size
      backend = new ClickHouseBackend({ batchSize: 3 });

      // Mock successful HTTP response
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") return mockRequestObject;
        if (event === "timeout") return mockRequestObject;
        return mockRequestObject;
      });

      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              // No data
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      // Add 2 spans - should not flush yet
      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });
      backend.addToBatch({
        traceId: "trace-2",
        spanId: "span-2",
        name: "span-2",
        startTimeUnixNano: 1000000000000000,
      });

      expect((backend as any).batch).toHaveLength(2);

      // Add 3rd span - should trigger flush
      backend.addToBatch({
        traceId: "trace-3",
        spanId: "span-3",
        name: "span-3",
        startTimeUnixNano: 1000000000000000,
      });

      // Batch should be cleared after flush
      expect((backend as any).batch).toHaveLength(0);
      expect(mockRequest).toHaveBeenCalled();
    });

    it("should handle manual flush", async () => {
      // Mock successful HTTP response
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") return mockRequestObject;
        if (event === "timeout") return mockRequestObject;
        return mockRequestObject;
      });

      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              // No data
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      expect((backend as any).batch).toHaveLength(1);

      const result = await backend.flush();

      expect(result).toBe(true);
      expect((backend as any).batch).toHaveLength(0);
      expect(mockRequest).toHaveBeenCalled();
    });

    it("should return true for empty batch flush", async () => {
      const result = await backend.flush();
      expect(result).toBe(true);
      expect(mockRequest).not.toHaveBeenCalled();
    });

    it("should preserve batch on failed flush", async () => {
      // Mock failed HTTP response
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") {
          callback(new Error("Network error"));
        }
        return mockRequestObject;
      });

      mockRequest.mockReturnValue(mockRequestObject);

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(false);
      // Batch is cleared before flush attempt
      expect((backend as any).batch).toHaveLength(0);
    });
  });

  describe("compression", () => {
    beforeEach(() => {
      // Mock successful HTTP response
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") return mockRequestObject;
        if (event === "timeout") return mockRequestObject;
        return mockRequestObject;
      });

      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              // No data
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });
    });

    it("should use gzip compression for large payloads", async () => {
      // Create spans that will produce >1024 bytes
      for (let i = 0; i < 10; i++) {
        backend.addToBatch({
          traceId: `trace-${i}`,
          spanId: `span-${i}`,
          name: `span-name-${i}`,
          startTimeUnixNano: 1000000000000000,
          attributes: [
            {
              key: "long.attribute",
              value: {
                stringValue:
                  "This is a very long attribute value to exceed the compression threshold",
              },
            },
          ],
        });
      }

      await backend.flush();

      expect(zlib.gzipSync).toHaveBeenCalled();

      // Check that Content-Encoding header was set
      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];
      expect(options.headers["Content-Encoding"]).toBe("gzip");
    });

    it("should not compress small payloads", async () => {
      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      expect(zlib.gzipSync).not.toHaveBeenCalled();

      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];
      expect(options.headers["Content-Encoding"]).toBeUndefined();
    });

    it("should respect compressionEnabled=false", async () => {
      backend = new ClickHouseBackend({ compressionEnabled: false });

      // Mock response for new backend
      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              // No data
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      // Create large payload
      for (let i = 0; i < 50; i++) {
        backend.addToBatch({
          traceId: `trace-${i}`,
          spanId: `span-${i}`,
          name: `span-name-${i}`,
          startTimeUnixNano: 1000000000000000,
          attributes: [
            {
              key: "long.attribute",
              value: {
                stringValue:
                  "This is a very long attribute value to exceed the compression threshold",
              },
            },
          ],
        });
      }

      await backend.flush();

      expect(zlib.gzipSync).not.toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should handle HTTP errors", async () => {
      // Mock error response
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") {
          callback(new Error("Connection refused"));
        }
        return mockRequestObject;
      });

      mockRequest.mockReturnValue(mockRequestObject);

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(false);
    });

    it("should handle non-200 status codes", async () => {
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") return mockRequestObject;
        if (event === "timeout") return mockRequestObject;
        return mockRequestObject;
      });

      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 500,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              cb("Internal Server Error");
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(false);
    });

    it("should retry on failure with exponential backoff", async () => {
      backend = new ClickHouseBackend({ maxRetries: 3 });

      let attemptCount = 0;

      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") {
          callback(new Error("Network error"));
        }
        return mockRequestObject;
      });

      mockRequest.mockImplementation(() => {
        attemptCount++;
        return mockRequestObject;
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(false);
      expect(attemptCount).toBe(3); // Should have tried 3 times
    });

    it("should succeed on retry after initial failure", async () => {
      backend = new ClickHouseBackend({ maxRetries: 3 });

      let attemptCount = 0;

      mockRequest.mockImplementation((options: any, callback: any) => {
        attemptCount++;

        if (attemptCount === 1) {
          // First attempt fails
          mockRequestObject.on.mockImplementation(
            (event: string, cb: any) => {
              if (event === "error") {
                cb(new Error("Network error"));
              }
              return mockRequestObject;
            }
          );
          return mockRequestObject;
        } else {
          // Second attempt succeeds
          const mockResponse: any = {
            statusCode: 200,
            on: jest.fn((event: string, cb: any): any => {
              if (event === "data") {
                // No data
              } else if (event === "end") {
                cb();
              }
              return mockResponse;
            }),
          };
          callback(mockResponse);
          return mockRequestObject;
        }
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(true);
      expect(attemptCount).toBe(2); // First failed, second succeeded
    });

    it("should handle timeout errors", async () => {
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "timeout") {
          callback();
        }
        return mockRequestObject;
      });

      mockRequest.mockReturnValue(mockRequestObject);

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      const result = await backend.flush();

      expect(result).toBe(false);
      expect(mockRequestObject.destroy).toHaveBeenCalled();
    });

    it("should handle sendTrace errors gracefully", () => {
      // Mock addToBatch to throw an error
      jest.spyOn(backend as any, "addToBatch").mockImplementation(() => {
        throw new Error("Transformation error");
      });

      const result = backend.sendTrace({ some: "data" });

      // Should not throw, but return false
      expect(result).toBe(false);
    });
  });

  describe("HTTP request construction", () => {
    beforeEach(() => {
      mockRequestObject.on.mockImplementation((event: string, callback: any) => {
        if (event === "error") return mockRequestObject;
        if (event === "timeout") return mockRequestObject;
        return mockRequestObject;
      });

      mockRequest.mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, cb: any): any => {
            if (event === "data") {
              // No data
            } else if (event === "end") {
              cb();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });
    });

    it("should construct correct HTTP request URL", async () => {
      backend = new ClickHouseBackend({
        endpoint: "http://localhost:8123",
        database: "test_db",
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];

      expect(options.hostname).toBe("localhost");
      expect(options.port).toBe("8123");
      expect(options.path).toContain(
        "query=INSERT+INTO+test_db.test_table+FORMAT+JSONEachRow"
      );
    });

    it("should include authentication headers", async () => {
      backend = new ClickHouseBackend({
        username: "testuser",
        password: "testpass",
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];

      expect(options.headers.Authorization).toBeDefined();
      expect(options.headers.Authorization).toMatch(/^Basic /);
    });

    it("should use HTTPS for https endpoints", async () => {
      backend = new ClickHouseBackend({
        endpoint: "https://secure.clickhouse.com:8443",
      });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      expect(https.request).toHaveBeenCalled();
      expect(http.request).not.toHaveBeenCalled();
    });

    it("should set correct Content-Type header", async () => {
      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];

      expect(options.headers["Content-Type"]).toBe("application/x-ndjson");
    });

    it("should set timeout from config", async () => {
      backend = new ClickHouseBackend({ timeout: 10000 });

      backend.addToBatch({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      await backend.flush();

      const requestCall = mockRequest.mock.calls[0];
      const options = requestCall[0];

      expect(options.timeout).toBe(10000);
    });
  });

  describe("sendTrace convenience method", () => {
    it("should add span to batch and return true", () => {
      const result = backend.sendTrace({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      expect(result).toBe(true);
      expect((backend as any).batch).toHaveLength(1);
    });

    it("should handle multiple sendTrace calls", () => {
      backend.sendTrace({
        traceId: "trace-1",
        spanId: "span-1",
        name: "span-1",
        startTimeUnixNano: 1000000000000000,
      });

      backend.sendTrace({
        traceId: "trace-2",
        spanId: "span-2",
        name: "span-2",
        startTimeUnixNano: 1000000000000000,
      });

      expect((backend as any).batch).toHaveLength(2);
    });
  });
});
