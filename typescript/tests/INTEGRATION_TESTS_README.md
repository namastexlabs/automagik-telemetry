# TypeScript Integration Tests

## Quick Start

```bash
# Install dependencies
pnpm install

# Run all tests
pnpm test

# Run only integration tests
pnpm test -- integration.test.ts

# Run with verbose output
pnpm test -- --verbose integration.test.ts
```

## Test Suites

The `integration.test.ts` file contains comprehensive integration tests:

1. **Express/Fastify Integration** - HTTP server integration
2. **High-Throughput Tests** - Sustained high load scenarios
3. **Real OTLP Collector Integration** - Network tests with real backend
4. **Memory Leak Detection** - Long-running memory stability tests
5. **Error Handling** - Graceful failure scenarios
6. **Configuration** - Custom endpoint and batch configuration

## Common Commands

```bash
# Run specific test suite
pnpm test -- --testNamePattern="Real OTLP Collector"

# Run specific test
pnpm test -- --testNamePattern="should handle burst of 1000 events"

# Enable integration tests in CI
RUN_INTEGRATION_TESTS=true pnpm test

# Run with memory profiling
node --expose-gc node_modules/.bin/jest integration.test.ts
```

## Environment Variables

- `AUTOMAGIK_TELEMETRY_ENABLED=true` - Enable telemetry (required for tests)
- `AUTOMAGIK_TELEMETRY_ENDPOINT` - Override collector endpoint
- `AUTOMAGIK_TELEMETRY_VERBOSE=true` - Enable verbose output
- `RUN_INTEGRATION_TESTS=true` - Run integration tests in CI

## CI Behavior

Integration tests are **skipped by default in CI** unless `RUN_INTEGRATION_TESTS=true` is set.

## See Also

Full documentation: `/docs/INTEGRATION_TESTS.md`
