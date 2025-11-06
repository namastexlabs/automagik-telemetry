/**
 * Tests for ClickHouse backend error handling and verbose logging paths.
 *
 * This test suite covers the uncovered error logging branches in clickhouse.ts:
 * - Auto-flush error logging (lines 635, 1095, 1242)
 * - Verbose success logging (line 770)
 * - Verbose retry logging (line 780)
 * - Verbose failure logging (line 798)
 * - Verbose HTTP error logging (line 883)
 * - Verbose batch error logging (lines 944, 1102, 1249)
 * - Verbose metric type warning (line 982)
 */

import * as http from 'http';
import * as https from 'https';
import { ClickHouseBackend } from '../src/backends/clickhouse';

// Mock Node.js modules
jest.mock('http');
jest.mock('https');

describe('ClickHouse Backend Error Handling', () => {
  let consoleSpy: jest.SpyInstance;
  let consoleDebugSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    consoleDebugSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  describe('Auto-flush error logging', () => {
    it('should log auto-flush trace errors (line 635)', async () => {
      // Create backend with small batch size
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        batchSize: 2, // Small batch to trigger auto-flush
        verbose: true,
      });

      // Mock the flush method to return a rejected Promise
      const flushError = new Error('Flush failed');
      jest.spyOn(backend, 'flush').mockRejectedValue(flushError);

      // Add spans to trigger auto-flush
      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
        attributes: [],
      };

      backend.sendTrace(mockSpan);
      backend.sendTrace(mockSpan); // This triggers auto-flush

      // Wait for async catch handler to execute
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify auto-flush error was logged (line 635)
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ClickHouse] Auto-flush traces failed:',
        flushError
      );
    });

    it('should log auto-flush metric errors (line 1095)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        batchSize: 2,
        verbose: true,
      });

      // Mock the flush method to return a rejected Promise
      const flushError = new Error('Flush failed');
      jest.spyOn(backend, 'flush').mockRejectedValue(flushError);

      // Add metrics to trigger auto-flush
      backend.sendMetric('test.metric', 1, 'GAUGE', 'count', {}, {});
      backend.sendMetric('test.metric', 2, 'GAUGE', 'count', {}, {});

      // Wait for async catch handler to execute
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify auto-flush error was logged (line 1095)
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ClickHouse] Auto-flush metrics failed:',
        flushError
      );
    });

    it('should log auto-flush log errors (line 1242)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        batchSize: 2,
        verbose: true,
      });

      // Mock the flush method to return a rejected Promise
      const flushError = new Error('Flush failed');
      jest.spyOn(backend, 'flush').mockRejectedValue(flushError);

      // Add logs to trigger auto-flush
      backend.sendLog('Test message 1', 'INFO', {}, {});
      backend.sendLog('Test message 2', 'INFO', {}, {});

      // Wait for async catch handler to execute
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify auto-flush error was logged (line 1242)
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ClickHouse] Auto-flush logs failed:',
        flushError
      );
    });
  });

  describe('Verbose success logging', () => {
    it('should log successful inserts (line 770)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        verbose: true,
        batchSize: 100,
      });

      // Mock successful HTTP response
      const mockRequestObject: any = {
        write: jest.fn(),
        end: jest.fn(),
        on: jest.fn().mockReturnThis(),
        destroy: jest.fn(),
      };

      jest.spyOn(http, 'request').mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 200,
          on: jest.fn((event: string, handler: any) => {
            if (event === 'data') {
              handler(Buffer.from('OK'));
            } else if (event === 'end') {
              handler();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
      };

      backend.sendTrace(mockSpan);
      await backend.flush();

      // Verify success was logged (line 770)
      expect(consoleDebugSpy).toHaveBeenCalledWith(
        expect.stringMatching(/Inserted \d+ rows to ClickHouse table traces successfully/)
      );
    });
  });

  describe('Verbose retry and failure logging', () => {
    it('should log retry attempts (line 780)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        verbose: true,
        batchSize: 100,
        maxRetries: 3,
      });

      const mockRequestObject: any = {
        write: jest.fn(),
        end: jest.fn(),
        on: jest.fn((event: string, handler: any) => {
          if (event === 'error') {
            setTimeout(() => handler(new Error('Connection refused')), 10);
          }
          return mockRequestObject;
        }),
        destroy: jest.fn(),
      };

      jest.spyOn(http, 'request').mockImplementation(() => mockRequestObject);

      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
      };

      backend.sendTrace(mockSpan);
      await backend.flush();

      // Wait for retries to complete
      await new Promise(resolve => setTimeout(resolve, 500));

      // Verify retry logging (line 780)
      expect(consoleDebugSpy).toHaveBeenCalledWith(
        expect.stringMatching(/Error inserting to ClickHouse \(attempt \d+\/\d+\)/)
      );
    });

    it('should log final failure after retries (line 798)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        verbose: true,
        maxRetries: 2,
      });

      const mockRequestObject: any = {
        write: jest.fn(),
        end: jest.fn(),
        on: jest.fn((event: string, handler: any) => {
          if (event === 'error') {
            setTimeout(() => handler(new Error('Persistent failure')), 10);
          }
          return mockRequestObject;
        }),
        destroy: jest.fn(),
      };

      jest.spyOn(http, 'request').mockImplementation(() => mockRequestObject);

      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
      };

      backend.sendTrace(mockSpan);
      await backend.flush();

      await new Promise(resolve => setTimeout(resolve, 500));

      // Verify final failure logging (line 798)
      expect(consoleDebugSpy).toHaveBeenCalledWith(
        expect.stringMatching(/Failed to insert to ClickHouse after \d+ retries/)
      );
    });
  });

  describe('Verbose HTTP error logging', () => {
    it('should log HTTP error responses (line 883)', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        verbose: true,
      });

      const mockRequestObject: any = {
        write: jest.fn(),
        end: jest.fn(),
        on: jest.fn().mockReturnThis(),
        destroy: jest.fn(),
      };

      jest.spyOn(http, 'request').mockImplementation((options: any, callback: any) => {
        const mockResponse: any = {
          statusCode: 500,
          on: jest.fn((event: string, handler: any) => {
            if (event === 'data') {
              handler(Buffer.from('Internal Server Error'));
            } else if (event === 'end') {
              handler();
            }
            return mockResponse;
          }),
        };
        callback(mockResponse);
        return mockRequestObject;
      });

      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
      };

      backend.sendTrace(mockSpan);
      await backend.flush();

      // Verify HTTP error was logged (line 883)
      expect(consoleDebugSpy).toHaveBeenCalledWith(
        expect.stringMatching(/ClickHouse returned status \d+/)
      );
    });
  });

  describe('Verbose batch error logging', () => {
    it('should log trace batch errors (line 944)', () => {
      const backend = new ClickHouseBackend({
        verbose: true,
      });

      // sendTrace with null will cause an error
      const result = backend.sendTrace(null as any);

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error adding span to batch:',
        expect.any(Error)
      );
    });

    it('should log metric batch errors (line 1102)', () => {
      const backend = new ClickHouseBackend({
        verbose: true,
      });

      // Mock extractExtendedResourceAttributes to throw an error
      jest.spyOn(backend as any, 'extractExtendedResourceAttributes').mockImplementation(() => {
        throw new Error('Test error');
      });

      const result = backend.sendMetric('test', 42, 'GAUGE', '', {}, {});

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error adding metric to batch:',
        expect.any(Error)
      );
    });

    it('should log log batch errors (line 1249)', () => {
      const backend = new ClickHouseBackend({
        verbose: true,
      });

      // Mock extractExtendedResourceAttributes to throw an error
      jest.spyOn(backend as any, 'extractExtendedResourceAttributes').mockImplementation(() => {
        throw new Error('Test error');
      });

      const result = backend.sendLog('test message', 'INFO', {}, {});

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error adding log to batch:',
        expect.any(Error)
      );
    });

    it('should log warning for invalid metric type (line 982)', () => {
      const backend = new ClickHouseBackend({
        verbose: true,
        batchSize: 100,
      });

      // Send metric with invalid type
      backend.sendMetric('test.metric', 42, 'INVALID_TYPE' as any, 'count', {}, {});

      // Should log warning (line 982)
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid metric type: INVALID_TYPE')
      );
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Using GAUGE as fallback')
      );
    });
  });

  describe('Non-verbose mode', () => {
    it('should not log errors when verbose is disabled', async () => {
      const backend = new ClickHouseBackend({
        endpoint: 'http://localhost:8123',
        batchSize: 2,
        verbose: false,
        maxRetries: 1,
      });

      const mockRequestObject: any = {
        write: jest.fn(),
        end: jest.fn(),
        on: jest.fn((event: string, handler: any) => {
          if (event === 'error') {
            setTimeout(() => handler(new Error('Network error')), 10);
          }
          return mockRequestObject;
        }),
        destroy: jest.fn(),
      };

      jest.spyOn(http, 'request').mockImplementation(() => mockRequestObject);

      const mockSpan = {
        traceId: '123',
        spanId: '456',
        name: 'test-span',
        startTimeUnixNano: 1000000000,
        endTimeUnixNano: 2000000000,
      };

      backend.sendTrace(mockSpan);
      backend.sendTrace(mockSpan);

      await new Promise(resolve => setTimeout(resolve, 200));

      // Errors should not be logged when verbose is false
      expect(consoleSpy).not.toHaveBeenCalled();
      expect(consoleDebugSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });
  });
});
