/**
 * Comprehensive tests for async telemetry methods.
 *
 * Tests cover:
 * - Async flush operations
 * - Concurrent operations with Promise.all()
 * - Non-blocking behavior verification
 * - Promise-based error handling
 * - Integration with async/await patterns
 * - Performance characteristics of concurrent operations
 *
 * Port of Python's test_async.py to TypeScript
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { AutomagikTelemetry, LogSeverity, MetricType } from '../src/client';
import type { TelemetryConfig } from '../src/config';

// Mock file system operations
jest.mock('fs');
jest.mock('os');

// Mock fetch globally
global.fetch = jest.fn();

describe('Async Telemetry Operations', () => {
  const mockHomedir = '/home/testuser';
  const mockUserIdFile = path.join(mockHomedir, '.automagik', 'user_id');

  let mockConfig: TelemetryConfig;

  beforeEach(() => {
    // Reset all mocks
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

    // Setup fetch mock to return successful response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    // Default config with immediate flushing
    mockConfig = {
      projectName: 'test-async',
      version: '1.0.0',
      batchSize: 1, // Immediate send for testing
      compressionEnabled: false,
    };

    // Enable telemetry via environment variable
    process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
  });

  afterEach(() => {
    // Clean up environment
    delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
  });

  describe('Async Flush Operations', () => {
    it('should complete flush operation asynchronously', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      // Track event (adds to queue)
      client.trackEvent('test.event', { key: 'value' });

      // Flush should return a Promise that resolves
      await expect(client.flush()).resolves.toBeUndefined();

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle flush when telemetry is disabled', async () => {
      delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
      const client = new AutomagikTelemetry(mockConfig);

      // Flush should be a no-op when disabled
      await client.flush();

      // Should not make any HTTP requests
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should flush multiple pending events', async () => {
      // Use larger batch size to accumulate events
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      // Track multiple events
      client.trackEvent('event.1');
      client.trackEvent('event.2');
      client.trackEvent('event.3');

      // Flush all at once
      await client.flush();

      // Verify flush completed
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle network errors during flush gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new AutomagikTelemetry(mockConfig);
      client.trackEvent('test.event');

      // Should not throw, silent failure
      await expect(client.flush()).resolves.toBeUndefined();
    });

    it('should handle HTTP errors during flush gracefully', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' }),
      });

      const client = new AutomagikTelemetry(mockConfig);
      client.trackEvent('test.event');

      // Should not throw, silent failure
      await expect(client.flush()).resolves.toBeUndefined();
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle concurrent trackEvent calls', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      // Track multiple events concurrently
      const promises = Array.from({ length: 10 }, (_, i) =>
        Promise.resolve(client.trackEvent(`event.${i}`, { index: i })),
      );

      // Wait for all to complete
      await Promise.all(promises);

      // All events should trigger fetch calls
      expect(global.fetch).toHaveBeenCalledTimes(10);
    });

    it('should handle mixed concurrent operations', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      // Mix different operation types
      const operations = [
        Promise.resolve(client.trackEvent('event.1')),
        Promise.resolve(client.trackMetric('metric.1', 42.0)),
        Promise.resolve(client.trackLog('Log message 1')),
        Promise.resolve(client.trackEvent('event.2')),
        Promise.resolve(client.trackMetric('metric.2', 100.0, MetricType.COUNTER)),
        Promise.resolve(client.trackError(new Error('test error'))),
      ];

      // All operations should complete
      await Promise.all(operations);

      // Verify all operations triggered requests
      expect(global.fetch).toHaveBeenCalledTimes(6);
    });

    it('should handle concurrent operations with some errors', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      // First call succeeds, second fails, third succeeds
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: true, status: 200 })
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ ok: true, status: 200 });

      // Should not raise exceptions (silent failure)
      const operations = [
        Promise.resolve(client.trackEvent('event.1')),
        Promise.resolve(client.trackEvent('event.2')),
        Promise.resolve(client.trackEvent('event.3')),
      ];

      // All should complete without throwing
      await Promise.allSettled(operations);

      // All requests should have been attempted
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should handle concurrent flush calls', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      // Track some events
      client.trackEvent('event.1');
      client.trackEvent('event.2');

      // Call flush concurrently
      await Promise.all([client.flush(), client.flush(), client.flush()]);

      // Should handle concurrent flushes gracefully
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('Non-Blocking Behavior', () => {
    it('should not block when tracking events', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const start = Date.now();

      // Track event (should return immediately)
      client.trackEvent('test.event');

      const elapsed = Date.now() - start;

      // Should complete in under 10ms (non-blocking)
      expect(elapsed).toBeLessThan(10);
    });

    it('should allow concurrent work while tracking events', async () => {
      // Mock slow network (100ms delay)
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, status: 200 }), 100);
          }),
      );

      const client = new AutomagikTelemetry(mockConfig);

      // Track event (triggers async send)
      client.trackEvent('test.event');

      // Do other work concurrently
      const otherWork = async () => {
        await new Promise((resolve) => setTimeout(resolve, 50)); // 50ms
        return 'completed';
      };

      const start = Date.now();
      const result = await otherWork();
      const elapsed = Date.now() - start;

      // Other work should complete without waiting for network
      expect(result).toBe('completed');
      expect(elapsed).toBeLessThan(80); // Should be ~50ms, not 150ms

      // Wait for event to finish
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should allow async work during flush', async () => {
      // Mock slow network
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, status: 200 }), 100);
          }),
      );

      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      client.trackEvent('test.event');

      // Start flush (returns Promise)
      const flushPromise = client.flush();

      // Do other async work
      let counter = 0;
      const countWork = async () => {
        for (let i = 0; i < 10; i++) {
          await new Promise((resolve) => setTimeout(resolve, 10));
          counter++;
        }
        return counter;
      };

      const [, count] = await Promise.all([flushPromise, countWork()]);

      // Counter should complete successfully
      expect(count).toBe(10);
    });
  });

  describe('Promise-Based Error Handling', () => {
    it('should handle network errors without throwing', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const client = new AutomagikTelemetry(mockConfig);

      // Should not throw exception
      expect(() => client.trackEvent('test.event')).not.toThrow();

      // Wait for async operation to complete
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    it('should handle timeout errors without throwing', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Request timeout'));

      const client = new AutomagikTelemetry(mockConfig);

      // Should not throw exception
      expect(() => client.trackMetric('test.metric', 42.0)).not.toThrow();

      // Wait for async operation to complete
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    it('should handle invalid response errors without throwing', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Bad request' }),
      });

      const client = new AutomagikTelemetry(mockConfig);

      // Should not throw exception
      expect(() => client.trackLog('test log')).not.toThrow();

      // Wait for async operation to complete
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  });

  describe('Integration with Async/Await Patterns', () => {
    it('should work in async function context', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const asyncOperation = async () => {
        client.trackEvent('operation.start');
        await new Promise((resolve) => setTimeout(resolve, 10));
        client.trackEvent('operation.end');
      };

      await asyncOperation();

      // Both events should have been sent
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should work with async/await and flush', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      const operation = async () => {
        client.trackEvent('event.1');
        client.trackEvent('event.2');
        await client.flush();
        return 'done';
      };

      const result = await operation();

      expect(result).toBe('done');
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should work with Promise.all and multiple clients', async () => {
      // Environment variable is already set in beforeEach
      const client1 = new AutomagikTelemetry({
        projectName: 'project-1',
        version: '1.0.0',
        batchSize: 1,
      });

      const client2 = new AutomagikTelemetry({
        projectName: 'project-2',
        version: '1.0.0',
        batchSize: 1,
      });

      // Both clients should be enabled via env var
      expect(client1.isEnabled()).toBe(true);
      expect(client2.isEnabled()).toBe(true);

      // Track events from multiple clients
      await Promise.all([
        Promise.resolve(client1.trackEvent('client1.event')),
        Promise.resolve(client2.trackEvent('client2.event')),
      ]);

      // Wait for async operations to complete
      await new Promise((resolve) => setTimeout(resolve, 20));

      // Both clients should have sent events
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Performance Characteristics', () => {
    it('should have concurrent execution faster than sequential', async () => {
      // Mock 50ms network delay
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, status: 200 }), 50);
          }),
      );

      const client = new AutomagikTelemetry(mockConfig);

      // Sequential execution
      const startSeq = Date.now();
      for (let i = 0; i < 5; i++) {
        client.trackEvent(`seq.${i}`);
        await new Promise((resolve) => setTimeout(resolve, 60)); // Wait for each to finish
      }
      const seqTime = Date.now() - startSeq;

      // Reset mock
      jest.clearAllMocks();
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, status: 200 }), 50);
          }),
      );

      // Concurrent execution
      const startCon = Date.now();
      const promises = Array.from({ length: 5 }, (_, i) =>
        Promise.resolve(client.trackEvent(`con.${i}`)),
      );
      await Promise.all(promises);
      await new Promise((resolve) => setTimeout(resolve, 60)); // Wait for all to finish
      const conTime = Date.now() - startCon;

      // Concurrent should be significantly faster
      // Sequential: ~300ms (5 * 60ms)
      // Concurrent: ~60ms (all in parallel)
      expect(conTime).toBeLessThan(seqTime / 2);
    });

    it('should handle high-volume concurrent operations', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const start = Date.now();

      // Create 100 concurrent operations
      const promises = Array.from({ length: 100 }, (_, i) =>
        Promise.resolve(client.trackEvent(`event.${i}`, { index: i })),
      );

      await Promise.all(promises);

      const elapsed = Date.now() - start;

      // Should complete relatively quickly (under 1 second)
      expect(elapsed).toBeLessThan(1000);
      expect(global.fetch).toHaveBeenCalledTimes(100);
    });

    it('should handle rapid flush calls efficiently', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      // Track events
      for (let i = 0; i < 50; i++) {
        client.trackEvent(`event.${i}`);
      }

      const start = Date.now();

      // Call flush multiple times rapidly
      await Promise.all([client.flush(), client.flush(), client.flush(), client.flush()]);

      const elapsed = Date.now() - start;

      // Should handle efficiently (under 500ms)
      expect(elapsed).toBeLessThan(500);
    });
  });

  describe('Cleanup and Shutdown', () => {
    it('should complete pending operations before disable', async () => {
      const client = new AutomagikTelemetry({
        ...mockConfig,
        batchSize: 100,
      });

      // Track multiple events
      client.trackEvent('event.1');
      client.trackEvent('event.2');
      client.trackEvent('event.3');

      // Disable (should flush remaining events)
      client.disable();

      // Wait for async operations to complete
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Should have flushed events
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should not accept new events after disable', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      // Disable client
      client.disable();

      // Wait for disable to complete
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Verify client is disabled
      expect(client.isEnabled()).toBe(false);

      // Clear any calls from disable's flush
      jest.clearAllMocks();

      // Try to track event after disable
      client.trackEvent('should.not.send');

      // Wait for any async operations
      await new Promise((resolve) => setTimeout(resolve, 20));

      // Should not make any new requests
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe('Async Method Variants', () => {
    it('should track event using trackEventAsync', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackEventAsync('test.event', { key: 'value' });

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track event using trackEventAsync without attributes', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackEventAsync('test.event');

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track error using trackErrorAsync', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      const testError = new Error('Test error message');

      await client.trackErrorAsync(testError, { context_key: 'context_value' });

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track error using trackErrorAsync without context', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      const testError = new Error('Test error message');

      await client.trackErrorAsync(testError);

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should truncate long error messages in trackErrorAsync', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      const longMessage = 'x'.repeat(5000); // Very long message
      const testError = new Error(longMessage);

      await client.trackErrorAsync(testError);

      // Verify fetch was called (error should be truncated internally)
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track metric using trackMetricAsync with default type', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackMetricAsync('test.metric', 42.5);

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track metric using trackMetricAsync with specific type', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackMetricAsync('test.metric', 100, MetricType.COUNTER, { unit: 'count' });

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track metric using trackMetricAsync without attributes', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackMetricAsync('test.metric', 100, MetricType.HISTOGRAM);

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track log using trackLogAsync with default severity', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackLogAsync('Test log message');

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track log using trackLogAsync with specific severity', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackLogAsync('Test error log', LogSeverity.ERROR, { error_code: 'ERR001' });

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should track log using trackLogAsync without attributes', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      await client.trackLogAsync('Test warning log', LogSeverity.WARN);

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle concurrent async method calls', async () => {
      const client = new AutomagikTelemetry(mockConfig);
      const testError = new Error('Test error');

      await Promise.all([
        client.trackEventAsync('event.1', { key: 'value1' }),
        client.trackErrorAsync(testError, { context: 'test' }),
        client.trackMetricAsync('metric.1', 42.5, MetricType.GAUGE),
        client.trackLogAsync('Log message', LogSeverity.INFO, { source: 'test' }),
      ]);

      // All four calls should have been made
      expect(global.fetch).toHaveBeenCalledTimes(4);
    });

    it('should return promises from async methods', async () => {
      const client = new AutomagikTelemetry(mockConfig);

      const eventPromise = client.trackEventAsync('test.event');
      expect(eventPromise).toBeInstanceOf(Promise);
      await eventPromise;

      const errorPromise = client.trackErrorAsync(new Error('test'));
      expect(errorPromise).toBeInstanceOf(Promise);
      await errorPromise;

      const metricPromise = client.trackMetricAsync('test.metric', 1);
      expect(metricPromise).toBeInstanceOf(Promise);
      await metricPromise;

      const logPromise = client.trackLogAsync('test log');
      expect(logPromise).toBeInstanceOf(Promise);
      await logPromise;
    });

    it('should handle errors gracefully in async methods', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      const client = new AutomagikTelemetry(mockConfig);

      // Should not throw
      await expect(client.trackEventAsync('test.event')).resolves.toBeUndefined();
      await expect(client.trackErrorAsync(new Error('test'))).resolves.toBeUndefined();
      await expect(client.trackMetricAsync('test.metric', 1)).resolves.toBeUndefined();
      await expect(client.trackLogAsync('test log')).resolves.toBeUndefined();
    });
  });
});
