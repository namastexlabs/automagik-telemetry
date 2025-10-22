/**
 * Comprehensive tests for TelemetryOptIn.
 *
 * Tests cover:
 * - Opt-in prompt flow
 * - Preference storage and retrieval
 * - hasUserDecided() logic
 * - getUserPreference() behavior
 * - savePreference() functionality
 * - CI environment detection
 * - Color support detection
 * - Interactive environment detection
 */

// Mock modules BEFORE importing the module under test
jest.mock('fs');
jest.mock('os', () => ({
  homedir: jest.fn(() => '/home/testuser'),
}));
jest.mock('readline');

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as readline from 'readline';
import { TelemetryOptIn, shouldPromptUser, promptUserIfNeeded } from '../src/opt-in';

describe('TelemetryOptIn', () => {
  const mockHomedir = '/home/testuser';
  const mockPreferenceFile = path.join(mockHomedir, '.automagik', 'telemetry_preference');
  const mockOptOutFile = path.join(mockHomedir, '.automagik-no-telemetry');

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock os.homedir
    (os.homedir as jest.Mock).mockReturnValue(mockHomedir);

    // Mock fs methods
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    (fs.readFileSync as jest.Mock).mockReturnValue('');
    (fs.writeFileSync as jest.Mock).mockReturnValue(undefined);
    (fs.mkdirSync as jest.Mock).mockReturnValue(undefined);
    (fs.unlinkSync as jest.Mock).mockReturnValue(undefined);
    (fs.openSync as jest.Mock).mockReturnValue(3);
    (fs.closeSync as jest.Mock).mockReturnValue(undefined);

    // Mock process.stdin/stdout as TTY by default
    Object.defineProperty(process.stdin, 'isTTY', {
      value: true,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(process.stdout, 'isTTY', {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('hasUserDecided', () => {
    it('should return false when no preference exists', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      expect(TelemetryOptIn.hasUserDecided()).toBe(false);
    });

    it('should return true when preference file exists', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      expect(TelemetryOptIn.hasUserDecided()).toBe(true);
    });

    it('should return true when opt-out file exists', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockOptOutFile;
      });
      expect(TelemetryOptIn.hasUserDecided()).toBe(true);
    });

    it('should return true when environment variable is set', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      expect(TelemetryOptIn.hasUserDecided()).toBe(true);
    });

    it('should return true when environment variable is set to false', () => {
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'false';
      expect(TelemetryOptIn.hasUserDecided()).toBe(true);
    });
  });

  describe('getUserPreference', () => {
    it('should return null when no preference exists', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      expect(TelemetryOptIn.getUserPreference()).toBeNull();
    });

    it('should return false when opt-out file exists', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockOptOutFile;
      });
      expect(TelemetryOptIn.getUserPreference()).toBe(false);
    });

    it('should return true when preference file contains "enabled"', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('enabled');
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should return true when preference file contains "true"', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('true');
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should return true when preference file contains "yes"', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('yes');
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should return true when preference file contains "1"', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('1');
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should return false when preference file contains other value', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('disabled');
      expect(TelemetryOptIn.getUserPreference()).toBe(false);
    });

    it('should prefer opt-out file over preference file', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      (fs.readFileSync as jest.Mock).mockReturnValue('enabled');
      expect(TelemetryOptIn.getUserPreference()).toBe(false);
    });

    it('should handle file read errors gracefully', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Read error');
      });
      expect(TelemetryOptIn.getUserPreference()).toBeNull();
    });

    it('should check environment variable if no files exist', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'true';
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should return true for env var values: 1, yes, on', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);

      process.env.AUTOMAGIK_TELEMETRY_ENABLED = '1';
      expect(TelemetryOptIn.getUserPreference()).toBe(true);

      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'yes';
      expect(TelemetryOptIn.getUserPreference()).toBe(true);

      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'on';
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });

    it('should be case-insensitive for environment variable', () => {
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      process.env.AUTOMAGIK_TELEMETRY_ENABLED = 'TRUE';
      expect(TelemetryOptIn.getUserPreference()).toBe(true);
    });
  });

  describe('savePreference', () => {
    it('should save enabled preference to file', () => {
      TelemetryOptIn.savePreference(true);

      expect(fs.mkdirSync).toHaveBeenCalledWith(
        path.join(mockHomedir, '.automagik'),
        { recursive: true }
      );
      expect(fs.writeFileSync).toHaveBeenCalledWith(mockPreferenceFile, 'enabled');
    });

    it('should remove opt-out file when saving enabled preference', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockOptOutFile;
      });

      TelemetryOptIn.savePreference(true);

      expect(fs.unlinkSync).toHaveBeenCalledWith(mockOptOutFile);
    });

    it('should create opt-out file when saving disabled preference', () => {
      TelemetryOptIn.savePreference(false);

      expect(fs.openSync).toHaveBeenCalledWith(mockOptOutFile, 'w');
      expect(fs.closeSync).toHaveBeenCalled();
    });

    it('should remove preference file when saving disabled preference', () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });

      TelemetryOptIn.savePreference(false);

      expect(fs.unlinkSync).toHaveBeenCalledWith(mockPreferenceFile);
    });

    it('should handle errors gracefully when saving enabled', () => {
      (fs.mkdirSync as jest.Mock).mockImplementation(() => {
        throw new Error('mkdir error');
      });

      expect(() => TelemetryOptIn.savePreference(true)).not.toThrow();
    });

    it('should handle errors gracefully when saving disabled', () => {
      (fs.openSync as jest.Mock).mockImplementation(() => {
        throw new Error('open error');
      });

      expect(() => TelemetryOptIn.savePreference(false)).not.toThrow();
    });
  });

  describe('Color Support Detection', () => {
    it('should not support color when NO_COLOR is set', () => {
      process.env.NO_COLOR = '1';
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(false);
    });

    it('should support color when FORCE_COLOR is set', () => {
      process.env.FORCE_COLOR = '1';
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(true);
    });

    it('should not support color when stdout is not a TTY', () => {
      Object.defineProperty(process.stdout, 'isTTY', {
        value: false,
        writable: true,
        configurable: true,
      });
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(false);
    });

    it('should support color on Windows platform', () => {
      Object.defineProperty(process, 'platform', {
        value: 'win32',
        writable: true,
        configurable: true,
      });
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(true);
    });

    it('should support color when TERM is set', () => {
      Object.defineProperty(process, 'platform', {
        value: 'linux',
        writable: true,
        configurable: true,
      });
      process.env.TERM = 'xterm-256color';
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(true);
    });

    it('should not support color when TERM is dumb', () => {
      process.env.TERM = 'dumb';
      const supportsColor = (TelemetryOptIn as any).supportsColor();
      expect(supportsColor).toBe(false);
    });
  });

  describe('Interactive Environment Detection', () => {
    it('should be interactive when stdin and stdout are TTYs', () => {
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(true);
    });

    it('should not be interactive when stdin is not a TTY', () => {
      Object.defineProperty(process.stdin, 'isTTY', {
        value: false,
        writable: true,
        configurable: true,
      });
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });

    it('should not be interactive when stdout is not a TTY', () => {
      Object.defineProperty(process.stdout, 'isTTY', {
        value: false,
        writable: true,
        configurable: true,
      });
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });

    it('should not be interactive in CI environment', () => {
      process.env.CI = 'true';
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });

    it('should not be interactive in GITHUB_ACTIONS', () => {
      process.env.GITHUB_ACTIONS = 'true';
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });

    it('should not be interactive in TRAVIS', () => {
      process.env.TRAVIS = 'true';
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });

    it('should not be interactive in JENKINS', () => {
      process.env.JENKINS = 'true';
      const isInteractive = (TelemetryOptIn as any).isInteractive();
      expect(isInteractive).toBe(false);
    });
  });

  describe('promptUser', () => {
    let mockReadlineInterface: any;

    beforeEach(() => {
      mockReadlineInterface = {
        question: jest.fn(),
        close: jest.fn(),
      };
      (readline.createInterface as jest.Mock).mockReturnValue(mockReadlineInterface);
    });

    it('should not prompt if user already decided', async () => {
      (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
        return filePath === mockPreferenceFile;
      });
      (fs.readFileSync as jest.Mock).mockReturnValue('enabled');

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(true);
      expect(readline.createInterface).not.toHaveBeenCalled();
    });

    it('should not prompt in non-interactive environment', async () => {
      Object.defineProperty(process.stdin, 'isTTY', {
        value: false,
        writable: true,
        configurable: true,
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(false);
      expect(readline.createInterface).not.toHaveBeenCalled();
    });

    it('should prompt user and save yes response', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('y');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(true);
      expect(readline.createInterface).toHaveBeenCalled();
      expect(fs.writeFileSync).toHaveBeenCalledWith(mockPreferenceFile, 'enabled');
    });

    it('should prompt user and save yes (full word) response', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('yes');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(true);
    });

    it('should prompt user and save no response', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('n');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(false);
      expect(fs.openSync).toHaveBeenCalledWith(mockOptOutFile, 'w');
    });

    it('should treat empty response as no', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(false);
    });

    it('should be case-insensitive', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('YES');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(true);
    });

    it('should handle user cancellation (error)', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        throw new Error('User cancelled');
      });

      const result = await TelemetryOptIn.promptUser('TestProject');

      expect(result).toBe(false);
      expect(fs.openSync).toHaveBeenCalledWith(mockOptOutFile, 'w');
    });

    it('should display project name in prompt', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('y');
      });

      await TelemetryOptIn.promptUser('MyAwesomeProject');

      expect(consoleSpy).toHaveBeenCalled();
      const calls = consoleSpy.mock.calls;
      const promptText = calls.find((call) => call[0]?.includes('MyAwesomeProject'));
      expect(promptText).toBeDefined();

      consoleSpy.mockRestore();
    });

    it('should close readline interface after response', async () => {
      mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
        callback('y');
      });

      await TelemetryOptIn.promptUser('TestProject');

      expect(mockReadlineInterface.close).toHaveBeenCalled();
    });
  });

  describe('Helper Functions', () => {
    describe('shouldPromptUser', () => {
      it('should return true when user has not decided and is interactive', () => {
        (fs.existsSync as jest.Mock).mockReturnValue(false);
        expect(shouldPromptUser('TestProject')).toBe(true);
      });

      it('should return false when user already decided', () => {
        (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
          return filePath === mockPreferenceFile;
        });
        expect(shouldPromptUser('TestProject')).toBe(false);
      });

      it('should return false in non-interactive environment', () => {
        Object.defineProperty(process.stdin, 'isTTY', {
          value: false,
          writable: true,
          configurable: true,
        });
        expect(shouldPromptUser('TestProject')).toBe(false);
      });
    });

    describe('promptUserIfNeeded', () => {
      let mockReadlineInterface: any;

      beforeEach(() => {
        mockReadlineInterface = {
          question: jest.fn(),
          close: jest.fn(),
        };
        (readline.createInterface as jest.Mock).mockReturnValue(mockReadlineInterface);
      });

      it('should prompt if needed', async () => {
        mockReadlineInterface.question.mockImplementation((prompt: string, callback: Function) => {
          callback('y');
        });

        const result = await promptUserIfNeeded('TestProject');
        expect(result).toBe(true);
      });

      it('should not prompt if user already decided', async () => {
        (fs.existsSync as jest.Mock).mockImplementation((filePath) => {
          return filePath === mockPreferenceFile;
        });
        (fs.readFileSync as jest.Mock).mockReturnValue('enabled');

        const result = await promptUserIfNeeded('TestProject');
        expect(result).toBe(true);
        expect(readline.createInterface).not.toHaveBeenCalled();
      });
    });
  });

});
