/**
 * Jest test setup and global mocks.
 *
 * This file runs before all tests to set up global mocks and utilities.
 */

// Mock the global fetch API
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();

  // Reset fetch mock to a default successful response
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
  });
});

// Clean up environment variables after each test
afterEach(() => {
  // Clean up telemetry-related env vars
  delete process.env.AUTOMAGIK_TELEMETRY_ENABLED;
  delete process.env.AUTOMAGIK_TELEMETRY_ENDPOINT;
  delete process.env.AUTOMAGIK_TELEMETRY_VERBOSE;
  delete process.env.AUTOMAGIK_TELEMETRY_TIMEOUT;
  delete process.env.CI;
  delete process.env.GITHUB_ACTIONS;
  delete process.env.TRAVIS;
  delete process.env.JENKINS;
  delete process.env.GITLAB_CI;
  delete process.env.CIRCLECI;
  delete process.env.ENVIRONMENT;
  delete process.env.NO_COLOR;
  delete process.env.FORCE_COLOR;
  delete process.env.TERM;
});
