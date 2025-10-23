# Python Tests

📚 **Complete Testing Guide:** [docs/DEVELOPER_GUIDES/TESTING.md](../../docs/DEVELOPER_GUIDES/TESTING.md)

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=automagik_telemetry --cov-report=html

# Integration tests only
pytest -m integration

# Skip integration tests
pytest -m "not integration"

# ClickHouse tests only
pytest tests/integration/test_clickhouse_integration.py
```

## Test Files

- `test_*.py` - Unit tests
- `integration/test_*.py` - Integration tests

## Documentation

- [Testing Guide](../../docs/DEVELOPER_GUIDES/TESTING.md) - Complete guide
- [Quick Reference](../../docs/USER_GUIDES/QUICK_REFERENCE.md) - Command cheat sheet
