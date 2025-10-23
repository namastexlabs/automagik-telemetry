# TypeScript Tests

📚 **Complete Testing Guide:** [docs/DEVELOPER_GUIDES/TESTING.md](../../docs/DEVELOPER_GUIDES/TESTING.md)

## Quick Start

```bash
# Run all tests
pnpm test

# Run with coverage
pnpm test -- --coverage

# Integration tests (requires ClickHouse)
RUN_INTEGRATION_TESTS=true pnpm test

# ClickHouse tests only
pnpm test:integration:clickhouse
```

## Test Files

- `*.test.ts` - Unit tests
- `integration.test.ts` - OTLP integration tests
- `clickhouse.integration.test.ts` - ClickHouse backend tests

## Documentation

- [Testing Guide](../../docs/DEVELOPER_GUIDES/TESTING.md) - Complete guide
- [Quick Reference](../../docs/USER_GUIDES/QUICK_REFERENCE.md) - Command cheat sheet
