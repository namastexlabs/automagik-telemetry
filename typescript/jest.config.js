/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests', '<rootDir>/src'],
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/index.ts', // Exclude barrel file
    '!src/schema.ts', // Exclude constants-only file
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],
  coverageThreshold: {
    global: {
      branches: 85, // ClickHouse backend has some edge cases hard to test
      functions: 98,
      lines: 99,
      statements: 99,
    },
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  verbose: true,
  forceExit: true, // Force exit after tests complete
  testTimeout: 60000, // 60 second timeout for all tests
};
